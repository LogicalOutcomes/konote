# QA-DATA6: Seed Missing Demo Clients for Scenario Runner

**Created:** 2026-02-08
**Status:** Done (2026-02-08)
**Affects:** 13 failing scenario tests

## Problem

The scenario runner in `tests/scenario_eval/scenario_runner.py` creates test data in `_create_test_data()`, but only seeds 4 clients:

| Client | Created By | Program |
|--------|-----------|---------|
| Jane Doe | `browser_base.py` (base) | Housing Support |
| Bob Smith | `browser_base.py` (base) | Youth Services |
| Aisha Mohamed | `scenario_runner.py` | Youth Services |
| James Thompson | `scenario_runner.py` | Housing Support |

13 scenarios fail because they reference clients that don't exist in the test database.

## Missing Clients

6 clients need to be added to `ScenarioRunner._create_test_data()`:

### 1. Maria Santos
- **Needed by:** SCN-015 (batch notes), SCN-058 (cognitive load)
- **Program:** Housing Support (`program_a`)
- **Data needed:** Active status, phone number
- **Conflict note:** SCN-010 (new intake) and SCN-045 (validation errors) both CREATE Maria Santos as part of the test workflow. Since `setUp` runs before each test, seeding Maria means those two scenarios would find her already existing. Two options:
  - **Option A (recommended):** Seed Maria for the 2 scenarios that need her. Update SCN-010 and SCN-045 in the qa-scenarios repo to use a different client name (e.g., "Sofia Reyes" for SCN-010, keep validation test generic in SCN-045).
  - **Option B:** Don't seed Maria. Instead, add a setup step to SCN-015 and SCN-058 that creates her before the test actions begin. More complex, less clean.

### 2. Priya Patel
- **Needed by:** SCN-015 (batch notes), SCN-025 (receptionist lookup)
- **Program:** Housing Support (`program_a`)
- **Data needed:** Active status, phone number, email

### 3. Alex Chen
- **Needed by:** SCN-015 (batch notes)
- **Program:** Housing Support (`program_a`)
- **Data needed:** Active status

### 4. Aaliyah Thompson
- **Needed by:** SCN-042 (multi-program client)
- **Programs:** Housing Support (`program_a`) AND Youth Services (`program_b`) -- dual enrolment is the whole point of SCN-042
- **Data needed:** Active status, enrolment in both programs, at least one note in each program

### 5. Marcus Williams
- **Needed by:** SCN-049 (shared-device handoff / data bleed)
- **Program:** Housing Support (`program_a`)
- **Data needed:** Active status, at least one note (so there's data to potentially leak between sessions)

### 6. David Park
- **Needed by:** SCN-070 (PIPEDA consent withdrawal)
- **Program:** Housing Support (`program_a`)
- **Data needed:** Active status, consent_given_at set, consent_type = "written", at least one note and one event (so there's data to export/delete)

## Implementation Steps

All changes in `tests/scenario_eval/scenario_runner.py`, method `_create_test_data()`, after the existing Aisha Mohamed and James Thompson blocks (~line 252):

### Step 1: Add Maria Santos (Housing Support)

```python
# SCN-015, SCN-058 need Maria Santos in Housing Support
if not any(c.first_name == "Maria" for c in ClientFile.objects.all()):
    maria = ClientFile.objects.create(is_demo=False)
    maria.first_name = "Maria"
    maria.last_name = "Santos"
    maria.status = "active"
    maria.save()
    ClientProgramEnrolment.objects.create(
        client_file=maria, program=self.program_a,
    )
    if hasattr(self, "phone_field"):
        ClientDetailValue.objects.create(
            client_file=maria, field_def=self.phone_field,
            value="416-555-0147",
        )
```

### Step 2: Add Priya Patel (Housing Support)

```python
# SCN-015, SCN-025 need Priya Patel in Housing Support
if not any(c.first_name == "Priya" for c in ClientFile.objects.all()):
    priya = ClientFile.objects.create(is_demo=False)
    priya.first_name = "Priya"
    priya.last_name = "Patel"
    priya.status = "active"
    priya.save()
    ClientProgramEnrolment.objects.create(
        client_file=priya, program=self.program_a,
    )
    if hasattr(self, "phone_field"):
        ClientDetailValue.objects.create(
            client_file=priya, field_def=self.phone_field,
            value="905-555-0233",
        )
```

### Step 3: Add Alex Chen (Housing Support)

```python
# SCN-015 needs Alex Chen in Housing Support
if not any(c.first_name == "Alex" for c in ClientFile.objects.all()):
    alex = ClientFile.objects.create(is_demo=False)
    alex.first_name = "Alex"
    alex.last_name = "Chen"
    alex.status = "active"
    alex.save()
    ClientProgramEnrolment.objects.create(
        client_file=alex, program=self.program_a,
    )
```

### Step 4: Add Aaliyah Thompson (dual-program)

```python
# SCN-042 needs Aaliyah Thompson enrolled in BOTH programs
if not any(c.first_name == "Aaliyah" for c in ClientFile.objects.all()):
    aaliyah = ClientFile.objects.create(is_demo=False)
    aaliyah.first_name = "Aaliyah"
    aaliyah.last_name = "Thompson"
    aaliyah.status = "active"
    aaliyah.save()
    ClientProgramEnrolment.objects.create(
        client_file=aaliyah, program=self.program_a,
    )
    ClientProgramEnrolment.objects.create(
        client_file=aaliyah, program=self.program_b,
    )
    # Add a note in each program so cross-program visibility can be tested
    ProgressNote.objects.create(
        client_file=aaliyah, author=self.staff_user,
        author_program=self.program_a, note_type="quick",
    )
```

### Step 5: Add Marcus Williams (Housing Support)

```python
# SCN-049 needs Marcus Williams with existing data (shared-device handoff)
if not any(c.first_name == "Marcus" for c in ClientFile.objects.all()):
    marcus = ClientFile.objects.create(is_demo=False)
    marcus.first_name = "Marcus"
    marcus.last_name = "Williams"
    marcus.status = "active"
    marcus.save()
    ClientProgramEnrolment.objects.create(
        client_file=marcus, program=self.program_a,
    )
    ProgressNote.objects.create(
        client_file=marcus, author=self.staff_user,
        author_program=self.program_a, note_type="quick",
    )
```

### Step 6: Add David Park (Housing Support, with consent)

```python
# SCN-070 needs David Park with consent and data for PIPEDA withdrawal test
if not any(c.first_name == "David" for c in ClientFile.objects.all()):
    david = ClientFile.objects.create(is_demo=False)
    david.first_name = "David"
    david.last_name = "Park"
    david.status = "active"
    david.consent_given_at = timezone.now()
    david.consent_type = "written"
    david.save()
    ClientProgramEnrolment.objects.create(
        client_file=david, program=self.program_a,
    )
    ProgressNote.objects.create(
        client_file=david, author=self.staff_user,
        author_program=self.program_a, note_type="quick",
    )
    Event.objects.create(
        client_file=david, title="Initial intake",
        event_type=self.event_type, start_timestamp=timezone.now(),
        author_program=self.program_a,
    )
```

### Step 7: Update qa-scenarios for Maria Santos conflict

In the **konote-qa-scenarios** repo, update:
- `scenarios/setup/SCN-010-morning-intake.yaml` — change client name from "Maria Santos" to "Sofia Reyes"
- `scenarios/edge-cases/SCN-045-error-states.yaml` — change client name from "Maria Santos" to "Lucia Vargas" (or any name not in the seed list)

This avoids the conflict where seeded Maria Santos breaks scenarios that expect to create her fresh.

## Imports Needed

At the top of the client-seeding block, add these imports (some may already be available from the existing Aisha/James blocks):

```python
from apps.clients.models import ClientFile, ClientProgramEnrolment, ClientDetailValue
from apps.notes.models import ProgressNote
from apps.events.models import Event
from django.utils import timezone
```

## Verification

After implementation, re-run the 13 previously failing scenarios:
```
pytest tests/scenario_eval/ -k "SCN-010 or SCN-015 or SCN-020 or SCN-025 or SCN-042 or SCN-045 or SCN-046 or SCN-048 or SCN-049 or SCN-050 or SCN-058 or SCN-059 or SCN-070" -v
```

All 13 should now pass (or fail for new/different reasons unrelated to missing clients).
