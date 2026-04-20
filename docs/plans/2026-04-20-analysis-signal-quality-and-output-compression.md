# Analysis Signal Quality And Output Compression Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reduce verbose intermediate multi-agent output while preserving reasoning quality, and improve the system's ability to connect current fundamentals with future business outcomes and market expectations.

**Architecture:** Keep the existing multi-agent graph, but change what each node produces and how that output is handed downstream. Analyst, debate, trader, and risk nodes should emit compact structured summaries rather than long narrative transcripts, while the fundamentals and decision-manager prompts gain an explicit forward-looking layer: expected business trajectory, market-implied expectations, catalysts, risks, and where current valuation sits relative to that future path.

**Tech Stack:** Python, LangGraph, LangChain/OpenAI-compatible chat models, existing TradingAgents graph/state system, pytest

---

## File Structure

- `tradingagents/agents/analysts/market_analyst.py`
  Responsibility: compress market output into concise evidence-focused summary instead of long prose
- `tradingagents/agents/analysts/news_analyst.py`
  Responsibility: compress news output and add forward-looking catalysts/risks
- `tradingagents/agents/analysts/social_media_analyst.py`
  Responsibility: compress sentiment output and separate noise from leading demand/brand signals
- `tradingagents/agents/analysts/fundamentals_analyst.py`
  Responsibility: shift from backward-looking dump to future-linked fundamental analysis
- `tradingagents/agents/researchers/bull_researcher.py`
  Responsibility: produce compact bull case tied to future operating outcomes and market expectations
- `tradingagents/agents/researchers/bear_researcher.py`
  Responsibility: produce compact bear case tied to future downside path and expectation risk
- `tradingagents/agents/managers/research_manager.py`
  Responsibility: synthesize concise debate into actionable investment plan without replaying long transcripts
- `tradingagents/agents/trader/trader.py`
  Responsibility: turn research plan into tighter trading action summary
- `tradingagents/agents/risk_mgmt/aggressive_debator.py`
  Responsibility: produce compact risk argument
- `tradingagents/agents/risk_mgmt/conservative_debator.py`
  Responsibility: produce compact risk argument
- `tradingagents/agents/risk_mgmt/neutral_debator.py`
  Responsibility: produce compact risk argument
- `tradingagents/agents/managers/portfolio_manager.py`
  Responsibility: final decision should emphasize what the market is pricing versus what the business may actually do
- `cli/main.py`
  Responsibility: save/display a shorter final report structure and stop promoting raw debate transcripts as first-class output
- `tradingagents/web/runner.py`
  Responsibility: persist only useful compact partials in `web_runs/`
- `tests/`
  Responsibility: prompt/content-shape regression tests for compact outputs and forward-looking thesis structure

---

### Task 1: Lock The New Output Shape With Tests

**Files:**
- Modify: `tests/test_web_app.py`
- Create: `tests/test_report_structure.py`

- [ ] **Step 1: Write a failing test that the web UI no longer centers raw long-form Markdown output**

```python
def test_web_result_panel_prefers_result_path_over_large_inline_markdown(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "结果文件路径" in response.text
    assert "Markdown 结果" not in response.text
```

- [ ] **Step 2: Write failing tests that final report structure emphasizes concise conclusions over transcript replay**

```python
def test_save_report_to_disk_does_not_require_raw_bull_and_bear_transcripts(tmp_path):
    final_state = {
        "market_report": "## Market Summary\n- Trend: up",
        "news_report": "## News Summary\n- Catalyst: product launch",
        "fundamentals_report": "## Fundamentals Summary\n- Forward view: margin expansion",
        "investment_debate_state": {"judge_decision": "## Research View\n- Recommendation: Buy"},
        "trader_investment_plan": "## Trading Plan\n- Entry: scale in",
        "risk_debate_state": {"judge_decision": "## Final Decision\n- Rating: Buy"},
    }
    report_path = save_report_to_disk(final_state, "TSM", tmp_path)
    text = Path(report_path).read_text(encoding="utf-8")
    assert "Bull Researcher" not in text
    assert "Bear Researcher" not in text
```

- [ ] **Step 3: Run targeted tests to verify they fail**

Run: `uv run --with pytest python -m pytest -q tests/test_web_app.py tests/test_report_structure.py`
Expected: FAIL because UI and report assembly still expose verbose output structure.

### Task 2: Compress Analyst Outputs At The Source

**Files:**
- Modify: `tradingagents/agents/analysts/market_analyst.py`
- Modify: `tradingagents/agents/analysts/news_analyst.py`
- Modify: `tradingagents/agents/analysts/social_media_analyst.py`
- Modify: `tradingagents/agents/analysts/fundamentals_analyst.py`

- [ ] **Step 1: Rewrite analyst prompts to cap output format**

```python
"Return exactly these sections:\n"
"1. Core View (3 bullets max)\n"
"2. Evidence (3 bullets max)\n"
"3. Forward Signals (3 bullets max)\n"
"4. Key Risk (2 bullets max)\n"
"5. Bottom Line (1 short paragraph)\n"
```

- [ ] **Step 2: Explicitly ban long narrative recap and redundant markdown tables**

```python
"Do not write a long narrative report."
"Do not restate all source data."
"Do not append a large markdown table unless it materially changes the decision."
```

- [ ] **Step 3: Upgrade the fundamentals analyst to answer future-linked questions**

```python
"Connect current fundamentals to the next 4-8 quarters."
"State what revenue, margin, cash flow, or capital intensity path is implied by today's business conditions."
"Explain what the market likely expects, what could beat those expectations, and what could miss them."
```

- [ ] **Step 4: Run focused tests or fixture-based prompt assertions**

Run: `uv run --with pytest python -m pytest -q tests/test_report_structure.py`
Expected: FAIL shifts to downstream nodes still expanding the text.

### Task 3: Compress Debate Nodes Without Losing Decision Logic

**Files:**
- Modify: `tradingagents/agents/researchers/bull_researcher.py`
- Modify: `tradingagents/agents/researchers/bear_researcher.py`
- Modify: `tradingagents/agents/risk_mgmt/aggressive_debator.py`
- Modify: `tradingagents/agents/risk_mgmt/conservative_debator.py`
- Modify: `tradingagents/agents/risk_mgmt/neutral_debator.py`

- [ ] **Step 1: Replace “conversation-style” prompts with compact argument cards**

```python
"Respond with at most 5 bullets."
"Each bullet must be one of: Thesis, Evidence, Forward Path, Weakness In Opponent, Risk."
"Avoid rhetorical back-and-forth."
```

- [ ] **Step 2: Keep state history machine-readable enough for the next agent**

```python
argument = f"Bear Analyst Summary:\\n{response.content}"
new_state["history"] = history + "\\n\\n" + argument
```

- [ ] **Step 3: Make risk debators argue about scenario outcomes rather than generic caution**

```python
"Frame your argument as scenario analysis: bull case, base case, bear case, and sizing consequences."
```

- [ ] **Step 4: Run targeted tests to verify compact state shape remains valid**

Run: `uv run --with pytest python -m pytest -q tests/test_report_structure.py`
Expected: PASS or fail only at manager/final report formatting.

### Task 4: Improve Decision Makers With Expectation-Versus-Reality Logic

**Files:**
- Modify: `tradingagents/agents/managers/research_manager.py`
- Modify: `tradingagents/agents/trader/trader.py`
- Modify: `tradingagents/agents/managers/portfolio_manager.py`

- [ ] **Step 1: Change the research manager prompt from “summarize debate” to “decide what future path matters most”**

```python
"Decide which future business path is most likely over the next 4-8 quarters."
"State what the market appears to be pricing in."
"Explain whether current price/setup underestimates or overestimates that future path."
```

- [ ] **Step 2: Make the trader consume a concise investment plan, not a long retrospective report**

```python
"Output only: trade direction, entry style, invalidation level, time horizon, and what new evidence would change the view."
```

- [ ] **Step 3: Make the portfolio manager final output explicitly answer the core forward-looking question**

```python
"Required output structure:"
"1. Rating"
"2. Chinese Summary"
"3. What The Market Is Pricing"
"4. What The Business Likely Does Next"
"5. Why The Gap Creates A Buy/Hold/Sell Decision"
```

- [ ] **Step 4: Ensure final user-facing summary stays compact**

```python
"Keep the executive summary under 8 bullets or 2 short paragraphs."
```

- [ ] **Step 5: Run targeted tests**

Run: `uv run --with pytest python -m pytest -q tests/test_report_structure.py`
Expected: PASS for final output structure expectations.

### Task 5: Shrink Saved Reports And Web Partials

**Files:**
- Modify: `cli/main.py`
- Modify: `tradingagents/web/runner.py`

- [ ] **Step 1: Save compact summaries as primary artifacts and demote raw debate detail**

```python
sections.append(f"## II. Research Team Decision\\n\\n{debate['judge_decision']}")
```

- [ ] **Step 2: Stop always stitching bull/bear/aggressive/conservative/neutral transcripts into the main report**

```python
if include_transcripts:
    ...
else:
    sections.append(compact_manager_summary)
```

- [ ] **Step 3: Persist only the compact manager outputs plus selected partials in the web runner**

```python
run.write_partial("research_manager", judge_decision)
run.write_partial("portfolio_manager", judge_decision)
```

- [ ] **Step 4: Run targeted tests**

Run: `uv run --with pytest python -m pytest -q tests/test_report_structure.py tests/test_web_app.py`
Expected: PASS.

### Task 6: Manual Validation Against The Two Product Problems

**Files:**
- Modify: `README.md`
- Modify: `docs/plans/2026-04-20-web-form-simplification-and-preflight.md` only if this new work changes that UX plan

- [ ] **Step 1: Document the new mental model**

```markdown
- Intermediate agent outputs are intentionally compressed for machine readability and concise human review.
- Final decisions should explain current fundamentals, future business path, and market expectations as separate concepts.
```

- [ ] **Step 2: Run the full suite**

Run: `uv run --with pytest python -m pytest -q`
Expected: PASS

- [ ] **Step 3: Manual validation with one real run**

Run: `uv run tradingagents-web`
Expected:
- intermediate `partials/` are materially shorter than before
- final result no longer reads like a transcript dump
- output explicitly distinguishes:
  - current fundamentals
  - future business path
  - market-implied expectations
  - the decision created by the gap
