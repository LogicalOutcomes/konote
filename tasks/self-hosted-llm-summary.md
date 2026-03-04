# Self-Hosted AI Model — Summary

## What It Is

A dedicated AI inference server hosted in Canada (OVHcloud, Beauharnois QC) running an open-source model. No data leaves Canada, no per-question charges, unlimited use.

You add it as a connection in OpenWebUI — point to the server's address in the admin panel, enter the API key, and it appears as an available model.

## What It's For

The main use case is **data cleaning for qualitative analysis** — preparing raw survey responses so they're ready for deep analysis by a frontier model.

### How the Two-Stage Workflow Works

**Stage 1 — Data cleaning (self-hosted model, in Canada)**

You have a file of open-ended survey responses — a spreadsheet, a Word document, a PDF. The raw data typically has problems: questions may be mislabelled, responses may contain participant names or other identifying details, some answers may be nonsensical or off-topic, and formatting is often inconsistent.

Open a chat in OpenWebUI connected to our self-hosted model. Upload your file (Excel, CSV, Word, PDF) and ask the model to:

- **Verify structure** — confirm that questions/columns are correctly labelled and responses are matched to the right questions
- **Remove identifying information** — strip participant names, locations, program names, worker names, and other personal details
- **Assess response quality** — flag responses that are nonsensical, too short to be useful, off-topic, or contradictory
- **Standardise formatting** — fix typos, encoding errors (garbled characters), inconsistent spelling, and duplicate entries
- **Document what was changed** — note what was removed, flagged, or corrected so you have a record of your cleaning decisions

You can do this iteratively — upload the file, review what the model finds, ask follow-up questions, and refine until the data is clean. The model has a 262K-token context window, so it can handle hundreds of responses in a single conversation.

OpenWebUI is configured to bypass RAG (no chunking, no embedding, no vector search). When you upload a file, OpenWebUI extracts the full content and sends it directly to the model as part of the conversation. The data travels encrypted (HTTPS) to our Canadian server, is processed in memory, and the cleaned result comes back. Nothing is saved on the inference server between requests — Ollama doesn't retain conversation history.

Your conversation history (including the uploaded file content) is stored in **your** OpenWebUI instance, on your own machine — not on the inference server.

**Stage 2 — Deep analysis (frontier model)**

Copy the cleaned output from your OpenWebUI conversation, or download it as a file. Then open Claude, ChatGPT, or whichever frontier model you prefer and paste or upload it there. Ask it to do the deeper analytical work — thematic coding, pattern identification, narrative summaries, cross-question analysis.

Since personal information was already stripped in Stage 1, there's no privacy concern sending this data to a commercial API.

### Why Two Stages?

Data cleaning is methodical work — checking labels, spotting names, flagging junk responses, fixing formatting. The self-hosted model handles this well. But deep qualitative analysis (nuanced thematic coding, interpreting meaning across hundreds of responses, surfacing unexpected patterns) is where frontier models are significantly better. Splitting the work gives you both data sovereignty and analytical quality.

## What We'd Build: A "Survey Data Cleaner" Custom Model

Rather than asking users to remember all the cleaning steps themselves, we'd create a custom model in OpenWebUI called **Survey Data Cleaner**. This is a pre-configured model with built-in instructions — the user just selects it from the model dropdown and uploads their file.

The custom model would automatically:

1. **Report what it found** — number of questions, number of responses, file structure, any obvious problems
2. **Check question labels** — verify that columns or headings match the response content, flag mismatches
3. **Scan for identifying information** — list every name, location, or personal detail it found, and where
4. **Flag quality issues** — nonsensical responses, too-short answers, off-topic entries, contradictions
5. **Fix formatting** — typos, encoding errors, inconsistent spelling, duplicates
6. **Produce cleaned output** — the cleaned responses in a consistent format, plus a change log documenting every modification

The user reviews the output, asks follow-up questions if needed, and iterates. When satisfied, they copy or download the cleaned data for Stage 2.

This is a Modelfile in OpenWebUI — no code required, just a system prompt and parameter settings. RAG is disabled on this model so uploaded files are sent directly to the model in full, not chunked or embedded. We can create and test it before the server is even set up, using a local Ollama install.

## First Step: Testing

Before committing to the server, we'll test the full workflow locally:

1. Install Ollama on a laptop and pull the Qwen3.5 model
2. Connect your OpenWebUI instance to the local Ollama
3. Create the Survey Data Cleaner custom model with its system prompt
4. Upload real survey data (or realistic sample data) and run through the cleaning process
5. Evaluate the results — did it catch the PII? Did it flag the junk responses? Is the change log useful?

If the model handles the cleaning well locally, it will work identically on the server — just faster with more RAM. If it doesn't, we adjust the system prompt or try a different model before spending anything on hosting.

## Pricing (OVHcloud Canada)

All prices in Canadian dollars.

### VPS (for smaller models, CPU-only)

| Server | Specs | Monthly Cost | Best model that fits |
|--------|-------|-------------|---------------------|
| Minimum | 8 CPUs, 24 GB RAM | ~$23/mo | Qwen 3.5-35B-A3B (20 GB) |
| **Recommended** | **12 CPUs, 48 GB RAM** | **~$40/mo** | **Qwen 3.5-35B-A3B (comfortable)** |
| Upgrade | 16 CPUs, 64 GB RAM | ~$59/mo | Llama 3.3 70B (42 GB) |

### Bare Metal (for large models, CPU-only)

| Server | CPU | RAM | Monthly Cost | Best model that fits |
|--------|-----|-----|-------------|---------------------|
| Advance-1 (2026) | AMD EPYC 4245P (6c/12t) | 192 GB | ~$186-229/mo | Qwen3 235B (134 GB) |
| **Advance-2 (2026)** | **AMD EPYC 4345P (8c/16t)** | **256 GB** | **~$223-286/mo** | **Qwen 3.5 397B (214 GB)** |
| Scale-a1 | AMD EPYC 9124 (16c/32t) | 256 GB | ~$600+/mo | DeepSeek V3.2 (250+ GB) |

*CPU inference on MoE models: ~3-5 tok/s. A 30K-token data cleaning job takes ~100 minutes on the 397B.*

The VPS recommended tier runs **Qwen3.5-35B-A3B** — a Mixture of Experts model (35B total parameters, 3B active per request) that scores competitively with commercial models on benchmarks. The bare metal Advance-2 runs the full **Qwen 3.5 397B** — an S-tier model with top reasoning scores. Fixed monthly cost, unlimited use.

Multiple organisations can connect their own OpenWebUI instances to the same server simultaneously.

---

## Appendix: Data Cleaner — System Prompts

Two variants of the Data Cleaner are configured in OpenWebUI. Both use temperature 0.3. The full system prompts are maintained in the open-webui repo:

- **Data Cleaner (35B)** — simplified prompt for the smaller Qwen 3.5-35B-A3B model (~3B active params). Four-step assessment, no code interpreter.
- **Data Cleaner (397B)** — full prompt for the larger Qwen 3.5-397B-A17B model (~17B active params). Five-step assessment with code interpreter, regex-based PII scanning, re-identification risk assessment, and quantitative summary statistics.

Both prompts share the same core workflow:

1. **Two-phase process** — Phase 1 assesses and reports (structure, PII, quality, formatting). Phase 2 produces cleaned output only after the user reviews and confirms.
2. **Three data types** — survey responses, interview/focus group transcripts, and other text data (field notes, open-ended feedback).
3. **Transcript cleaning** — removes Zoom/Teams timestamps, platform artifacts, and filler words (asks user whether they're doing thematic or discourse analysis before removing fillers).
4. **Privacy-first PII detection** — flags names, locations, contact details, identifying combinations, and meeting metadata. Uses numbered markers ([NAME-1], [LOCATION-1]) so cross-references are preserved.
5. **De-identification key** — output separately with a warning to store apart from cleaned data.
6. **Critical rules** — process all content regardless of subject matter, preserve participant voice, flag rather than change when uncertain, never produce cleaned output before user confirms.
7. **Canadian context** — Canadian English spelling, PIPEDA compliance reference, bilingual PII patterns (English and French).
