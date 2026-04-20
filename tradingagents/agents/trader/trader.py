import functools

from tradingagents.agents.utils.agent_utils import build_instrument_context
from tradingagents.agents.utils.summary_memory import build_reference_summary_block


def create_trader(llm, memory):
    def trader_node(state, name):
        company_name = state["company_of_interest"]
        instrument_context = build_instrument_context(company_name)
        investment_plan = state["investment_plan"]
        market_research_report = state["market_report"]
        sentiment_report = state["sentiment_report"]
        news_report = state["news_report"]
        fundamentals_report = state["fundamentals_report"]
        prior_run_summary = build_reference_summary_block(state.get("prior_run_summary", ""))

        context = {
            "role": "user",
            "content": (
                f"Based on a compact investment plan for {company_name}, {instrument_context} "
                "Use the plan as a tactical input.\n\n"
                f"Proposed Investment Plan: {investment_plan}\n\n"
                f"Market report: {market_research_report}\n"
                f"Sentiment report: {sentiment_report}\n"
                f"News report: {news_report}\n"
                f"Fundamentals report: {fundamentals_report}"
            ),
        }

        messages = [
            {
                "role": "system",
                "content": "\n".join(
                    part
                    for part in [
                        "You are a trading agent focused on tactical execution.\n\n"
                        "Output only:\n"
                        "- tactical direction\n"
                        "- entry style\n"
                        "- invalidation\n"
                        "- near-term catalyst watchlist\n\n"
                        "Keep the answer concise and action-oriented. Do not restate the strategic ownership case.\n"
                        "This is a fresh run. If current evidence conflicts with the prior summary, prefer current evidence.",
                        prior_run_summary,
                        "End with a firm decision and always conclude your response with 'FINAL TRANSACTION PROPOSAL: **BUY/HOLD/SELL**'.",
                    ]
                    if part
                ),
            },
            context,
        ]

        result = llm.invoke(messages)

        return {
            "messages": [result],
            "trader_investment_plan": result.content,
            "sender": name,
        }

    return functools.partial(trader_node, name="Trader")
