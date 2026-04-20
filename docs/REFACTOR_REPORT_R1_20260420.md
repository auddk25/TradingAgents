# Refactor Report R1 20260420

## Scope
- Simplified the local web control panel so the default form shows only the core inputs and moves quick/deep model overrides plus provider-specific reasoning controls into an advanced section.
- Added parameter help text, a `主模型` control, and path-first result/error display in the web UI.
- Added runtime model preflight for run creation so invalid model names and gateway-unavailable models can be rejected before a background run starts.
- Compressed analyst, researcher, and risk-agent prompt contracts toward short structured reasoning cards instead of long narrative transcripts.
- Reworked manager-level prompts and final report assembly to emphasize:
  - future business path
  - what the market is pricing
  - gap between price and future path
  - short-term tactical action vs long-term ownership view

## Risk Areas
- Runtime model probing is only implemented for OpenAI-compatible providers and Azure. Google and Anthropic still rely on static validation.
- Run-completion SSE payloads still include full markdown and traceback for compatibility, even though the web UI no longer renders them directly.
- Prompt compression changes output shape, so downstream report quality should still be checked with a real end-to-end run against the active gateway.

## Verification
- `uv run --with pytest python -m pytest -q tests/test_web_app.py tests/test_report_structure.py tests/test_report_encoding.py`
  - `15 passed`
- `uv run --with pytest python -m pytest -q`
  - `37 passed, 2 warnings, 40 subtests passed`

## Not Verified
- No live end-to-end TradingAgents web run was executed against the current gateway after this final integration pass.
- No manual browser smoke test was rerun after the final preflight change; UI behavior is covered by tests only in this pass.
