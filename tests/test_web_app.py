from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Iterator

import pytest
from fastapi.testclient import TestClient

from cli.utils import ANALYST_ORDER
from tradingagents.default_config import get_provider_base_url
from tradingagents.llm_clients.model_catalog import get_model_options
from tradingagents.web.app import app
from tradingagents.web import runner as web_runner
from tradingagents.web.models import UnsupportedModelError


@pytest.fixture
def client() -> TestClient:
    web_runner.RUNS.clear()
    return TestClient(app)


@pytest.fixture(autouse=True)
def bypass_runtime_model_probe(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(
        "tradingagents.web.models.probe_runtime_model_availability",
        lambda payload, model, field_label: None,
    )


@pytest.fixture
def sample_payload() -> dict:
    return {
        "ticker": "spy",
        "analysis_date": "2026-04-19",
        "output_language": "Chinese",
        "analysts": ["market", "news", "fundamentals"],
        "research_depth": 1,
        "llm_provider": "openai",
        "backend_url": "https://api.openai.com/v1",
        "quick_think_llm": "gpt-5.4-mini",
        "deep_think_llm": "gpt-5.4",
        "google_thinking_level": "high",
        "openai_reasoning_effort": "high",
        "anthropic_effort": "high",
    }


@pytest.fixture
def form_options_response(client: TestClient):
    response = client.get("/api/form-options")
    assert response.status_code == 200
    return response.json()


def test_form_options_exposes_cli_equivalents_and_defaults(form_options_response):
    payload = form_options_response

    assert set(payload) == {"defaults", "options", "field_help"}

    defaults = payload["defaults"]
    assert defaults == {
        "ticker": "SPY",
        "analysis_date": date.today().isoformat(),
        "output_language": "English",
        "analysts": [analyst.value for _, analyst in ANALYST_ORDER],
        "research_depth": 1,
        "llm_provider": "openai",
        "backend_url": get_provider_base_url("openai"),
        "quick_think_llm": "gpt-5.4",
        "deep_think_llm": get_model_options("openai", "deep")[0][1],
        "google_thinking_level": "high",
        "openai_reasoning_effort": "medium",
        "anthropic_effort": "high",
        "main_model": "gpt-5.4",
    }

    options = payload["options"]
    assert [item["label"] for item in options["providers"]] == [
        "OpenAI",
        "Google",
        "Anthropic",
        "xAI",
        "DeepSeek",
        "Qwen",
        "GLM",
        "OpenRouter",
        "Azure OpenAI",
        "Ollama",
    ]
    assert [item["value"] for item in options["providers"]] == [
        "openai",
        "google",
        "anthropic",
        "xai",
        "deepseek",
        "qwen",
        "glm",
        "openrouter",
        "azure",
        "ollama",
    ]
    assert [item["label"] for item in options["analysts"]] == [
        "市场分析师",
        "社交媒体分析师",
        "新闻分析师",
        "基本面分析师",
    ]
    assert [item["value"] for item in options["analysts"]] == [
        analyst.value for _, analyst in ANALYST_ORDER
    ]
    assert [item["label"] for item in options["research_depths"]] == [
        "浅度 - 快速研究，较少辩论和策略讨论轮次",
        "中等 - 平衡研究深度与讨论轮次",
        "深度 - 全面研究，包含更深入的辩论和策略讨论",
    ]
    assert [item["value"] for item in options["research_depths"]] == [1, 3, 5]
    assert options["output_languages"] == [
        {"label": "英文", "value": "English"},
        {"label": "中文", "value": "Chinese"},
        {"label": "日文", "value": "Japanese"},
        {"label": "韩文", "value": "Korean"},
        {"label": "印地语", "value": "Hindi"},
        {"label": "西班牙语", "value": "Spanish"},
        {"label": "葡萄牙语", "value": "Portuguese"},
        {"label": "法语", "value": "French"},
        {"label": "德语", "value": "German"},
        {"label": "阿拉伯语", "value": "Arabic"},
        {"label": "俄语", "value": "Russian"},
    ]
    assert options["google_thinking_levels"] == [
        {"label": "高", "value": "high"},
        {"label": "最小", "value": "minimal"},
    ]
    assert options["openai_reasoning_efforts"] == [
        {"label": "中等", "value": "medium"},
        {"label": "高", "value": "high"},
        {"label": "低", "value": "low"},
    ]
    assert options["anthropic_efforts"] == [
        {"label": "高", "value": "high"},
        {"label": "中等", "value": "medium"},
        {"label": "低", "value": "low"},
    ]
    assert payload["field_help"] == {
        "research_depth": "控制研究团队和风险团队的讨论轮次，不是模型能力等级。",
        "main_model": "默认给整条链路使用。未展开高级选项时，快速模型和深度模型都跟随它。",
        "quick_think_llm": "给分析师、交易员、风险辩手等高频节点使用。",
        "deep_think_llm": "给研究经理和投资组合经理等最终裁决节点使用。",
        "google_thinking_level": "控制 Google 系列模型的单次思考预算。",
        "openai_reasoning_effort": "控制 OpenAI 推理调用的推理强度，不等于研究轮次。",
        "anthropic_effort": "控制 Anthropic 推理调用的思考强度，不等于研究轮次。",
    }
    assert options["model_options"]["openai"]["quick"][0]["label"].startswith("GPT-5.4 Mini - ")
    assert "快速" in options["model_options"]["openai"]["quick"][0]["label"]
    assert options["model_options"]["openrouter"]["quick"] == [
        {"label": "自定义模型 ID", "value": ""}
    ]
    assert options["model_options"]["azure"]["deep"] == [
        {"label": "自定义部署名称", "value": ""}
    ]


def test_root_page_is_localized_in_chinese(client: TestClient):
    response = client.get("/")

    assert response.status_code == 200
    assert "本地参数提交面板" in response.text
    assert "提交参数" in response.text
    assert "运行状态" in response.text
    assert "主模型" in response.text
    assert "高级选项" in response.text
    assert "结果文件路径" in response.text
    assert "错误文件路径" in response.text
    assert "Markdown 结果" not in response.text
    assert "错误详情" not in response.text


def test_submission_persists_normalized_payload_in_repo_local_web_runs_dir(
    client: TestClient, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, sample_payload: dict
):
    monkeypatch.chdir(tmp_path)

    response = client.post("/api/submissions", json=sample_payload)
    assert response.status_code == 200

    body = response.json()
    assert body["submission_id"]
    assert body["saved_path"].startswith(str(tmp_path / "web_runs"))
    assert body["saved_path"].endswith(".json")
    assert body["payload"] == {
        "ticker": "SPY",
        "analysis_date": "2026-04-19",
        "output_language": "Chinese",
        "analysts": ["market", "news", "fundamentals"],
        "research_depth": 1,
        "llm_provider": "openai",
        "backend_url": "https://api.openai.com/v1",
        "quick_think_llm": "gpt-5.4-mini",
        "deep_think_llm": "gpt-5.4",
        "google_thinking_level": "high",
        "openai_reasoning_effort": "high",
        "anthropic_effort": "high",
    }

    saved_path = Path(body["saved_path"])
    assert saved_path.is_file()

    files = list((tmp_path / "web_runs").rglob("*.json"))
    assert len(files) == 1
    with files[0].open("r", encoding="utf-8") as handle:
        assert json.load(handle) == body["payload"]


def parse_sse_events(chunks: Iterator[str]) -> list[tuple[str, dict]]:
    buffer = "".join(chunks)
    events: list[tuple[str, dict]] = []
    for block in buffer.strip().split("\n\n"):
        event_name = None
        data = None
        for line in block.splitlines():
            if line.startswith("event: "):
                event_name = line.removeprefix("event: ").strip()
            elif line.startswith("data: "):
                data = json.loads(line.removeprefix("data: ").strip())
        if event_name and data is not None:
            events.append((event_name, data))
    return events


def wait_for_terminal_status(client: TestClient, run_id: str) -> dict:
    for _ in range(50):
        response = client.get(f"/api/runs/{run_id}")
        assert response.status_code == 200
        body = response.json()
        if body["status"] in {"completed", "failed"}:
            return body
    raise AssertionError("Run did not reach a terminal state in time.")


def test_run_creation_uses_repo_local_versioned_directory(
    client: TestClient, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, sample_payload: dict
):
    monkeypatch.chdir(tmp_path)

    def fake_run_analysis_job(run):
        run.emit_event("step_started", "分析师团队开始", step="分析师团队")
        run.write_partial("market_report", "# 市场分析")
        report_path = run.write_markdown_report("# 最终报告\n\n内容")
        run.mark_completed(markdown="# 最终报告\n\n内容", report_path=report_path)

    monkeypatch.setattr(web_runner, "run_analysis_job", fake_run_analysis_job)

    response = client.post("/api/runs", json=sample_payload)
    assert response.status_code == 200

    body = response.json()
    run_dir = Path(body["run_dir"])
    assert body["run_id"]
    assert body["status"] in {"queued", "running", "completed"}
    body = wait_for_terminal_status(client, body["run_id"])
    run_dir = Path(body["run_dir"])
    assert run_dir.is_dir()
    assert str(run_dir).startswith(str(tmp_path / "web_runs" / "SPY" / "2026-04-19"))
    assert (run_dir / "input.json").is_file()
    assert (run_dir / "partials" / "market_report.md").is_file()
    assert (run_dir / "complete_report.md").is_file()


def test_run_events_stream_created_progress_and_completion(
    client: TestClient, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, sample_payload: dict
):
    monkeypatch.chdir(tmp_path)

    def fake_run_analysis_job(run):
        run.emit_event("step_started", "分析师团队开始", step="分析师团队")
        run.emit_event("step_completed", "分析师团队完成", step="分析师团队")
        report_path = run.write_markdown_report("# 最终报告\n\n完成")
        run.mark_completed(markdown="# 最终报告\n\n完成", report_path=report_path)

    monkeypatch.setattr(web_runner, "run_analysis_job", fake_run_analysis_job)

    create_response = client.post("/api/runs", json=sample_payload)
    run_id = create_response.json()["run_id"]
    wait_for_terminal_status(client, run_id)

    with client.stream("GET", f"/api/runs/{run_id}/events") as response:
        assert response.status_code == 200
        events = parse_sse_events(response.iter_text())

    event_names = [event_name for event_name, _ in events]
    assert "run_created" in event_names
    assert "step_started" in event_names
    assert "step_completed" in event_names
    assert "run_completed" in event_names

    completed = next(data for event_name, data in events if event_name == "run_completed")
    assert completed["report_path"].endswith("complete_report.md")
    assert completed["markdown"].startswith("# 最终报告")


def test_failed_run_persists_error_logs_and_partials(
    client: TestClient, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, sample_payload: dict
):
    monkeypatch.chdir(tmp_path)

    def fake_run_analysis_job(run):
        run.emit_event("step_started", "分析师团队开始", step="分析师团队")
        run.write_partial("news_report", "# 新闻分析")
        run.write_stdout("first line\n")
        run.write_stderr("boom line\n")
        raise RuntimeError("simulated failure")

    monkeypatch.setattr(web_runner, "run_analysis_job", fake_run_analysis_job)

    create_response = client.post("/api/runs", json=sample_payload)
    run = create_response.json()
    run = wait_for_terminal_status(client, run["run_id"])
    run_dir = Path(run["run_dir"])

    with client.stream("GET", f"/api/runs/{run['run_id']}/events") as response:
        assert response.status_code == 200
        events = parse_sse_events(response.iter_text())

    failed = next(data for event_name, data in events if event_name == "run_failed")
    assert failed["error_path"].endswith("error.md")
    assert failed["stderr_path"].endswith("stderr.log")
    assert failed["stdout_path"].endswith("stdout.log")
    assert (run_dir / "error.md").is_file()
    assert (run_dir / "stdout.log").read_text(encoding="utf-8") == "first line\n"
    stderr_text = (run_dir / "stderr.log").read_text(encoding="utf-8")
    assert stderr_text.startswith("boom line\n")
    assert "RuntimeError: simulated failure" in stderr_text
    assert (run_dir / "partials" / "news_report.md").is_file()


def test_run_creation_rejects_invalid_model_name_before_background_start(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, sample_payload: dict
):
    def fail_if_called(*args, **kwargs):
        raise AssertionError("start_run should not be called for invalid models")

    monkeypatch.setattr(web_runner, "start_run", fail_if_called)

    payload = dict(sample_payload)
    payload["quick_think_llm"] = "model_not_found"

    response = client.post("/api/runs", json=payload)

    assert response.status_code == 400
    assert "模型不可用" in response.text
    assert "model_not_found" in response.text
    assert web_runner.RUNS == {}


def test_run_creation_rejects_gateway_unavailable_model_before_background_start(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, sample_payload: dict
):
    def fail_if_called(*args, **kwargs):
        raise AssertionError("start_run should not be called for gateway-unavailable models")

    def fake_probe(payload, model, field_label):
        raise UnsupportedModelError(
            f"模型不可用：{model}。当前网关不支持这个模型，请改用 gpt-5.4 或检查网关配置。"
        )

    monkeypatch.setattr(web_runner, "start_run", fail_if_called)
    monkeypatch.setattr("tradingagents.web.models.probe_runtime_model_availability", fake_probe)

    payload = dict(sample_payload)
    payload["backend_url"] = "https://gateway.example/v1"

    response = client.post("/api/runs", json=payload)

    assert response.status_code == 400
    assert "gpt-5.4-mini" in response.text
    assert "当前网关不支持这个模型" in response.text
    assert web_runner.RUNS == {}


@pytest.mark.parametrize(
    ("payload", "expected_detail"),
    [
        (
            {
                "ticker": "SPY",
                "analysis_date": "2026-04-19",
                "output_language": "English",
                "analysts": [],
                "research_depth": 1,
                "llm_provider": "openai",
                "backend_url": None,
                "quick_think_llm": "gpt-5.4-mini",
                "deep_think_llm": "gpt-5.4",
                "google_thinking_level": "high",
                "openai_reasoning_effort": "medium",
                "anthropic_effort": "high",
            },
            "At least one analyst must be selected.",
        ),
        (
            {
                "ticker": "SPY",
                "analysis_date": "2026-04-19",
                "output_language": "English",
                "analysts": ["market"],
                "research_depth": 2,
                "llm_provider": "openai",
                "backend_url": None,
                "quick_think_llm": "gpt-5.4-mini",
                "deep_think_llm": "gpt-5.4",
                "google_thinking_level": "high",
                "openai_reasoning_effort": "medium",
                "anthropic_effort": "high",
            },
            "Input should be 1, 3 or 5",
        ),
    ],
)
def test_submission_rejects_invalid_cli_equivalent_fields(
    client: TestClient, payload: dict, expected_detail: str
):
    response = client.post("/api/submissions", json=payload)

    assert response.status_code == 422
    assert expected_detail in response.text
