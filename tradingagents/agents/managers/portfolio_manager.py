from tradingagents.agents.utils.agent_utils import (
    build_instrument_context,
    get_language_instruction,
)
from tradingagents.agents.utils.summary_memory import build_reference_summary_block


def create_portfolio_manager(llm, memory):
    def portfolio_manager_node(state) -> dict:
        instrument_context = build_instrument_context(state["company_of_interest"])

        history = state["risk_debate_state"]["history"]
        risk_debate_state = state["risk_debate_state"]
        market_research_report = state["market_report"]
        news_report = state["news_report"]
        fundamentals_report = state["fundamentals_report"]
        sentiment_report = state["sentiment_report"]
        research_plan = state["investment_plan"]
        trader_plan = state["trader_investment_plan"]
        prior_run_summary = build_reference_summary_block(state.get("prior_run_summary", ""))

        prompt_parts = [
            "As the Portfolio Manager, synthesize the risk analysts' debate and deliver the final decision.",
            "Treat the current evidence as primary. This is a fresh run.",
            "If current evidence conflicts with the prior summary, prefer current evidence.",
        ]

        if prior_run_summary:
            prompt_parts.append(prior_run_summary)

        prompt_parts.extend(
            [
                f"Instrument context:\n{instrument_context}",
                "Current evidence:",
                f"- Research Manager investment plan: {research_plan}",
                f"- Trader transaction proposal: {trader_plan}",
                f"- Market report: {market_research_report}",
                f"- Sentiment report: {sentiment_report}",
                f"- News report: {news_report}",
                f"- Fundamentals report: {fundamentals_report}",
                "",
                "Required Output Structure:",
                "1. Rating",
                "2. Chinese Summary",
                "3. Short-Term View",
                "4. Long-Term Ownership View",
                "5. What The Market Is Pricing",
                "6. Gap Between Price And Future Path",
                "7. Portfolio Action",
                "8. Risk Triggers",
                "",
                "Rating Scale (use exactly one): Buy, Overweight, Hold, Underweight, Sell.",
                "Portfolio Action must choose exactly one of: Exit fully, Trim position, Hold core position, Add gradually, Wait for better entry.",
                "Rules:",
                "- Separate short-term tactical action from long-term ownership judgment.",
                "- Explain the market pricing gap against the likely future business path.",
                "- Keep the answer concise, decisive, and evidence-based.",
                f"Risk analysts' debate history:\n{history}",
                f"{get_language_instruction()}",
            ]
        )

        prompt = "\n".join(part for part in prompt_parts if part)

        response = llm.invoke(prompt)

        new_risk_debate_state = {
            "judge_decision": response.content,
            "history": risk_debate_state["history"],
            "aggressive_history": risk_debate_state["aggressive_history"],
            "conservative_history": risk_debate_state["conservative_history"],
            "neutral_history": risk_debate_state["neutral_history"],
            "latest_speaker": "Judge",
            "current_aggressive_response": risk_debate_state["current_aggressive_response"],
            "current_conservative_response": risk_debate_state["current_conservative_response"],
            "current_neutral_response": risk_debate_state["current_neutral_response"],
            "count": risk_debate_state["count"],
        }

        return {
            "risk_debate_state": new_risk_debate_state,
            "final_trade_decision": response.content,
        }

    return portfolio_manager_node

