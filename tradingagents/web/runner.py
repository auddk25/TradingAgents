from __future__ import annotations

import contextlib
import json
import queue
import sys
import threading
import traceback
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Literal

from cli.main import save_report_to_disk
from tradingagents.default_config import DEFAULT_CONFIG
from tradingagents.graph.trading_graph import TradingAgentsGraph
from tradingagents.web.models import RunEvent, RunRecord, SubmissionPayload, preflight_validate_submission, new_submission_id
from tradingagents.web.storage import create_run_dir, write_json_file

RUNS: dict[str, "WebRun"] = {}
TERMINAL_STATUSES = {"completed", "failed"}
ANALYST_STAGE = "分析师团队"
RESEARCH_STAGE = "研究团队"
TRADING_STAGE = "交易团队"
RISK_STAGE = "风险管理"
PORTFOLIO_STAGE = "投资组合决策"
ANALYST_REPORT_FIELDS = {
    "market": ("market_report", "市场分析师"),
    "social": ("sentiment_report", "社交媒体分析师"),
    "news": ("news_report", "新闻分析师"),
    "fundamentals": ("fundamentals_report", "基本面分析师"),
}


class TeeWriter:
    def __init__(self, *streams):
        self.streams = streams

    def write(self, data):
        for stream in self.streams:
            stream.write(data)
        return len(data)

    def flush(self):
        for stream in self.streams:
            stream.flush()


@dataclass
class WebRun:
    run_id: str
    payload: SubmissionPayload
    run_dir: Path
    status: Literal["queued", "running", "completed", "failed"] = "queued"
    current_step: str | None = None
    report_path: str | None = None
    error_path: str | None = None
    stdout_path: str | None = None
    stderr_path: str | None = None
    result_markdown: str | None = None
    events: list[RunEvent] = field(default_factory=list)
    event_queue: queue.Queue[RunEvent | None] = field(default_factory=queue.Queue)
    last_partial_content: dict[str, str] = field(default_factory=dict)

    @classmethod
    def create(cls, payload: SubmissionPayload) -> "WebRun":
        run_id = new_submission_id()
        run_dir = create_run_dir(payload, run_id)
        run = cls(run_id=run_id, payload=payload, run_dir=run_dir)
        run.run_dir.mkdir(parents=True, exist_ok=True)
        write_json_file(run.run_dir / "input.json", payload.model_dump(mode="json"))
        run.stdout_path = str(run.run_dir / "stdout.log")
        run.stderr_path = str(run.run_dir / "stderr.log")
        Path(run.stdout_path).write_text("", encoding="utf-8")
        Path(run.stderr_path).write_text("", encoding="utf-8")
        run.emit_event("run_created", "运行已创建，等待执行。")
        return run

    def to_record(self) -> RunRecord:
        return RunRecord(
            run_id=self.run_id,
            status=self.status,
            run_dir=str(self.run_dir),
            current_step=self.current_step,
            report_path=self.report_path,
            error_path=self.error_path,
            stdout_path=self.stdout_path,
            stderr_path=self.stderr_path,
        )

    def emit_event(
        self,
        event: str,
        message: str,
        *,
        step: str | None = None,
        data: dict[str, Any] | None = None,
    ) -> RunEvent:
        event_obj = RunEvent(
            event=event,
            step=step,
            message=message,
            timestamp=datetime.now().isoformat(timespec="seconds"),
            data=data or {},
        )
        self.events.append(event_obj)
        self.event_queue.put(event_obj)
        self._append_event_log(event_obj)
        return event_obj

    def _append_event_log(self, event: RunEvent) -> None:
        line = {
            "event": event.event,
            "step": event.step,
            "message": event.message,
            "timestamp": event.timestamp,
            "data": event.data,
        }
        with (self.run_dir / "events.log").open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(line, ensure_ascii=False) + "\n")

    def set_running(self, step: str | None = None, message: str | None = None) -> None:
        self.status = "running"
        if step:
            self.current_step = step
        if message:
            self.emit_event("step_started", message, step=step)

    def write_partial(self, name: str, content: str) -> Path:
        previous = self.last_partial_content.get(name)
        if previous == content:
            return self.run_dir / "partials" / f"{name}.md"
        partial_dir = self.run_dir / "partials"
        partial_dir.mkdir(parents=True, exist_ok=True)
        path = partial_dir / f"{name}.md"
        path.write_text(content, encoding="utf-8")
        self.last_partial_content[name] = content
        return path

    def write_stdout(self, content: str) -> None:
        if self.stdout_path is None:
            self.stdout_path = str(self.run_dir / "stdout.log")
        with Path(self.stdout_path).open("a", encoding="utf-8") as handle:
            handle.write(content)

    def write_stderr(self, content: str) -> None:
        if self.stderr_path is None:
            self.stderr_path = str(self.run_dir / "stderr.log")
        with Path(self.stderr_path).open("a", encoding="utf-8") as handle:
            handle.write(content)

    def write_markdown_report(self, markdown: str) -> str:
        path = self.run_dir / "complete_report.md"
        path.write_text(markdown, encoding="utf-8")
        self.report_path = str(path)
        self.result_markdown = markdown
        return str(path)

    def mark_completed(
        self,
        *,
        markdown: str,
        report_path: str | None = None,
        memory_summary_path: str | None = None,
        memory_snapshot_path: str | None = None,
    ) -> None:
        self.result_markdown = markdown
        if report_path:
            self.report_path = report_path
        self.emit_event(
            "run_completed",
            "分析完成。",
            step=self.current_step,
            data={
                "run_id": self.run_id,
                "run_dir": str(self.run_dir),
                "report_path": self.report_path,
                "memory_summary_path": memory_summary_path,
                "memory_snapshot_path": memory_snapshot_path,
                "markdown": markdown,
                "stdout_path": self.stdout_path,
                "stderr_path": self.stderr_path,
            },
        )
        self.status = "completed"
        self.event_queue.put(None)

    def mark_failed(self, exc: BaseException) -> None:
        tb = traceback.format_exc()
        error_path = self.run_dir / "error.md"
        error_path.write_text(
            f"# Run Failed\n\n- 当前步骤：{self.current_step or '未知'}\n- 异常类型：{exc.__class__.__name__}\n- 异常消息：{exc}\n\n```text\n{tb}\n```\n",
            encoding="utf-8",
        )
        self.error_path = str(error_path)
        self.write_stderr(tb)
        self.emit_event(
            "run_failed",
            f"运行失败：{exc}",
            step=self.current_step,
            data={
                "run_id": self.run_id,
                "run_dir": str(self.run_dir),
                "error_path": self.error_path,
                "stdout_path": self.stdout_path,
                "stderr_path": self.stderr_path,
                "traceback": tb,
            },
        )
        self.status = "failed"
        self.event_queue.put(None)


def start_run(payload: SubmissionPayload, *, skip_preflight: bool = False) -> WebRun:
    if not skip_preflight:
        preflight_validate_submission(payload)
    run = WebRun.create(payload)
    RUNS[run.run_id] = run
    thread = threading.Thread(target=_run_job_wrapper, args=(run,), daemon=True)
    thread.start()
    return run


def get_run(run_id: str) -> WebRun | None:
    return RUNS.get(run_id)


def _run_job_wrapper(run: WebRun) -> None:
    run.status = "running"
    try:
        run_analysis_job(run)
        if run.status not in TERMINAL_STATUSES:
            if run.result_markdown:
                run.mark_completed(markdown=run.result_markdown, report_path=run.report_path)
            else:
                report_path = run.write_markdown_report("# 分析完成\n\n当前运行没有返回报告内容。")
                run.mark_completed(markdown="# 分析完成\n\n当前运行没有返回报告内容。", report_path=report_path)
    except Exception as exc:  # pragma: no cover - validated through API tests
        run.mark_failed(exc)


def run_analysis_job(run: WebRun) -> None:
    payload = run.payload
    config = DEFAULT_CONFIG.copy()
    config["max_debate_rounds"] = payload.research_depth
    config["max_risk_discuss_rounds"] = payload.research_depth
    config["quick_think_llm"] = payload.quick_think_llm
    config["deep_think_llm"] = payload.deep_think_llm
    config["backend_url"] = payload.backend_url
    config["llm_provider"] = payload.llm_provider.lower()
    config["google_thinking_level"] = payload.google_thinking_level
    config["openai_reasoning_effort"] = payload.openai_reasoning_effort
    config["anthropic_effort"] = payload.anthropic_effort
    config["output_language"] = payload.output_language
    config["results_dir"] = str(run.run_dir / "engine_results")
    config["data_cache_dir"] = str(Path.cwd() / ".tradingagents_cache")

    selected_analysts = [analyst.value if hasattr(analyst, "value") else str(analyst) for analyst in payload.analysts]
    graph = TradingAgentsGraph(selected_analysts=selected_analysts, config=config, debug=False)

    stage_state = {
        "analysts_started": False,
        "analysts_completed": False,
        "analyst_reports": set(),
        "research_started": False,
        "research_completed": False,
        "trading_started": False,
        "trading_completed": False,
        "risk_started": False,
        "risk_completed": False,
        "portfolio_started": False,
        "portfolio_completed": False,
    }

    init_agent_state = graph.prepare_initial_state(payload.ticker, payload.analysis_date.isoformat())
    args = graph.propagator.get_graph_args()
    final_state = None

    stdout_path = Path(run.stdout_path or run.run_dir / "stdout.log")
    stderr_path = Path(run.stderr_path or run.run_dir / "stderr.log")

    with (
        stdout_path.open("a", encoding="utf-8") as stdout_handle,
        stderr_path.open("a", encoding="utf-8") as stderr_handle,
        contextlib.redirect_stdout(TeeWriter(sys.stdout, stdout_handle)),
        contextlib.redirect_stderr(TeeWriter(sys.stderr, stderr_handle)),
    ):
        run.emit_event("step_started", "分析师团队开始分析。", step=ANALYST_STAGE)
        run.current_step = ANALYST_STAGE
        for chunk in graph.graph.stream(init_agent_state, **args):
            final_state = chunk
            process_stream_chunk(run, chunk, selected_analysts, stage_state)

    if final_state is None:
        raise RuntimeError("TradingAgents did not return any final state.")

    report_path = save_report_to_disk(final_state, payload.ticker, run.run_dir)
    markdown = Path(report_path).read_text(encoding="utf-8")
    summary_paths = graph.persist_run_summary(
        payload.ticker,
        payload.analysis_date.isoformat(),
        final_state,
        run_id=run.run_id,
        report_path=str(report_path),
        error_path=run.error_path,
    )
    run.current_step = PORTFOLIO_STAGE
    if not stage_state["portfolio_completed"]:
        run.emit_event("step_completed", "投资组合决策完成。", step=PORTFOLIO_STAGE)
    run.mark_completed(
        markdown=markdown,
        report_path=str(report_path),
        memory_summary_path=str(summary_paths["latest_summary"]),
        memory_snapshot_path=str(summary_paths["snapshot"]),
    )


def process_stream_chunk(run: WebRun, chunk: dict[str, Any], selected_analysts: list[str], stage_state: dict[str, Any]) -> None:
    persist_analyst_reports(run, chunk, selected_analysts, stage_state)
    persist_research_step(run, chunk, stage_state)
    persist_trading_step(run, chunk, stage_state)
    persist_risk_and_portfolio_steps(run, chunk, stage_state)


def persist_analyst_reports(run: WebRun, chunk: dict[str, Any], selected_analysts: list[str], stage_state: dict[str, Any]) -> None:
    completed_reports = stage_state["analyst_reports"]
    for analyst_key in selected_analysts:
        if analyst_key not in ANALYST_REPORT_FIELDS:
            continue
        field_name, analyst_label = ANALYST_REPORT_FIELDS[analyst_key]
        content = chunk.get(field_name)
        if not content:
            continue
        run.write_partial(field_name, str(content))
        if field_name not in completed_reports:
            completed_reports.add(field_name)
            run.current_step = ANALYST_STAGE
            run.emit_event("step_updated", f"{analyst_label}已完成。", step=ANALYST_STAGE)

    expected_fields = {
        ANALYST_REPORT_FIELDS[analyst_key][0]
        for analyst_key in selected_analysts
        if analyst_key in ANALYST_REPORT_FIELDS
    }
    if expected_fields and expected_fields.issubset(completed_reports) and not stage_state["analysts_completed"]:
        stage_state["analysts_completed"] = True
        run.current_step = ANALYST_STAGE
        run.emit_event("step_completed", "分析师团队完成。", step=ANALYST_STAGE)


def persist_research_step(run: WebRun, chunk: dict[str, Any], stage_state: dict[str, Any]) -> None:
    debate_state = chunk.get("investment_debate_state")
    if not debate_state:
        return

    judge_decision = str(debate_state.get("judge_decision", "")).strip()

    if not stage_state["research_started"]:
        stage_state["research_started"] = True
        run.current_step = RESEARCH_STAGE
        run.emit_event("step_started", "研究团队开始辩论。", step=RESEARCH_STAGE)

    if judge_decision:
        run.write_partial("research_manager", judge_decision)

    if judge_decision and not stage_state["research_completed"]:
        stage_state["research_completed"] = True
        run.current_step = RESEARCH_STAGE
        run.emit_event("step_completed", "研究团队完成。", step=RESEARCH_STAGE)


def persist_trading_step(run: WebRun, chunk: dict[str, Any], stage_state: dict[str, Any]) -> None:
    trader_plan = str(chunk.get("trader_investment_plan", "")).strip()
    if not trader_plan:
        return

    if not stage_state["trading_started"]:
        stage_state["trading_started"] = True
        run.current_step = TRADING_STAGE
        run.emit_event("step_started", "交易团队开始制定计划。", step=TRADING_STAGE)

    run.write_partial("trader_investment_plan", trader_plan)

    if not stage_state["trading_completed"]:
        stage_state["trading_completed"] = True
        run.current_step = TRADING_STAGE
        run.emit_event("step_completed", "交易团队完成。", step=TRADING_STAGE)


def persist_risk_and_portfolio_steps(run: WebRun, chunk: dict[str, Any], stage_state: dict[str, Any]) -> None:
    risk_state = chunk.get("risk_debate_state")
    if not risk_state:
        return

    judge_decision = str(risk_state.get("judge_decision", "")).strip()

    if not stage_state["risk_started"]:
        stage_state["risk_started"] = True
        run.current_step = RISK_STAGE
        run.emit_event("step_started", "风险管理开始评估。", step=RISK_STAGE)

    if judge_decision:
        run.write_partial("portfolio_manager", judge_decision)
        if not stage_state["risk_completed"]:
            stage_state["risk_completed"] = True
            run.current_step = RISK_STAGE
            run.emit_event("step_completed", "风险管理完成。", step=RISK_STAGE)
        if not stage_state["portfolio_started"]:
            stage_state["portfolio_started"] = True
            run.current_step = PORTFOLIO_STAGE
            run.emit_event("step_started", "投资组合经理正在生成最终决策。", step=PORTFOLIO_STAGE)
