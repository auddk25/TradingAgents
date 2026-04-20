# Custom Gateway Fallback Chain Investigation

## Symptom

Web runs against the custom OpenAI-compatible gateway can fail even after retry/fallback logic is active.

Recent failures:

- `gpt-5.2` returns `502 unknown provider`
- fallback to `gpt-4.1` returns `503 model_not_found`

## Attempts

1. Added retry and provider-safe fallback for `openai` provider.
2. Restricted fallback away from `grok-*` after mixed-provider responses broke LangChain response parsing.
3. Retested with `gpt-4.1` as fallback and observed repeated `model_not_found`.

## Evidence

- `web_runs/ORCL/2026-04-20/20260420_195224_ad211ed7895c4d47b38d181df7e0d8f7/error.md`
- `web_runs/ORCL/2026-04-20/20260420_195224_ad211ed7895c4d47b38d181df7e0d8f7/stdout.log`

Observed sequence:

- primary `gpt-5.2` fails twice with `502 unknown provider`
- fallback `gpt-4.1` fails twice with `503 model_not_found`

## Hypothesis

The custom gateway does not expose the same model inventory as official OpenAI. Fallback models must be chosen from gateway-tested model IDs rather than provider-native OpenAI catalog defaults.

## Next Step

Change the custom gateway fallback defaults to the models already observed to return non-empty chat responses on this gateway, and keep `OPENAI_FALLBACK_MODELS` as an explicit override for future tuning.
