# Plane Adoption Proposal

**Prepared for**: Technical Manager  
**Date**: February 2026  
**Purpose**: Evaluate Plane as a replacement for Microsoft Planner

---

## Executive Summary

We recommend piloting **Plane**, an open-source project management tool, to address ongoing challenges with Microsoft Planner. Plane offers a modern, fast interface with reliable notifications and would integrate with our existing Microsoft Entra ID authentication.

---

## Current Challenges with Microsoft Planner

| Issue | Business Impact |
|-------|-----------------|
| Unreliable email notifications | Tasks missed, deadlines slipped |
| Slow performance in Teams | Reduced productivity, user frustration |
| Cumbersome task entry | Time wasted on administrative overhead |
| No individual task subscriptions | Users overwhelmed or uninformed |
| Limited views (board only) | Cannot adapt to different work styles |

---

## Why Plane

### Key Benefits

1. **Reliable Notifications**
   - Automatic notifications for assigned tasks
   - Granular control over notification preferences
   - Email and webhook delivery options

2. **Fast, Modern Interface**
   - Loads in under 2 seconds
   - Inline editing and quick actions
   - Keyboard shortcuts for power users

3. **Better Task Management**
   - Multiple views: Board, List, Calendar
   - Task priorities and labels
   - Subtasks and dependencies
   - Activity history

4. **Microsoft Integration**
   - Microsoft Entra ID single sign-on
   - Embeddable as Teams tab
   - Webhook notifications to Teams channels

5. **Open Source**
   - No per-user licensing costs
   - Full control over data
   - Active community and development

### Comparison Summary

| Criteria | Microsoft Planner | Plane |
|----------|-------------------|-------|
| Notification reliability | ❌ Unreliable | ✅ Reliable |
| Performance | ❌ Slow | ✅ Fast |
| Task entry | ❌ Cumbersome | ✅ Quick |
| Views | ⚠️ Board only | ✅ Board, List, Calendar |
| Teams integration | ✅ Native app | ⚠️ Tab + webhooks |
| Cost | Included in M365 | Free (self-hosted) |

---

## Deployment Plan

### Architecture Overview

```
GitHub (Private Repo) → Railway (Hosting) → Microsoft Entra ID (Auth)
                                    ↓
                            Microsoft Teams (Tab + Webhooks)
```

### Prerequisites

- [ ] GitHub organization account with private repository access
- [ ] Railway account (can use existing organizational account)
- [ ] Microsoft Entra ID admin access for SSO configuration
- [ ] Domain for Plane instance (optional but recommended)

---

## Setup Steps

### Step 1: Fork Plane Repository

1. Navigate to https://github.com/makeplane/plane
2. Click **Fork** → Create fork in your organization
3. Set repository to **Private** (for security)
4. Note your fork URL: `https://github.com/YOUR-ORG/plane`

### Step 2: Create Railway Project

1. Log in to Railway (https://railway.app)
2. Click **New Project**
3. Select **Deploy from GitHub repo**
4. Authorize Railway to access your GitHub organization
5. Select your forked Plane repository

### Step 3: Configure Environment Variables

In Railway dashboard, add the following environment variables:

#### Required Variables

```bash
# Database (Railway will provide these if you add PostgreSQL)
DATABASE_URL=<from-railway-postgresql>

# Redis (Railway will provide if you add Redis)
REDIS_URL=<from-railway-redis>

# Security
SECRET_KEY=<generate-a-random-32-char-string>
WEB_URL=https://your-plane-domain.railway.app

# Admin user (for initial setup)
DEFAULT_EMAIL=admin@yourdomain.com
DEFAULT_PASSWORD=<secure-password>
```

#### Microsoft Entra ID Variables

```bash
# Enable SAML/OAuth
OAUTH_ENABLED=1

# Azure AD Configuration
AZURE_CLIENT_ID=<from-step-4>
AZURE_CLIENT_SECRET=<from-step-4>
AZURE_TENANT_ID=<from-step-4>
```

### Step 4: Configure Microsoft Entra ID

1. Go to **Microsoft Entra admin center** (https://entra.microsoft.com)
2. Navigate to **Identity** → **Applications** → **App registrations**
3. Click **New registration**:
   - Name: `Plane`
   - Supported account types: Single tenant
   - Redirect URI: `https://your-plane-domain.railway.app/auth/callback/azure`
4. After registration, note:
   - **Application (client) ID** → `AZURE_CLIENT_ID`
   - **Directory (tenant) ID** → `AZURE_TENANT_ID`
5. Go to **Certificates & secrets** → **New client secret**
6. Copy the secret value → `AZURE_CLIENT_SECRET`
7. Go to **API permissions** → Add:
   - `User.Read`
   - `email`
   - `profile`

### Step 5: Add Database and Redis in Railway

1. In your Railway project, click **Add service**
2. Select **Database** → **PostgreSQL**
3. Railway will auto-link and provide `DATABASE_URL`
4. Click **Add service** again
5. Select **Database** → **Redis**
6. Railway will auto-link and provide `REDIS_URL`

### Step 6: Deploy

1. In Railway, click **Deploy**
2. Monitor the build logs
3. Once deployed, access your instance at the Railway URL
4. Log in with the default admin credentials
5. Configure Microsoft Entra ID in Plane settings

### Step 7: Configure Teams Integration

#### Add Plane as Teams Tab

1. Open Microsoft Teams
2. Navigate to desired team/channel
3. Click **+** (Add tab)
4. Select **Website**
5. Enter:
   - Name: `Plane`
   - URL: `https://your-plane-domain.railway.app`
6. Click **Save**

#### Configure Webhook Notifications

1. In Teams, go to channel → **...** → **Connectors**
2. Add **Incoming Webhook**
3. Copy the webhook URL
4. In Plane, go to **Settings** → **Integrations** → **Webhooks**
5. Add webhook with Teams URL
6. Select events to notify (task created, assigned, completed, etc.)

---

## Estimated Costs

| Item | Cost |
|------|------|
| Plane license | Free (Apache 2.0) |
| Railway hosting | ~$5-20/month (usage-based) |
| Domain (optional) | ~$12/year |
| **Total** | **~$5-20/month** |

Compare to: Atlassian Jira ($7.75/user/month) or Monday.com ($8-16/user/month)

---

## Pilot Plan

### Phase 1: Technical Validation (Week 1)
- Deploy to Railway
- Configure Microsoft Entra ID SSO
- Test with IT team

### Phase 2: Small Group Pilot (Weeks 2-3)
- Onboard 5-10 users
- Migrate one project from Planner
- Gather feedback

### Phase 3: Evaluation (Week 4)
- Survey pilot users
- Compare metrics (task completion, user satisfaction)
- Decision: Continue, adjust, or abandon

### Phase 4: Full Rollout (If successful)
- Migrate remaining projects
- User training
- Decommission Planner for migrated projects

---

## Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| No native Teams app | Medium | Medium | Use Teams tab + webhooks |
| Learning curve | Low | Low | Interface is intuitive; minimal training needed |
| Self-hosted maintenance | Medium | Medium | Railway handles infrastructure; updates are straightforward |
| Feature gaps | Low | Medium | Plane is actively developed; feature requests welcome |

---

## Recommendation

We recommend proceeding with a **4-week pilot** of Plane to validate it addresses our current pain points with Microsoft Planner. The low cost, modern interface, and Microsoft Entra ID integration make it a low-risk trial.

**Next Steps**:
1. Approve pilot project
2. Allocate technical resources for deployment
3. Identify pilot user group
4. Schedule kickoff meeting

---

## Resources

- [Plane Documentation](https://docs.plane.so)
- [Plane GitHub](https://github.com/makeplane/plane)
- [Railway Documentation](https://docs.railway.app)
- [Microsoft Entra ID SAML Setup](https://learn.microsoft.com/en-us/entra/identity-platform/v2-oauth2-auth-code-flow)
