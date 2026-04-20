from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from tradingagents.agents.utils.agent_utils import (
    build_instrument_context,
    get_balance_sheet,
    get_cashflow,
    get_fundamentals,
    get_income_statement,
    get_insider_transactions,
    get_language_instruction,
    should_use_host_managed_tools,
    safe_invoke_tool,
    should_fallback_after_empty_tool_result,
)


def create_fundamentals_analyst(llm):
    def fundamentals_analyst_node(state):
        current_date = state["trade_date"]
        instrument_context = build_instrument_context(state["company_of_interest"])

        tools = [
            get_fundamentals,
            get_balance_sheet,
            get_cashflow,
            get_income_statement,
        ]

        system_message = (
            "You are a fundamentals analyst tasked with connecting today's company fundamentals to the next 4-8 quarters."
            + " Use the available tools: `get_fundamentals` for comprehensive company analysis, `get_balance_sheet`, `get_cashflow`, and `get_income_statement` for specific financial statements."
            + """

State the most likely revenue, margin, capex, and cash flow path. Explain which operating outcomes are already priced in and which are not.

Return exactly these sections:
1. Thesis
2. 4-8 Quarter Path
3. What is priced in
4. Forward Implication
5. Key Risk
6. Confidence

Keep the full output under 8 bullets or 180 words. Do not write a backward-looking narrative dump or add a Markdown table.""" 
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
            fundamentals = safe_invoke_tool(
                get_fundamentals,
                ticker=ticker,
                curr_date=current_date,
            )
            balance_sheet = safe_invoke_tool(
                get_balance_sheet,
                ticker=ticker,
                freq="quarterly",
                curr_date=current_date,
            )
            cashflow = safe_invoke_tool(
                get_cashflow,
                ticker=ticker,
                freq="quarterly",
                curr_date=current_date,
            )
            income_statement = safe_invoke_tool(
                get_income_statement,
                ticker=ticker,
                freq="quarterly",
                curr_date=current_date,
            )
            fallback_prompt = "\n".join(
                [
                    system_message,
                    f"Current date: {current_date}.",
                    instrument_context,
                    "The native tool-calling path returned no tool calls and no content. Fall back to the pre-fetched data below.",
                    f"Fundamentals snapshot:\n{fundamentals}",
                    f"Balance sheet:\n{balance_sheet}",
                    f"Cash flow:\n{cashflow}",
                    f"Income statement:\n{income_statement}",
                    "Now write the final compact reasoning card directly.",
                ]
            )
            result = llm.invoke(fallback_prompt)

        report = str(getattr(result, "content", "") or "").strip() if len(getattr(result, "tool_calls", []) or []) == 0 else ""

        return {
            "messages": [result],
            "fundamentals_report": report,
        }

    return fundamentals_analyst_node
