# AI-Assisted Admin Toolkit

Task ID: DEPLOY-TOOLKIT1
Related: DEPLOY-PC1 (deployment protocol), DEPLOY-TEMPLATE1 (config templates), ADMIN-UX1 (admin self-service)

## The Idea

Instead of building custom software tools for agency deployment and configuration, assemble a set of **decision documents** — structured reference materials that any AI tool (Claude, ChatGPT, etc.) can consume to guide a person through the process.

The admin (or developer) opens their AI tool of choice, gives it the relevant decision documents, and says "help me set up KoNote for my agency." The AI reads the documents, asks the right questions, captures answers, and produces configuration output.

## Why This Approach

1. **AI tools are evolving fast.** Anything custom we build today (skills, plugins, MCP servers) may be obsolete in months. Well-structured reference documents work with any AI tool, now and later.
2. **The knowledge is the asset, not the tooling.** Our deployment protocol and config templates already capture most of the knowledge. We just need to reformat it so AI tools can use it effectively.
3. **It scales without us.** Once decision documents exist, any competent AI tool can run the conversation. We don't need to be in the room for every agency setup.
4. **It works for different users.** Today, our developer uses Claude Code desktop. Next month, an admin might use Claude.ai or the Claude desktop app. Next year, who knows. The documents work for all of them.

## What Already Exists

We're not starting from scratch. These assets already capture most of the deployment knowledge:

| Asset | Location | What it covers |
|-------|----------|---------------|
| Deployment Protocol | [tasks/prosper-canada/deployment-protocol.md](prosper-canada/deployment-protocol.md) | Full 5-phase onboarding process with interview scripts |
| Config Templates | [config_templates/](../config_templates/) | Pre-built configuration for financial coaching agencies |
| Permissions Interview | [tasks/agency-permissions-interview.md](agency-permissions-interview.md) | Guided interview for roles and access decisions |
| Admin Docs | [docs/admin/](../docs/admin/) | Feature-by-feature admin documentation |
| Deploying KoNote | [docs/deploying-konote.md](../docs/deploying-konote.md) | Platform comparison and technical deployment guides |

## What's Missing: AI-Consumable Decision Documents

The existing docs are written for humans reading linearly. AI tools work better with **structured decision documents** — each covering one configuration domain, with a consistent format:

```markdown
# [Domain Name]

## What This Configures
2-3 sentences in plain language.

## Decisions Needed
1. Question in plain language?
   - Option A -> consequence
   - Option B -> consequence
   - Default: [what happens if you skip this]

2. Next question...

## Common Configurations
- Financial coaching agency: [pre-answered set]
- Mental health agency: [pre-answered set]

## Output Format
[What the completed configuration looks like --
YAML/JSON snippet, admin steps, or management command]

## Dependencies
- Requires: [what must be done first]
- Feeds into: [what uses this configuration]

## Example: [funder partner]
[Completed decisions with rationale]
```

This format works because:
- Any LLM can parse the structure and run an interactive Q&A session
- The "decisions needed" list tells the AI exactly what to ask
- The "consequences" help the AI explain trade-offs conversationally
- The "common configurations" give starting points so agencies only discuss exceptions
- The "output format" tells the AI what to produce

## Decision Document Set

One document per configuration domain. Organised in setup order.

| # | Document | Decisions Covered | Source Material |
|---|----------|------------------|----------------|
| 00 | Overview | Order of operations, what "fully configured" means | deployment-protocol.md |
| 01 | Terminology | What to call participants, plans, notes, etc. | deployment-protocol.md 3.1 |
| 02 | Features | Which modules to enable/disable | agency-permissions-interview.md Session 2.7 |
| 03 | Roles & Permissions | Who can see and do what | agency-permissions-interview.md (full) |
| 04 | Programs | How work is organised, confidentiality | deployment-protocol.md 3.2 |
| 05 | Surveys & Metrics | What outcomes to track, assessment tools | deployment-protocol.md 3.3 |
| 06 | Plan & Note Templates | Structure for coaching plans and session notes | deployment-protocol.md 3.4-3.5 |
| 07 | Reports | What funders need, export formats | report-template.json, RPT-SCHEMA1 |
| 08 | Users | Initial accounts, authentication method | deployment-protocol.md Phase 2, 4 |
| 09 | Verification | Confirm everything works | deployment-protocol.md Phase 4 |

Most of the content for these already exists in the deployment protocol and permissions interview. The work is **reformatting**, not writing from scratch.

## Two-Week Plan: [funder partner] Prototype

The first test is [funder partner], where our developer ([Dev]) uses Claude Code desktop to do the setup. This is our instrumented prototype.

### Week 1 (by Mar 1)

| Day | Action | Owner |
|-----|--------|-------|
| 1-2 | Create 00-overview.md — the master document mapping the full setup journey | GG |
| 2-3 | Create decision documents 01-06 by reformatting deployment-protocol.md sections | GG |
| 3-4 | Fill in [funder partner] examples using existing config_templates/ data | GG |
| 4-5 | Developer dry-run: [Dev] opens Claude Code desktop, gives it the docs, attempts to configure a test instance. **Keeps a friction log.** | PD |

### Week 2 (Mar 1-7)

| Day | Action | Owner |
|-----|--------|-------|
| 1-2 | Fix gaps identified in the friction log | GG |
| 3-5 | Developer does the real [funder partner] setup using the documents + Claude | PD |
| 5 | Retrospective: what worked, what didn't, what would an admin need that the developer didn't | All |

### The Friction Log

The most important artefact from the prototype. During both the dry run and real setup, [Dev] keeps a simple markdown file noting every point where:

- The reference doc didn't answer a question Claude asked
- Claude couldn't figure out how to do something from the docs alone
- A step required manual work that should have been documented
- The AI gave wrong or confusing guidance
- Something took much longer than expected

This log drives the next iteration. It's also the kind of thing an AI tool can help organise — dump the log in and ask "what are the top five gaps?"

## Long-Term Vision

### Near-term (next 3 months)
- Decision documents refined based on [funder partner] friction log
- Common configurations added for 2-3 agency types (financial coaching, mental health, youth services)
- Developer continues to use Claude Code desktop for setups, guided by the docs

### Medium-term (3-6 months)
- Admin-facing version: simplified decision documents that a program manager could use with Claude desktop app or Claude.ai
- The "common configurations" section grows as more agencies onboard
- Consider a Claude Project (claude.ai) pre-loaded with all decision documents for admin self-service

### Long-term (6+ months)
- AI tools will likely be able to handle more of the execution (not just Q&A)
- The decision documents remain the durable asset; the delivery mechanism adapts
- May add a `apply_agency_config` management command that takes completed decisions as YAML input
- May build a simple web form that non-AI-users can fill in (for agencies that don't use AI tools)

## What We Explicitly Do NOT Build (Yet)

- Custom Claude skills or SKILL.md files for deployment
- MCP servers or API endpoints for configuration
- Automation scripts beyond what `apply_setup` already does
- A polished admin-facing configuration UI

These are all good ideas for later, but the AI landscape is changing too fast to invest in custom integrations now. The decision documents are the right abstraction level.

## Success Criteria

After the [funder partner] prototype:

1. Developer was able to complete the full setup using Claude + decision documents
2. Friction log has fewer than 10 significant gaps
3. The setup took less time than a manual walk-through of the deployment protocol would
4. We can identify which decision documents an admin (non-developer) could realistically use without help
