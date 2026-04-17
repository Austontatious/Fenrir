# Frontend Usage

## First Screen Priorities

The local UI is setup-first.

It answers:

- is Fenrir running,
- where Fenrir is running,
- what endpoint is configured,
- whether endpoint connection is healthy,
- which battery/conditions are available,
- how to run evaluation immediately.

## Setup Flow

1. Open local URL printed on startup.
2. Set provider (`openai_compatible` or `mock`).
3. Set base URL, model, timeout, and API key/token.
4. Save configuration.
5. Run `Test Connection`.
6. Run `Run Evaluation`.
7. Review canonical readout and optional export.

## Direct Model Configuration (Primary)

Primary UX is direct model adapter configuration.

Supported in this phase:

- OpenAI-compatible endpoints,
- mock provider for local smoke/demo.

## Optional MCP Info (Secondary)

The MCP panel shows:

- enabled/disabled state,
- host/port metadata,
- tool-facade command snippets,
- reminder that MCP mode is optional integration.

## Readout and Export

The UI displays canonical heuristic readout from the latest hybrid summary artifact.

Export options:

- canonical JSON/markdown artifacts (primary),
- LLM-native derived export (secondary convenience).

The LLM-native export preserves uncertainty and explicit non-claim guardrails.
