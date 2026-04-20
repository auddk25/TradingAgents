# LLM Resilience And Capability Adapter Design

## Goal

Make TradingAgents more tolerant of custom gateway instability without changing the graph structure.

## Scope

This design adds two layers:

1. A unified resilience layer around all LLM calls.
2. A capability adapter layer that decides whether tool-using agents should use native tool calling or host-managed tools.

## Unified Resilience Layer

All model invocations must pass through a shared wrapper that can:

- add a small per-provider buffer between requests
- retry once on transient gateway failures
- fall back to alternate models when the primary model is unavailable
- treat empty assistant payloads as failures instead of successful completions
- log retry/fallback decisions to captured stdout so they appear in run logs

### Failure Classes

The wrapper should treat the following as retryable or fallback-worthy:

- HTTP 429 / rate limit
- HTTP 502
- HTTP 503
- timeout / connection reset / temporary upstream failures
- `unknown provider`
- `model_not_found`
- empty content with no tool calls

### Fallback Policy

For the current `openai` provider running against a custom gateway, the preferred fallback chain is:

1. requested model
2. `grok-4`
3. `grok-4-thinking`

Official OpenAI should keep its requested model and only retry, not switch to non-OpenAI models.

## Capability Adapter Layer

Tool-using agents should not always attempt native tool calling.

### Policy

- Official OpenAI base URL: prefer `native_tools`
- Custom OpenAI-compatible gateway: prefer `host_managed_tools`
- Other providers: keep existing behavior unless explicitly overridden later

### Host-Managed Tools

When `host_managed_tools` is active:

- code invokes the required data tools directly
- tool output is inserted into a compact prompt context
- the model only summarizes the fetched data

This avoids unstable `bind_tools(...)` behavior on incompatible gateways.

## Affected Areas

- `tradingagents/llm_clients/`: resilience wrapper and capability policy
- `tradingagents/graph/trading_graph.py`: resolved runtime config for tool mode and wrapped LLMs
- `tradingagents/agents/analysts/`: switch between native tools and host-managed tools
- tests covering retry, fallback, tool-mode resolution, and analyst fallback behavior

## Non-Goals

- No graph topology changes
- No database or queueing layer
- No provider-specific UI for resilience tuning in this change
