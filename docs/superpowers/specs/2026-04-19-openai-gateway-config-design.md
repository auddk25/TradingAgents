# Provider Gateway Config Design

## Goal
Make provider gateway URLs configurable from `.env` so changing gateways does not require source edits.

## Scope
- Treat provider-specific environment variables as the single runtime input for gateway URLs.
- Keep existing built-in URLs as fallbacks when the matching environment variable is unset.
- Make CLI provider selection, Python API defaults, and client construction resolve from the same setting.

## Behavior
- If `.env` contains `OPENAI_BASE_URL=https://gateway.example/v1`, the CLI should present that URL for the `OpenAI` provider.
- If `.env` contains `XAI_BASE_URL=https://xai-gateway.example/v1`, provider resolution for `xai` should use that URL.
- If `.env` contains `AZURE_OPENAI_ENDPOINT=https://azure.example.com/`, Azure resolution should use that endpoint.
- If a provider-specific variable is missing, resolution should fall back to the provider's current default URL or `None` where no default exists.

## Non-Goals
- No model-selection changes.
- No CLI UX redesign.

## Validation
- Unit test provider URL resolution with and without provider-specific environment variables.
- Unit test OpenAI-compatible and Azure clients to confirm they consume the resolved URLs.
- Run the current targeted test set and confirm the CLI help command still works.
