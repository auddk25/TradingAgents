# Provider Gateway Config Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make provider-specific gateway environment variables the only settings users need to change when switching gateways.

**Architecture:** Centralize provider URL resolution in configuration helpers, then have CLI, graph setup, and client constructors consume that single source. Keep the existing endpoint defaults as fallbacks so current behavior remains stable when no override is present.

**Tech Stack:** Python, `unittest`, `pytest`, `python-dotenv`

---

### Task 1: Lock The Desired Provider URL Behavior

**Files:**
- Modify: `docs/superpowers/specs/2026-04-19-openai-gateway-config-design.md`
- Modify: `docs/plans/2026-04-19-openai-gateway-config.md`
- Modify: `tests/test_cli_provider_selection.py`
- Modify: `tests/test_default_config.py`
- Create: `tests/test_client_base_url_resolution.py`

- [ ] **Step 1: Write the failing tests**
- [ ] **Step 2: Run tests to verify they fail**
- [ ] **Step 3: Capture the fallback and override cases explicitly across multiple providers**

### Task 2: Route CLI, Graph Setup, And Clients Through The Same Setting

**Files:**
- Modify: `tradingagents/default_config.py`
- Modify: `cli/utils.py`
- Modify: `tradingagents/graph/trading_graph.py`
- Modify: `tradingagents/llm_clients/openai_client.py`
- Modify: `tradingagents/llm_clients/azure_client.py`

- [ ] **Step 1: Add provider URL resolution helpers in default config**
- [ ] **Step 2: Make CLI provider selection read the resolved provider URLs**
- [ ] **Step 3: Make graph setup resolve the active provider URL when `backend_url` is unset**
- [ ] **Step 4: Make OpenAI-compatible and Azure clients honor explicit overrides first and provider defaults second**

### Task 3: Verify Regression Safety

**Files:**
- Test: `tests/test_cli_provider_selection.py`
- Test: `tests/test_default_config.py`
- Test: `tests/test_client_base_url_resolution.py`
- Test: `tests/test_google_api_key.py`
- Test: `tests/test_model_validation.py`
- Test: `tests/test_ticker_symbol_handling.py`
- Modify: `.env.example`

- [ ] **Step 1: Run the targeted test suite**
- [ ] **Step 2: Run `uv run python -m cli.main --help`**
- [ ] **Step 3: Confirm `.env` loading still exposes OpenAI settings**
