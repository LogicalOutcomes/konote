# Multilingual Strategy for KoNote

## Overview

KoNote is open source. Agencies must be able to set up and run bilingual (or multilingual) instances without our involvement. This document defines the architecture and roadmap.

## Design Principles

1. **English + French ship complete** — Canadian table stakes
2. **French users are first-class** — not a "translated version" feeling
3. **Other languages are self-service** — agencies can add Spanish, Arabic, etc.
4. **AI translation is optional** — works without API key (manual entry)
5. **AI never sees client data** — only agency configuration (programs, metrics, templates)
6. **Admin interface for ongoing management** — no CLI required after initial setup

## UX Requirement: First-Class French Experience

French-speaking users must never feel like they're using a translated afterthought. This is especially important in Canada where language is a matter of rights and identity.

### Landing/Login Page: Equal Welcome

The first screen shows both languages with equal prominence:

```
┌─────────────────────────────────────────────────────────────┐
│                                                             │
│                        KoNote                              │
│                                                             │
│         ┌─────────────────┐  ┌─────────────────┐           │
│         │                 │  │                 │           │
│         │    English      │  │    Français     │           │
│         │                 │  │                 │           │
│         └─────────────────┘  └─────────────────┘           │
│                                                             │
│              Outcome Management for Nonprofits              │
│         Gestion des résultats pour les organismes          │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

- Two equal buttons, side by side
- Tagline in both languages
- Click either → sets preference → proceeds to login in that language
- **Message:** "Both languages are equally supported here"

### Returning Users

- Cookie remembers preference before login
- User profile stores preference after login
- They go straight to their language — no re-choosing

### Language Switcher (After Choice)

Clear text in navbar, not a hidden flag icon:

```
┌──────────────────────────────────────────────────────────────────┐
│ KoNote     Clients  Notes  Plans  Reports     [EN | FR]   Alex ▼│
└──────────────────────────────────────────────────────────────────┘
```

- Current language highlighted
- One click to switch
- No dropdown needed for two languages

### Completeness Requirements

Every part of the French experience must feel native:

| Area | Requirement |
|------|-------------|
| Error messages | All validation in French |
| Empty states | "Aucun client trouvé" not "No clients found" |
| Dates | "5 février 2026" not "February 5, 2026" |
| Numbers | "1 000,50" not "1,000.50" (if applicable) |
| Email notifications | Sent in user's preferred language |
| PDF exports | Generated in user's language |
| Help text / tooltips | All translated |
| Placeholders | "Rechercher..." not "Search..." |

### Pre-Login Language Detection

For first-time visitors (no cookie yet):
1. Check browser Accept-Language header
2. If French, show landing page with Français pre-highlighted
3. Still allow choice — don't force based on browser

## Canadian Localization (Beyond Language)

Both English and French Canadian users expect Canadian formatting. Don't make them fight US-designed forms.

### Address Fields

| Field | Label (EN) | Label (FR) | Notes |
|-------|------------|------------|-------|
| Province/Territory | Province | Province | Never "State" |
| Postal Code | Postal Code | Code postal | Never "ZIP Code" |

### Postal Code Validation

Canadian postal codes: `A1A 1A1` (letter-number-letter space number-letter-number)

**Accept both formats:**
- `A1A 1A1` (with space) ✓
- `A1A1A1` (without space) ✓

**Normalize on save:** Store as `A1A 1A1` (with space) for consistency, but accept either input.

```python
def normalize_postal_code(value):
    """Accept A1A1A1 or A1A 1A1, store as A1A 1A1."""
    cleaned = value.upper().replace(" ", "")
    if len(cleaned) == 6:
        return f"{cleaned[:3]} {cleaned[3:]}"
    return value  # Return as-is if not valid format
```

### Phone Numbers

Accept multiple formats:
- `(416) 555-1234` ✓
- `416-555-1234` ✓
- `416.555.1234` ✓
- `4165551234` ✓

Don't reject valid numbers because of formatting differences.

### Dates

| Language | Format | Example |
|----------|--------|---------|
| English | Month D, YYYY | February 5, 2026 |
| French | D month YYYY | 5 février 2026 |

Use Django's localization (`{% localize %}` or `date` filter with format).

### Currency

- Symbol: `$` (same for both languages)
- Format (EN): `$1,234.56`
- Format (FR): `1 234,56 $` (space as thousands separator, comma as decimal, symbol after)

### Implementation Notes

1. **Postal code field:** Add normalization in form `clean_postal_code()` method
2. **Phone field:** Use permissive regex, normalize on save
3. **Date display:** Already handled by Django i18n if `USE_L10N = True`
4. **Address labels:** Use `{% trans "Province" %}` not hardcoded "State"

## Three Types of Translatable Content

| Type | Examples | Ships With | Agency Does |
|------|----------|------------|-------------|
| **System UI** | Buttons, labels, menus | EN + FR complete | Nothing (or generate new languages) |
| **Terminology** | "Client" → "Participant" | EN + FR defaults | Customize if desired |
| **Agency Content** | Program names, metrics | — | Create and translate |

## Privacy: What AI Can and Cannot See

**Sent to AI for translation (agency configuration only):**
- Program names and descriptions
- Metric definition names and descriptions
- Template names
- Custom field labels
- Terminology overrides

**Never sent to AI:**
- Client names or any ClientFile data
- Progress notes (clinical documentation)
- Plan targets for individual clients
- Any model with a client ForeignKey

This separation is enforced architecturally — client data models simply don't have translation infrastructure.

## Strategy: "English + French Ready, Expand on Demand"

### Phase 1: English Only (Current State)

**What's already done:**
- Django i18n infrastructure is enabled
- 630 system strings extracted to `locale/fr/LC_MESSAGES/django.po`
- Terminology model has `display_value_fr` field
- SafeLocaleMiddleware provides graceful fallback
- Templates use `{% trans %}` and `{{ term.client }}` patterns

**What to do now:**
- Nothing for i18n — infrastructure is in place
- Continue using `{% trans %}` for new system strings
- Continue using `{{ term.X }}` for customizable terms

### Phase 2: Enable French System UI (When Needed)

**Trigger:** Agency explicitly requests French interface

**Steps (VSCode/CLI — one-time setup):**

1. **Translate system strings** using AI
   ```bash
   python manage.py translate_strings --target-lang=fr
   ```
   (Uses Claude API — see [tasks/ai-translation-implementation.md](ai-translation-implementation.md))

2. **Compile translations**
   ```bash
   python manage.py compilemessages
   ```

3. **Enable French in settings**
   ```python
   # konote/settings/base.py
   LANGUAGES = [
       ("en", "English"),
       ("fr", "Français"),
   ]
   ```

4. **Add language switcher to UI** (navbar dropdown)

5. **Commit .mo files** (pre-compiled, no Docker changes needed)

**Estimated effort:** 2-4 hours
**Estimated cost:** ~$1 for AI translation API calls

### Phase 3: Translate Agency Content (When Needed)

This is the complex part — programs, metrics, and templates are created by each agency.

#### Recommended Architecture: JSON Translation Fields

Add a `translations` JSONField to models that need multilingual support:

```python
# Example: apps/programs/models.py
class Program(models.Model):
    name = models.CharField(max_length=200)  # Primary (English)
    description = models.TextField(blank=True)

    # New field for translations
    translations = models.JSONField(default=dict, blank=True)
    # Structure: {"fr": {"name": "...", "description": "..."}}

    def get_translated(self, field, lang='en'):
        """Get translated field value, falling back to English."""
        if lang == 'en' or lang not in self.translations:
            return getattr(self, field)
        return self.translations.get(lang, {}).get(field) or getattr(self, field)
```

**Why JSON over separate fields (`name_fr`, `description_fr`)?**
- No schema changes when adding new languages
- Flexible — any language, any field
- Easy to add "stale" tracking
- Admin UI can be a simple form, not JSON editing

#### Models to Add Translation Support

| Model | Fields to Translate | Priority |
|-------|---------------------|----------|
| Program | name, description | High |
| MetricDefinition | name, definition, unit | High |
| PlanTemplate | name, description | High |
| ProgressNoteTemplate | name | Medium |
| CustomFieldDefinition | name | Medium |
| EventType | name, description | Low |

**Note:** Client data (names, notes) is NOT translated — it's clinical documentation.

#### Admin Interface for Translations

Add to Settings → Translations page:

```
┌─────────────────────────────────────────────────────────────┐
│ Translations                                                 │
├─────────────────────────────────────────────────────────────┤
│ Language: [French ▼]                                        │
│                                                             │
│ Programs                                                    │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ Housing Support Program                                  │ │
│ │ English: Housing Support Program                        │ │
│ │ French:  [Programme de soutien au logement    ] ⚠ stale │ │
│ └─────────────────────────────────────────────────────────┘ │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ Employment Services                                      │ │
│ │ English: Employment Services                            │ │
│ │ French:  [Services d'emploi                   ] ✓       │ │
│ └─────────────────────────────────────────────────────────┘ │
│                                                             │
│ [💡 Suggest translations with AI]  [Save all]              │
└─────────────────────────────────────────────────────────────┘
```

#### Keeping Translations Fresh

**Problem:** English source text changes, French translation becomes stale.

**Solution:** Track source text hash

```python
translations = {
    "fr": {
        "name": "Programme de soutien au logement",
        "name_source_hash": "abc123",  # Hash of English name when translated
        "_stale": ["name"]  # List of stale fields (computed on save)
    }
}
```

On save, compare current English hash to stored hash. If different, mark field as stale.

Admin shows ⚠ icon next to stale translations.

#### AI-Assisted Translation (Optional Enhancement)

"Suggest translations" button in admin:
1. Sends English text to Claude API
2. Gets French translation suggestion
3. Admin reviews and approves
4. Saves with current source hash

This is optional — agencies can manually translate if they prefer.

## Language Selection Logic

```
User visits page
    ↓
Check user.preferred_language (if logged in)
    ↓ (not set)
Check agency.default_language (from SiteSettings)
    ↓ (not set)
Check browser Accept-Language header
    ↓ (not available)
Default to English
```

**Storage:**
- User preference: `User.preferred_language` field
- Agency default: `SiteSettings.default_language` field
- Session: `request.LANGUAGE_CODE` (Django standard)

## Implementation Phases

### Phase 1: Complete French for v1.0 Launch

Before any Canadian agency can use the system.

**1A: System UI Translation**
- [ ] Implement AI translation management command (I18N1)
- [ ] Translate 630 system strings to French
- [ ] Compile and commit .mo files
- [ ] Enable French in LANGUAGES setting

**1B: Bilingual Landing Page**
- [ ] Create equal-prominence language choice page (I18N2)
- [ ] Two buttons side by side: English | Français
- [ ] Bilingual tagline below logo
- [ ] Store choice in cookie (pre-login) and user profile (post-login)
- [ ] Detect browser Accept-Language for first-time highlighting

**1C: Language Switcher**
- [ ] Add [EN | FR] toggle to navbar (I18N2b)
- [ ] Current language highlighted
- [ ] One-click switch, no dropdown

**1D: Terminology Defaults**
- [ ] Ensure all 24 terms have French defaults (I18N3)
- [ ] Test terminology switching by language

**1E: French UX Audit**
- [ ] Audit all empty states for French text (I18N4a)
- [ ] Audit all error/validation messages (I18N4b)
- [ ] Verify date formatting uses French locale (I18N4c)
- [ ] Verify all placeholders are translated (I18N4d)
- [ ] Test complete user journey in French (I18N4e)

**1F: Canadian Localization**
- [ ] Postal code field accepts "A1A 1A1" and "A1A1A1", normalizes on save (I18N5)
- [ ] Address labels use "Province" not "State" (I18N5a)
- [ ] Phone fields accept multiple Canadian formats (I18N5b)
- [ ] Date/currency formatting respects language locale (I18N5c)

### Phase 2: Agency Content Translation Infrastructure

**2A: Database Schema**
- [ ] Create TranslatableMixin with `translations` JSONField (I18N10)
- [ ] Add mixin to Program, MetricDefinition, PlanTemplate, CustomFieldDefinition (I18N11)
- [ ] Create migration
- [ ] Add `get_translated(field, lang)` helper method
- [ ] Add stale detection (hash comparison)

**2B: Translations Admin Page**
- [ ] Create Settings → Translations view (I18N12)
- [ ] List content grouped by type (Programs, Metrics, Templates)
- [ ] Show translation status: ✓ complete, ⚠️ stale, ✗ missing
- [ ] Inline editing with save

**2C: Display Translated Content**
- [ ] Update templates to use `get_translated()` (I18N13)
- [ ] Update all dropdowns and lists
- [ ] Test language switching end-to-end

### Phase 3: AI Translation Integration

**3A: API Key Management**
- [ ] Create Settings → Integrations page (I18N14)
- [ ] Add AI provider selection (Anthropic / OpenAI)
- [ ] Encrypted API key storage (Fernet)
- [ ] "Test connection" button
- [ ] Clear messaging that AI is optional

**3B: AI Translation Suggestions**
- [ ] Add "Suggest" button to translation fields (I18N15)
- [ ] Call AI API with source text
- [ ] Show suggestion for review before saving
- [ ] Works for any configured language

### Phase 4: Self-Service Language Addition

**4A: Language Management**
- [ ] Create Settings → Languages page (I18N16)
- [ ] Show enabled languages with toggle
- [ ] "Add language" flow with common languages list
- [ ] Warning about translation effort required

**4B: System UI Generation for New Languages**
- [ ] Extend translation command for any target language (I18N17)
- [ ] Admin trigger: "Generate system translations" button
- [ ] Progress indicator for long-running translation
- [ ] Review/apply workflow

## Files to Create/Modify

| File | Purpose |
|------|---------|
| `konote/mixins.py` | `TranslatableMixin` with `translations` JSONField |
| `apps/programs/models.py` | Add mixin to Program |
| `apps/metrics/models.py` | Add mixin to MetricDefinition |
| `apps/plans/models.py` | Add mixin to PlanTemplate |
| `apps/admin_settings/models.py` | Add mixin to CustomFieldDefinition |
| `apps/admin_settings/views/translations.py` | Translations admin view |
| `apps/admin_settings/views/integrations.py` | API key management view |
| `apps/admin_settings/templates/.../translations.html` | Translation admin UI |
| `apps/admin_settings/templates/.../integrations.html` | API key settings UI |
| `apps/admin_settings/templates/.../languages.html` | Language management UI |
| `templates/includes/language_switcher.html` | Navbar dropdown |
| `konote/translation_service.py` | AI translation abstraction (Anthropic/OpenAI) |

## Cost Estimates

| Item | One-time | Ongoing |
|------|----------|---------|
| AI translation of 630 system strings | ~$1 | — |
| AI translation of agency content (100 items) | ~$0.50 | Per new item |
| Developer time (Phase 1 only) | 4-6 hours | — |
| Developer time (all phases) | 20-30 hours | — |

## Decisions Made

| Question | Decision |
|----------|----------|
| More than EN/FR? | Yes — self-service via JSON approach |
| Stale translations block publishing? | No — warning only |
| Who can edit translations? | Admins only (via Settings) |
| Auto-translate on create? | No — manual trigger, review required |
| AI required? | No — optional enhancement |
| Which AI providers? | Anthropic (Claude) and OpenAI |

## Summary

**For v1.0 launch (Phase 1):**
- Complete French system UI translation
- Complete French terminology defaults
- Add language switcher
- Ship bilingual for Canada

**For content translation (Phase 2):**
- Add `translations` JSONField to key models
- Build admin interface for managing translations
- Stale tracking when source text changes

**For AI assistance (Phase 3):**
- Optional API key configuration
- "Suggest" button for translation help
- Supports Anthropic and OpenAI

**For additional languages (Phase 4):**
- Self-service language addition
- Generate system UI translations via AI
- No code changes required per language
