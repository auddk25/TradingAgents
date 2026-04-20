# Refactor Report R2

## Scope
- Added ticker-scoped short-summary memory under `memory_runs/` via `tradingagents/agents/utils/summary_memory.py`.
- Centralized fresh-run initialization in `TradingAgentsGraph.prepare_initial_state()` and centralized summary persistence in `TradingAgentsGraph.persist_run_summary()`.
- Updated real execution paths in CLI and web runner to use the fresh-run initializer instead of calling `graph.graph.stream(...)` with raw initial state.
- Simplified report persistence so the primary saved report focuses on analyst summaries plus manager decisions rather than raw bull/bear/risk transcript sections.
- Tightened web defaults and tests so OpenAI quick/deep defaults both resolve to `gpt-5.4`.

## Risks
- Prompt-contract changes rely on model compliance with numbered section headings; summary extraction now tolerates numbered headings, but real-model drift is still possible.
- CLI and web now both persist summary memory through graph-level helpers; future direct graph invocations should also use those helpers to avoid bypassing the contract again.
- The web SSE completion payload still includes inline markdown for compatibility, even though the UI is path-first.

## Verification
- Targeted: `uv run --with pytest python -m pytest -q tests/test_report_structure.py tests/test_web_app.py tests/test_report_encoding.py`
- Regression subset: `uv run --with pytest python -m pytest -q tests/test_default_config.py tests/test_client_base_url_resolution.py tests/test_cli_provider_selection.py tests/test_model_validation.py tests/test_google_api_key.py tests/test_ticker_symbol_handling.py`
- Full suite: `uv run --with pytest python -m pytest -q`

## Verification Gaps
- Did not run a manual browser click-through against the live web app in this pass.
- Did not run a full end-to-end live analysis against an external model gateway in this pass.
