# Multi-Factor Authentication (SEC2)

## Overview

Document MFA options for KoNote and implement TOTP support for local authentication.

## Current State

| Auth Mode | MFA Support |
|-----------|-------------|
| Azure AD SSO | Yes — configured in Azure Entra ID by the agency |
| Local password | **No** — single-factor only |

## Recommendation Summary

| Situation | MFA Approach |
|-----------|--------------|
| Agency uses Microsoft 365 | Use Azure AD SSO — MFA is built-in and free |
| Agency doesn't use M365 | Implement TOTP (authenticator apps) for local auth |
| Small agency, low risk | Local auth acceptable if strong passwords enforced |

---

## Option 1: Azure AD SSO (Recommended)

**Best for:** Agencies already using Microsoft 365 or Azure.

### How It Works

1. Agency configures Azure Entra ID (formerly Azure AD) as identity provider
2. KoNote redirects login to Microsoft
3. Microsoft handles MFA (SMS, authenticator app, security key, etc.)
4. User is redirected back to KoNote with authentication token

### Agency Setup Steps

1. Create an App Registration in Azure Entra ID
2. Configure redirect URI to point to KoNote
3. Enable MFA in Azure Entra ID security settings (free with Microsoft 365)
4. Add `AZURE_*` environment variables to KoNote

### Documentation to Add

Add to `docs/security-operations.md`:

```markdown
## Multi-Factor Authentication with Azure AD

If your agency uses Microsoft 365, you can enable MFA for KoNote through Azure Entra ID:

1. Sign in to the [Azure Portal](https://portal.azure.com)
2. Navigate to Azure Active Directory → Security → MFA
3. Enable MFA for all users or specific security groups
4. Configure allowed authentication methods (authenticator app recommended)

Once enabled, all users signing into KoNote will be prompted for MFA through Microsoft.
```

---

## Option 2: TOTP for Local Auth

**Best for:** Agencies without Microsoft 365 who need MFA.

### Implementation Approach

Use `django-otp` with TOTP (Time-based One-Time Password) — compatible with Google Authenticator, Microsoft Authenticator, Authy, etc.

### Dependencies

```
django-otp>=1.3.0
qrcode>=7.4.0
```

### User Flow

1. **Setup:** User goes to Profile → Security → Enable MFA
2. **Enrollment:** Scan QR code with authenticator app
3. **Verification:** Enter 6-digit code to confirm setup
4. **Login:** After password, prompted for 6-digit code

### Model Changes

```python
# apps/auth_app/models.py

class User(AbstractBaseUser, PermissionsMixin):
    # Existing fields...

    # MFA fields
    mfa_enabled = models.BooleanField(default=False)
    mfa_secret = models.CharField(max_length=32, blank=True)
    mfa_backup_codes = models.JSONField(default=list, blank=True)
```

### Admin Controls

- Admin can require MFA for specific roles (e.g., program managers and above)
- Admin can reset user's MFA if they lose their device
- Backup codes for account recovery (one-time use)

### Files to Create/Modify

| File | Change |
|------|--------|
| `apps/auth_app/models.py` | Add MFA fields to User |
| `apps/auth_app/views.py` | Add MFA setup and verification views |
| `apps/auth_app/forms.py` | Add MFA setup form |
| `templates/auth_app/mfa_setup.html` | QR code display and confirmation |
| `templates/auth_app/mfa_verify.html` | Code entry during login |
| `requirements.txt` | Add django-otp, qrcode |

### Estimated Effort

- Dependencies and configuration: ~30 minutes
- Model changes and migration: ~1 hour
- Views and templates: ~2 hours
- Testing: ~1 hour
- Documentation: ~30 minutes

---

## Option 3: Documentation Only (Minimum Viable)

If TOTP implementation is deferred, document the security trade-offs:

### Add to `docs/security-operations.md`:

```markdown
## Authentication Security

### Azure AD SSO (Recommended)

Use Azure AD SSO for production deployments. This provides:
- Multi-factor authentication
- Conditional access policies
- Centralized user management
- Audit logging through Azure

### Local Password Authentication

Local auth is suitable for:
- Development and testing
- Small agencies without Microsoft 365
- Demos and trials

**Security considerations for local auth:**
- Enforce strong passwords (12+ characters)
- Passwords are hashed with Argon2 (industry-leading)
- No built-in MFA — consider Azure AD if MFA is required
- Session timeout after 8 hours of inactivity
```

---

## Recommendation

**Phase 1 (Minimum):** Add documentation explaining MFA options and when to use Azure AD vs. local auth. Update security-operations.md.

**Phase 2 (When requested):** Implement TOTP for local auth using django-otp.

Most nonprofits using Microsoft 365 can get MFA "for free" through Azure AD. TOTP implementation is only needed for agencies without M365 access.

---

## Compliance Notes

| Standard | MFA Requirement |
|----------|-----------------|
| PIPEDA | Not explicitly required, but "appropriate safeguards" expected |
| PHIPA | Not explicitly required, but recommended for health data |
| SOC 2 | Typically expected for access to sensitive systems |
| WCAG 2.2 | MFA flows must be accessible (no CAPTCHA, support assistive tech) |

For agencies serving vulnerable populations (health, housing, youth services), MFA is considered a best practice even when not legally mandated.
