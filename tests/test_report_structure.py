import json
from pathlib import Path
from types import SimpleNamespace

from tradingagents.agents.utils.summary_memory import (
    build_reference_summary_block,
    build_run_summary,
    load_latest_summary,
    persist_summary_memory,
)
from tradingagents.agents.managers.portfolio_manager import create_portfolio_manager
from tradingagents.agents.managers.research_manager import create_research_manager
from tradingagents.agents.trader.trader import create_trader
from tradingagents.default_config import DEFAULT_CONFIG
from tradingagents.graph.propagation import Propagator
from tradingagents.graph.trading_graph import TradingAgentsGraph


REPO_ROOT = Path(__file__).resolve().parents[1]


class RecordingLLM:
    def __init__(self, content: str = "stub"):
        self.calls = []
        self.content = content

    def invoke(self, prompt, config=None, **kwargs):
        self.calls.append(prompt)
        return SimpleNamespace(content=self.content)


class EmptyMemory:
    def get_memories(self, situation, n_matches=2):
        return []


def read_repo_file(relative_path: str) -> str:
    return (REPO_ROOT / relative_path).read_text(encoding="utf-8")


def make_minimal_state() -> dict:
    return {
        "company_of_interest": "TSM",
        "trade_date": "2026-04-19",
        "prior_run_summary": "",
        "market_report": "Market report",
        "sentiment_report": "Sentiment report",
        "news_report": "News report",
        "fundamentals_report": "Fundamentals report",
        "investment_plan": "Investment plan",
        "trader_investment_plan": "Trader plan",
        "investment_debate_state": {
            "history": "Debate history",
            "bull_history": "Bull history",
            "bear_history": "Bear history",
            "current_response": "Current response",
            "judge_decision": "Research manager decision",
            "count": 2,
        },
        "risk_debate_state": {
            "history": "Risk history",
            "aggressive_history": "Aggressive history",
            "conservative_history": "Conservative history",
            "neutral_history": "Neutral history",
            "latest_speaker": "Neutral",
            "current_aggressive_response": "Aggressive response",
            "current_conservative_response": "Conservative response",
            "current_neutral_response": "Neutral response",
            "judge_decision": "Portfolio manager decision",
            "count": 3,
        },
        "messages": [{"role": "user", "content": "Continue"}],
    }


def test_intermediate_agent_prompt_sources_require_compact_reasoning_cards():
    expected_fragments = {
        "tradingagents/agents/analysts/market_analyst.py": [
            "Return exactly these sections",
            "What is priced in",
            "Forward Implication",
            "Keep the full output under 8 bullets or 180 words",
        ],
        "tradingagents/agents/analysts/news_analyst.py": [
            "Return exactly these sections",
            "Catalysts",
            "What is priced in",
            "Keep the full output under 8 bullets or 180 words",
        ],
        "tradingagents/agents/analysts/social_media_analyst.py": [
            "Return exactly these sections",
            "Signal vs Noise",
            "What is priced in",
            "Keep the full output under 8 bullets or 180 words",
        ],
        "tradingagents/agents/analysts/fundamentals_analyst.py": [
            "next 4-8 quarters",
            "revenue, margin, capex, and cash flow path",
            "What is priced in",
            "Keep the full output under 8 bullets or 180 words",
        ],
        "tradingagents/agents/researchers/bull_researcher.py": [
            "Respond with at most 5 bullets",
            "Claim",
            "Forward Impact",
            "Do not write rhetorical dialogue",
        ],
        "tradingagents/agents/researchers/bear_researcher.py": [
            "Respond with at most 5 bullets",
            "Claim",
            "Forward Impact",
            "Do not write rhetorical dialogue",
        ],
        "tradingagents/agents/risk_mgmt/aggressive_debator.py": [
            "Respond with at most 5 bullets",
            "Portfolio Action",
            "Counterpoint",
            "Do not write rhetorical dialogue",
        ],
        "tradingagents/agents/risk_mgmt/conservative_debator.py": [
            "Respond with at most 5 bullets",
            "Portfolio Action",
            "Counterpoint",
            "Do not write rhetorical dialogue",
        ],
        "tradingagents/agents/risk_mgmt/neutral_debator.py": [
            "Respond with at most 5 bullets",
            "Portfolio Action",
            "Counterpoint",
            "Do not write rhetorical dialogue",
        ],
    }

    for relative_path, fragments in expected_fragments.items():
        source = read_repo_file(relative_path)
        for fragment in fragments:
            assert fragment in source, f"Missing {fragment!r} in {relative_path}"
        assert "This prior summary is reference only." not in source
        assert "prior_run_summary" not in source


def test_manager_prompt_contract_requires_future_pricing_and_horizon_split():
    llm = RecordingLLM()
    memory = EmptyMemory()
    state = make_minimal_state()
    state["prior_run_summary"] = "Prior summary: short-term trim, long-term hold."

    create_research_manager(llm, memory)(state)
    research_prompt = llm.calls[-1]
    assert "This prior summary is reference only." in research_prompt
    assert "If current evidence conflicts with the summary, prefer current evidence." in research_prompt
    assert "Future Business Path" in research_prompt
    assert "What The Market Is Pricing" in research_prompt
    assert "What Could Beat Expectations" in research_prompt
    assert "What Could Miss Expectations" in research_prompt
    assert "Strategic Ownership View" in research_prompt

    create_portfolio_manager(llm, memory)(state)
    portfolio_prompt = llm.calls[-1]
    assert "This prior summary is reference only." in portfolio_prompt
    assert "If current evidence conflicts with the summary, prefer current evidence." in portfolio_prompt
    assert "Short-Term View" in portfolio_prompt
    assert "Long-Term Ownership View" in portfolio_prompt
    assert "What The Market Is Pricing" in portfolio_prompt
    assert "Gap Between Price And Future Path" in portfolio_prompt
    assert "Chinese Summary" in portfolio_prompt
    assert "Trim position" in portfolio_prompt
    assert "Hold core position" in portfolio_prompt
    assert "Add gradually" in portfolio_prompt
    assert "Wait for better entry" in portfolio_prompt
    assert "Do not average away disagreement." in portfolio_prompt
    assert "Choose the side with the stronger evidence and say why." in portfolio_prompt
    assert "A conditional bullish tactical trade is not the same as a proven long-term ownership case." in portfolio_prompt


def test_trader_prompt_contract_focuses_on_tactical_execution_only():
    llm = RecordingLLM(content="FINAL TRANSACTION PROPOSAL: **HOLD**")
    memory = EmptyMemory()
    state = make_minimal_state()
    state["prior_run_summary"] = "Prior summary: reference only."

    create_trader(llm, memory)(state)

    messages = llm.calls[-1]
    prompt_text = "\n".join(message["content"] for message in messages)
    assert "This prior summary is reference only." in prompt_text
    assert "tactical direction" in prompt_text
    assert "entry style" in prompt_text
    assert "invalidation" in prompt_text
    assert "near-term catalyst watchlist" in prompt_text
    assert "long-term ownership" not in prompt_text.lower()
    assert "prior summary" in prompt_text.lower()
    assert "Take a view." in prompt_text
    assert "If the setup is only conditionally attractive, say so explicitly." in prompt_text
    assert "Do not soften the call into generic balance." in prompt_text


def test_debate_prompts_require_high_conviction_and_direct_rebuttals():
    bull_source = read_repo_file("tradingagents/agents/researchers/bull_researcher.py")
    bear_source = read_repo_file("tradingagents/agents/researchers/bear_researcher.py")
    aggressive_source = read_repo_file("tradingagents/agents/risk_mgmt/aggressive_debator.py")
    conservative_source = read_repo_file("tradingagents/agents/risk_mgmt/conservative_debator.py")
    neutral_source = read_repo_file("tradingagents/agents/risk_mgmt/neutral_debator.py")

    for source in (bull_source, bear_source):
        assert "high-conviction PM" in source
        assert "Attack weak assumptions" in source
        assert "Do not hedge your stance into neutrality" in source

    assert "missing upside is also a risk" in aggressive_source
    assert "Push for size when the upside asymmetry is real" in aggressive_source
    assert "Do not compromise just to sound balanced" in aggressive_source

    assert "capital preservation comes first" in conservative_source
    assert "Treat drawdown risk as more important than upside regret" in conservative_source
    assert "Do not soften the downside case" in conservative_source

    assert "Choose the base case with the strongest evidence" in neutral_source
    assert "Do not split the difference unless the evidence truly supports it" in neutral_source


def test_manager_prompts_require_forced_judgment_not_moderation():
    llm = RecordingLLM()
    memory = EmptyMemory()
    state = make_minimal_state()

    create_research_manager(llm, memory)(state)
    research_prompt = llm.calls[-1]
    assert "Do not moderate for the sake of harmony." in research_prompt
    assert "Explicitly say which side of the debate is more convincing" in research_prompt
    assert "If both sides are weak, say that plainly." in research_prompt


def test_fresh_run_state_starts_empty_and_summary_memory_defaults_empty():
    state = Propagator().create_initial_state("TSM", "2026-04-19")

    assert state["investment_debate_state"]["history"] == ""
    assert state["risk_debate_state"]["history"] == ""
    assert state.get("prior_run_summary", "") == ""


def test_trading_graph_resets_run_memory_before_each_run(monkeypatch, tmp_path: Path):
    from tradingagents.graph import trading_graph as trading_graph_module

    monkeypatch.setattr(
        trading_graph_module,
        "create_llm_client",
        lambda *args, **kwargs: SimpleNamespace(get_llm=lambda: RecordingLLM()),
    )

    config = DEFAULT_CONFIG.copy()
    config["results_dir"] = str(tmp_path / "results")
    config["data_cache_dir"] = str(tmp_path / "cache")
    config["quick_think_llm"] = "gpt-5.4"
    config["deep_think_llm"] = "gpt-5.4"

    graph = TradingAgentsGraph(config=config)
    stale_pair = [("stale-situation", "stale recommendation")]
    graph.bull_memory.add_situations(stale_pair)
    graph.bear_memory.add_situations(stale_pair)
    graph.trader_memory.add_situations(stale_pair)
    graph.invest_judge_memory.add_situations(stale_pair)
    graph.portfolio_manager_memory.add_situations(stale_pair)

    graph.reset_run_memory()

    for memory in (
        graph.bull_memory,
        graph.bear_memory,
        graph.trader_memory,
        graph.invest_judge_memory,
        graph.portfolio_manager_memory,
    ):
        assert memory.get_memories("stale-situation") == []


def test_prepare_initial_state_attaches_ticker_scoped_prior_summary(monkeypatch, tmp_path: Path):
    from tradingagents.graph import trading_graph as trading_graph_module

    monkeypatch.setattr(
        trading_graph_module,
        "create_llm_client",
        lambda *args, **kwargs: SimpleNamespace(get_llm=lambda: RecordingLLM()),
    )
    monkeypatch.chdir(tmp_path)

    config = DEFAULT_CONFIG.copy()
    config["results_dir"] = str(tmp_path / "results")
    config["data_cache_dir"] = str(tmp_path / "cache")
    config["quick_think_llm"] = "gpt-5.4"
    config["deep_think_llm"] = "gpt-5.4"

    persist_summary_memory(
        "TSM",
        "- Rating: Hold\n- Short-term action: wait\n- Long-term view: keep core position",
        metadata={},
        base_dir=tmp_path,
        timestamp="20260420_132804",
    )

    graph = TradingAgentsGraph(config=config)
    state = graph.prepare_initial_state("TSM", "2026-04-20")

    assert state["prior_run_summary"].startswith("- Rating: Hold")
    assert state["investment_debate_state"]["history"] == ""
    assert state["risk_debate_state"]["history"] == ""


def test_summary_memory_helpers_write_ticker_scoped_files(tmp_path: Path):
    ticker = "TSM"
    summary = (
        "- Rating: Hold\n"
        "- Short-term action: wait for a better entry\n"
        "- Long-term view: core ownership remains intact\n"
        "- Market pricing: stable growth and moderate multiple expansion\n"
        "- Key risk: margin compression\n"
    )
    metadata = {
        "run_id": "run-001",
        "analysis_date": "2026-04-19",
        "provider": "openai",
        "model_selection": {
            "quick_think_llm": "gpt-5.4",
            "deep_think_llm": "gpt-5.4",
        },
        "report_path": "reports/complete_report.md",
        "error_path": None,
    }

    assert load_latest_summary(ticker, base_dir=tmp_path) == ""

    paths = persist_summary_memory(
        ticker,
        summary,
        metadata=metadata,
        base_dir=tmp_path,
        timestamp="20260420_132804",
    )

    latest_path = paths["latest_summary"]
    summary_path = paths["summary"]
    snapshot_path = paths["snapshot"]

    assert latest_path.read_text(encoding="utf-8") == summary
    assert summary_path.name == "20260420_132804.md"
    assert summary_path.read_text(encoding="utf-8") == summary

    snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
    assert snapshot["ticker"] == ticker
    assert snapshot["summary_text"] == summary
    assert snapshot["report_path"] == "reports/complete_report.md"
    assert snapshot["error_path"] is None
    assert load_latest_summary(ticker, base_dir=tmp_path) == summary
    assert load_latest_summary("AAPL", base_dir=tmp_path) == ""


def test_run_summary_builder_prefers_structured_manager_sections():
    final_state = make_minimal_state()
    final_state["final_trade_decision"] = (
        "1. Rating: Hold\n\n"
        "3. Short-Term View:\nWait for a better entry.\n\n"
        "4. Long-Term Ownership View:\nCore ownership still works.\n\n"
        "5. What The Market Is Pricing:\nStable growth and modest expansion.\n\n"
        "6. Gap Between Price And Future Path:\nPrice already discounts most of the near-term upside.\n\n"
        "8. Risk Triggers:\nMargin compression or weakening demand."
    )

    summary = build_run_summary(final_state)

    assert "Short-term action" in summary
    assert "Long-term view" in summary
    assert "Market pricing" in summary
    assert "Risk" in summary or "risk" in summary.lower()
    assert "Wait for a better entry" in summary
    assert "Core ownership still works" in summary


def test_reference_summary_block_is_only_emitted_when_summary_exists():
    assert build_reference_summary_block("") == ""
    block = build_reference_summary_block("Short summary")
    assert "This prior summary is reference only." in block
    assert "If current evidence conflicts with the summary, prefer current evidence." in block
