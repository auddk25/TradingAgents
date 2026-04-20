from langchain_core.messages import HumanMessage, RemoveMessage

# Import tools from separate utility files
from tradingagents.agents.utils.core_stock_tools import (
    get_stock_data
)
from tradingagents.agents.utils.technical_indicators_tools import (
    get_indicators
)
from tradingagents.agents.utils.fundamental_data_tools import (
    get_fundamentals,
    get_balance_sheet,
    get_cashflow,
    get_income_statement
)
from tradingagents.agents.utils.news_data_tools import (
    get_news,
    get_insider_transactions,
    get_global_news
)
from tradingagents.dataflows.config import get_config


def get_language_instruction() -> str:
    """Return a prompt instruction for the configured output language.

    Returns empty string when English (default), so no extra tokens are used.
    Only applied to user-facing agents (analysts, portfolio manager).
    Internal debate agents stay in English for reasoning quality.
    """
    lang = get_config().get("output_language", "English")
    if lang.strip().lower() == "english":
        return ""
    return f" Write your entire response in {lang}."


def get_tool_execution_mode() -> str:
    return str(get_config().get("tool_execution_mode") or "native_tools")


def should_use_host_managed_tools() -> bool:
    return get_tool_execution_mode() == "host_managed_tools"


def build_instrument_context(ticker: str) -> str:
    """Describe the exact instrument so agents preserve exchange-qualified tickers."""
    return (
        f"The instrument to analyze is `{ticker}`. "
        "Use this exact ticker in every tool call, report, and recommendation, "
        "preserving any exchange suffix (e.g. `.TO`, `.L`, `.HK`, `.T`)."
    )


def should_fallback_after_empty_tool_result(result) -> bool:
    """Detect provider failures that return neither tool calls nor text."""
    tool_calls = getattr(result, "tool_calls", None) or []
    content = getattr(result, "content", "")
    return len(tool_calls) == 0 and not str(content or "").strip()


def safe_invoke_tool(tool, **kwargs) -> str:
    """Invoke a tool directly and convert failures into prompt-visible context."""
    try:
        return str(tool.invoke(kwargs))
    except Exception as exc:  # pragma: no cover - defensive path
        tool_name = getattr(tool, "name", tool.__class__.__name__)
        return f"[{tool_name} failed: {exc}]"

def create_msg_delete():
    def delete_messages(state):
        """Clear messages and add placeholder for Anthropic compatibility"""
        messages = state["messages"]

        # Remove all messages
        removal_operations = [RemoveMessage(id=m.id) for m in messages]

        # Add a minimal placeholder message
        placeholder = HumanMessage(content="Continue")

        return {"messages": removal_operations + [placeholder]}

    return delete_messages


        
