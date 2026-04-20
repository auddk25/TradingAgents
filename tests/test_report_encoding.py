from pathlib import Path

from cli.main import save_report_to_disk


def test_save_report_to_disk_writes_utf8_markdown(tmp_path: Path):
    final_state = {
        "market_report": "中文市场分析",
        "sentiment_report": "",
        "news_report": "",
        "fundamentals_report": "",
        "investment_debate_state": {
            "bull_history": "",
            "bear_history": "",
            "judge_decision": "",
        },
        "trader_investment_plan": "",
        "risk_debate_state": {
            "aggressive_history": "",
            "conservative_history": "",
            "neutral_history": "",
            "judge_decision": "",
        },
    }

    report_path = save_report_to_disk(final_state, "TSM", tmp_path)

    assert Path(report_path).read_text(encoding="utf-8")
    assert (tmp_path / "1_analysts" / "market.md").read_text(encoding="utf-8") == "中文市场分析"
