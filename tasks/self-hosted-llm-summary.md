# Self-Hosted AI Model — Summary

## What It Is

A dedicated AI inference server hosted in Canada (OVHcloud, Beauharnois QC) running a high-quality open-source model. No data leaves Canada, no per-question charges, unlimited use.

You add it as a connection in OpenWebUI — point to our server's address in the admin panel, enter the API key, and it appears as an available model.

## What It's For

The main use case is **data cleaning for qualitative analysis** — stripping identifying information from raw survey responses so they can safely be sent to a frontier model for deep analysis.

### How the Two-Stage Workflow Works

**Stage 1 — De-identification (self-hosted model, in Canada)**

You have a spreadsheet of open-ended survey responses. Some contain participant names, locations, program names, worker names, or other identifying details.

Open a chat in OpenWebUI connected to our self-hosted model. Upload your spreadsheet (Excel, CSV) and ask the model to:

- Remove all names, locations, and identifying details
- Clean up formatting (fix typos, encoding issues, duplicate entries)
- Flag responses that are too short or off-topic to be useful
- Output the cleaned responses in a structured format

OpenWebUI extracts the content from the uploaded file and sends it to our model on the Canadian server. The data travels encrypted (HTTPS), is processed in memory, and the cleaned result comes back. Nothing is saved on the inference server between requests — Ollama doesn't retain conversation history.

Your conversation history (including the uploaded file content) is stored in **your** OpenWebUI instance, on your own machine — not on the inference server.

**Stage 2 — Thematic analysis (frontier model)**

Take the de-identified output from Stage 1 and bring it to Claude, ChatGPT, or whichever frontier model you prefer. Ask it to do the deep analytical work — thematic coding, pattern identification, narrative summaries.

Since the PII was already stripped in Stage 1, there's no privacy concern sending this data to a commercial API.

### Why Two Stages?

The self-hosted model is good enough for data cleaning — identifying names, addresses, and personal details is a relatively straightforward task. But deep qualitative analysis (nuanced thematic coding, interpreting meaning across hundreds of responses) is where frontier models are significantly better. Splitting the work gives you both data sovereignty and analytical quality.

## Pricing (OVHcloud Canada)

All prices in Canadian dollars.

| Server | Specs | Monthly Cost |
|--------|-------|-------------|
| Minimum | 8 CPUs, 24 GB RAM | ~$23/mo |
| **Recommended** | **12 CPUs, 48 GB RAM** | **~$40/mo** |
| Upgrade | 16 CPUs, 64 GB RAM | ~$59/mo |

The recommended tier runs **Qwen3.5-35B-A3B** — a Mixture of Experts model (35B total parameters, 3B active per request) that scores competitively with commercial models on benchmarks. Fixed monthly cost, unlimited use.

Multiple organisations can connect their own OpenWebUI instances to the same server simultaneously.
