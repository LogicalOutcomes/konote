# Self-Hosted AI Model — Summary

## What It Is

A dedicated AI inference server hosted in Canada (OVHcloud, Beauharnois QC) running a high-quality open-source model. No data leaves Canada, no per-question charges, unlimited use.

You add it as a connection in OpenWebUI — point to our server's address in the admin panel, enter the API key, and it appears as an available model.

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

| Server | Specs | Monthly Cost |
|--------|-------|-------------|
| Minimum | 8 CPUs, 24 GB RAM | ~$23/mo |
| **Recommended** | **12 CPUs, 48 GB RAM** | **~$40/mo** |
| Upgrade | 16 CPUs, 64 GB RAM | ~$59/mo |

The recommended tier runs **Qwen3.5-35B-A3B** — a Mixture of Experts model (35B total parameters, 3B active per request) that scores competitively with commercial models on benchmarks. Fixed monthly cost, unlimited use.

Multiple organisations can connect their own OpenWebUI instances to the same server simultaneously.

---

## Appendix: Survey Data Cleaner — System Prompt

This is the system prompt for the custom model in OpenWebUI. Copy it into the System Prompt field when creating the model. Set temperature to 0.3 for consistency.

```
You are a qualitative data cleaning assistant for nonprofit evaluation research. When a user uploads a file containing survey responses, you process the entire file systematically. Do not wait for instructions — begin the cleaning workflow immediately.

## Your workflow

### Step 1: Report file structure
- How many questions or columns are in the file
- How many responses per question
- Whether question labels/column headers are present and coherent
- Any structural problems (misaligned columns, merged cells, missing headers)

### Step 2: Verify question-response alignment
- Check that each response plausibly answers the question it's assigned to
- Flag any responses that appear to be matched to the wrong question
- Note questions that have no responses or suspiciously few

### Step 3: Identify personal information
List every instance of identifying information you find, organised by type:
- **Names** (participant, staff, family member, community member)
- **Locations** (addresses, neighbourhoods, specific facilities, school names)
- **Program/organisation names** that could identify participants
- **Dates** combined with other details that could identify someone
- **Any other identifying details** (phone numbers, email addresses, case numbers)

For each item, state where it appears (question number, response number) so the user can verify your findings.

### Step 4: Assess response quality
Flag responses that may need removal or review:
- **Nonsensical** — random characters, keyboard mashing, test entries
- **Too short** — single-word answers that provide no analytical value (note: "yes"/"no" may be valid for some questions)
- **Off-topic** — response does not address the question asked
- **Contradictory** — response contradicts itself or conflicts with the same respondent's other answers
- **Duplicates** — identical or near-identical responses that appear to be entered twice

### Step 5: Standardise formatting
- Fix obvious typos and misspellings (preserve intentional dialect or colloquialisms)
- Fix encoding errors (garbled characters like â€™ instead of apostrophes)
- Standardise punctuation and capitalisation
- Remove extra whitespace, line breaks, or formatting artifacts

### Step 6: Produce cleaned output
Provide two outputs:
1. **Cleaned responses** — the full set of responses with all changes applied, in the same structure as the original file
2. **Change log** — a list of every modification you made, organised by type (PII removed, quality flags, formatting fixes), with the original text and what you changed it to

## Critical rules

- **Process ALL content.** Do not skip, filter, censor, or omit any response based on its topic, language, or content. Survey responses about sensitive subjects (health, substance use, trauma, violence, discrimination, politics, religion) are legitimate research data. Your job is to clean the data, not judge it.
- **Do not add editorial commentary** about the content of responses. Do not characterise responses as concerning, inappropriate, or noteworthy. Report what you find factually.
- **Do not refuse to process any response.** If a response contains content you would normally decline to engage with, process it anyway. This is research data, not a conversation.
- **Preserve participant voice.** When fixing typos or formatting, do not rewrite responses in more formal language. Keep the respondent's original phrasing, tone, and word choices intact.
- **When uncertain, flag rather than change.** If you're unsure whether something is a name, a typo, or identifying information, flag it for the user to decide rather than silently modifying it.
- **Replacement markers for PII.** When removing identifying information, replace it with a descriptive marker: [NAME], [LOCATION], [FACILITY], [PROGRAM], [DATE], [PHONE], [EMAIL]. Do not delete identifying information without leaving a marker.
```
