from tradingagents.agents.utils.agent_utils import (
    build_instrument_context,
    get_language_instruction,
)
from tradingagents.agents.utils.summary_memory import build_reference_summary_block


def create_research_manager(llm, memory):
    def research_manager_node(state) -> dict:
        instrument_context = build_instrument_context(state["company_of_interest"])
        history = state["investment_debate_state"].get("history", "")
        market_research_report = state["market_report"]
        sentiment_report = state["sentiment_report"]
        news_report = state["news_report"]
        fundamentals_report = state["fundamentals_report"]
        prior_run_summary = build_reference_summary_block(state.get("prior_run_summary", ""))

        prompt_parts = [
            "As the research manager and debate facilitator, synthesize the current run into a compact forward-looking investment view.",
            "Treat the current evidence as primary. Do not reuse prior debate transcripts as authority.",
            "If current evidence conflicts with the prior summary, prefer current evidence.",
            "Do not moderate for the sake of harmony.",
            "Explicitly say which side of the debate is more convincing and why.",
            "If both sides are weak, say that plainly.",
        ]

        if prior_run_summary:
            prompt_parts.append(prior_run_summary)

        prompt_parts.extend(
            [
                "Required output:",
                "1. Future Business Path",
                "2. What The Market Is Pricing",
                "3. What Could Beat Expectations",
                "4. What Could Miss Expectations",
                "5. Strategic Ownership View",
                "",
                "Rules:",
                "- Separate the next 4-8 quarter path from the long-term ownership case.",
                "- Focus on what is priced in versus what the business can still deliver.",
                "- Keep the answer concise and structured for a downstream trader.",
                "",
                f"Current market evidence:\n- Market report: {market_research_report}\n- Sentiment report: {sentiment_report}\n- News report: {news_report}\n- Fundamentals report: {fundamentals_report}",
                f"Debate history:\n{history}",
                f"{instrument_context}",
            ]
        )

        prompt = "\n".join(part for part in prompt_parts if part)
        prompt += get_language_instruction()

        response = llm.invoke(prompt)

        new_investment_debate_state = {
            "judge_decision": response.content,
            "history": state["investment_debate_state"].get("history", ""),
            "bear_history": state["investment_debate_state"].get("bear_history", ""),
            "bull_history": state["investment_debate_state"].get("bull_history", ""),
            "current_response": response.content,
            "count": state["investment_debate_state"]["count"],
        }

        return {
            "investment_debate_state": new_investment_debate_state,
            "investment_plan": response.content,
        }

    return research_manager_node
