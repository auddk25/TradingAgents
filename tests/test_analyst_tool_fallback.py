from __future__ import annotations

from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.runnables import RunnableLambda

from tradingagents.agents.analysts import fundamentals_analyst, market_analyst, news_analyst, social_media_analyst


class ToolStub:
    def __init__(self, name: str, output: str):
        self.name = name
        self.output = output
        self.calls: list[dict] = []

    def invoke(self, payload: dict) -> str:
        self.calls.append(payload)
        return self.output


class FakeLLM:
    def __init__(self, first_result: AIMessage, fallback_result: AIMessage):
        self.first_result = first_result
        self.fallback_result = fallback_result
        self.fallback_prompts: list[str] = []
        self.bind_tools_calls = 0

    def bind_tools(self, tools):
        self.bind_tools_calls += 1
        return RunnableLambda(lambda _: self.first_result)

    def invoke(self, prompt: str) -> AIMessage:
        self.fallback_prompts.append(prompt)
        return self.fallback_result


def _state() -> dict:
    return {
        "trade_date": "2026-04-20",
        "company_of_interest": "SPY",
        "messages": [HumanMessage(content="Analyze SPY")],
    }


def test_market_analyst_falls_back_to_host_managed_fetch(monkeypatch):
    stock = ToolStub("get_stock_data", "stock-data")
    indicators = ToolStub("get_indicators", "indicator-data")
    monkeypatch.setattr(market_analyst, "get_stock_data", stock)
    monkeypatch.setattr(market_analyst, "get_indicators", indicators)
    llm = FakeLLM(AIMessage(content="", tool_calls=[]), AIMessage(content="market fallback report", tool_calls=[]))

    result = market_analyst.create_market_analyst(llm)(_state())

    assert result["market_report"] == "market fallback report"
    assert stock.calls and indicators.calls
    assert "stock-data" in llm.fallback_prompts[0]
    assert "indicator-data" in llm.fallback_prompts[0]


def test_news_analyst_falls_back_to_host_managed_fetch(monkeypatch):
    company_news = ToolStub("get_news", "company-news")
    global_news = ToolStub("get_global_news", "global-news")
    monkeypatch.setattr(news_analyst, "get_news", company_news)
    monkeypatch.setattr(news_analyst, "get_global_news", global_news)
    llm = FakeLLM(AIMessage(content="", tool_calls=[]), AIMessage(content="news fallback report", tool_calls=[]))

    result = news_analyst.create_news_analyst(llm)(_state())

    assert result["news_report"] == "news fallback report"
    assert company_news.calls and global_news.calls
    assert "company-news" in llm.fallback_prompts[0]
    assert "global-news" in llm.fallback_prompts[0]


def test_fundamentals_analyst_falls_back_to_host_managed_fetch(monkeypatch):
    fundamentals = ToolStub("get_fundamentals", "fundamentals")
    balance_sheet = ToolStub("get_balance_sheet", "balance-sheet")
    cashflow = ToolStub("get_cashflow", "cashflow")
    income_statement = ToolStub("get_income_statement", "income-statement")
    monkeypatch.setattr(fundamentals_analyst, "get_fundamentals", fundamentals)
    monkeypatch.setattr(fundamentals_analyst, "get_balance_sheet", balance_sheet)
    monkeypatch.setattr(fundamentals_analyst, "get_cashflow", cashflow)
    monkeypatch.setattr(fundamentals_analyst, "get_income_statement", income_statement)
    llm = FakeLLM(AIMessage(content="", tool_calls=[]), AIMessage(content="fundamentals fallback report", tool_calls=[]))

    result = fundamentals_analyst.create_fundamentals_analyst(llm)(_state())

    assert result["fundamentals_report"] == "fundamentals fallback report"
    assert fundamentals.calls and balance_sheet.calls and cashflow.calls and income_statement.calls
    assert "fundamentals" in llm.fallback_prompts[0]
    assert "balance-sheet" in llm.fallback_prompts[0]


def test_social_analyst_falls_back_to_host_managed_fetch(monkeypatch):
    social_proxy = ToolStub("get_news", "social-proxy-news")
    monkeypatch.setattr(social_media_analyst, "get_news", social_proxy)
    llm = FakeLLM(AIMessage(content="", tool_calls=[]), AIMessage(content="social fallback report", tool_calls=[]))

    result = social_media_analyst.create_social_media_analyst(llm)(_state())

    assert result["sentiment_report"] == "social fallback report"
    assert social_proxy.calls
    assert "social-proxy-news" in llm.fallback_prompts[0]


def test_market_analyst_uses_host_managed_mode_without_native_tool_call(monkeypatch):
    stock = ToolStub("get_stock_data", "stock-data")
    indicators = ToolStub("get_indicators", "indicator-data")
    monkeypatch.setattr(market_analyst, "get_stock_data", stock)
    monkeypatch.setattr(market_analyst, "get_indicators", indicators)
    monkeypatch.setattr(market_analyst, "should_use_host_managed_tools", lambda: True)
    llm = FakeLLM(AIMessage(content="native report", tool_calls=[]), AIMessage(content="host managed report", tool_calls=[]))

    result = market_analyst.create_market_analyst(llm)(_state())

    assert result["market_report"] == "host managed report"
    assert llm.bind_tools_calls == 0
    assert stock.calls and indicators.calls
