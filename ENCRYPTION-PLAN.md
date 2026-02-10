# Progress Note Encryption Plan

## Background

### The Problem: CLOUD Act Exposure
The CLOUD Act (2018) allows US authorities to compel US companies to hand over data regardless of where it's stored. Since Railway uses US cloud infrastructure:
- Database encryption at rest (what Railway/PostgreSQL offer) doesn't help — the provider holds the keys
- Transit encryption (HTTPS/TLS) doesn't help — data is decrypted when stored

### The Solution: Application-Level Encryption
When data is encrypted by your application before it reaches the database, the hosting provider only sees encrypted blobs. Even if compelled to hand over data, they can't read it without your `FIELD_ENCRYPTION_KEY`.

---

## Current State (KoNote-web)

### Already Encrypted
| Model | Fields |
|-------|--------|
| ClientFile | first_name, middle_name, last_name, birth_date |
| User | email |
| ClientDetailValue | value (when field marked sensitive) |
| RegistrationSubmission | first_name, last_name, email, phone |

### Not Currently Encrypted (Clinical Content)
| Model | Field | Contains |
|-------|-------|----------|
| ProgressNote | `notes_text` | Quick note content |
| ProgressNote | `summary` | Session summary |
| ProgressNote | `participant_reflection` | Client's own words |
| ProgressNoteTarget | `notes` | Target-specific clinical notes |

---

## Recommendation

Extend the existing encryption pattern to progress note fields. The infrastructure already exists:
- `konote/encryption.py` with `encrypt_field()` / `decrypt_field()` functions
- Fernet encryption (AES-128 + HMAC)
- `FIELD_ENCRYPTION_KEY` environment variable
- Established `_encrypted` BinaryField + property accessor pattern in ClientFile

---

## Trade-offs

### What You Gain
- Clinical content protected from US legal compulsion
- Consistent security posture across all sensitive data
- Uses existing, tested encryption infrastructure

### What You Lose
- **No SQL search on encrypted content** — Can't do `WHERE notes_text LIKE '%housing%'`
- Must decrypt in Python to search (still fast for typical nonprofit scale)

### Search Performance (If Needed)
| Notes to search | Approximate time |
|-----------------|------------------|
| 100 | < 0.1 seconds |
| 1,000 | ~0.2-0.5 seconds |
| 5,000 | ~1-2 seconds |
| 10,000 | ~3-5 seconds |

---

## Implementation Steps

### Step 1: Add Encrypted Columns to ProgressNote Model
**File:** `apps/notes/models.py`

```python
from konote.encryption import encrypt_field, decrypt_field

class ProgressNote(models.Model):
    # ... existing fields ...

    # Add encrypted storage columns
    _notes_text_encrypted = models.BinaryField(default=b"", blank=True)
    _summary_encrypted = models.BinaryField(default=b"", blank=True)
    _participant_reflection_encrypted = models.BinaryField(default=b"", blank=True)

    # Property accessors (replace existing TextField definitions)
    @property
    def notes_text(self):
        if self._notes_text_encrypted:
            return decrypt_field(self._notes_text_encrypted)
        return ""

    @notes_text.setter
    def notes_text(self, value):
        self._notes_text_encrypted = encrypt_field(value) if value else b""

    @property
    def summary(self):
        if self._summary_encrypted:
            return decrypt_field(self._summary_encrypted)
        return ""

    @summary.setter
    def summary(self, value):
        self._summary_encrypted = encrypt_field(value) if value else b""

    @property
    def participant_reflection(self):
        if self._participant_reflection_encrypted:
            return decrypt_field(self._participant_reflection_encrypted)
        return ""

    @participant_reflection.setter
    def participant_reflection(self, value):
        self._participant_reflection_encrypted = encrypt_field(value) if value else b""
```

### Step 2: Add Encrypted Column to ProgressNoteTarget Model
**File:** `apps/notes/models.py`

```python
class ProgressNoteTarget(models.Model):
    # ... existing fields ...

    _notes_encrypted = models.BinaryField(default=b"", blank=True)

    @property
    def notes(self):
        if self._notes_encrypted:
            return decrypt_field(self._notes_encrypted)
        return ""

    @notes.setter
    def notes(self, value):
        self._notes_encrypted = encrypt_field(value) if value else b""
```

### Step 3: Create Schema Migration
```bash
python manage.py makemigrations notes --name add_encrypted_note_fields
```

### Step 4: Create Data Migration (If Existing Notes)
Encrypt existing plaintext notes:

```python
# apps/notes/migrations/XXXX_encrypt_existing_notes.py
from django.db import migrations
from konote.encryption import encrypt_field

def encrypt_existing_notes(apps, schema_editor):
    ProgressNote = apps.get_model('notes', 'ProgressNote')
    ProgressNoteTarget = apps.get_model('notes', 'ProgressNoteTarget')

    for note in ProgressNote.objects.all():
        changed = False
        if note.notes_text:
            note._notes_text_encrypted = encrypt_field(note.notes_text)
            changed = True
        if note.summary:
            note._summary_encrypted = encrypt_field(note.summary)
            changed = True
        if note.participant_reflection:
            note._participant_reflection_encrypted = encrypt_field(note.participant_reflection)
            changed = True
        if changed:
            note.save()

    for target in ProgressNoteTarget.objects.all():
        if target.notes:
            target._notes_encrypted = encrypt_field(target.notes)
            target.save()

class Migration(migrations.Migration):
    dependencies = [
        ('notes', 'XXXX_add_encrypted_note_fields'),
    ]

    operations = [
        migrations.RunPython(encrypt_existing_notes, migrations.RunPython.noop),
    ]
```

### Step 5: Remove Original Plaintext Columns
After verifying encryption works, create final migration to drop plaintext columns.

### Step 6: Update Key Rotation Command
**File:** `apps/auth_app/management/commands/rotate_encryption_key.py`

Add ProgressNote and ProgressNoteTarget fields to the rotation logic.

### Step 7: Add Tests
**File:** `tests/test_encryption.py`

```python
def test_progress_note_encryption(self):
    note = ProgressNote.objects.create(
        client_file=self.client,
        author=self.user,
        note_type='quick'
    )
    note.notes_text = "Sensitive clinical content"
    note.save()

    # Verify encrypted in database
    note.refresh_from_db()
    self.assertTrue(note._notes_text_encrypted)
    self.assertEqual(note.notes_text, "Sensitive clinical content")
```

---

## Files to Modify

1. `apps/notes/models.py` — Add encrypted fields and property accessors
2. `apps/notes/migrations/` — Schema and data migrations
3. `apps/auth_app/management/commands/rotate_encryption_key.py` — Key rotation
4. `tests/test_encryption.py` — Encryption tests

---

## Verification Checklist

- [ ] Back up database before running migrations
- [ ] Run migrations on staging/test first
- [ ] Create a test progress note and verify it saves/loads correctly
- [ ] Check database directly — encrypted columns should contain binary data
- [ ] Run full test suite: `python manage.py test`
- [ ] Verify existing notes still display correctly (if migrating data)

---

## Questions to Consider

1. **Do you have existing progress notes?** If yes, data migration is needed.
2. **Do users need to search note content?** If yes, we'd implement Python-based search.
3. **Backup strategy?** Ensure you have database backups before migrating.

---

## Alternative: Canadian Hosting

Instead of (or in addition to) encryption, you could host on Canadian-owned infrastructure:
- OVHcloud Canada (French-owned, Canadian datacentre)
- Self-hosted Canadian VPS

This adds legal friction but doesn't completely solve the problem. The hybrid approach (encryption + stay on Railway) provides the strongest protection.

---

## Note About KoNoteRedux

If you also use the **KoNoteRedux desktop application**, it already encrypts all data locally with AES-256-GCM. The CLOUD Act concern doesn't apply to the desktop app since data stays on users' computers.
