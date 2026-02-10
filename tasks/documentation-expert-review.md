# Documentation Expert Review — Non-Developer Accessibility

**Date:** 2026-02-03
**Method:** Expert panel convening (4 perspectives)
**Focus:** Can a nonprofit program manager or ED set up KoNote without developer help?

---

## Panel Members

1. **Nonprofit Technology Consultant** — Works with small agencies adopting technology
2. **Technical Writer / UX Specialist** — Designs documentation for non-technical audiences
3. **Nonprofit Executive Director** — Target user persona (tech-comfortable, not a developer)
4. **Information Security Advisor** — Simplifies security concepts for non-technical staff

---

## Key Findings

### Where Non-Developers Would Get Stuck

| Step | Problem | Severity |
|------|---------|----------|
| "Clone the repository" | Don't know what Git/cloning is | High |
| Key generation command | Looks like code, afraid to type it | High |
| "Edit your .env file" | Don't know how to open/edit dotfiles | High |
| PostgreSQL installer | Asks questions not covered in docs | Medium |
| Two databases concept | Why? Not explained in simple terms | Medium |
| "psql -U postgres" | No idea what psql is | High (Manual path) |

### What's Working Well

- Docker option is the right recommendation for non-developers
- Troubleshooting section anticipates real problems
- `.env.example` comments are helpful
- Encryption key warning is appropriately alarming
- Checklist format in security docs is good

---

## Recommendations

### High Priority (Before Promoting to Agencies) — COMPLETE

- [x] Add "What You'll Need" pre-flight checklist (DOC12)
- [x] Add "What just happened?" explanations after key commands (DOC13)
- [x] Add expected output examples showing what success looks like (DOC14)
- [x] Add glossary: terminal, repository, migration, container, etc. (DOC15)
- [x] Create "Before You Enter Real Data" checkpoint document (DOC16)
- [x] Fix placeholders to be obviously fake: `REPLACE_THIS_WITH_YOUR_PASSWORD` (DOC17)

### Medium Priority (Phase 2)

- [ ] Video walkthrough of Docker setup on Windows (DOC18)
- [ ] Helper script to generate keys and create .env (DOC19)
- [ ] Move Manual Setup to separate "Advanced Setup" document (DOC20)
- [ ] Add "Get Help" resources section (DOC21)

### Lower Priority

- [ ] Explain PostgreSQL installer options for Manual path
- [ ] Add time estimates to each section
- [ ] Create visual troubleshooting flowchart

---

## Proposed Documentation Structure

```
README.md
├── Overview (current - good)
├── Quick Start → Points to Getting Started

docs/
├── getting-started.md (Docker-focused, screenshots, glossary)
├── advanced-setup.md (NEW - Manual PostgreSQL, for IT-supported agencies)
├── understanding-security.md (NEW - post-setup reading)
├── security-operations.md (current - operational focus)
├── agency-setup.md (current - good)
├── [deployment guides] (current - good)
```

---

## Success Criteria

An executive director who has:
- Installed WordPress
- Used Excel competently
- No command-line experience

Should be able to complete the Docker setup path in **under 2 hours** without external help.

---

## Risk If Not Addressed

| Gap | Likely Outcome |
|-----|----------------|
| Jargon undefined | User Googles, finds conflicting advice, abandons |
| No screenshots | User doesn't know if output is correct, assumes failure |
| Key generation unexplained | User stores key insecurely or doesn't back up |
| Security content during setup | User overwhelmed, delays entering real data |

---

## Next Steps

1. Prioritize DOC12-DOC17 as Phase C.2 documentation improvements
2. Consider video walkthrough as separate initiative
3. Test documentation with actual nonprofit staff before wider release
