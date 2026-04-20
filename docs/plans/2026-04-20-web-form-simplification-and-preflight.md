# Web Form Simplification And Preflight Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Simplify the local TradingAgents web form so default usage is understandable, make unsupported-model failures fail fast before a run starts, and reduce result/error panels to path-first summaries instead of dumping long Markdown and traceback text into the UI.

**Architecture:** Keep the existing FastAPI + SSE runner architecture, but add a lightweight preflight validation path before run creation and split the frontend into a simple default form plus an advanced collapsible section. Treat `主模型` as the default source of truth for `quick/deep` unless the user explicitly overrides advanced settings, and move verbose artifacts entirely to files under `web_runs/`.

**Tech Stack:** Python, FastAPI, Pydantic, static HTML/CSS/JavaScript, pytest, existing TradingAgents runner

---

## File Structure

- `tradingagents/web/models.py`
  Responsibility: form defaults/options, new helper copy for field explanations, default OpenAI model choices
- `tradingagents/web/app.py`
  Responsibility: add preflight endpoint or integrate preflight into run creation response contract
- `tradingagents/web/runner.py`
  Responsibility: shared model availability probe used before long-running jobs start
- `tradingagents/web/static/index.html`
  Responsibility: default/simple form layout, advanced options toggle, explanatory text, compact result panel
- `tradingagents/web/static/app.js`
  Responsibility: main-model synchronization, advanced overrides, preflight handling, path-only result/error rendering
- `tradingagents/web/static/styles.css`
  Responsibility: collapsible advanced section, explanatory text styles, lighter result/error presentation
- `tests/test_web_app.py`
  Responsibility: lock UI strings, default model behavior, preflight failures, compact result/error rendering
- `tests/test_client_base_url_resolution.py`
  Responsibility: preserve gateway behavior if preflight reuses the OpenAI-compatible client path
- `README.md`
  Responsibility: document simplified form semantics and where to inspect full output

---

### Task 1: Lock The New UX Contract

**Files:**
- Modify: `tests/test_web_app.py`

- [ ] **Step 1: Write failing tests for the new default form contract**

```python
def test_form_options_default_openai_models_use_gpt_5_4_for_quick_and_deep(form_options_response):
    defaults = form_options_response["defaults"]
    assert defaults["quick_think_llm"] == "gpt-5.4"
    assert defaults["deep_think_llm"] == "gpt-5.4"


def test_root_page_mentions_main_model_advanced_options_and_parameter_help(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "主模型" in response.text
    assert "高级选项" in response.text
    assert "研究强度控制讨论轮次" in response.text
```

- [ ] **Step 2: Write failing tests for compact result and error panels**

```python
def test_root_page_shows_report_path_instead_of_full_markdown_dump(client):
    response = client.get("/")
    assert "结果文件路径" in response.text
    assert "Markdown 结果" not in response.text
    assert "错误详情" not in response.text
```

- [ ] **Step 3: Write failing tests for preflight model validation**

```python
def test_run_creation_rejects_unsupported_model_before_background_start(client, monkeypatch):
    monkeypatch.setattr("tradingagents.web.runner.validate_model_selection", fake_model_not_found)
    response = client.post("/api/runs", json=sample_payload())
    assert response.status_code == 422
    assert "模型不可用" in response.text
    assert "gpt-5.4-mini" in response.text
```

- [ ] **Step 4: Run the targeted tests to verify they fail**

Run: `uv run --with pytest python -m pytest -q tests/test_web_app.py`
Expected: FAIL because defaults, UI copy, compact result panel, and preflight handling still reflect the old behavior.

### Task 2: Define Simpler Form Defaults And Explanations

**Files:**
- Modify: `tradingagents/web/models.py`

- [ ] **Step 1: Change OpenAI default quick/deep model defaults to `gpt-5.4`**

```python
defaults = {
    ...
    "llm_provider": "openai",
    "quick_think_llm": "gpt-5.4",
    "deep_think_llm": "gpt-5.4",
    ...
}
```

- [ ] **Step 2: Add explicit field help metadata for simple and advanced sections**

```python
"field_help": {
    "research_depth": "控制研究团队和风险团队讨论几轮，不是模型能力等级。",
    "main_model": "默认给整条链路使用。未展开高级选项时，快速模型和深度模型都跟随它。",
    "quick_think_llm": "给分析师、交易员、风险辩手这类高频节点使用。",
    "deep_think_llm": "给研究经理、投资组合经理这类最终决策节点使用。",
    "openai_reasoning_effort": "控制单次调用愿意花多少推理成本，不等于讨论轮次。",
}
```

- [ ] **Step 3: Add a compact advanced-settings descriptor to the form options payload**

```python
"advanced_fields": [
    "quick_think_llm",
    "deep_think_llm",
    "google_thinking_level",
    "openai_reasoning_effort",
    "anthropic_effort",
]
```

- [ ] **Step 4: Run the targeted tests**

Run: `uv run --with pytest python -m pytest -q tests/test_web_app.py`
Expected: FAIL moves forward to missing frontend wiring and preflight behavior.

### Task 3: Add Model Preflight Validation Before Run Creation

**Files:**
- Modify: `tradingagents/web/runner.py`
- Modify: `tradingagents/web/app.py`
- Modify: `tests/test_web_app.py`

- [ ] **Step 1: Add a lightweight model validation function in the web runner**

```python
def validate_model_selection(payload: SubmissionPayload) -> None:
    provider = payload.llm_provider.lower()
    model = payload.quick_think_llm
    client = create_llm_client(
        provider=provider,
        model=model,
        base_url=payload.backend_url,
        reasoning_effort=payload.openai_reasoning_effort,
    )
    llm = client.get_llm()
    llm.invoke("Reply with OK.")
```

- [ ] **Step 2: Convert known unsupported-model/provider failures into a 4xx API response**

```python
@app.post("/api/runs", response_model=RunRecord)
def create_run(payload: SubmissionPayload):
    try:
        validate_model_selection(payload)
    except UnsupportedModelError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    return start_run(payload).to_record()
```

- [ ] **Step 3: Ensure the preflight error is concise and UI-safe**

```python
raise UnsupportedModelError(
    f"模型不可用：{model}。当前网关不支持这个模型，请改用 {fallback_model} 或检查网关配置。"
)
```

- [ ] **Step 4: Run the targeted tests**

Run: `uv run --with pytest python -m pytest -q tests/test_web_app.py`
Expected: PASS for preflight rejection tests; remaining failures should be limited to frontend layout changes.

### Task 4: Simplify The Frontend Form Into Default Plus Advanced

**Files:**
- Modify: `tradingagents/web/static/index.html`
- Modify: `tradingagents/web/static/app.js`
- Modify: `tradingagents/web/static/styles.css`

- [ ] **Step 1: Replace the current two-model-first layout with a default/simple form**

```html
<div class="form-grid">
  <label class="field">
    <span>研究强度</span>
    <select id="research_depth" name="research_depth"></select>
    <p class="help" id="help-research-depth"></p>
  </label>
  <label class="field">
    <span>主模型</span>
    <select id="main_model" name="main_model"></select>
    <p class="help" id="help-main-model"></p>
  </label>
</div>
```

- [ ] **Step 2: Add an advanced-options toggle and move quick/deep/reasoning fields inside it**

```html
<details id="advanced-options" class="advanced-panel">
  <summary>高级选项</summary>
  <div class="advanced-grid">
    ...
  </div>
</details>
```

- [ ] **Step 3: Wire `主模型` to quick/deep defaults unless advanced overrides are touched**

```javascript
function syncMainModelToAdvanced() {
  if (!state.quickOverrideTouched) {
    setModelField("quick", state.currentProvider, el.mainModel.value);
  }
  if (!state.deepOverrideTouched) {
    setModelField("deep", state.currentProvider, el.mainModel.value);
  }
}
```

- [ ] **Step 4: Render parameter explanations inline**

```javascript
el.helpResearchDepth.textContent = options.field_help.research_depth;
el.helpMainModel.textContent = options.field_help.main_model;
```

- [ ] **Step 5: Run the targeted tests**

Run: `uv run --with pytest python -m pytest -q tests/test_web_app.py`
Expected: PASS for form-structure and copy expectations.

### Task 5: Shrink Result And Error Panels To File Paths

**Files:**
- Modify: `tradingagents/web/static/index.html`
- Modify: `tradingagents/web/static/app.js`
- Modify: `tradingagents/web/static/styles.css`

- [ ] **Step 1: Replace the large Markdown/error body areas with compact path-first cards**

```html
<div class="result-block">
  <h3>结果文件路径</h3>
  <code id="response-report-path">-</code>
</div>
<div class="error-block">
  <h3>错误文件路径</h3>
  <code id="response-error-path">-</code>
</div>
```

- [ ] **Step 2: Update the event handlers so successful runs only render paths, not full content**

```javascript
case "run_completed":
  el.responseReportPath.textContent = payload.report_path ?? "-";
  el.responseErrorPath.textContent = "-";
  break;
case "run_failed":
  el.responseErrorPath.textContent = payload.error_path ?? "-";
  break;
```

- [ ] **Step 3: Keep long content on disk only and point users to `web_runs/`**

```javascript
setStatus("分析完成。完整内容请查看结果文件路径。");
setStatus("运行失败。完整错误请查看错误文件路径。", "error");
```

- [ ] **Step 4: Run the targeted tests**

Run: `uv run --with pytest python -m pytest -q tests/test_web_app.py`
Expected: PASS.

### Task 6: Verify The Simplified Flow End To End

**Files:**
- Modify: `README.md`
- Test: `tests/test_web_app.py`
- Test: `tests/test_client_base_url_resolution.py`

- [ ] **Step 1: Document the simpler mental model in the README**

```markdown
- `研究强度`: controls debate rounds, not model quality
- `主模型`: default model for the whole run
- `高级选项`: only needed when you want different quick/deep models or provider-specific reasoning knobs
```

- [ ] **Step 2: Run the full suite**

Run: `uv run --with pytest python -m pytest -q`
Expected: PASS

- [ ] **Step 3: Manual validation with the local web app**

Run: `uv run tradingagents-web`
Expected:
- the default form shows `主模型` and `研究强度`
- advanced options are collapsed by default
- choosing an unsupported model fails fast with a concise inline error
- successful runs show `结果文件路径`
- failed runs show `错误文件路径`
- full artifacts still land under `web_runs/<ticker>/<analysis_date>/<timestamp>_<run_id>/`
