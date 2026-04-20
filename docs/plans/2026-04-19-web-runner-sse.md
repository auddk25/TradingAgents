# Web Runner SSE Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extend the local Web MVP so form submission starts a real TradingAgents run, streams step updates to the browser, and saves every run under the repository `web_runs/` directory as versioned Markdown and log files.

**Architecture:** Keep FastAPI as the local host, but replace the old "save JSON only" submission path with an in-memory run manager plus SSE event streaming. Each run executes in a background thread, persists normalized input plus intermediate artifacts into `repo/web_runs/<ticker>/<analysis_date>/<timestamp>_<run_id>/`, and pushes lifecycle events to the frontend until success or failure.

**Tech Stack:** Python, FastAPI, Uvicorn, Pydantic, threading, Server-Sent Events (SSE), static HTML/CSS/JavaScript, pytest

---

### Task 1: Lock The New Run Contract

**Files:**
- Modify: `tests/test_web_app.py`

- [ ] **Step 1: Write failing tests for run creation, run status, SSE events, and repository-local output paths**

```python
def test_run_creation_uses_repo_web_runs_dir(client, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    response = client.post("/api/runs", json={...})
    assert response.status_code == 200
    body = response.json()
    assert body["run_id"]
    assert "web_runs" in body["run_dir"]
    assert body["run_dir"].startswith(str(tmp_path))


def test_sse_stream_emits_created_progress_and_completed_events(client, monkeypatch):
    monkeypatch.setattr("tradingagents.web.runner.run_analysis_job", fake_runner)
    create = client.post("/api/runs", json={...}).json()
    with client.stream("GET", f"/api/runs/{create['run_id']}/events") as response:
        payload = b"".join(response.iter_bytes())
    assert b"event: run_created" in payload
    assert b"event: step_started" in payload
    assert b"event: run_completed" in payload
```

- [ ] **Step 2: Run the targeted tests to verify they fail**

Run: `uv run --with pytest python -m pytest -q tests/test_web_app.py`
Expected: FAIL because `/api/runs`, run state models, and SSE plumbing do not exist yet.

### Task 2: Add Versioned Run Storage And State Models

**Files:**
- Modify: `tradingagents/web/models.py`
- Modify: `tradingagents/web/storage.py`

- [ ] **Step 1: Add run request, run status, event, and completed-result models**

```python
class RunEvent(BaseModel):
    event: str
    step: str | None = None
    message: str
    timestamp: str
    data: dict[str, Any] = Field(default_factory=dict)


class RunRecord(BaseModel):
    run_id: str
    status: Literal["queued", "running", "completed", "failed"]
    run_dir: str
    current_step: str | None = None
    report_path: str | None = None
    error_path: str | None = None
```

- [ ] **Step 2: Add repository-local run directory helpers and file writers**

```python
def get_repo_web_runs_dir() -> Path:
    return Path.cwd() / "web_runs"


def create_run_dir(payload: SubmissionPayload, run_id: str) -> Path:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return get_repo_web_runs_dir() / payload.ticker / payload.analysis_date.isoformat() / f"{timestamp}_{run_id}"
```

- [ ] **Step 3: Run the targeted tests again**

Run: `uv run --with pytest python -m pytest -q tests/test_web_app.py`
Expected: FAIL moves forward to missing runner and API behavior.

### Task 3: Add The Run Manager And SSE API

**Files:**
- Create: `tradingagents/web/runner.py`
- Modify: `tradingagents/web/app.py`

- [ ] **Step 1: Implement an in-memory run manager with background thread execution**

```python
RUNS: dict[str, WebRun] = {}


def start_run(payload: SubmissionPayload) -> WebRun:
    run = WebRun.create(payload)
    RUNS[run.run_id] = run
    thread = Thread(target=run_analysis_job, args=(run,), daemon=True)
    thread.start()
    return run
```

- [ ] **Step 2: Implement `POST /api/runs`, `GET /api/runs/{run_id}`, and `GET /api/runs/{run_id}/events`**

```python
@app.post("/api/runs", response_model=RunRecord)
def create_run(payload: SubmissionPayload):
    run = start_run(payload)
    return run.to_record()


@app.get("/api/runs/{run_id}/events")
def stream_run_events(run_id: str):
    return StreamingResponse(event_stream(run_id), media_type="text/event-stream")
```

- [ ] **Step 3: Map real TradingAgents phases into stable SSE steps**

```python
STEP_TITLES = {
    "analysts": "分析师团队",
    "research": "研究团队",
    "trading": "交易团队",
    "risk": "风险管理",
    "portfolio": "投资组合决策",
}
```

- [ ] **Step 4: Run the targeted tests to verify the API contract**

Run: `uv run --with pytest python -m pytest -q tests/test_web_app.py`
Expected: PASS for run API and event-stream tests, or fail only on frontend expectations not yet updated.

### Task 4: Execute Real Analysis And Persist Markdown Artifacts

**Files:**
- Modify: `tradingagents/web/runner.py`
- Modify: `cli/main.py`

- [ ] **Step 1: Extract or reuse report-building logic so the web runner can write Markdown without duplicating report structure**

```python
from cli.main import save_report_to_disk


report_path = save_report_to_disk(final_state, payload.ticker, run.report_dir)
run.report_path = str(report_path)
```

- [ ] **Step 2: Capture stdout, stderr, partial reports, and failures into the run directory**

```python
with redirect_stdout(stdout_handle), redirect_stderr(stderr_handle):
    ...
except Exception:
    traceback_text = traceback.format_exc()
    (run.dir / "error.md").write_text(f"# Run Failed\n\n```text\n{traceback_text}\n```", encoding="utf-8")
```

- [ ] **Step 3: Save partial completed sections under `partials/` even on failure**

```python
def persist_partial(run: WebRun, name: str, content: str) -> None:
    partial_dir = run.dir / "partials"
    partial_dir.mkdir(parents=True, exist_ok=True)
    (partial_dir / f"{name}.md").write_text(content, encoding="utf-8")
```

- [ ] **Step 4: Run targeted tests again**

Run: `uv run --with pytest python -m pytest -q tests/test_web_app.py`
Expected: PASS for storage, logs, and failure artifact tests.

### Task 5: Update The Frontend For Live Runs

**Files:**
- Modify: `tradingagents/web/static/index.html`
- Modify: `tradingagents/web/static/app.js`
- Modify: `tradingagents/web/static/styles.css`

- [ ] **Step 1: Replace the old response panel with run status, event timeline, error details, and Markdown result sections**

```html
<section class="card">
  <h2>运行状态</h2>
  <p id="run-status">尚未启动</p>
  <ol id="event-timeline"></ol>
</section>
<section class="card">
  <h2>分析结果</h2>
  <article id="markdown-result"></article>
  <pre id="error-details" hidden></pre>
</section>
```

- [ ] **Step 2: On submit, call `POST /api/runs`, then subscribe with `EventSource`**

```javascript
const create = await fetch("/api/runs", { method: "POST", body: JSON.stringify(payload) });
const run = await create.json();
const source = new EventSource(`/api/runs/${run.run_id}/events`);
source.addEventListener("step_started", handleStepStarted);
source.addEventListener("run_completed", handleCompleted);
source.addEventListener("run_failed", handleFailed);
```

- [ ] **Step 3: Render completed Markdown and show local output paths**

```javascript
function handleCompleted(event) {
  const data = JSON.parse(event.data);
  markdownResult.textContent = data.markdown;
  outputPath.textContent = data.report_path;
}
```

- [ ] **Step 4: Run the targeted tests**

Run: `uv run --with pytest python -m pytest -q tests/test_web_app.py`
Expected: PASS.

### Task 6: Manual Verification And Documentation

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Document the new run endpoints, SSE behavior, and `web_runs/` output layout**

```markdown
uv run tradingagents-web
# open http://127.0.0.1:8000
```

- [ ] **Step 2: Run the full test suite**

Run: `uv run --with pytest python -m pytest -q`
Expected: PASS

- [ ] **Step 3: Start the local web server and verify one real run**

Run: `uv run tradingagents-web`
Expected: Page loads in Chinese, clicking submit shows live step events, and a new `web_runs/<ticker>/<date>/<timestamp>_<run_id>/` directory appears with `input.json`, `events.log`, `stdout.log`, `stderr.log`, `partials/`, and either `complete_report.md` or `error.md`.
