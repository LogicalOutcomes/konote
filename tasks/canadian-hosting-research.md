# Canadian Hosting Options for KoNote

Research conducted 2026-02-04. Evaluating Canadian-owned hosting providers for nonprofits requiring data residency compliance.

---

## Requirements

- **Canadian-owned company** (not just Canadian data centres)
- **Data stored in Canada** (PIPEDA/PHIPA compliance)
- **Suitable for confidential client data** (nonprofits serving vulnerable populations)
- **Manageable by non-technical staff** with Claude Code assistance
- **~200 clients initially**, 5-10 staff users

---

## Current Encryption Status

> **Important:** As of February 2026, KoNote encrypts client identifying information (names, birth dates, sensitive custom fields) but **does NOT encrypt progress note content** at the application level.
>
> This means:
> - Canadian hosting is recommended to satisfy PIPEDA/PHIPA data residency requirements
> - If progress note encryption (SEC1) is implemented, US hosting becomes more viable because clinical content would be encrypted with agency-held keys
> - All recommended hosting providers encrypt data at rest at the infrastructure level, but this doesn't protect against CLOUD Act requests
>
> See TODO.md (SEC1) for progress note encryption status.

---

## Recommended Options

### Option 1: FullHost Cloud PaaS (Current Default)

**Why:** One-click deploy already built, web dashboard management, Canadian-owned.

| Aspect | Details |
|--------|---------|
| **Ownership** | Canadian (Victoria, BC, since 2004) |
| **Data centres** | Montreal, Vancouver |
| **Platform** | Virtuozzo/Jelastic PaaS |
| **Management** | Web dashboard — no command line needed |
| **Certifications** | BBB A+ (no SOC 2 documented) |
| **Cost** | ~$23 CAD/month (small nonprofit) |
| **Deployment** | One-click from existing manifest |

**Pros:**
- Simplest management for non-technical users
- Pay-as-you-go pricing
- Automatic scaling during busy periods
- KoNote already has deployment manifest (`fullhost-manifest.jps`)

**Cons:**
- No SOC 2 or government certifications documented
- Smaller company (may be concern for some funders)

**Best for:** Most nonprofits without strict compliance audit requirements.

---

### Option 2: CanSpace VPS

**Why:** Documented government clients, stronger compliance story.

| Aspect | Details |
|--------|---------|
| **Ownership** | 100% Canadian (since 2009) |
| **Data centres** | Quebec (Beauharnois) |
| **Platform** | Managed VPS with root access |
| **Management** | SSH command line (Claude can guide) |
| **Certifications** | CIRA certified |
| **Named clients** | Government of BC, City of Toronto, City of Vancouver, University of Manitoba, UBC |
| **Cost** | $54.99 CAD/month (8 GB RAM — overkill but lowest tier) |

**Pros:**
- Documented government and university clients
- Stronger due diligence story for funders
- Green energy (hydroelectric)

**Cons:**
- Requires SSH/command line (Claude can assist)
- More expensive than needed for 200 clients
- No SOC 2 certification published

**Best for:** Nonprofits needing to demonstrate due diligence to funders or boards.

---

### Option 3: WHC Self-Managed VPS

**Why:** Best value, SOC 2 certification in progress.

| Aspect | Details |
|--------|---------|
| **Ownership** | Private Canadian (Montreal, since 2003) |
| **Data centres** | Montreal, West Coast |
| **Platform** | Self-managed VPS with root access |
| **Management** | SSH command line (Claude can guide) |
| **Certifications** | SOC 2 Type 1 (pursuing Type 2), ICANN, CIRA |
| **Cost** | $18.50 CAD/month (2 GB RAM — sufficient for 200 clients) |

**Pros:**
- Most affordable option
- SOC 2 certification in progress
- 70,000+ customers

**Cons:**
- Requires SSH/command line
- No documented government clients

**Best for:** Budget-conscious nonprofits comfortable with occasional command-line tasks.

---

### Option 4: Canadian Web Hosting (VPS)

**Why:** Longest SOC 2 track record (13 years).

| Aspect | Details |
|--------|---------|
| **Ownership** | Canadian (Vancouver, since 1998) |
| **Data centres** | Vancouver |
| **Certifications** | **SOC 2 Type 2 for 13 consecutive years** |
| **Cost** | Contact for pricing |

**Pros:**
- Strongest security certification history
- Longest-established provider

**Cons:**
- Need to confirm Docker/container support
- No published government client list
- Pricing not transparent

**Best for:** Organisations with strict compliance requirements who can confirm Docker support.

---

## Providers Researched But Not Recommended

| Provider | Why Not |
|----------|---------|
| **CanTrust Hosting Coop** | Only supports WordPress, Drupal, Node.js — no Django |
| **Hosting.ca** | cPanel-based shared hosting — no Docker support |
| **Websavers** | Shared hosting focus — not designed for Django apps |
| **Micrologic** | Enterprise-level Kubernetes PaaS — overkill and expensive |
| **ThinkOn** | Enterprise IaaS — requires significant IT expertise |
| **Railway** | Excellent PaaS but US-owned (data residency concern) |

---

## Resource Requirements

For 200 clients with 5-10 staff:

| Resource | Minimum | Recommended |
|----------|---------|-------------|
| **RAM** | 1 GB | 2 GB |
| **Storage** | 5 GB | 10 GB |
| **CPU** | 1 core | 2 cores |

The application is designed for up to ~2,000 clients before performance optimisation is needed.

---

## VPS Deployment Complexity

If choosing a VPS option (CanSpace, WHC, Canadian Web Hosting), ongoing management involves:

### One-Time Setup (1-2 hours with Claude)
1. Order VPS, wait for provisioning email
2. SSH into server (Claude provides commands)
3. Install Docker and Docker Compose
4. Clone KoNote, configure `.env` file
5. Run `docker-compose up -d`
6. Point domain DNS to server
7. Create admin user

### Ongoing Tasks
| Task | Frequency | Time | Complexity |
|------|-----------|------|------------|
| Download database backup | Weekly | 5 min | Copy commands from Claude |
| Update KoNote | Monthly | 5 min | 4 commands |
| Server security updates | Monthly | 10 min | Copy commands from Claude |

Claude can provide exact commands for all tasks and troubleshoot errors.

---

## Recommendation Summary

| Situation | Recommended Provider |
|-----------|---------------------|
| **Simplest management, standard compliance** | FullHost Cloud PaaS |
| **Need to show government/university references** | CanSpace VPS |
| **Budget-conscious, willing to use terminal** | WHC Self-Managed VPS |
| **Strict compliance requirements** | Canadian Web Hosting (confirm Docker first) |

---

## Next Steps

1. **Decision:** Choose hosting provider based on compliance needs and comfort level
2. **If FullHost:** Test existing one-click deploy with the $25 free credit
3. **If VPS:** Create detailed deployment guide for chosen provider
4. **If compliance critical:** Contact CanSpace or Canadian Web Hosting to request SOC 2 documentation

---

## Sources

- [FullHost](https://www.fullhost.com/) — Canadian PaaS provider
- [CanSpace](https://www.canspace.ca/about.html) — Government client list
- [WHC](https://whc.ca/about-web-hosting-canada) — SOC 2 certification status
- [Canadian Web Hosting](https://www.prnewswire.com/news-releases/canadian-web-hosting-successfully-completes-annual-soc-2-and-soc-3-audits-continues-commitment-to-security-300448427.html) — SOC 2 history
- [Trustpilot](https://ca.trustpilot.com/review/www.fullhost.com) — FullHost reviews
- [BBB](https://www.bbb.org/ca/bc/victoria/profile/information-technology-services/fullhost-0047-90006379) — FullHost A+ rating
