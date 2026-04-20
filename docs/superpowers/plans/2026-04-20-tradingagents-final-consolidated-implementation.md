# TradingAgents Final Consolidated Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the approved TradingAgents improvements across analysis output compression, future-pricing-aware decisions, web UI simplification, preflight validation, and ticker-scoped short-summary memory.

**Architecture:** Keep the existing LangGraph flow and local FastAPI web shell, but tighten what gets generated and persisted. Analyst/debate nodes emit compact reasoning cards, final manager nodes explicitly separate short-term and long-term judgment, the web UI defaults to simple controls with path-first results, and every run starts fresh while only a short ticker-specific summary may carry forward into approved high-level prompts.

**Tech Stack:** Python, LangGraph, LangChain/OpenAI-compatible clients, FastAPI, SSE, static HTML/CSS/JavaScript, pytest

---

### Task 1: Lock Contracts With Tests

**Files:**
- Modify: `tests/test_web_app.py`
- Modify: `tests/test_report_structure.py`

- [ ] **Step 1: Extend UI contract tests**

Add assertions that:
- the root page exposes `主模型`, `高级选项`, `结果文件路径`, `错误文件路径`
- the page does not render full inline markdown/error blobs as the primary result view
- OpenAI defaults use `gpt-5.4` for both `quick_think_llm` and `deep_think_llm`

- [ ] **Step 2: Extend report/manager contract tests**

Add assertions that:
- analyst/research/risk prompt sources contain compact reasoning-card instructions
- research manager prompt contains `Future Business Path`, `What The Market Is Pricing`, `Strategic Ownership View`
- portfolio manager prompt contains `Short-Term View`, `Long-Term Ownership View`, `Gap Between Price And Future Path`, `Trim position`, `Hold core position`, `Add gradually`
- report output omits raw bull/bear/risk transcript sections

- [ ] **Step 3: Add fresh-run and short-summary tests**

Add tests that:
- a fresh run starts with empty debate history
- optional prior summary defaults to empty
- ticker-scoped summary storage is isolated per ticker
- historical full reports are not required for the next run

- [ ] **Step 4: Run target tests**

Run: `uv run --with pytest python -m pytest -q tests/test_web_app.py tests/test_report_structure.py`

Expected: failing assertions that define the new contract.

### Task 2: Implement Fresh Run Memory And Future-Pricing Analysis

**Files:**
- Create: `tradingagents/agents/utils/summary_memory.py`
- Modify: `tradingagents/agents/utils/memory.py`
- Modify: `tradingagents/graph/trading_graph.py`
- Modify: `tradingagents/agents/analysts/market_analyst.py`
- Modify: `tradingagents/agents/analysts/news_analyst.py`
- Modify: `tradingagents/agents/analysts/social_media_analyst.py`
- Modify: `tradingagents/agents/analysts/fundamentals_analyst.py`
- Modify: `tradingagents/agents/researchers/bull_researcher.py`
- Modify: `tradingagents/agents/researchers/bear_researcher.py`
- Modify: `tradingagents/agents/risk_mgmt/aggressive_debator.py`
- Modify: `tradingagents/agents/risk_mgmt/conservative_debator.py`
- Modify: `tradingagents/agents/risk_mgmt/neutral_debator.py`
- Modify: `tradingagents/agents/managers/research_manager.py`
- Modify: `tradingagents/agents/managers/portfolio_manager.py`
- Modify: `tradingagents/agents/trader/trader.py`

- [ ] **Step 1: Add summary memory utilities**

Implement ticker-scoped helpers under `summary_memory.py` for:
- loading `memory_runs/<ticker>/latest_summary.md`
- writing `latest_summary.md`
- writing immutable `summaries/<timestamp>.md`
- writing `snapshots/<timestamp>.json`

- [ ] **Step 2: Keep each run fresh**

Ensure graph/run setup:
- clears in-memory debate memory before each run
- starts with empty run-scoped history/messages
- never re-reads `web_runs/`, `partials/`, `complete_report.md`, or prior `engine_results/` into prompts

- [ ] **Step 3: Inject only short prior summary**

Allow only the loaded short summary to reach:
- `research_manager`
- `portfolio_manager`
- optionally `trader`

Do not inject it into analysts, bull/bear researchers, or risk debators.

- [ ] **Step 4: Compress analyst and debate prompts**

Change analyst/debate prompt instructions so outputs are short reasoning cards with logic-bearing fields such as:
- `Thesis`
- `Evidence`
- `What is priced in`
- `Forward Implication`
- `Key Risk`
- `Confidence`

Keep debate nodes in compact counterargument form instead of long transcript prose.

- [ ] **Step 5: Make fundamentals and final managers future-pricing aware**

Update prompts so final reasoning explicitly covers:
- current fundamentals
- next 4-8 quarter business path
- what the market is pricing
- what would beat/miss expectations
- short-term tactical view
- long-term ownership view
- partial portfolio actions such as trimming vs holding a core position

- [ ] **Step 6: Run target tests**

Run: `uv run --with pytest python -m pytest -q tests/test_report_structure.py`

Expected: prompt-contract and fresh-memory tests pass.

### Task 3: Implement Web/UI, Report Persistence, And Preflight

**Files:**
- Modify: `cli/main.py`
- Modify: `tradingagents/web/models.py`
- Modify: `tradingagents/web/app.py`
- Modify: `tradingagents/web/runner.py`
- Modify: `tradingagents/web/static/index.html`
- Modify: `tradingagents/web/static/app.js`
- Modify: `tradingagents/web/static/styles.css`
- Modify: `README.md`

- [ ] **Step 1: Simplify defaults and advanced controls**

Keep the simple form focused on:
- ticker
- analysis date
- output language
- analysts
- research depth
- provider
- backend URL
- main model

Move quick/deep models and provider-specific reasoning knobs into collapsible advanced settings.

- [ ] **Step 2: Add/finish inline help affordances**

Ensure field help is available from the `?` affordance for:
- research depth
- main model
- quick/deep models
- provider-specific reasoning knobs

Use concise Chinese explanations.

- [ ] **Step 3: Add preflight validation before run creation**

Validate:
- model/provider selections before long-running execution starts
- unsupported OpenAI-compatible gateway models fail fast with a clear message

- [ ] **Step 4: Reshape saved reports and web run artifacts**

Update CLI/web persistence so:
- the main report is built from compact analyst summaries + manager decisions
- raw bull/bear/risk transcripts are not primary report sections
- result and error payloads sent to the frontend are path-first
- `web_runs/` keeps run artifacts while `memory_runs/` keeps summary memory

- [ ] **Step 5: Document the new mental model**

Update `README.md` to explain:
- research depth vs model selection
- main model vs advanced overrides
- short-term vs long-term final decision
- fresh-run behavior with optional ticker-scoped short summary
- where to inspect `web_runs/` and `memory_runs/`

- [ ] **Step 6: Run target and full verification**

Run:
- `uv run --with pytest python -m pytest -q tests/test_web_app.py`
- `uv run --with pytest python -m pytest -q`

Expected: all relevant tests pass.

### Task 4: Manual Validation And Closeout

**Files:**
- Modify if needed: `docs/REFACTOR_REPORT_R2_20260420.md`

- [ ] **Step 1: Run the local web app**

Run: `uv run tradingagents-web`

- [ ] **Step 2: Perform manual checks**

Verify:
- simple form defaults render correctly
- help popovers explain controls
- unsupported models fail in preflight before a full run starts
- completed runs show result/error file paths instead of giant inline blobs
- generated artifacts land under repo-local `web_runs/` and `memory_runs/`

- [ ] **Step 3: Write refactor report if structural scope warrants it**

Capture:
- scope
- risks
- validation performed
- known gaps
