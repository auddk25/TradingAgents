# Empty Web Report Investigation

## Symptom
- Multiple web runs complete with `run_completed`, but `complete_report.md` only contains the report header.
- `memory_runs/<ticker>/latest_summary.md` is empty for those runs.
- Earlier runs also showed premature stage-start events and no useful partial artifacts.

## Attempts
1. Fixed stage progress so empty `investment_debate_state` / `risk_debate_state` no longer mark teams as started.
2. Rewired CLI/web execution paths to use `TradingAgentsGraph.prepare_initial_state()` and summary-memory helpers.
3. Re-ran the web app and submitted fresh SPY runs.
4. Tested the configured gateway directly through the OpenAI SDK using both `chat.completions` and `responses`.

## Evidence
- `web_runs/SPY/2026-04-20/20260420_182144_3f5ad08b7ecf43fcb5f9e63fc195b026/complete_report.md` contains only the title block.
- `events.log` for that run shows normal stage progression and `run_completed`, but no saved manager output appears in the final markdown payload.
- `memory_runs/SPY/latest_summary.md` is empty for that run, indicating no final decision content was available to summarize.
- Analyst nodes currently only write `*_report` when `len(result.tool_calls) == 0`; otherwise they return an empty report and depend on subsequent tool-loop iterations to produce text.
- Direct gateway test with `OpenAI(..., base_url=OPENAI_BASE_URL).chat.completions.create(...)` returned `finish_reason="stop"` but `choices[0].message.content == null` and `tool_calls == null` for the trivial prompt `Reply with exactly OK.`.
- Direct gateway test with `client.responses.create(...)` raised `TypeError: 'NoneType' object is not iterable` because `response.output` was `None`.
- Direct tool-calling test also returned `content == null` and `tool_calls == null`, so the tool loop cannot begin reliably on this gateway/model combination.

## Hypothesis
- The configured gateway/model combination is returning empty assistant payloads at the API layer, even for trivial prompts. That alone can explain empty analyst/manager reports, empty final summaries, and empty saved reports.
- There may still be secondary graph-state or persistence issues, but the gateway behavior is already sufficient to cause the observed empty-report failures.

## Next Step
- Confirm whether the issue is specific to:
  1. this gateway
  2. this model ID on the gateway
  3. the OpenAI-compatible API mode being used
- If the gateway continues to return null assistant payloads, treat it as an upstream incompatibility rather than a TradingAgents-only bug.
