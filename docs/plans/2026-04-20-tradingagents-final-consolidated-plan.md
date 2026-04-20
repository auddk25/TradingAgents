# TradingAgents Final Consolidated Improvement Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Improve TradingAgents in four linked areas: compress intermediate agent output without losing reasoning fidelity, upgrade final decisions to focus on future business path versus market expectations, simplify the local web UI so ordinary use is understandable while advanced controls remain available, and guarantee that every analysis run starts from a clean analytical context while allowing only a short ticker-specific prior summary to carry forward.

**Architecture:** Keep the existing multi-agent graph and local FastAPI web shell, but change the shape of information flowing through the system. Intermediate agent outputs become short structured reasoning cards instead of long narrative transcripts; final decision makers explicitly separate short-term tactical view from long-term strategic ownership; the web UI defaults to a simple form with explanations, optional advanced settings, preflight model validation, and path-first run results instead of dumping large Markdown and traceback blobs; and each run gets a fresh execution context with no prior debate history while allowing one short per-ticker carry-forward summary for continuity at selected high-level nodes.

**Tech Stack:** Python, LangGraph, LangChain/OpenAI-compatible clients, FastAPI, Server-Sent Events (SSE), static HTML/CSS/JavaScript, pytest

---

## File Structure

- `tradingagents/agents/analysts/market_analyst.py`
  Responsibility: short market thesis card; avoid long indicator essays
- `tradingagents/agents/analysts/news_analyst.py`
  Responsibility: short catalyst/risk card with forward-looking news implications
- `tradingagents/agents/analysts/social_media_analyst.py`
  Responsibility: short sentiment card separating signal from noise
- `tradingagents/agents/analysts/fundamentals_analyst.py`
  Responsibility: convert backward-looking fundamentals dump into future-path analysis
- `tradingagents/agents/researchers/bull_researcher.py`
  Responsibility: compact bull argument using machine-readable reasoning blocks
- `tradingagents/agents/researchers/bear_researcher.py`
  Responsibility: compact bear argument using machine-readable reasoning blocks
- `tradingagents/agents/managers/research_manager.py`
  Responsibility: synthesize debate into forward business path, market expectations, and strategic plan
- `tradingagents/agents/trader/trader.py`
  Responsibility: output concise short-term trading plan
- `tradingagents/agents/risk_mgmt/aggressive_debator.py`
  Responsibility: compact upside/risk sizing argument
- `tradingagents/agents/risk_mgmt/conservative_debator.py`
  Responsibility: compact downside/protection argument
- `tradingagents/agents/risk_mgmt/neutral_debator.py`
  Responsibility: compact base-case balancing argument
- `tradingagents/agents/managers/portfolio_manager.py`
  Responsibility: final short-term vs long-term decision split, valuation gap framing, portfolio action
- `tradingagents/agents/utils/memory.py`
  Responsibility: support explicit reset behavior and short-summary storage for cross-run analytical memory
- `tradingagents/agents/utils/summary_memory.py`
  Responsibility: read/write ticker-scoped carry-forward summaries and structured memory snapshots
- `cli/main.py`
  Responsibility: save and display compact report structure instead of replaying all debate transcripts
- `tradingagents/graph/trading_graph.py`
  Responsibility: construct fresh run-scoped memories and avoid carrying prior analytical context into new runs
- `tradingagents/web/models.py`
  Responsibility: form defaults, field help, advanced-field metadata, safer default model selection
- `tradingagents/web/app.py`
  Responsibility: preflight model validation endpoint or integrated preflight before run creation
- `tradingagents/web/runner.py`
  Responsibility: shared model preflight, compact partial persistence, path-only result/error metadata, and pre-run cleanup/isolation
- `tradingagents/web/static/index.html`
  Responsibility: simplified form layout, advanced toggle, explanatory text, compact result/error cards
- `tradingagents/web/static/app.js`
  Responsibility: main-model sync, advanced overrides, preflight handling, path-only run rendering
- `tradingagents/web/static/styles.css`
  Responsibility: simplified layout, explanation styles, advanced section styling
- `tests/test_report_structure.py`
  Responsibility: compact output structure and future-pricing final decision contract
- `tests/test_web_app.py`
  Responsibility: UI simplification, preflight validation, path-only result rendering
- `tests/test_report_encoding.py`
  Responsibility: preserve UTF-8 report writing during report reshaping
- `README.md`
  Responsibility: document mental model for analysis depth, main model, advanced settings, and run artifact inspection

---

### Task 1: Lock The New Product Contract With Tests

**Files:**
- Modify: `tests/test_web_app.py`
- Create: `tests/test_report_structure.py`

- [ ] **Step 1: Write failing tests for compact UI defaults**

```python
def test_root_page_defaults_to_simple_form_and_hides_advanced_controls(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "主模型" in response.text
    assert "高级选项" in response.text
    assert "结果文件路径" in response.text
    assert "Markdown 结果" not in response.text
```

- [ ] **Step 2: Write failing tests for safer model defaults**

```python
def test_form_options_default_openai_models_use_gpt_5_4_for_quick_and_deep(form_options_response):
    defaults = form_options_response["defaults"]
    assert defaults["quick_think_llm"] == "gpt-5.4"
    assert defaults["deep_think_llm"] == "gpt-5.4"
```

- [ ] **Step 3: Write failing tests for the new final decision structure**

```python
def test_portfolio_manager_output_contract_requires_short_and_long_horizon_sections():
    prompt = build_portfolio_manager_prompt_stub(...)
    assert "Short-Term View" in prompt
    assert "Long-Term Ownership View" in prompt
    assert "What The Market Is Pricing" in prompt
    assert "Gap Between Price And Future Path" in prompt
```

- [ ] **Step 4: Write failing tests that compact reports do not require raw debate transcript sections**

```python
def test_saved_report_prefers_compact_manager_outputs_over_raw_debate_transcripts(tmp_path):
    final_state = make_minimal_final_state()
    report_path = save_report_to_disk(final_state, "TSM", tmp_path)
    text = Path(report_path).read_text(encoding="utf-8")
    assert "Bull Researcher" not in text
    assert "Bear Researcher" not in text
    assert "Short-Term View" in text
```

- [ ] **Step 5: Run the targeted tests to verify they fail**

Run: `uv run --with pytest python -m pytest -q tests/test_web_app.py tests/test_report_structure.py`
Expected: FAIL because current UI, defaults, report assembly, and final decision prompts do not match the new contract.

### Task 2: Compress Intermediate Agent Output Without Changing The Flow

**Files:**
- Modify: `tradingagents/agents/analysts/market_analyst.py`
- Modify: `tradingagents/agents/analysts/news_analyst.py`
- Modify: `tradingagents/agents/analysts/social_media_analyst.py`
- Modify: `tradingagents/agents/analysts/fundamentals_analyst.py`
- Modify: `tradingagents/agents/researchers/bull_researcher.py`
- Modify: `tradingagents/agents/researchers/bear_researcher.py`
- Modify: `tradingagents/agents/risk_mgmt/aggressive_debator.py`
- Modify: `tradingagents/agents/risk_mgmt/conservative_debator.py`
- Modify: `tradingagents/agents/risk_mgmt/neutral_debator.py`

- [ ] **Step 1: Change analyst prompts from long prose to compact reasoning cards**

```python
"Return exactly these sections:"
"1. Thesis"
"2. Evidence"
"3. Forward Implication"
"4. Key Risk"
"5. Confidence"
"Keep the full output under 8 bullets or 180 words."
```

- [ ] **Step 2: Remove instructions that encourage excessive length**

```python
# remove phrases like:
"Write a very detailed and nuanced report"
"Please write a comprehensive long report"
"Make sure to include as much detail as possible"
"Make sure to append a Markdown table ..."
```

- [ ] **Step 3: Change debate prompts from conversational transcripts to compact counterargument blocks**

```python
"Respond with at most 5 bullets."
"Use only: Claim, Evidence, Forward Impact, Counterpoint, Confidence."
"Do not write rhetorical dialogue."
```

- [ ] **Step 4: Preserve fidelity by keeping logic-bearing tokens, not stylistic filler**

```python
argument = (
    "Bull Summary:\\n"
    f"Claim: ...\\n"
    f"Evidence: ...\\n"
    f"Forward Impact: ...\\n"
    f"Counterpoint: ...\\n"
    f"Confidence: ..."
)
```

- [ ] **Step 5: Run targeted tests**

Run: `uv run --with pytest python -m pytest -q tests/test_report_structure.py`
Expected: FAIL shifts downstream to manager and report formatting until those are updated.

### Task 3: Make Fundamentals And Final Decisions Future-Pricing Aware

**Files:**
- Modify: `tradingagents/agents/analysts/fundamentals_analyst.py`
- Modify: `tradingagents/agents/managers/research_manager.py`
- Modify: `tradingagents/agents/trader/trader.py`
- Modify: `tradingagents/agents/managers/portfolio_manager.py`

- [ ] **Step 1: Make the fundamentals analyst answer future-path questions directly**

```python
"Connect today's fundamentals to the next 4-8 quarters."
"State the most likely revenue, margin, capex, and cash flow path."
"Explain which operating outcomes are already priced in and which are not."
```

- [ ] **Step 2: Make the research manager synthesize current facts into a future business path**

```python
"Required output:"
"1. Future Business Path"
"2. What The Market Is Pricing"
"3. What Could Beat Expectations"
"4. What Could Miss Expectations"
"5. Strategic Ownership View"
```

- [ ] **Step 3: Split the final portfolio decision into short-term and long-term horizons**

```python
"Required output structure:"
"1. Rating"
"2. Chinese Summary"
"3. Short-Term View"
"4. Long-Term Ownership View"
"5. What The Market Is Pricing"
"6. Gap Between Price And Future Path"
"7. Portfolio Action"
```

- [ ] **Step 4: Make the portfolio action explicitly support partial reductions**

```python
"Portfolio Action must choose one:"
"- Exit fully"
"- Trim position"
"- Hold core position"
"- Add gradually"
"- Wait for better entry"
```

- [ ] **Step 5: Make the trader focus on tactical execution only**

```python
"Output only:"
"- tactical direction"
"- entry style"
"- invalidation"
"- near-term catalyst watchlist"
```

- [ ] **Step 6: Run targeted tests**

Run: `uv run --with pytest python -m pytest -q tests/test_report_structure.py`
Expected: PASS for future-pricing and horizon-split output structure.

### Task 4: Enforce Fresh Analysis Context While Allowing A Short Prior Summary

**Files:**
- Modify: `tradingagents/graph/trading_graph.py`
- Modify: `tradingagents/agents/utils/memory.py`
- Modify: `tradingagents/web/runner.py`
- Modify: `cli/main.py`
- Modify: `tests/test_report_structure.py`

- [ ] **Step 1: Add a test that each run starts with empty analytical history**

```python
def test_new_run_starts_with_empty_debate_state_and_only_optional_summary_memory():
    graph = TradingAgentsGraph(config=make_test_config())
    state = graph.propagator.create_initial_state("TSM", "2026-04-20")
    assert state["investment_debate_state"]["history"] == ""
    assert state["risk_debate_state"]["history"] == ""
    assert state.get("prior_run_summary", "") == ""
```

- [ ] **Step 2: Keep data caching separate from reasoning memory**

```python
# market/news/fundamental data cache may persist for speed
# full past analytical recommendations must not be injected into prompts
# only a short per-ticker summary may be loaded
config["enable_summary_memory"] = True
```

- [ ] **Step 3: Add ticker-scoped memory storage with current and historical summary files**

```python
repo/memory_runs/<ticker>/latest_summary.md
repo/memory_runs/<ticker>/summaries/<timestamp>.md
repo/memory_runs/<ticker>/snapshots/<timestamp>.json
```

- [ ] **Step 4: Make every web and CLI run explicitly reset run-scoped artifacts before execution**

```python
def reset_run_context(graph: TradingAgentsGraph) -> None:
    graph.bull_memory.clear()
    graph.bear_memory.clear()
    graph.trader_memory.clear()
    graph.invest_judge_memory.clear()
    graph.portfolio_manager_memory.clear()
```

- [ ] **Step 5: Ensure no prior run output directory is read back into the next run**

```python
# write to a fresh timestamped run dir
# do not read partials, complete_report.md, or prior engine_results as prompt context
```

- [ ] **Step 6: Inject only the short summary into selected high-level nodes**

```python
# allowed:
research_manager_context["prior_run_summary"] = summary_text
portfolio_manager_context["prior_run_summary"] = summary_text

# not allowed:
bull_prompt["prior_full_report"] = ...
```

- [ ] **Step 7: Generate a new short summary after each completed run**

```python
summary = build_run_summary(final_state)
write_latest_summary(ticker, summary)
write_summary_snapshot(run_id, ticker, summary, metadata)
```

- [ ] **Step 8: Document this explicitly in the user-facing behavior**

```markdown
- Every analysis starts from a clean analytical context.
- Prior debate text and full reports are not fed into the next run.
- Only one short ticker-scoped prior summary may be reused.
- The summary may be empty on the first run.
- Data caches may be reused for speed, but they are not treated as prior investment reasoning.
```

- [ ] **Step 9: Run targeted tests**

Run: `uv run --with pytest python -m pytest -q tests/test_report_structure.py`
Expected: PASS.

### Task 5: Shrink Saved Reports And Web Partials To Decision-Relevant Content

**Files:**
- Modify: `cli/main.py`
- Modify: `tradingagents/web/runner.py`
- Modify: `tests/test_report_structure.py`

- [ ] **Step 1: Rebuild `save_report_to_disk()` around compact manager outputs**

```python
sections = [
    f"## Analyst Summaries\\n\\n{compact_analyst_bundle}",
    f"## Research View\\n\\n{investment_debate_state['judge_decision']}",
    f"## Trading View\\n\\n{final_state['trader_investment_plan']}",
    f"## Final Portfolio Decision\\n\\n{risk_state['judge_decision']}",
]
```

- [ ] **Step 2: Stop stitching full bull/bear/aggressive/conservative/neutral histories into the main report**

```python
# persist compact partials if needed, but do not treat them as primary report sections
```

- [ ] **Step 3: Persist only useful compact partials in the web runner**

```python
run.write_partial("market_report", compact_market_summary)
run.write_partial("fundamentals_report", compact_fundamentals_summary)
run.write_partial("research_manager", judge_decision)
run.write_partial("portfolio_manager", final_decision)
```

- [ ] **Step 4: Run targeted tests**

Run: `uv run --with pytest python -m pytest -q tests/test_report_structure.py tests/test_web_app.py`
Expected: PASS.

### Task 6: Simplify The Web UI And Add Preflight Validation

**Files:**
- Modify: `tradingagents/web/models.py`
- Modify: `tradingagents/web/app.py`
- Modify: `tradingagents/web/runner.py`
- Modify: `tradingagents/web/static/index.html`
- Modify: `tradingagents/web/static/app.js`
- Modify: `tradingagents/web/static/styles.css`
- Modify: `tests/test_web_app.py`

- [ ] **Step 1: Change defaults so OpenAI quick/deep both start at `gpt-5.4`**

```python
defaults["quick_think_llm"] = "gpt-5.4"
defaults["deep_think_llm"] = "gpt-5.4"
```

- [ ] **Step 2: Add simple form defaults plus advanced-field metadata and help text**

```python
"field_help": {
    "research_depth": "控制研究团队和风险团队讨论轮次，不是模型能力等级。",
    "main_model": "默认给整条链路使用。未改高级选项时，快速模型和深度模型都跟随它。",
    "quick_think_llm": "给分析师、交易员、风险辩手等高频节点使用。",
    "deep_think_llm": "给研究经理和投资组合经理等最终裁决节点使用。",
    "openai_reasoning_effort": "控制单次调用愿意花多少推理成本，不等于讨论轮次。",
}
```

- [ ] **Step 3: Add preflight validation before run creation**

```python
def validate_model_selection(payload: SubmissionPayload) -> None:
    ...
    raise UnsupportedModelError(
        f"模型不可用：{model}。当前网关不支持这个模型，请改用 gpt-5.4 或检查网关配置。"
    )
```

- [ ] **Step 4: Render only simple fields by default and collapse advanced settings**

```html
<label class="field">
  <span>主模型</span>
  <select id="main_model"></select>
</label>
<details class="advanced-panel">
  <summary>高级选项</summary>
  ...
</details>
```

- [ ] **Step 5: Make the UI path-first for results and errors**

```javascript
case "run_completed":
  el.responseReportPath.textContent = payload.report_path ?? "-";
  el.responseResultHint.textContent = "完整结果请查看结果文件路径。";
  break;
case "run_failed":
  el.responseErrorPath.textContent = payload.error_path ?? "-";
  el.responseErrorHint.textContent = "完整错误请查看错误文件路径。";
  break;
```

- [ ] **Step 6: Run targeted tests**

Run: `uv run --with pytest python -m pytest -q tests/test_web_app.py`
Expected: PASS.

### Task 7: Documentation And Manual Validation

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Document the new mental model clearly**

```markdown
- `研究强度`: controls discussion rounds, not model quality
- `主模型`: default model for the whole run
- `高级选项`: only needed when you want different quick/deep models or provider-specific reasoning knobs
- Final decisions separate short-term tactical action from long-term ownership view
- Every analysis starts from a clean context; previous analytical outputs are not reused
- Only a short ticker-specific summary may carry into the next run
- Full prior reports and debates are never injected back as prompt context
- Full results and errors live under `web_runs/`
```

- [ ] **Step 2: Run the full suite**

Run: `uv run --with pytest python -m pytest -q`
Expected: PASS

- [ ] **Step 3: Manual validation with the local web app**

Run: `uv run tradingagents-web`
Expected:
- default form is understandable without opening advanced settings
- unsupported models fail fast before long-running analysis starts
- intermediate partials are shorter and more structured
- final decision explicitly distinguishes:
  - current fundamentals
  - future business path
  - what the market is pricing
  - the gap between price and future path
  - short-term action
  - long-term ownership view
- UI shows result and error file paths instead of giant inline blobs
