# AI-Powered Translation — IMPLEMENTED

**Status:** Done (2026-02-07)

## How It Works

`python manage.py translate_strings` extracts translatable strings, auto-translates empty ones via any OpenAI-compatible API, and compiles the .mo file.

## Configuration

Set these environment variables on your development machine:

| Variable | Purpose | Default |
|---|---|---|
| `TRANSLATE_API_KEY` | API key (required) | — |
| `TRANSLATE_API_BASE` | API base URL | `https://api.openai.com/v1` |
| `TRANSLATE_MODEL` | Model to use | `gpt-5` |

## Provider Examples

| Provider | `TRANSLATE_API_BASE` | `TRANSLATE_MODEL` |
|---|---|---|
| OpenAI | (default) | `gpt-5` (default) |
| Open Router | `https://openrouter.ai/api/v1` | `anthropic/claude-sonnet-4` |
| Anthropic | Not directly compatible — use Open Router | — |
| Local (Ollama) | `http://localhost:11434/v1` | `llama3` |

## Design Decisions

- **No vendor SDK** — uses `requests` (already a dependency) with the OpenAI chat completions format
- **Flagship model by default** — translation quality matters; this runs infrequently
- **Provider-agnostic** — each deploying agency chooses their own API provider
- **`validate_translations.py` errors on empty strings** — prevents untranslated text from shipping
