# VPS Migration: Swiss Server to Canadian Server

**Status:** Complete
**Created:** 2026-03-06
**Completed:** 2026-03-06
**Task ID:** OPS-MIGRATE1

## Context

Migrated the KoNote deployment from an OVHcloud VPS in Switzerland to a new OVHcloud VPS hosted in Canada (Beauharnois, QC). Both production and dev instances are running on the new server.

**Why:** Canadian data residency for PHIPA compliance. The Swiss VPS was the original deployment; the Canadian server aligns with the data residency policy in `tasks/design-rationale/data-access-residency-policy.md`.

## Runbook

The step-by-step migration procedure is in the private ops repo:

**`konote-ops/deployment/vps-migration-runbook.md`**

This runbook is reusable for any future VPS-to-VPS migration (region changes, tier upgrades, agency moves).

## Pre-Migration Checklist

- [ ] New VPS IP address received from OVH
- [ ] SSH key copied to new VPS
- [ ] DNS TTL lowered to 300 seconds (24 hours before cutover, if possible)
- [ ] Password manager has all current credentials (especially `FIELD_ENCRYPTION_KEY`)
- [ ] Notify any active users of brief maintenance window

## What Gets Migrated

| Data | Method |
|------|--------|
| Application database (participants, plans, notes, metrics) | pg_dump/pg_restore |
| Audit database (tamper-resistant audit trail) | pg_dump/pg_restore |
| .env configuration (encryption keys, secrets) | Secure copy via SSH |
| Code | Fresh git clone of `main` branch |

Static files and Docker images are rebuilt fresh — they don't need to be copied.

## What Changes

- VPS IP address (update SSH config, monitoring, server inventory)
- DNS A record (point domain to new IP)
- Let's Encrypt certificate (Caddy auto-provisions on new VPS)

## What Does NOT Change

- Domain name (konote.llewelyn.ca)
- All .env values (encryption keys, database passwords, Django secret)
- Application code and Docker configuration
- Backup schedule and monitoring configuration

## Estimated Downtime

5-15 minutes during DNS cutover. Users will see an error if they hit the old VPS during DNS propagation (typically 5-60 minutes). Lowering DNS TTL beforehand reduces this window.

## Post-Migration

- Update `konote-ops/servers/` inventory file
- Update `~/.ssh/config` to point `konote-vps` to new IP
- Update MEMORY.md with new VPS IP
- Update UptimeRobot monitoring
- Keep old VPS running (web stopped) for 1-2 weeks as fallback
- Cancel old VPS subscription after confirming stability

## Related Files

- `konote-ops/deployment/vps-migration-runbook.md` — Full step-by-step procedure
- `konote-ops/deployment/runbook.md` — General deployment operations
- `konote-ops/deployment/env-template.md` — .env variable reference
- `konote-ops/servers/TEMPLATE.md` — Server inventory template
- `tasks/design-rationale/ovhcloud-deployment.md` — Deployment architecture DRR
- `tasks/design-rationale/data-access-residency-policy.md` — Data residency policy
