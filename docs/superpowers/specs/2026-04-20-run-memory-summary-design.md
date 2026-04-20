# Run Memory Summary Design

## Goal
Keep each analysis run logically fresh while still preserving a minimal amount of useful continuity from prior runs.

The system must not carry forward full prior prompts, debate transcripts, or reports into the next run. Instead, it may inject one short prior-run summary as optional context. This summary is reference material, not a source of truth.

## Core Behavior

### Fresh Run Baseline
- Every new run starts with empty run-state:
  - `messages`
  - `investment_debate_state`
  - `risk_debate_state`
- No previous `web_runs/`, `partials/`, `complete_report.md`, or `engine_results/` files are read back into prompts.

### Allowed Memory
- The only cross-run reasoning context allowed by default is a short summary.
- The summary is optional and may be empty.
- Empty summary is the normal first-run boundary case.
- The summary is keyed by ticker, not shared globally across instruments.

### Summary Contract
- One summary per ticker is stored as the current carry-forward memory.
- The summary must be short:
  - target: 6 bullets or fewer
  - hard cap: about 180 words
- The summary should contain only:
  - prior short-term action
  - prior long-term ownership view
  - core reasons
  - key risk
  - unresolved question
  - what would change the conclusion

### Summary Scope
- The short summary may be shown to:
  - `research_manager`
  - `portfolio_manager`
  - optionally `trader`
- The short summary must not be injected into:
  - analyst tool prompts
  - bull researcher raw debate prompt
  - bear researcher raw debate prompt
  - risk debator raw debate prompt

### Prompt Rule
Whenever a prior summary is present, prompts must frame it as:
- prior compressed context
- useful for continuity
- subordinate to current evidence

Required instruction pattern:
- "This prior summary is reference only."
- "If current evidence conflicts with the summary, prefer current evidence."

## Memory Storage Layout
The repository should keep a dedicated local memory directory for later review and aggregation.

Recommended layout:

```text
repo/memory_runs/
  TSM/
    latest_summary.md
    summaries/
      20260420_132804.md
      20260421_091500.md
    snapshots/
      20260420_132804.json
      20260421_091500.json
```

### Files
- `latest_summary.md`
  - the currently active short carry-forward summary for this ticker
- `summaries/<timestamp>.md`
  - immutable historical summary snapshots
- `snapshots/<timestamp>.json`
  - structured metadata for later analysis, including:
    - ticker
    - run id
    - analysis date
    - provider
    - model selection
    - summary text
    - report path
    - error path if present

## Generation Flow
1. Start run with empty in-memory debate state.
2. Load ticker-specific `latest_summary.md` if it exists.
3. Inject only that short summary into approved high-level nodes.
4. Complete the run.
5. Generate a new short summary from the final decision.
6. Save the new summary into the ticker memory directory.
7. Update `latest_summary.md`.

## Non-Goals
- Do not reuse full previous debate transcripts.
- Do not build retrieval over all prior run documents in this iteration.
- Do not allow one ticker's summary to influence another ticker.
- Do not make historical summary mandatory for a run to start.

## Validation
- First run with no prior summary must succeed.
- Second run for the same ticker must see only the short summary, not full prior reports.
- A run for a different ticker must not receive another ticker's summary.
- The memory directory must contain both the current summary and historical snapshots.
