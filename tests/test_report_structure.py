from pathlib import Path
from types import SimpleNamespace

from cli.main import save_report_to_disk
from tradingagents.agents.managers.portfolio_manager import create_portfolio_manager
from tradingagents.agents.managers.research_manager import create_research_manager
from tradingagents.agents.trader.trader import create_trader


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


def test_manager_prompt_contract_requires_future_pricing_and_horizon_split():
    llm = RecordingLLM()
    memory = EmptyMemory()
    state = make_minimal_state()

    create_research_manager(llm, memory)(state)
    research_prompt = llm.calls[-1]
    assert "Future Business Path" in research_prompt
    assert "What The Market Is Pricing" in research_prompt
    assert "What Could Beat Expectations" in research_prompt
    assert "Strategic Ownership View" in research_prompt

    create_portfolio_manager(llm, memory)(state)
    portfolio_prompt = llm.calls[-1]
    assert "Short-Term View" in portfolio_prompt
    assert "Long-Term Ownership View" in portfolio_prompt
    assert "What The Market Is Pricing" in portfolio_prompt
    assert "Gap Between Price And Future Path" in portfolio_prompt
    assert "Trim position" in portfolio_prompt
    assert "Hold core position" in portfolio_prompt
    assert "Add gradually" in portfolio_prompt


def test_trader_prompt_contract_focuses_on_tactical_execution_only():
    llm = RecordingLLM(content="FINAL TRANSACTION PROPOSAL: **HOLD**")
    memory = EmptyMemory()
    state = make_minimal_state()

    create_trader(llm, memory)(state)

    messages = llm.calls[-1]
    prompt_text = "\n".join(message["content"] for message in messages)
    assert "tactical direction" in prompt_text
    assert "entry style" in prompt_text
    assert "invalidation" in prompt_text
    assert "near-term catalyst watchlist" in prompt_text
    assert "long-term ownership" not in prompt_text.lower()


def test_saved_report_prefers_compact_manager_outputs_over_raw_debate_transcripts(tmp_path: Path):
    final_state = make_minimal_state()
    report_path = save_report_to_disk(final_state, "TSM", tmp_path)
    text = Path(report_path).read_text(encoding="utf-8")

    assert "Bull Researcher" not in text
    assert "Bear Researcher" not in text
    assert "Aggressive Analyst" not in text
    assert "Conservative Analyst" not in text
    assert "Neutral Analyst" not in text
    assert "Research Manager" in text
    assert "Portfolio Manager" in text
