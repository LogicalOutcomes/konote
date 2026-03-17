# Documentation Review: Deployment Planning & Costing
Generated: 2026-03-14
Scope: All documents referenced by the `/deployment-planning` skill
Audience lens: Developers, managers, and nonprofit staff unfamiliar with KoNote

## Summary

- **Overall documentation quality:** Good technical depth, poor navigation and accessibility
- **Critical gaps:** 5
- **Cost consistency issues:** 4 (including a calculator bug)
- **Improvement opportunities:** 18

KoNote's deployment documentation contains accurate, detailed information across 20+ files in three repos. The content is technically sound, the DRRs are well-reasoned, and the anti-patterns are clearly stated. However, a newcomer faces three structural problems:

1. **No entry point** — five deployment guides, no map showing which to read first
2. **Audience mismatch** — docs swing from "for AI assistants" to "for nonprofit directors" with no labelling
3. **Cost figures diverge** across the source chain without explanation

---

## What's Strong

These areas are working well and should be preserved:

- **DRR quality**: Anti-patterns are explicit with reasons, not just rules. The multi-tenancy DRR's rejection of row-level isolation is a model of clear decision documentation.
- **Self-healing architecture**: The 4-layer recovery stack in `ovhcloud-deployment.md` is thoroughly documented with failure modes, escalation paths, and cost implications.
- **Deployment protocol**: Five-phase onboarding (`deployment-protocol.md`) with templates, checklists, and role assignments is actionable for a PM running it.
- **Calculator design**: Assumptions at the top, calculations below — easy to modify and re-run. Figures verified against prose docs (5-agency OVH per-agency: $92, 30-agency AI share: $1.33).
- **Ops docs are current**: All five ops documents dated March 2026 with correct paths and commands.

---

## Critical Gaps (Must Address)

### 1. No Entry Point for Newcomers

**Impact:** A nonprofit director or new developer opening the docs folder sees `deploying-konote.md`, `deploy-ovhcloud.md`, `deploy-dev-vps.md`, `llm-deployment-guide.md` and has no idea which to start with. The same problem exists in konote-ops with five deployment files and no index.

**Suggestion:** Create a single `docs/deployment-index.md` (or rename `deploying-konote.md`) that maps scenarios to documents:

| I want to... | Read this |
|---|---|
| Understand deployment options and costs | `/deployment-planning` skill |
| Deploy to OVHcloud for the first time | `deploy-ovhcloud.md` |
| Update an existing instance | `konote-ops/deployment/update-checklist.md` |
| Migrate to a new VPS | `konote-ops/deployment/vps-migration-runbook.md` |
| Set up Azure instead | `docs/archive/deploy-azure.md` |
| Troubleshoot a broken deployment | `konote-ops/deployment/runbook.md` |

### 2. LLM VPS Price Discrepancy ($31 vs $40)

**Impact:** The primary source (`hosting-cost-comparison.md`) says the LLM VPS costs **$31 CAD/mo** (VPS-4). All downstream documents (`p0-managed-service-plan.md`, `costing-model.md`, `hosting-budget-scenarios.md`, calculator) use **$40 CAD/mo**. The $9/month difference cascades to per-agency costs: $57/agency upstream vs. $74/agency downstream for single-tenant OVHcloud.

No document explains the divergence. The COST_VERSION headers claim to derive from upstream but carry different values.

**Suggestion:** Reconcile. Either:
- Update `hosting-cost-comparison.md` to $40 (if prices rose) and note when/why
- Or update downstream docs to $31 and re-run the calculator

Then add a reconciliation note to each COST_VERSION header explaining the value.

### 3. Calculator Bug: Azure Key Vault Treatment

**Impact:** The calculator treats Azure Key Vault as **$0.40 per agency** (line 46: `azure_keyvault: 0.40`), but `hosting-cost-comparison.md` treats it as **~$2 CAD/mo total shared** across all agencies. This means the calculator's Azure per-agency cost is wrong by a small amount, but more importantly the logic is inconsistent with the prose.

**Suggestion:** Fix the calculator to match the prose — Key Vault is a shared cost divided across agencies, not a per-agency flat fee.

### 4. Ops Hours Ambiguity (Total vs Human-Only)

**Impact:** `p0-managed-service-plan.md` says **4-5 hr/mo** for 1 agency. `hosting-cost-comparison.md` says **~1 hr/mo human** (LLM-assisted). `costing-model.md` says **1.0 hrs network ops + 2.1 hrs agency support = 3.1 hrs total**. These are answering different questions (total work vs. human-only vs. network+agency split) but the COST_VERSION headers don't clarify which is which.

**Suggestion:** Add a "unit" to each ops-hours value in COST_VERSION headers: `ops_hours_1_agency: ~1 hr/mo (human-only; ~4-5 hr/mo total including LLM work)`.

### 5. Dangling References

| Document | References | Problem |
|---|---|---|
| `multi-tenancy.md` line 6 | `tasks/multi-tenancy-implementation-plan.md` | File doesn't exist |
| `deploy-ovhcloud.md` line 27 | `plans/2026-02-20-deploy-script-design.md` | File is at `docs/plans/archive/` |
| `deployment-protocol.md` | `agency-permissions-interview.md` | Not reviewed; may not exist |
| `update-checklist.md` | `incidents/log.md` | May not exist |

**Suggestion:** Fix or remove each reference. For the multi-tenancy implementation plan, either create the file or remove the reference and note "implementation plan to be written when MT-CORE1 starts."

---

## Cost Consistency Matrix

| Cost Item | hosting-cost-comparison | p0-managed-service | costing-model | budget-scenarios | calculator |
|---|---|---|---|---|---|
| **LLM VPS** | $31 | **$40** | **$40** | **$40** | **$40** |
| **OVH app VPS (per agency)** | $14 (VPS-2) | — | $15 (VPS-1) | $15 | $15 |
| **Azure Key Vault** | ~$2 shared | — | — | — | $0.40/agency |
| **Ops hours (1 agency)** | ~1 hr human | 4-5 hr total | 1.0+2.1 hrs | — | 1.0+2.1 |
| **OVH single-tenant total** | $57 | $74 | — | — | — |

The upstream file (`hosting-cost-comparison.md`) uses different VPS tiers (VPS-2 at $14) while downstream files use VPS-1 at $15. The calculator also defines `ovh_vps1_shared2: 7.50` and `ovh_vps2: 26.00` which don't map cleanly to the VPS tier names in the prose docs.

---

## Organization & Clarity Issues

### Document Audience Mismatch

| Document | Written For | Should Say So At Top |
|---|---|---|
| `deploy-ovhcloud.md` | Nonprofit staff with terminal comfort | "Assumes: SSH, command line, domain access" |
| `llm-deployment-guide.md` | AI assistants (Claude) | "This guide is for AI assistants, not humans" |
| `hosting-cost-comparison.md` | Technical decision-makers | "Assumes: cloud hosting concepts" |
| `hosting-budget-scenarios.md` | Nonprofit funders | Already clear, but add "non-technical audience" |
| `hardening-guide.md` | Linux sysadmins | "Assumes: Linux security, Docker, SSH" |

**Suggestion:** Add a one-line audience statement at the top of each document.

### Deployment Protocol Is Azure-Only

The deployment protocol (`deployment-protocol.md`) references Azure throughout (Phase 2 is "Azure Infrastructure"). There is no equivalent OVHcloud deployment protocol, despite OVHcloud being the recommended path.

**Suggestion:** Either generalize the protocol to cover both paths, or create a parallel `deployment-protocol-ovhcloud.md`.

### Encryption Key Guidance Is Scattered

Three documents explain how to generate encryption keys, each differently. None says clearly **where to store them**. The critical warning ("if you lose this key, data is permanently unrecoverable") appears in `deploy-ovhcloud.md` but not in `deploying-konote.md` or `env-template.md`.

**Suggestion:** Consolidate into one section (perhaps in `env-template.md`) and reference from all deployment guides.

### Dev Instance Setup Is Complex and Fragmented

- `deploy-ovhcloud.md` Section 14 has 240+ lines for dual-instance setup on one VPS
- `deploy-dev-vps.md` is 81 lines covering only the update wrapper script
- Neither explains when or why to set up a dev instance

**Suggestion:** Extract Section 14 into a standalone `deploy-dual-instance.md`. Rename `deploy-dev-vps.md` to `update-dev-instance.md` to reflect what it actually covers.

### Workflow Design Is Unfinished

`deployment-workflow-design.md` is a problem statement with open questions and no answers. It uses different phase names ("Assessment / Customization / Production") than the deployment protocol ("Phases 0-5"). No status, no owner, no timeline.

**Suggestion:** Either complete it with recommendations or archive it with a note. Align naming with the deployment protocol.

### SaaS Agreement Is a Checklist, Not a Template

`saas-service-agreement.md` outlines what sections a SaaS agreement should contain but provides no template language. It's marked "not started, needs lawyer review" but this status isn't prominent.

**Suggestion:** Add a banner: "DRAFT OUTLINE — NOT APPROVED FOR USE. Requires legal review before any agency signs." Add dispute resolution and jurisdiction sections (missing).

---

## Scorecard

### Deployment How-To Guides

| Document | Clarity | Completeness | Organization | Currency | Beginner-Friendly? |
|---|---|---|---|---|---|
| deploying-konote.md | 7/10 | 6/10 | 6/10 | Current | Partially |
| deploy-ovhcloud.md | 8/10 | 9/10 | 7/10 | Current | Yes (with effort) |
| deploy-dev-vps.md | 4/10 | 3/10 | 4/10 | Unclear | No |
| llm-deployment-guide.md | 10/10 (for AI) | 9/10 | 9/10 | Current | No (AI-only) |
| archive/deploy-azure.md | 7/10 | 6/10 | 6/10 | Stale | No |

### Cost & Service Documents

| Document | Clarity | Completeness | Consistency | Currency | Beginner-Friendly? |
|---|---|---|---|---|---|
| hosting-cost-comparison.md | 7/10 | 8/10 | Upstream source | Current | No |
| p0-managed-service-plan.md | 7/10 | 6/10 | Diverges ($40 vs $31) | Current | Partially |
| costing-model.md | 7/10 | 7/10 | Matches downstream | Current | Partially |
| hosting-budget-scenarios.md | 8/10 | 7/10 | Matches downstream | Current | Yes |
| costing-model-calculator.py | 8/10 | 7/10 | Key Vault bug | Current | N/A (tool) |

### DRRs & Onboarding

| Document | Clarity | Completeness | Organization | Currency | Beginner-Friendly? |
|---|---|---|---|---|---|
| ovhcloud-deployment.md | 7/10 | 8/10 | 7/10 | Current | No (DevOps audience) |
| multi-tenancy.md | 7/10 | 6/10 | 8/10 | Current (not yet built) | No |
| data-access-residency-policy.md | 7/10 | 7/10 | 7/10 | Current | Partially |
| self-hosted-llm-infrastructure.md | 7/10 | 8/10 | 6/10 | Current | No (ML audience) |
| deployment-protocol.md | 8/10 | 7/10 | 8/10 | Current | Yes (for PMs) |
| saas-service-agreement.md | 5/10 | 3/10 | 5/10 | Not started | No |
| deployment-workflow-design.md | 4/10 | 2/10 | 3/10 | Stale/unclear | No |

### Operations (konote-ops)

| Document | Clarity | Completeness | Organization | Currency | Beginner-Friendly? |
|---|---|---|---|---|---|
| runbook.md | 6/10 | 6/10 | 6/10 | Current | No |
| vps-migration-runbook.md | 7/10 | 8/10 | 7/10 | Current | Limited |
| hardening-guide.md | 7/10 | 7/10 | 6/10 | Current | No |
| update-checklist.md | 8/10 | 6/10 | 8/10 | Current | Yes |
| env-template.md | 7/10 | 7/10 | 8/10 | Current | Limited |

---

## Prioritised Recommendations

### Tier 1: Critical (do first)

1. **Reconcile LLM VPS price** ($31 vs $40) across the cost source chain
2. **Fix calculator Key Vault bug** — shared cost, not per-agency
3. **Create `docs/deployment-index.md`** — scenario-to-document map as the single entry point
4. **Fix dangling references** (4 identified above)
5. **Add ops hours unit labels** to all COST_VERSION headers

### Tier 2: High Value

6. **Add audience statement** to the top of each deployment document
7. **Create an OVHcloud deployment protocol** (parallel to the Azure one)
8. **Consolidate encryption key guidance** into one section with cross-references
9. **Extract dual-instance setup** from deploy-ovhcloud.md Section 14 into its own file
10. **Create `konote-ops/deployment/index.md`** — ops-specific entry point
11. **Add "archive" banners** to deploy-azure.md and deploy-elestio.md
12. **Create a cost data dictionary** defining "shared infrastructure", "per-agency cost", "network ops", "base support"

### Tier 3: Nice to Have

13. Expand glossary in `deploying-konote.md` (currently 8 terms — Docker, migration, container not defined)
14. Add macOS/Linux SSH instructions to `deploy-ovhcloud.md` (currently Windows-only)
15. Create a "testing your .env" checklist in `env-template.md`
16. Add visual cost breakdown charts to `hosting-budget-scenarios.md` (currently tables only)
17. Complete or archive `deployment-workflow-design.md`
18. Add review dates to DRRs ("review annually or when team composition changes")
