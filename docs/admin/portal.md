# Portal

The participant portal gives participants a secure way to view their goals, progress, and journal entries. Staff manage portal access from the participant detail page.

---

## Inviting a Participant to the Portal

1. Navigate to the participant's file
2. Click **Portal** -> **Create Invite**
3. Optionally set a **verbal code** -- an extra verification step the participant must enter when accepting the invite (useful when you want to confirm identity in person or by phone)
4. Click **Create Invite**
5. Copy the generated invite link and share it with the participant

The invite link is valid for **7 days** and can only be used once. When the participant opens the link, they create their own email, display name, and password. They are then guided through a consent flow before reaching their dashboard.

> **Tip:** If a verbal code is set, share it separately from the invite link (e.g., tell the participant in person and send the link by email). This adds a layer of identity verification.

---

## Managing Portal Access

From the participant file, click **Portal** -> **Manage Portal** to see:

- Whether the participant has an active portal account
- A list of all invites (pending, accepted, expired)
- Any pending correction requests from the participant

---

## Revoking Portal Access

If a participant should no longer have portal access:

1. Go to their file -> **Portal** -> **Manage Portal**
2. Click **Revoke Access**

This deactivates their account immediately. They will not be able to log in. Historical data (journal entries, messages) is preserved.

---

## Resetting Multi-Factor Authentication

If a participant is locked out of their MFA (lost their phone, can't access their authenticator app):

1. Go to their file -> **Portal** -> **Manage Portal**
2. Click **Reset MFA**

This clears their MFA setup. The next time they log in, they can set up MFA again from their portal settings.

All portal management actions (invite creation, access revocation, MFA resets) are recorded in the audit log.

---

[Back to Admin Guide](index.md)
