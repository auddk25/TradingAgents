# Refactor Report R3 - 2026-04-20

## Scope

This refactor added a two-layer gateway hardening path:

- a shared LLM resilience wrapper for retry, request spacing, and model fallback
- a runtime capability adapter that switches custom OpenAI-compatible gateways to host-managed tool execution

## Files Added

- `docs/superpowers/specs/2026-04-20-llm-resilience-and-capability-adapter-design.md`
- `docs/superpowers/plans/2026-04-20-llm-resilience-and-capability-adapter.md`
- `tradingagents/llm_clients/capabilities.py`
- `tradingagents/llm_clients/resilience.py`
- `tests/test_llm_resilience.py`
- `tests/test_tool_capabilities.py`

## Files Updated

- `tradingagents/default_config.py`
- `tradingagents/graph/trading_graph.py`
- `tradingagents/agents/utils/agent_utils.py`
- `tradingagents/agents/analysts/market_analyst.py`
- `tradingagents/agents/analysts/news_analyst.py`
- `tradingagents/agents/analysts/fundamentals_analyst.py`
- `tradingagents/agents/analysts/social_media_analyst.py`
- `tests/test_analyst_tool_fallback.py`

## Behavior Changes

- All quick/deep model calls created by `TradingAgentsGraph` now use `ResilientLLM`.
- Custom OpenAI-compatible gateways default to `host_managed_tools` instead of native tool-calling.
- Analyst nodes no longer attempt native tool-calling on gateways marked `host_managed_tools`.
- Retryable gateway failures and empty assistant payloads now trigger retry/fallback instead of silently propagating as empty reports.

## Risks

- Model fallback currently has a strong opinion only for the custom `openai` gateway path; other providers mainly gain retry and spacing, not rich fallback chains.
- Host-managed tools reduce gateway instability but increase deterministic tool traffic from the app process.
- Real external gateway behavior is still subject to upstream routing variance.

## Verification

- `uv run --with pytest python -m pytest -q tests/test_llm_resilience.py tests/test_tool_capabilities.py tests/test_analyst_tool_fallback.py`
- `uv run --with pytest python -m pytest -q tests/test_web_app.py tests/test_default_config.py tests/test_report_structure.py`
- `uv run python -` integration smoke check:
  - `TradingAgentsGraph` initializes
  - quick/deep LLM objects are `ResilientLLM`
  - custom gateway resolves `tool_execution_mode=host_managed_tools`

## Gaps

- No full end-to-end live gateway rerun was executed in this refactor step.
- Web service restart is operational only; browser-level manual verification is still pending.
