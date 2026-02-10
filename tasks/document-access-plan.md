# Document Access Feature — Design Plan

**Status:** Draft for review
**Created:** 2026-02-03
**Purpose:** Enable staff to access client documents stored in external systems (SharePoint, Google Drive) from within KoNote

---

## Executive Summary

After expert panel review, the original "Document Link" feature (DOC5) has been redesigned. Instead of staff manually linking individual documents to client records, KoNote will provide a single "Open Documents Folder" button that navigates to the client's folder in the organization's document storage system.

**Key Decision:** Don't build per-document linking. Build folder-level access instead.

---

## Problem Statement

### Original Feature Request
Allow staff to paste URLs to individual documents (consent forms, referrals, assessments) into client records.

### Expert Panel Findings

A panel of three experts (Frontline Social Worker, Nonprofit IT Administrator, UX Researcher) evaluated the usability of per-document linking.

#### Workflow Analysis

The proposed workflow for linking a single document:

1. Client signs paper consent form
2. Staff scans document (walk to scanner, wait, name file, save)
3. Open SharePoint in browser, navigate to correct folder
4. Upload file
5. Wait for upload
6. Right-click file → "Copy link"
7. SharePoint asks: "Who should this link work for?" (4 confusing options)
8. Copy the generated link
9. Switch to KoNote, find client, find "Add Document"
10. Paste link, add title, select type, save

**Conclusion:** 10 steps across 3 systems. Staff will abandon this after the first few clients.

#### SharePoint Link Permission Dialog

When staff click "Copy link" in SharePoint, they see:

```
┌────────────────────────────────────────────┐
│  Copy link                                 │
│                                            │
│  ○ Anyone with the link      ← DANGEROUS   │
│  ○ People in your organization             │
│  ● People with existing access             │
│  ○ Specific people                         │
│                                            │
│  [ Other settings ▼ ]                      │
│                                            │
│  [  Copy  ]                                │
└────────────────────────────────────────────┘
```

**Problems:**
- Staff don't understand these options
- Wrong choice → colleague can't access, or security violation
- Creates IT helpdesk burden
- Staff will give up and just email documents (worse security)

#### Adoption Prediction

| Metric | Per-Document Links | Folder Button |
|--------|-------------------|---------------|
| Initial adoption | 20-30% | 60-80% |
| 3-month sustained use | <5% | 60-80% |
| If mandated | Resentment, workarounds | Acceptable |

---

## Revised Design: Folder Link Button

### Concept

Instead of linking individual documents, provide a button on each client record that opens the client's document folder in the external storage system.

```
┌─────────────────────────────────────────────────────────────┐
│  Client: Jane Smith (REC-2024-042)                         │
│  Status: Active                                             │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  [Info] [Plan] [Notes] [Events] [Analysis]                  │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  📁 Open Documents Folder                           │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  Programs: Youth Housing, Mental Health Support            │
│  ...                                                        │
└─────────────────────────────────────────────────────────────┘
```

### How It Works

1. Admin configures document storage URL template once (during setup)
2. Button appears on all client records
3. Staff clicks button → opens client's folder in new tab
4. SharePoint/Google Drive handles authentication and permissions
5. Staff can view, upload, download documents directly in storage system

### URL Templates by Provider

#### SharePoint (Microsoft 365)

SharePoint URLs are path-based and predictable:

```
Template: https://{tenant}.sharepoint.com/sites/{site}/Clients/{record_id}/

Example:  https://contoso.sharepoint.com/sites/KoNote/Clients/REC-2024-042/
```

**Folder structure required in SharePoint:**
```
📁 KoNote (SharePoint site)
  📁 Clients/
    📁 REC-2024-001/
      📄 Consent Form.pdf
      📄 Referral Letter.pdf
    📁 REC-2024-002/
      📄 ...
```

**Permissions:** Set at folder level. Staff with access to a client in KoNote should be in the SharePoint group for that client's folder (or a parent folder).

#### Google Drive (Google Workspace)

Google Drive URLs use opaque folder IDs, not paths:

```
Folder URL: https://drive.google.com/drive/folders/1AbCdEfGhIjKlMnOpQrStUvWxYz
                                               └── Random ID, not derivable from Record ID
```

**Problem:** Cannot construct URL from Record ID.

**Solution:** Use search URL instead:

```
Template: https://drive.google.com/drive/search?q={record_id}

Example:  https://drive.google.com/drive/search?q=REC-2024-042
```

**Folder naming required in Google Drive:**
```
📁 Clients (Shared Drive)
  📁 REC-2024-001 - Smith, Jane/
  📁 REC-2024-002 - Jones, Marcus/
```

Folder name MUST start with Record ID for search to work.

**Permissions:** Set at Shared Drive or folder level.

---

## Comparison: SharePoint vs Google Drive

| Aspect | SharePoint | Google Drive |
|--------|------------|--------------|
| **URL predictability** | ✅ Path-based, derivable from Record ID | ❌ Opaque folder IDs |
| **Button behaviour** | Opens folder directly | Opens search results |
| **Button label** | "Open Documents Folder" | "Search Documents" |
| **User experience** | Slightly better (direct) | Acceptable (one extra click) |
| **Folder naming** | Flexible (just use Record ID) | Must start with Record ID |
| **Permission model** | Folder/site groups | Shared Drive / folder sharing |
| **Enterprise adoption** | More common in Canadian nonprofits | Less common for sensitive data |

---

## Implementation Plan

### Data Model

Add provider configuration to instance settings:

```python
# apps/admin_settings/models.py

class InstanceSetting(models.Model):
    # ... existing fields ...

    # Document storage configuration
    document_storage_provider = models.CharField(
        max_length=20,
        choices=[
            ('none', 'Not configured'),
            ('sharepoint', 'SharePoint / OneDrive'),
            ('google_drive', 'Google Drive'),
        ],
        default='none'
    )
    document_storage_url_template = models.CharField(
        max_length=500,
        blank=True,
        help_text='URL template with {record_id} placeholder'
    )
```

### Admin UI

Add to Instance Settings page:

```
Document Storage
────────────────

Provider: [SharePoint / OneDrive ▼]

URL Template:
┌─────────────────────────────────────────────────────────────────┐
│ https://contoso.sharepoint.com/sites/KoNote/Clients/{record_id}/│
└─────────────────────────────────────────────────────────────────┘

ℹ️ Use {record_id} where the client's Record ID should appear.

[Test with sample Record ID: REC-2024-001] → Opens URL in new tab
```

### Template Implementation

```html
<!-- templates/clients/_client_header.html -->

{% if settings.document_storage_provider != 'none' %}
<a href="{{ settings.document_storage_url_template|replace:'{record_id}':client.record_id }}"
   target="_blank"
   rel="noopener noreferrer"
   class="button outline"
   title="Opens in {{ settings.get_document_storage_provider_display }}">
    {% if settings.document_storage_provider == 'google_drive' %}
        🔍 Search Documents
    {% else %}
        📁 Open Documents Folder
    {% endif %}
</a>
{% endif %}
```

### Context Processor

```python
# konote/context_processors.py

def document_storage(request):
    settings = get_cached_settings()
    return {
        'document_storage': {
            'provider': settings.document_storage_provider,
            'url_template': settings.document_storage_url_template,
            'provider_display': settings.get_document_storage_provider_display(),
        }
    }
```

### URL Generation (View Helper)

```python
# apps/clients/helpers.py

def get_document_folder_url(client):
    """
    Generate URL to client's document folder in external storage.
    Returns None if document storage not configured.
    """
    settings = get_cached_settings()

    if settings.document_storage_provider == 'none':
        return None

    if not settings.document_storage_url_template:
        return None

    return settings.document_storage_url_template.replace(
        '{record_id}',
        client.record_id
    )
```

---

## Setup Documentation for Agencies

### SharePoint Setup Guide

1. **Create document library structure:**
   ```
   SharePoint site: https://[tenant].sharepoint.com/sites/KoNote

   Create folder: Clients/
   ```

2. **Create client folders:**
   - When creating a new client in KoNote, note the Record ID
   - In SharePoint, create folder: `Clients/[Record ID]/`
   - Example: `Clients/REC-2024-042/`

3. **Set permissions:**
   - Option A: Give all staff access to `/Clients/` folder
   - Option B: Create SharePoint groups matching KoNote programs
   - Option C: Set per-client folder permissions (most restrictive)

4. **Configure KoNote:**
   - Go to Admin → Settings → Instance Settings
   - Provider: SharePoint / OneDrive
   - URL Template: `https://[tenant].sharepoint.com/sites/KoNote/Clients/{record_id}/`
   - Click "Test" to verify

### Google Drive Setup Guide

1. **Create Shared Drive:**
   - In Google Drive, create Shared Drive: "KoNote Documents"
   - This ensures consistent access for team members

2. **Create client folders:**
   - Folder naming convention: `[Record ID] - [Last Name], [First Name]`
   - Example: `REC-2024-042 - Smith, Jane`
   - **Important:** Record ID must be at the start for search to work

3. **Set permissions:**
   - Add staff to Shared Drive with appropriate access level
   - Or manage per-folder if needed

4. **Configure KoNote:**
   - Go to Admin → Settings → Instance Settings
   - Provider: Google Drive
   - URL Template: `https://drive.google.com/drive/search?q={record_id}`
   - Click "Test" to verify

---

## Security Considerations

### What KoNote Stores

- Provider type (sharepoint, google_drive, none)
- URL template string (not sensitive — just a pattern)

**No client document URLs are stored in KoNote.** URLs are generated at render time from the template + Record ID.

### What KoNote Does NOT Handle

- Document storage
- Document permissions
- Document versioning
- Document retention
- Virus scanning
- Encryption of documents

All of these remain the responsibility of the external storage system (SharePoint/Google Drive).

### Permission Synchronization

KoNote roles and external storage permissions are separate:

| Scenario | Result |
|----------|--------|
| Staff has KoNote access, lacks SharePoint access | Sees button, but SharePoint shows "Access Denied" |
| Staff lacks KoNote access, has SharePoint access | Cannot reach client page, cannot see button |
| Staff has both | Full access works |

**Recommendation:** Document for agencies that SharePoint/Google Drive permissions should align with KoNote program roles.

---

## What We're NOT Building

### Per-Document Links (Original DOC5)
- ❌ Model to store individual document URLs
- ❌ Form to add document links
- ❌ List of linked documents on client record
- ❌ Document type dropdown
- ❌ Encrypted URL storage

**Reason:** Expert panel unanimously concluded adoption would be <5% due to workflow friction.

### Document Upload/Storage
- ❌ File upload to KoNote servers
- ❌ Virus scanning
- ❌ Storage management
- ❌ Backup of documents

**Reason:** Massive complexity; storage systems (SharePoint, Google Drive) already solve this well.

### SharePoint/Google Drive API Integration
- ❌ OAuth connection to storage provider
- ❌ Folder listing within KoNote
- ❌ Document preview/iframe
- ❌ Automatic folder creation

**Reason:** Significant complexity; folder link button provides 80% of value at 5% of cost.

---

## Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Feature adoption | >50% of orgs configure it | Count of orgs with provider != 'none' |
| Button click rate | >20% of client page views | Analytics on button clicks (if added) |
| Support tickets | <5 per month | Helpdesk tracking |
| Time to configure | <10 minutes | Agency feedback |

---

## Open Questions for Review

1. **Should we add a "Copy folder URL" button** (in addition to opening it)?
   - Use case: Sharing folder link with external partner
   - Adds slight complexity

2. **Should there be a "Create folder" reminder** when folder doesn't exist?
   - Could detect 404 and show message
   - Adds complexity; may not be worth it

3. **Should we support multiple storage providers per org?**
   - E.g., SharePoint for most, but OneDrive personal for some staff
   - Current design: One provider per instance
   - Recommendation: Keep it simple — one provider

4. **Should Google Drive orgs store folder ID per client instead of using search?**
   - More direct access, but requires staff to copy/paste folder ID once per client
   - Trade-off: Slightly better UX vs. one-time setup burden
   - Recommendation: Start with search; add folder ID field if adoption is low

---

## Implementation Checklist

- [ ] Add `document_storage_provider` and `document_storage_url_template` to InstanceSetting model
- [ ] Create migration
- [ ] Add fields to Instance Settings admin form
- [ ] Add "Test URL" button to admin form
- [ ] Create `get_document_folder_url()` helper function
- [ ] Add document folder button to client detail header
- [ ] Add context processor for template access
- [ ] Write setup guide for SharePoint
- [ ] Write setup guide for Google Drive
- [ ] Update agency-setup.md with document storage section
- [ ] Add to "What KoNote Is and Isn't" documentation

---

## Appendix: Expert Panel Summary

**Panel Members:**
- Frontline Social Worker (12 years community mental health)
- Nonprofit IT Administrator (manages M365 for 40-person agency)
- UX Researcher (specializes in software for non-technical users)

**Key Quotes:**

> "After my third client of the morning, I'm not doing steps 7-10. The document is in SharePoint. Good enough." — Frontline Social Worker

> "When a counsellor clicks 'Copy link,' SharePoint shows a dialog they don't understand. They'll pick the wrong option, call IT, then give up." — IT Administrator

> "The real job is: 'When I open a client record, I want to see everything relevant.' A folder link solves this with minimal friction." — UX Researcher

**Unanimous Conclusion:** Don't build per-document linking. Build folder-level access instead.

---

*This plan is ready for review by another conversation or stakeholder.*
