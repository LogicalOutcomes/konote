# Self-Hosted AI Model — Summary

## What It Is

A dedicated AI server hosted in Canada (OVHcloud, Beauharnois QC) running a high-quality open-source language model. Think of it as our own private ChatGPT — no data leaves Canada, no per-question charges, unlimited use.

## How You'd Use It

You connect **OpenWebUI** (the chat interface you're already familiar with) to this server as a custom model. In OpenWebUI's connection settings, you point it to our server's address and it appears as an available model alongside any others.

### Data Cleaning Workflow

For survey analysis with open-ended responses:

1. **Paste raw responses into OpenWebUI** and ask the model to strip names, locations, contact details, and other identifying information
2. **The model cleans and structures the data** — fixes formatting, flags low-quality responses, outputs a clean de-identified dataset
3. **Take the cleaned data to Claude** (or another frontier AI) for deep thematic analysis — since the PII is already gone, there's no privacy concern

The self-hosted model handles the privacy-sensitive work. The frontier model handles the analytical work. Best of both worlds.

## Pricing (OVHcloud Canada)

All prices in Canadian dollars.

| Server | Specs | Monthly Cost |
|--------|-------|-------------|
| Minimum | 8 CPUs, 24 GB RAM | ~$23/mo |
| **Recommended** | **12 CPUs, 48 GB RAM** | **~$40/mo** |
| Upgrade | 16 CPUs, 64 GB RAM | ~$59/mo |

The recommended tier runs the **Qwen3.5-35B-A3B** model — a high-quality open-source model that scores competitively with commercial AI on benchmarks. Fixed monthly cost, unlimited use, no per-question charges.

Multiple people across multiple organisations can connect their own OpenWebUI instances to the same server simultaneously.
