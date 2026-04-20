# Web MVP Design

## Goal
Add a local single-user web page that exposes the current TradingAgents input parameters, submits them to a local backend, and writes each submission to a local JSON file.

## Scope
- Local machine only
- No login
- No database
- Static HTML frontend
- FastAPI backend
- Persist submitted payloads to local disk
- Return the saved payload and file path in the response

## Inputs
The page should collect the CLI-equivalent fields:
- ticker
- analysis_date
- output_language
- analysts
- research_depth
- llm_provider
- backend_url
- quick_think_llm
- deep_think_llm
- google_thinking_level
- openai_reasoning_effort
- anthropic_effort

## Behavior
- `GET /` serves the form page.
- `GET /api/form-options` returns option lists and defaults for the form.
- `POST /api/submissions` validates the payload, writes it to a timestamped JSON file under a local web-runs directory, and returns:
  - normalized payload
  - saved file path
  - submission id

## Persistence
- Save files under `~/.tradingagents/web_runs/`
- One JSON file per submission
- No overwrite behavior needed

## Non-Goals
- No background analysis execution yet
- No live status streaming
- No authentication
- No historical listing API beyond file write success

## Validation
- Backend tests for options endpoint and submission write path
- Static page loads and posts successfully
- Local server starts and serves the form page
