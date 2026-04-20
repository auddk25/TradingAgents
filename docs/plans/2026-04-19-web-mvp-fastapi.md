# Web MVP FastAPI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a local web page that captures TradingAgents parameters and posts them to a FastAPI backend which saves each submission to a local JSON file.

**Architecture:** Use a small FastAPI app to serve one static HTML page and two JSON endpoints. Keep the frontend intentionally thin: fetch form options, render defaults, POST the form, and display the saved payload plus file path. Store submissions as timestamped JSON files under the user's TradingAgents home directory.

**Tech Stack:** Python, FastAPI, Uvicorn, Pydantic, static HTML/CSS/JavaScript, pytest

---

### Task 1: Lock The Web Contract

**Files:**
- Create: `tests/test_web_app.py`

- [ ] **Step 1: Write failing tests for `GET /api/form-options` and `POST /api/submissions`**
- [ ] **Step 2: Run the tests to verify they fail**

### Task 2: Add The Backend

**Files:**
- Modify: `pyproject.toml`
- Create: `tradingagents/web/__init__.py`
- Create: `tradingagents/web/app.py`
- Create: `tradingagents/web/models.py`
- Create: `tradingagents/web/storage.py`

- [ ] **Step 1: Add FastAPI and Uvicorn dependencies**
- [ ] **Step 2: Implement form option/default generation from existing CLI choices**
- [ ] **Step 3: Implement validated submission persistence to local JSON files**
- [ ] **Step 4: Run tests to verify backend behavior**

### Task 3: Add The Frontend

**Files:**
- Create: `tradingagents/web/static/index.html`
- Create: `tradingagents/web/static/app.js`
- Create: `tradingagents/web/static/styles.css`

- [ ] **Step 1: Render a form for the CLI-equivalent fields**
- [ ] **Step 2: Fetch options/defaults from the backend**
- [ ] **Step 3: Submit JSON to the backend and render the saved result**

### Task 4: Verify Local Startup

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Start the FastAPI app locally**
- [ ] **Step 2: Confirm `GET /` loads**
- [ ] **Step 3: Submit one payload and verify a JSON file is written**
