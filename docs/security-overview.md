# KoNote Security Overview

**Last updated:** February 2026 | **Applies to:** KoNote v1.x

> **Disclaimer:** This document describes KoNote's security features. It is not legal advice. Consult your privacy officer or legal counsel to ensure your implementation meets your jurisdiction's requirements.

---

## What KoNote Protects

KoNote stores sensitive client information -- names, dates of birth, contact information, progress notes, and outcome measurements. This is the kind of data that privacy legislation like PIPEDA and PHIPA is designed to protect.

All personally identifiable information is encrypted in the database using AES encryption. Even if someone gained direct access to the database, they would see scrambled data, not client records. The encryption key is stored separately from the database, so compromising one does not compromise the other.

---

## How Security Works

KoNote uses multiple layers of protection. Each layer addresses a different type of risk.

- **Encryption at rest** -- All client names, notes, and outcome ratings are encrypted using Fernet, which combines AES-128 encryption with HMAC authentication (a method that detects tampering). Encrypted fields are stored as unreadable ciphertext in the database. A database breach alone does not expose client data.

- **Key management options** -- Agencies can manage their own encryption key or use a hosting-managed key. Either way, the key is stored outside the application code and never appears in the source repository.

- **Audit logging** -- Every data access, export, and administrative action is logged to a separate audit database. When configured as recommended, these logs cannot be modified through the application, creating a reliable record for compliance reviews.

- **Role-based access control** -- Four roles (front desk, staff, program manager, admin) control what each person can see and do. These permissions are enforced on the server, not just in the user interface, so they cannot be bypassed.

- **Export controls** -- Elevated exports (such as bulk data downloads) have built-in time delays and generate audit entries, giving administrators visibility into data movement.

- **Demo and real data separation** -- Demo users never see real client data and real users never see demo data. This separation is enforced at the database query level, not just the interface, so it cannot be accidentally circumvented.

---

## Protection Levels

During setup, agencies choose a protection level based on their resources and risk tolerance.

### Standard Protection (Recommended for most agencies)

- Encryption key stored in the hosting platform's environment variables
- **Protects against:** database breaches, backup exposure, unauthorised staff access
- **Key recovery:** the hosting provider can assist if account access is maintained
- **Choose this if:** you trust your hosting provider and want strong protection without the burden of managing your own encryption key

### Enhanced Protection

- Encryption key stored separately from the hosting platform
- **Protects against:** all of the above, plus access by the hosting provider itself
- **Key recovery:** the agency is solely responsible -- if the key is lost, encrypted data is permanently unrecoverable
- **Choose this if:** you have IT support, documented key management procedures, and a specific need for additional isolation between your data and your hosting provider

---

## Trust, But Verify

KoNote is open-source software licensed under the MIT licence. Unlike proprietary case management tools, any agency can verify our security claims independently -- no vendor permission needed.

Three ways to verify:

1. **AI code review** -- Use a free AI-powered code review tool. We provide ready-made review prompts to make this straightforward.
2. **Internal review** -- Have your IT staff or consultant clone the public repository and review the code directly.
3. **Professional audit** -- Hire a security firm for a penetration test. They get full access to the source code, which makes audits faster and more thorough.

We also run automated security scanning tools on every code change. Results are visible on the public GitHub repository. For details, see the [Independent Review Guide](independent-review.md).

---

## Authentication Options

KoNote supports two ways for users to sign in.

- **Azure AD Single Sign-On (recommended for agencies using Microsoft 365)** -- Users sign in with their existing Microsoft account. Multi-factor authentication is handled by Microsoft and can be required by your organisation's IT policies.

- **Local passwords with Argon2 hashing** -- For agencies without Microsoft 365. Argon2 is the current industry standard for secure password storage, designed to resist brute-force attacks.

While PIPEDA does not explicitly mandate multi-factor authentication, the Privacy Commissioner increasingly considers it a reasonable safeguard for sensitive data. Agencies handling health or social service data should treat MFA as expected.

---

## Compliance Support

KoNote provides technical safeguards, but compliance also requires organisational measures. The table below shows the division of responsibility.

| KoNote provides | Your agency still needs |
|---|---|
| Encryption of personally identifiable information | Privacy policies tailored to your services |
| Role-based access control | Consent procedures for data collection |
| Audit logging of all data access | Staff training on privacy and security |
| Session timeouts for inactive users | A breach response plan |
| Data erasure workflows (PIPEDA/PHIPA) | Data retention policies |
| Export monitoring and controls | Data processing agreements with your hosting provider |

For agencies completing Privacy Impact Assessments, see the PIA Template Answers document for pre-written responses covering KoNote's technical controls.

---

## Further Reading

- [Security Operations Guide](security-operations.md) -- for IT staff setting up and maintaining KoNote
- [Independent Review Guide](independent-review.md) -- for verifying security claims
- [Security Architecture](security-architecture.md) -- for developers and security reviewers
- [PIA Template Answers](pia-template-answers.md) -- pre-written answers for Privacy Impact Assessments
