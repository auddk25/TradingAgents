from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from datetime import datetime, timedelta
from tradingagents.agents.utils.agent_utils import (
    build_instrument_context,
    get_language_instruction,
    get_news,
    should_use_host_managed_tools,
    safe_invoke_tool,
    should_fallback_after_empty_tool_result,
)


def create_social_media_analyst(llm):
    def social_media_analyst_node(state):
        current_date = state["trade_date"]
        instrument_context = build_instrument_context(state["company_of_interest"])

        tools = [
            get_news,
        ]

        system_message = (
            "You are a sentiment analyst tasked with reviewing the past week's social-media chatter, company-specific news, and public positioning around the company. Use get_news(query, start_date, end_date) to gather company-specific news and social discussion proxies."
            + """

Return exactly these sections:
1. Thesis
2. Signal vs Noise
3. What is priced in
4. Forward Implication
5. Key Risk
6. Confidence

Separate durable positioning signals from attention noise and crowd narrative. Keep the full output under 8 bullets or 180 words. Do not add a Markdown table or long narrative.""" 
            + """Write this as a compact reasoning card rather than a long essay."""
            + get_language_instruction()
        )

        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "You are a helpful AI assistant, collaborating with other assistants."
                    " Use the provided tools to progress towards answering the question."
                    " If you are unable to fully answer, that's OK; another assistant with different tools"
                    " will help where you left off. Execute what you can to make progress."
                    " If you or any other assistant has the FINAL TRANSACTION PROPOSAL: **BUY/HOLD/SELL** or deliverable,"
                    " prefix your response with FINAL TRANSACTION PROPOSAL: **BUY/HOLD/SELL** so the team knows to stop."
                    " You have access to the following tools: {tool_names}.\n{system_message}"
                    "For your reference, the current date is {current_date}. {instrument_context}",
                ),
                MessagesPlaceholder(variable_name="messages"),
            ]
        )

        prompt = prompt.partial(system_message=system_message)
        prompt = prompt.partial(tool_names=", ".join([tool.name for tool in tools]))
        prompt = prompt.partial(current_date=current_date)
        prompt = prompt.partial(instrument_context=instrument_context)

        use_host_managed_tools = should_use_host_managed_tools()
        result = None
        if not use_host_managed_tools:
            chain = prompt | llm.bind_tools(tools)
            result = chain.invoke(state["messages"])

        if use_host_managed_tools or should_fallback_after_empty_tool_result(result):
            ticker = state["company_of_interest"]
            start_date = (datetime.strptime(current_date, "%Y-%m-%d") - timedelta(days=7)).date().isoformat()
            social_proxy_news = safe_invoke_tool(
                get_news,
                ticker=ticker,
                start_date=start_date,
                end_date=current_date,
            )
            fallback_prompt = "\n".join(
                [
                    system_message,
                    f"Current date: {current_date}.",
                    instrument_context,
                    "The native tool-calling path returned no tool calls and no content. Fall back to the pre-fetched data below.",
                    f"Company news and social proxy context:\n{social_proxy_news}",
                    "Now write the final compact reasoning card directly.",
                ]
            )
            result = llm.invoke(fallback_prompt)

        report = str(getattr(result, "content", "") or "").strip() if len(getattr(result, "tool_calls", []) or []) == 0 else ""

        return {
            "messages": [result],
            "sentiment_report": report,
        }

    return social_media_analyst_node
