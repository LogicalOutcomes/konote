# First-Run Setup Wizard Design (SETUP1)

**Status:** Deferred — build when first agency requests setup assistance

## Overview

A consultant-assisted setup workflow that uses Claude to analyze agency documents, generate configuration recommendations, and apply settings to a new KoNote instance. This is not a traditional click-through wizard — the intelligence lives in a Claude skill, and KoNote receives a configuration file.

---

## Workflow

```
┌─────────────────────────────────────────────────────────────┐
│  PHASE 0: Hosting Selection (Claude-Assisted)               │
│                                                             │
│  Questions:                                                 │
│    • Does your funder require SOC 2 compliance?             │
│    • Do you have staff comfortable with command line?       │
│    • What's your monthly hosting budget?                    │
│    • Do you need to demonstrate government references?      │
│                                                             │
│  Output: Recommended hosting provider + deployment guide    │
│  Reference: tasks/canadian-hosting-research.md              │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│  PHASE 1: Document Analysis (Claude Skill)                  │
│                                                             │
│  Inputs:                                                    │
│    • Program description documents                          │
│    • Evaluation framework / logic model                     │
│    • Funder reporting templates                             │
│    • Existing intake forms (if any)                         │
│                                                             │
│  Outputs:                                                   │
│    • Draft setup_config.json                                │
│    • decision-questions.md (for agency meeting)             │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│  PHASE 2: Decision Meeting (Consultant + Agency)            │
│                                                             │
│  Walk through decision-questions.md:                        │
│    • Terminology preferences (Client vs Participant, etc.)  │
│    • Which features to enable/disable                       │
│    • Metric selection from library                          │
│    • Program structure and colours                          │
│    • Custom field requirements                              │
│                                                             │
│  Output: Final decisions captured                           │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│  PHASE 3: Configuration Generation (Claude Skill)          │
│                                                             │
│  Input: Final decisions from meeting                        │
│  Output: Final setup_config.json                            │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│  PHASE 4: Apply Configuration (KoNote)                      │
│                                                             │
│  Command: python manage.py apply_setup setup_config.json    │
│                                                             │
│  Creates:                                                   │
│    • Instance settings (name, logo, support email)          │
│    • Terminology overrides                                  │
│    • Feature toggles                                        │
│    • Programs                                               │
│    • Plan templates with sections and targets               │
│    • Custom field groups and fields                         │
│    • Metric enable/disable flags                            │
└─────────────────────────────────────────────────────────────┘
```

---

## What's NOT Included

- **User accounts** — Agency creates staff accounts through the existing User Management UI
- **Custom metrics** — Created through a separate evaluation framework workflow
- **Client data import** — Handled separately via CSV import (IMP1)

---

## Phase 0: Hosting Selection Guide

Before deploying KoNote, help the organisation choose the right hosting provider. See [canadian-hosting-research.md](canadian-hosting-research.md) for detailed research.

### Decision Questions

| Question | If Yes → | If No → |
|----------|----------|---------|
| Does your funder require SOC 2 compliance? | Canadian Web Hosting or WHC | Any option works |
| Do you need to show government/university references? | CanSpace VPS | Any option works |
| Are you comfortable with occasional command-line tasks? | VPS options are fine | FullHost PaaS (dashboard only) |
| Is budget the top priority? | WHC ($18.50/mo) | FullHost ($23/mo) or CanSpace ($55/mo) |
| Do you use Microsoft 365? | Azure AD SSO for MFA (free) | Consider TOTP if MFA needed |

### Security Context

**Current encryption status:** Client names and birth dates are encrypted. Progress notes are NOT encrypted at the application level (planned — see SEC1).

**MFA options:**
- **Azure AD SSO** (recommended): Free MFA through Microsoft 365 — agency configures in Azure Entra ID
- **Local auth**: No built-in MFA yet — use for small agencies without M365, or enable TOTP when implemented (SEC2)

See [mfa-implementation.md](mfa-implementation.md) for details.

### Quick Recommendation Matrix

| Situation | Provider | Monthly Cost | Management |
|-----------|----------|--------------|------------|
| **Simplest option** — no command line, web dashboard | FullHost Cloud PaaS | ~$23 CAD | Dashboard |
| **Compliance-focused** — SOC 2, government references | CanSpace VPS | ~$55 CAD | SSH (Claude guides) |
| **Budget-conscious** — some terminal comfort | WHC VPS | ~$19 CAD | SSH (Claude guides) |
| **Strict compliance** — 13-year SOC 2 track record | Canadian Web Hosting | Contact | SSH (Claude guides) |

### What Each Choice Means

**FullHost Cloud PaaS (Recommended for most)**
- One-click deploy using existing manifest
- All management through web dashboard
- No command line needed
- Slightly higher cost, but simplest to maintain

**VPS Options (CanSpace, WHC, Canadian Web Hosting)**
- More control, lower cost
- Requires occasional SSH commands (Claude provides exact commands)
- Weekly backup downloads, monthly updates (~15 min/week)
- Better compliance story for some funders

### Deployment Guides

Each hosting option has (or will have) a deployment guide:
- [Azure Deployment Guide](azure-deployment-guide.md) — For agencies already using Azure
- FullHost deployment — Built into the platform (one-click)
- VPS deployment — Generic guide works for all VPS providers

---

## Configuration File Format

The Claude skill generates this JSON; the management command consumes it.

```json
{
  "instance_settings": {
    "product_name": "Youth Services - KoNote",
    "support_email": "support@agency.ca",
    "logo_url": "https://agency.ca/logo.png",
    "date_format": "YYYY-MM-DD"
  },
  "terminology": {
    "client": "Participant",
    "client_plural": "Participants",
    "plan": "Service Plan",
    "target": "Goal",
    "target_plural": "Goals",
    "progress_note": "Session Note"
  },
  "features": {
    "programs": true,
    "events": true,
    "quick_notes": true,
    "alerts": false,
    "analysis_charts": true
  },
  "programs": [
    {
      "name": "Youth Housing",
      "description": "Transitional housing support for youth aged 16-24",
      "colour_hex": "#6366F1"
    },
    {
      "name": "Mental Health Support",
      "description": "Counselling and mental health services",
      "colour_hex": "#10B981"
    }
  ],
  "metrics_enabled": [
    "PHQ-9 (Depression)",
    "GAD-7 (Anxiety)",
    "Housing Stability Index",
    "Life Skills Assessment"
  ],
  "metrics_disabled": [
    "Days Clean",
    "Cravings Intensity",
    "Harm Reduction Score"
  ],
  "plan_templates": [
    {
      "name": "Youth Housing Standard Plan",
      "description": "Default plan template for youth housing program",
      "sections": [
        {
          "name": "Housing Stability",
          "targets": [
            {
              "name": "Maintain stable housing for 3+ months",
              "description": "Client will maintain current housing placement with fewer than 2 unplanned absences per week."
            },
            {
              "name": "Develop independent living skills",
              "description": "Client will demonstrate competency in budgeting, cooking, and household management."
            }
          ]
        },
        {
          "name": "Education & Employment",
          "targets": [
            {
              "name": "Enroll in or maintain education/employment",
              "description": "Client will be enrolled in school, training, or employed."
            }
          ]
        }
      ]
    }
  ],
  "custom_field_groups": [
    {
      "title": "Funding & Referral",
      "fields": [
        {
          "name": "Funding Source",
          "input_type": "select",
          "options": ["Government", "Foundation", "Private", "Self-funded"],
          "is_required": true,
          "is_sensitive": false
        },
        {
          "name": "Referral Date",
          "input_type": "date",
          "is_required": false,
          "is_sensitive": false
        },
        {
          "name": "Referral Agency",
          "input_type": "text",
          "is_required": false,
          "is_sensitive": false
        }
      ]
    },
    {
      "title": "Demographics",
      "fields": [
        {
          "name": "Gender Identity",
          "input_type": "select",
          "options": ["Woman", "Man", "Non-binary", "Two-Spirit", "Prefer not to say", "Other"],
          "is_required": false,
          "is_sensitive": true
        },
        {
          "name": "Indigenous Identity",
          "input_type": "select",
          "options": ["First Nations", "Métis", "Inuit", "Non-Indigenous", "Prefer not to say"],
          "is_required": false,
          "is_sensitive": true
        }
      ]
    }
  ]
}
```

---

## Management Command: apply_setup

**Location:** `apps/admin_settings/management/commands/apply_setup.py`

**Usage:**
```bash
python manage.py apply_setup setup_config.json
python manage.py apply_setup setup_config.json --dry-run  # Preview without changes
```

**Behaviour:**
1. Validates JSON structure
2. Reports what will be created
3. Creates/updates in this order:
   - Instance settings
   - Terminology overrides
   - Feature toggles
   - Programs
   - Plan templates (with sections and targets)
   - Custom field groups and fields
   - Metric enable/disable flags
4. Reports summary of what was created

**Not idempotent** — running twice will create duplicates. Clear the database or use Django admin to remove items before re-running.

---

## Claude Skill Design (Future)

The skill would be created in Claude's skill system, not in the KoNote codebase.

### Skill Inputs
- PDF/Word documents via `markitdown` or `pdf` skill
- Program descriptions
- Evaluation frameworks / logic models
- Funder reporting templates

### Skill Outputs

**1. Draft Configuration**
- Maps agency outcomes to KoNote's 24-metric library
- Extracts program names and descriptions
- Suggests terminology based on document language
- Proposes plan template structure from evaluation framework

**2. Decision Questions Document**
Generated when the skill can't determine something automatically:

```markdown
# Setup Decisions for [Agency Name]

## Terminology
- Your documents use "participant" and "client" interchangeably.
  Which term should appear in the system? [ ] Client [ ] Participant

## Features
- Your evaluation framework mentions crisis tracking.
  Enable the Events feature for crisis logging? [ ] Yes [ ] No

## Metrics
- Your logic model includes "housing stability" but doesn't specify
  a measurement scale. Use our 1-5 Housing Stability Index? [ ] Yes [ ] Custom scale

## Programs
- I found references to "Youth Housing" and "Transitional Support".
  Are these separate programs or one program? [ ] Separate [ ] Combined
```

---

## What's Already Built

These existing components support the setup workflow:

| Component | Location | Status |
|-----------|----------|--------|
| Terminology model | `apps/admin_settings/models.py` | ✅ Complete |
| Feature toggles | `apps/admin_settings/models.py` | ✅ Complete |
| Instance settings | `apps/admin_settings/models.py` | ✅ Complete |
| Program model | `apps/programs/models.py` | ✅ Complete |
| Plan templates | `apps/plans/models.py` | ✅ Complete |
| Custom fields | `apps/clients/models.py` | ✅ Complete |
| Metric library | `seeds/metric_library.json` | ✅ 24 metrics |
| Seed command | `apps/admin_settings/management/commands/seed.py` | ✅ Reference |
| Agency setup guide | `docs/agency-setup.md` | ✅ Manual process documented |

---

## What Needs Building

| Component | Effort | Notes |
|-----------|--------|-------|
| `apply_setup` management command | ~2 hours | Straightforward Django command |
| Claude skill for document analysis | ~4 hours | Separate from codebase |
| Sample `setup_config.json` | ~30 min | For testing and documentation |

---

## When to Build

Build this when:
1. An agency requests setup assistance, AND
2. You want to streamline the process beyond the manual `agency-setup.md` guide

The manual guide works fine for 1-2 agencies. This automation pays off at 3+ agencies or when setup needs to be repeatable.
