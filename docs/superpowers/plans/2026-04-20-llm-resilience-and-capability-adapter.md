# LLM Resilience And Capability Adapter Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a shared LLM resilience wrapper and a runtime tool capability adapter so unstable gateways retry, fall back, and avoid native tool-calling where unsupported.

**Architecture:** Wrap all model invocations in a provider-aware resilience object that spaces calls, retries transient failures, and switches models when needed. Resolve tool execution mode at graph startup so tool-using analysts can choose between native tool-calling and host-managed data fetches without changing the workflow graph.

**Tech Stack:** Python, LangChain chat models, LangGraph workflow graph, pytest

---

### Task 1: Add resilience wrapper

**Files:**
- Create: `tradingagents/llm_clients/resilience.py`
- Test: `tests/test_llm_resilience.py`

- [ ] Add a shared wrapper for `invoke()` and `bind_tools().invoke()`
- [ ] Add retry classification for gateway failures and empty payloads
- [ ] Add per-provider request spacing with small delay/jitter
- [ ] Add model fallback chain handling
- [ ] Add unit tests for retry, fallback, and empty-response handling

### Task 2: Add tool capability resolver

**Files:**
- Create: `tradingagents/llm_clients/capabilities.py`
- Modify: `tradingagents/graph/trading_graph.py`
- Test: `tests/test_tool_capabilities.py`

- [ ] Resolve runtime tool mode from provider + base URL
- [ ] Store resolved `tool_execution_mode` in graph config before agent execution
- [ ] Wrap quick/deep LLMs with the resilience layer
- [ ] Add tests for official OpenAI vs custom gateway mode selection

### Task 3: Route analysts through capability adapter

**Files:**
- Modify: `tradingagents/agents/utils/agent_utils.py`
- Modify: `tradingagents/agents/analysts/market_analyst.py`
- Modify: `tradingagents/agents/analysts/news_analyst.py`
- Modify: `tradingagents/agents/analysts/fundamentals_analyst.py`
- Modify: `tradingagents/agents/analysts/social_media_analyst.py`
- Test: `tests/test_analyst_tool_fallback.py`

- [ ] Add helper for reading resolved tool mode
- [ ] Skip native `bind_tools(...)` entirely when tool mode is `host_managed_tools`
- [ ] Keep existing empty-result fallback for safety
- [ ] Extend tests to cover explicit host-managed mode, not just empty native tool results

### Task 4: Verify end-to-end behavior

**Files:**
- Modify: `docs/REFACTOR_REPORT_R3_20260420.md`

- [ ] Run targeted pytest coverage for resilience + web + analyst behavior
- [ ] Run one real web analysis smoke test if gateway budget allows
- [ ] Record verification and residual risk in refactor report
