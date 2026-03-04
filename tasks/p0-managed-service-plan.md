# P0 Deliverable: Managed Service Model

**Requirement ID:** MA5 (managed hosting and support), related to MA3/MA4
**Deliverable type:** Costed plan
**Date:** 2026-03-04 (updated with self-healing support cost impact)
**Source documents:** tasks/hosting-cost-comparison.md, tasks/design-rationale/ovhcloud-deployment.md, tasks/deployment-protocol.md, tasks/saas-service-agreement.md, tasks/design-rationale/data-access-residency-policy.md

---

## Executive Summary

LogicalOutcomes offers KoNote as a managed service: agencies get a fully hosted, maintained KoNote instance without managing their own infrastructure. This document defines the service model, support tiers, cost structure, and deployment approach for both Azure and OVHcloud hosting paths.

---

## Service Model

### What LogicalOutcomes Provides

| Service | Detail |
|---------|--------|
| **Hosting** | Dedicated or shared infrastructure (Azure Canada Central or OVHcloud Beauharnois) |
| **Setup** | Agency provisioned per deployment protocol — configuration, customisation, domain |
| **Maintenance** | Software updates, security patches, database maintenance |
| **Backups** | Nightly automated backups with 30-day retention (90 days for audit logs) |
| **Monitoring** | UptimeRobot external monitoring, Docker healthchecks, automated self-healing |
| **Support** | Incident response, configuration changes, report template setup |
| **Encryption** | Per-agency encryption keys managed via Azure Key Vault |
| **Data export** | On-demand encrypted exports (individual or agency-wide) |
| **Offboarding** | Full data export, confirmed deletion, written confirmation |

### What the Agency Provides

| Responsibility | Detail |
|----------------|--------|
| **Configuration decisions** | Terminology, programs, metrics, user accounts |
| **Data entry** | Staff enter participant data through the web interface |
| **Report review** | Approve funder reports before publishing |
| **User management** | Add/remove staff accounts (or request LogicalOutcomes do it) |
| **Privacy accountability** | Agency remains the data controller under PIPEDA/PHIPA |

---

## Two Hosting Paths

Both paths are fully supported. The choice depends on the agency's requirements and budget.

### Path A: OVHcloud Beauharnois, QC (Recommended for most agencies)

**Architecture:** Docker Compose stack on OVHcloud VPS. Self-managed PostgreSQL. 4-layer self-healing automation. Azure Key Vault for encryption keys.

**Why OVHcloud:**
- 60–70% lower cost than Azure
- OVH Groupe SA is French-incorporated — not subject to US CLOUD Act
- Data centre in Beauharnois, QC — Canadian data residency
- Full deployment architecture documented (see OVHcloud deployment DRR)
- OVHcloud deployment in progress (as of March 2026)

**Operational model:**
- Layer 1: Docker HEALTHCHECK + autoheal (auto-restart failed containers)
- Layer 2: UptimeRobot → OVHcloud API (auto-reboot VPS on extended downtime)
- Layer 3: Preventive cron jobs (backups, log rotation, disk monitoring)
- Layer 4: Human escalation (email alerts to KoNote team)

### Path B: Azure Canada Central

**Architecture:** Azure VM + Azure Database for PostgreSQL (managed). Azure Key Vault for encryption keys. Azure Monitor for monitoring.

**Why Azure:**
- Managed database (automated backups, patching, HA)
- Azure Monitor, alerts, diagnostics built in
- SLA-backed uptime (99.9%+)
- Required when an agency or funder specifically mandates Azure

**Operational model:**
- Azure manages database patching, backups, failover
- Azure Monitor handles alerts and diagnostics
- KoNote team manages application updates and configuration

---

## Cost Structure

### Per-Agency Monthly Cost (CAD)

| Scale | OVHcloud (single-tenant) | OVHcloud (multi-tenant) | Azure (single-tenant) | Azure (multi-tenant) |
|-------|-------------------------|------------------------|-----------------------|---------------------|
| 1 agency | $45 | $53* | $112 | $374* |
| 5 agencies | $35 | $16 | $102 | $80 |
| 10 agencies | $35 | $12 | $102 | $46 |

*Multi-tenant with 1 agency costs more due to the larger shared VM. Cost advantage starts at 3+ agencies.*

### What's Included in Infrastructure Cost

- Server hosting (VPS or Azure VM)
- Database hosting (self-managed or Azure managed)
- Encryption key management (Azure Key Vault: ~$2/mo)
- AI API costs (translation + metrics generation: ~$7/agency/mo)
- Self-hosted LLM for suggestion theme tagging (shared OVHcloud VPS: ~$1–2/agency/mo)
- Backup storage
- External monitoring (UptimeRobot free tier)

### What's Not Included (Operational Costs)

The 4-layer self-healing automation handles ~99% of operational incidents automatically (container restarts, VPS reboots, backups, disk monitoring, health reports). Human support is needed only for: software updates (~1–2×/month), escalation alerts that self-healing couldn't resolve (~1×/month), agency support requests, and periodic security reviews. See [hosting cost comparison — tech support estimates](hosting-cost-comparison.md#technical-support-cost-estimates) for detailed hour breakdowns.

| Item | Estimate | When needed |
|------|----------|-------------|
| KoNote team time (~4–5 hr/mo per agency) | Internal cost | Always |
| Freelance sysadmin on-call retainer | ~$75–150 CAD/mo | 3–5 agencies (recommended) |
| Canadian MSP | ~$300–500 CAD/mo | 10+ agencies or when 24/7 SLA required |
| SaaS agreement legal review | One-time ~$2,000–5,000 | Before first managed agency |
| SSL certificates | $0 (Let's Encrypt via Caddy) | Always |
| Domain registration | ~$15–20/year per agency | If LogicalOutcomes provides subdomain |

**Impact of self-healing on support costs:** Without automation, managing even one OVHcloud VPS would require ~10–15 hours/month of sysadmin time (manual monitoring, backup management, incident response). With the 4-layer stack, this drops to ~4–5 hours/month — most of which is reviewing automated reports and applying software updates. At 5 agencies, the per-agency support burden is ~2 hours/month.

---

## Support Tiers

### Tier 1: Included (All Managed Agencies)

- Automated monitoring and self-healing (4-layer stack on OVHcloud, Azure Monitor on Azure)
- Nightly backups with 30-day retention
- Software updates applied within 5 business days of release
- Security patches applied within 24 hours of notification
- Email support during business hours (ET)
- Configuration changes (terminology, programs, metrics, users) within 2 business days

### Tier 2: Enhanced (Available on Request)

- Priority incident response (2-hour response during business hours)
- Custom report template creation
- Quarterly data quality review
- Training sessions for new staff
- Estimated additional cost: $50–100 CAD/month

### Tier 3: Premium (For Large Agencies or Consortiums)

- Dedicated infrastructure (own VPS/VM, not shared)
- Extended support hours
- Custom feature development (scoped and quoted separately)
- Quarterly business reviews
- Estimated additional cost: negotiated per agency

---

## Deployment Protocol (Both Paths)

The deployment protocol (see tasks/deployment-protocol.md) defines five phases for onboarding a new agency:

| Phase | What happens | Timeline |
|-------|-------------|----------|
| 0 | Discovery call — agency needs, configuration decisions, hosting choice | Week 1 |
| 1 | Permissions interview — data handling acknowledgement, access setup | Week 1–2 |
| 2 | Infrastructure provisioning — VPS/VM, database, domain, encryption | Week 2 |
| 3 | Customisation — terminology, programs, metrics, users, report templates | Week 2–3 |
| 4 | Go-live verification — health check, login test, demo data review, sign-off | Week 3 |
| 5 | 30-day check-in — usage review, support questions, configuration adjustments | Week 7 |

**Total onboarding time:** 3–4 weeks from discovery call to go-live.

**Azure-specific steps:** Azure VM provisioning, Azure Database setup, Azure AD SSO configuration.
**OVHcloud-specific steps:** VPS provisioning, Docker Compose deployment, Caddy DNS setup, cron job configuration.

---

## Data Sovereignty Summary

| Factor | OVHcloud | Azure |
|--------|----------|-------|
| Data stored in Canada | Yes (Beauharnois, QC) | Yes (Toronto, Canada Central) |
| Parent company jurisdiction | French (not subject to US CLOUD Act) | US (subject to US CLOUD Act) |
| Canadian law enforcement access | Yes (expected and acceptable) | Yes |
| Encryption key storage | Azure Key Vault (Canada Central) | Azure Key Vault (Canada Central) |

Both paths meet Canadian data residency requirements. OVHcloud offers stronger protection against US government data requests due to its French parent company. Agencies serving populations with specific concerns about US jurisdictional reach should consider OVHcloud.

---

## SaaS Agreement

A SaaS service agreement is required before the first managed agency (see tasks/saas-service-agreement.md for recommended contents). Key terms:

- LogicalOutcomes as data processor, agency as data controller
- Purpose limitation — data processed only to operate the service
- Data residency — all data in Canada
- Breach notification — within 24 hours of discovery
- Data export — on-demand encrypted exports, 5 business days routine, 48 hours for PIPEDA requests
- Termination — full encrypted export, confirmed deletion, written confirmation

**Status:** Outline complete. Needs lawyer to draft actual agreement language.

---

## Scaling Plan

| Stage | Agencies | Infrastructure | Support | Monthly Infra Cost | Monthly Support Cost | All-In/Agency |
|-------|----------|---------------|---------|-------------------|---------------------|---------------|
| Launch | 1–2 | OVHcloud single-tenant VPS per agency | KoNote team + runbook | $45–90 | $0 (internal) | ~$45 |
| Early growth | 3–5 | OVHcloud single-tenant (or start multi-tenant) | KoNote team + freelance on-call | $105–175 (ST) or $81 (MT) | ~$75–150 | ~$50–60 |
| Scale | 5–10 | Multi-tenant on larger VPS | Freelance sysadmin retainer | $81–116 (MT) | ~$100–200 | ~$27–36 |
| Enterprise | 10+ | Multi-tenant, dedicated VPS per large agency | Canadian MSP | Custom | ~$300–500 | Custom |

---

## What This Plan Demonstrates (for P0)

- **MA5 (managed service):** Complete service model with hosting, support, backup, monitoring, and offboarding
- **Two paths:** Azure and OVHcloud are both fully supported with documented deployment procedures
- **Credible cost model:** Per-agency costs from $12–112/month depending on scale and platform
- **Clear scaling path:** From 1 agency (single-tenant, KoNote team support) to 10+ (multi-tenant, MSP support)
- **Privacy and sovereignty:** Both paths meet Canadian data residency requirements; OVHcloud offers additional protection from US CLOUD Act
