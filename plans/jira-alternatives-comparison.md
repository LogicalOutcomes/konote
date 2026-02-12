# Jira Alternatives Comparison: Plane vs Leantime

**Purpose**: Evaluate open source issue/project tracking tools for a team of non-developer consultants currently using Microsoft Planner.

**Current Pain Points with Microsoft Planner**:
- Difficulty subscribing to tasks
- Unreliable email notifications
- Slow to open/load
- Onerous task entry and updates
- Need for Microsoft Teams app integration

**Requirements**:
- Microsoft Sign In (Azure AD/Microsoft Entra ID)
- Non-developer friendly interface
- Task and project management capabilities
- Microsoft Teams compatibility (via webhooks)

---

## Executive Summary

| Criteria | Plane | Leantime |
|----------|-------|----------|
| **Overall Fit** | ⭐⭐⭐⭐⭐ Excellent | ⭐⭐⭐⭐ Very Good |
| **UI/UX** | Modern, clean, intuitive | Functional, slightly dated |
| **Non-Dev Friendly** | Excellent | Excellent |
| **Microsoft Auth** | Native SAML/OAuth | SAML supported |
| **Learning Curve** | Low | Low |
| **Active Development** | Very Active | Active |
| **License** | Apache 2.0 | GPL-2.0 |

**Recommendation**: **Plane** is the preferred choice for teams seeking a modern, intuitive interface similar to Linear or Asana. **Leantime** is a solid alternative if you need more traditional project management features like timesheets and detailed project planning.

---

## Plane vs Microsoft Planner: Addressing Your Pain Points

This section directly compares Plane against your current experience with Microsoft Planner.

### Pain Point Comparison

| Pain Point | Microsoft Planner | Plane | Improvement |
|------------|-------------------|-------|-------------|
| **Subscribing to tasks** | Confusing subscription model; must subscribe to entire plan | Automatic notifications for assigned tasks; granular watch options | ✅ Significant |
| **Email notifications** | Unreliable; often delayed or missing | Configurable instant or digest notifications | ✅ Significant |
| **Speed/Load time** | Slow, especially in Teams | Fast, lightweight interface | ✅ Significant |
| **Task entry** | Multiple clicks, modal dialogs | Quick add with keyboard shortcuts, inline editing | ✅ Significant |
| **Updating tasks** | Cumbersome interface | Drag-and-drop, inline editing, quick actions | ✅ Significant |
| **Teams integration** | Native Teams app | ⚠️ Webhook notifications only | ❌ Limitation |

### Detailed Comparison: Plane vs Microsoft Planner

#### Task Subscriptions & Notifications

**Microsoft Planner Problems**:
- Users must subscribe to the entire "Plan" to get notifications
- No way to subscribe to individual tasks
- Email notifications are often delayed or don't arrive
- No control over notification frequency
- Notifications go to the group mailbox, not individual

**Plane Solution**:
- **Automatic notifications**: Anyone assigned to or mentioned in a task gets notified
- **Watch feature**: Subscribe to specific tasks without being assigned
- **Granular control**: Choose which events trigger notifications
- **Reliable delivery**: Notifications sent immediately via email or webhook
- **In-app notifications**: Bell icon shows all activity
- **Digest option**: Daily or weekly summary emails available

#### Speed & Performance

**Microsoft Planner Problems**:
- Slow loading, especially in Teams
- Laggy drag-and-drop
- Refreshes lose scroll position
- Heavy SharePoint integration causes delays

**Plane Solution**:
- **Fast loading**: Optimized React frontend, loads in under 2 seconds
- **Smooth interactions**: Real-time updates without page refreshes
- **Keyboard navigation**: Quick actions without mouse
- **Lightweight**: No heavy SharePoint dependencies
- **Mobile responsive**: Works well on phones/tablets

#### Task Entry & Updates

**Microsoft Planner Problems**:
- Click task → wait for modal → edit → save → close
- No quick add from board view
- Required fields slow down entry
- No keyboard shortcuts
- Bulk updates require opening each task

**Plane Solution**:
- **Quick add**: Press `C` or click + to add task inline
- **Inline editing**: Click any field to edit directly on the card
- **Drag and drop**: Move tasks between statuses instantly
- **Keyboard shortcuts**: `C` (create), `E` (edit), `D` (delete), `Enter` (save)
- **Bulk operations**: Select multiple tasks and update at once
- **Templates**: Create tasks from predefined templates

### Teams Integration: The Challenge

**Important Limitation**: Plane does not have a native Microsoft Teams app. This is a significant consideration for your team.

#### Current Teams Integration Options

| Option | Description | Effort | User Experience |
|--------|-------------|--------|-----------------|
| **Webhook notifications** | Post notifications to Teams channel | Low | One-way only |
| **Power Automate** | Create custom flows between Plane and Teams | Medium | Customizable |
| **Embed as tab** | Add Plane URL as Teams tab | Low | Good |
| **Custom Teams app** | Build a Teams wrapper for Plane | High | Best |

#### Recommended Approach: Teams Tab + Webhooks

1. **Add Plane as a Teams Tab**:
   - Add a website tab in Teams pointing to your Plane instance
   - Users can access Plane without leaving Teams
   - Single sign-on works through Microsoft Entra ID

2. **Configure Webhook Notifications**:
   - Set up incoming webhooks in Teams channels
   - Configure Plane to send notifications for important events
   - Users see updates in Teams, click to open in Plane tab

3. **Power Automate Integration** (Optional):
   - Create flows for specific scenarios
   - Example: "When a task is assigned to me, post in my chat"
   - Example: "When a task is due tomorrow, send reminder"

### Feature Comparison: Plane vs Microsoft Planner

| Feature | Microsoft Planner | Plane | Notes |
|---------|-------------------|-------|-------|
| **Kanban board** | ✅ | ✅ | Plane has more view options |
| **List view** | ❌ | ✅ | Planner only has board view |
| **Calendar view** | ✅ (in Outlook) | ✅ | Built into Plane |
| **Task priorities** | ❌ | ✅ | Urgent, High, Medium, Low, None |
| **Due dates** | ✅ | ✅ | Both support |
| **Assignees** | ✅ | ✅ | Multiple assignees in Plane |
| **Labels/tags** | ✅ (limited) | ✅ | Unlimited labels in Plane |
| **Subtasks** | ✅ (checklist) | ✅ | True subtasks in Plane |
| **Attachments** | ✅ | ✅ | Both support file attachments |
| **Comments** | ✅ | ✅ | @mentions in both |
| **Task history** | ❌ | ✅ | Full activity log in Plane |
| **Search** | ⚠️ Limited | ✅ | Global search across projects |
| **Filtering** | ⚠️ Basic | ✅ | Advanced filters and saved views |
| **Recurring tasks** | ❌ | ❌ | Neither supports natively |
| **Time tracking** | ❌ | ⚠️ Basic | Estimates only |
| **Reporting** | ❌ | ⚠️ Basic | Charts and dashboards |
| **Mobile app** | ✅ | ✅ | Both have mobile apps |
| **Offline mode** | ❌ | ❌ | Neither supports offline |

### User Experience Comparison

#### Microsoft Planner Workflow (Current)
```
1. Open Teams → Navigate to Planner tab (wait for load)
2. Click on task → Modal opens (wait)
3. Edit fields → Click Save → Modal closes
4. Repeat for each task
5. Hope notifications work
```

#### Plane Workflow (Proposed)
```
1. Open Teams → Plane tab already loaded (fast)
2. Press 'C' to create task OR click task to edit inline
3. Type title, press Enter → Done
4. Drag to change status
5. Notifications reliably sent to email and Teams channel
```

### Migration Considerations

**What You'll Gain**:
- Faster, more responsive interface
- Reliable notifications
- Better task organization (priorities, labels, subtasks)
- Multiple views (board, list, calendar)
- Activity history on tasks
- Advanced filtering and saved views

**What You'll Lose**:
- Native Teams app experience (requires tab workaround)
- Direct integration with other Microsoft 365 apps
- Familiar interface for existing users

**Migration Effort**:
- Export Planner tasks (via Power Automate or manually)
- Import into Plane (CSV import supported)
- User training (minimal - interface is intuitive)
- Configure Teams tab and webhooks

---

## Tool Overview

### Plane

Plane is a modern, open-source project management tool designed to be simple yet powerful. It offers a clean, intuitive interface that feels similar to commercial tools like Linear and Asana.

- **Website**: https://plane.so
- **GitHub**: https://github.com/makeplane/plane
- **License**: Apache 2.0
- **Self-hosted**: Yes (Docker)
- **Cloud offering**: Yes (plane.so)

**Key Features**:
- Issues and task management
- Kanban boards and list views
- Cycles (sprints) for iterative work
- Modules for grouping related work
- Views for saved filters
- Multiple project support
- Activity tracking
- Integrations (Slack, webhooks)

### Leantime

Leantime is an open-source project management system designed for non-technical teams. It focuses on making project management accessible while providing comprehensive features.

- **Website**: https://leantime.io
- **GitHub**: https://github.com/Leantime/leantime
- **License**: GPL-2.0
- **Self-hosted**: Yes (Docker, LAMP stack)
- **Cloud offering**: Yes (leantime.io)

**Key Features**:
- Task management with Kanban boards
- Project dashboards
- Timesheets and time tracking
- Wiki/knowledge base
- Goal setting and tracking
- Idea management
- Reporting and analytics
- Multiple project support

---

## Feature Comparison

### Task Management

| Feature | Plane | Leantime |
|---------|-------|----------|
| Kanban boards | ✅ | ✅ |
| List view | ✅ | ✅ |
| Task priorities | ✅ | ✅ |
| Due dates | ✅ | ✅ |
| Assignees | ✅ | ✅ |
| Labels/tags | ✅ | ✅ |
| Subtasks | ✅ | ✅ |
| Task relationships | ✅ (parent/child, blocking) | ✅ (dependencies) |
| Task templates | ❌ | ✅ |
| Recurring tasks | ❌ | ✅ |

### Project Organization

| Feature | Plane | Leantime |
|---------|-------|----------|
| Multiple projects | ✅ | ✅ |
| Project categories | ❌ | ✅ |
| Cycles/Sprints | ✅ | ✅ |
| Milestones | ✅ (via modules) | ✅ |
| Gantt charts | ❌ | ✅ |
| Project templates | ❌ | ✅ |

### Collaboration

| Feature | Plane | Leantime |
|---------|-------|----------|
| Comments | ✅ | ✅ |
| @mentions | ✅ | ✅ |
| Activity feed | ✅ | ✅ |
| Notifications | ✅ | ✅ |
| Email notifications | ✅ | ✅ |
| File attachments | ✅ | ✅ |

### Time Tracking

| Feature | Plane | Leantime |
|---------|-------|----------|
| Time tracking | ⚠️ Basic | ✅ Full timesheets |
| Time estimates | ✅ | ✅ |
| Time reports | ❌ | ✅ |
| Billable hours | ❌ | ✅ |

### Reporting & Analytics

| Feature | Plane | Leantime |
|---------|-------|----------|
| Burndown charts | ❌ | ✅ |
| Progress reports | ⚠️ Basic | ✅ |
| Custom reports | ❌ | ⚠️ Limited |
| Dashboards | ✅ | ✅ |
| Export data | ✅ | ✅ |

### Integrations

| Feature | Plane | Leantime |
|---------|-------|----------|
| Webhooks | ✅ | ✅ |
| Slack integration | ✅ | ✅ |
| Microsoft Teams | ⚠️ Via webhook | ⚠️ Via webhook |
| GitHub integration | ✅ | ❌ |
| GitLab integration | ✅ | ❌ |
| API | ✅ | ✅ |

---

## User Experience Comparison

### Plane UI/UX

**Strengths**:
- Modern, clean interface similar to Linear/Asana
- Intuitive navigation
- Fast and responsive
- Dark mode support
- Keyboard shortcuts
- Clean visual hierarchy

**Considerations**:
- May feel minimal for teams wanting detailed project views
- No Gantt chart view
- Focused on agile/iterative workflows

**Best for**: Teams that want a modern, fast, and intuitive experience similar to commercial SaaS tools.

### Leantime UI/UX

**Strengths**:
- Comprehensive project views
- Traditional project management layout
- Built-in wiki for documentation
- Goal tracking visualization
- More detailed reporting

**Considerations**:
- UI feels more traditional/dated
- More features can mean more complexity
- Navigation can be overwhelming initially

**Best for**: Teams that need traditional project management features like timesheets, Gantt charts, and detailed planning.

---

## Microsoft Entra ID Authentication Setup

### Plane: Microsoft Entra ID Setup

Plane supports SAML 2.0 and OAuth for Microsoft Entra ID authentication.

#### Prerequisites
- Microsoft Entra ID (Azure AD) admin access
- Plane self-hosted instance or Plane Cloud
- SSL certificate for your domain

#### Step 1: Register Application in Microsoft Entra ID

1. Navigate to **Microsoft Entra admin center** (https://entra.microsoft.com)
2. Go to **Identity** > **Applications** > **App registrations**
3. Click **New registration**
4. Enter details:
   - **Name**: Plane
   - **Supported account types**: Single tenant or Multi-tenant based on your needs
   - **Redirect URI**: 
     - For OAuth: `https://your-plane-domain.com/auth/callback/azure`
     - For SAML: `https://your-plane-domain.com/complete/saml/`
5. Click **Register**

#### Step 2: Configure SAML (Recommended)

1. In your app registration, go to **Expose an API**
2. Set the Application ID URI
3. Go to **Certificates & secrets** > **New client secret**
4. Copy the secret value

#### Step 3: Configure Plane

For self-hosted Plane, set these environment variables:

```bash
# Enable SAML
SAML_ENABLED=1

# Azure AD SAML Configuration
AZURE_CLIENT_ID=your-application-client-id
AZURE_CLIENT_SECRET=your-client-secret
AZURE_TENANT_ID=your-tenant-id

# Or for OAuth
OAUTH_ENABLED=1
AZURE_OAUTH_CLIENT_ID=your-application-client-id
AZURE_OAUTH_CLIENT_SECRET=your-client-secret
AZURE_OAUTH_TENANT_ID=your-tenant-id
```

#### Step 4: Configure in Plane Admin

1. Log in to Plane as admin
2. Go to **Settings** > **Authentication**
3. Enable **Azure AD** or **SAML**
4. Enter the configuration details from your Microsoft Entra app

---

### Leantime: Microsoft Entra ID Setup

Leantime supports SAML 2.0 authentication with Microsoft Entra ID.

#### Prerequisites
- Microsoft Entra ID (Azure AD) admin access
- Leantime self-hosted instance
- SSL certificate for your domain

#### Step 1: Register Application in Microsoft Entra ID

1. Navigate to **Microsoft Entra admin center** (https://entra.microsoft.com)
2. Go to **Identity** > **Applications** > **Enterprise applications**
3. Click **New application** > **Create your own application**
4. Enter name: Leantime
5. Select **Integrate any other application you dont find in the gallery**
6. Click **Create**

#### Step 2: Configure SAML

1. In the application, go to **Single sign-on**
2. Select **SAML**
3. Configure **Basic SAML Configuration**:
   - **Identifier**: `https://your-leantime-domain.com`
   - **Reply URL**: `https://your-leantime-domain.com/saml/acs`
   - **Sign on URL**: `https://your-leantime-domain.com`
4. Download the **Federation Metadata XML**

#### Step 3: Configure Leantime

Set these environment variables in your Leantime installation:

```bash
# Enable SAML
LEAN_SAML_ENABLED=true

# SAML Configuration
LEAN_SAML_IDP_ENTITYID=https://sts.windows.net/your-tenant-id/
LEAN_SAML_IDP_SSO_URL=https://login.microsoftonline.com/your-tenant-id/saml2
LEAN_SAML_IDP_X509CERT=your-certificate-from-metadata

# Or use metadata URL
LEAN_SAML_IDP_METADATA_URL=https://nexus.microsoftonline-p.com/federationmetadata/saml/federationmetadata.xml
```

#### Step 4: Configure in Leantime Admin

1. Log in to Leantime as admin
2. Go to **Settings** > **Users & Permissions**
3. Enable **SAML Authentication**
4. Upload the metadata XML or enter configuration manually

---

## Microsoft Teams Integration

Both tools can integrate with Microsoft Teams via webhooks for notifications.

### Setting Up Teams Webhook Notifications

#### Step 1: Create Incoming Webhook in Teams

1. Open Microsoft Teams
2. Navigate to the channel where you want notifications
3. Click **...** (more options) > **Connectors**
4. Search for **Incoming Webhook**
5. Click **Configure**
6. Enter a name (e.g., "Plane Notifications")
7. Upload an icon if desired
8. Click **Create**
9. Copy the webhook URL

#### Step 2: Configure Webhook in Plane

1. Go to **Project Settings** > **Integrations**
2. Add a new webhook
3. Paste the Teams webhook URL
4. Select events to trigger notifications:
   - Issue created
   - Issue updated
   - Issue commented
   - Issue closed

#### Step 2: Configure Webhook in Leantime

1. Go to **Project Settings** > **Integrations**
2. Add a new webhook
3. Paste the Teams webhook URL
4. Select events to trigger notifications

### Notification Format

Both tools will send JSON payloads to Teams. You may need to use a middleware service like **Power Automate** to format the messages nicely in Teams.

---

## Deployment Options

### Plane Deployment

**Docker (Recommended)**:
```yaml
# docker-compose.yml
version: '3.8'
services:
  plane:
    image: makeplane/plane:latest
    ports:
      - "3000:3000"
    environment:
      - DATABASE_URL=postgresql://user:pass@db:5432/plane
      - REDIS_URL=redis://redis:6379
      - SAML_ENABLED=1
      - AZURE_CLIENT_ID=your-client-id
      - AZURE_CLIENT_SECRET=your-client-secret
      - AZURE_TENANT_ID=your-tenant-id
    depends_on:
      - db
      - redis
  
  db:
    image: postgres:15
    environment:
      - POSTGRES_DB=plane
      - POSTGRES_USER=user
      - POSTGRES_PASSWORD=pass
    volumes:
      - pgdata:/var/lib/postgresql/data
  
  redis:
    image: redis:alpine

volumes:
  pgdata:
```

**Requirements**:
- PostgreSQL 15+
- Redis
- 2GB+ RAM recommended
- Docker and Docker Compose

### Leantime Deployment

**Docker (Recommended)**:
```yaml
# docker-compose.yml
version: '3.8'
services:
  leantime:
    image: leantime/leantime:latest
    ports:
      - "80:80"
    environment:
      - LEAN_DB_HOST=db
      - LEAN_DB_USER=user
      - LEAN_DB_PASSWORD=pass
      - LEAN_DB_DATABASE=leantime
      - LEAN_SAML_ENABLED=true
      - LEAN_SAML_IDP_ENTITYID=https://sts.windows.net/your-tenant-id/
      - LEAN_SAML_IDP_SSO_URL=https://login.microsoftonline.com/your-tenant-id/saml2
    depends_on:
      - db
  
  db:
    image: mysql:8.0
    environment:
      - MYSQL_DATABASE=leantime
      - MYSQL_USER=user
      - MYSQL_PASSWORD=pass
      - MYSQL_ROOT_PASSWORD=rootpass
    volumes:
      - dbdata:/var/lib/mysql

volumes:
  dbdata:
```

**Requirements**:
- MySQL 8.0+ or MariaDB
- 1GB+ RAM recommended
- Docker and Docker Compose

---

## Cost Comparison

### Self-Hosted

| Cost Factor | Plane | Leantime |
|-------------|-------|----------|
| License | Free (Apache 2.0) | Free (GPL-2.0) |
| Server costs | ~$20-50/month | ~$15-40/month |
| Database | PostgreSQL (free) | MySQL (free) |
| SSL certificate | Let's Encrypt (free) | Let's Encrypt (free) |
| Maintenance | Required | Required |

### Cloud Offering

| Plan | Plane Cloud | Leantime Cloud |
|------|-------------|----------------|
| Free tier | 1 workspace, 5 users | 1 project, 2 users |
| Pro | $7/user/month | $8/user/month |
| Enterprise | Custom pricing | Custom pricing |

---

## Migration Considerations

### From Microsoft Planner

**Data to Migrate**:
- Tasks and their status
- Due dates
- Assignees
- Attachments
- Comments

**Migration Approach**:
1. Export Planner data using Microsoft Graph API or Power Automate
2. Transform data to match target tool schema
3. Import via API or CSV (both tools support CSV import)

**Challenges**:
- Planner doesn't have native export functionality
- Custom fields may not map directly
- Attachments may need manual migration

---

## Recommendation Summary

### Choose Plane If:
- ✅ You want a modern, intuitive interface
- ✅ Your team prefers Kanban-style task management
- ✅ You want something similar to Linear or Asana
- ✅ You need cycles/sprints for iterative work
- ✅ You value speed and simplicity

### Choose Leantime If:
- ✅ You need timesheets and time tracking
- ✅ You want Gantt charts for project planning
- ✅ You need a built-in wiki for documentation
- ✅ You prefer traditional project management views
- ✅ You need goal tracking and reporting

---

## Next Steps

1. **Pilot Testing**: Deploy both tools in a test environment
2. **User Feedback**: Have a small group test each tool
3. **Authentication Setup**: Configure Microsoft Entra ID for the preferred tool
4. **Data Migration**: Plan the migration from Microsoft Planner
5. **Training**: Create user guides for the team
6. **Rollout**: Gradual rollout with support

---

## Additional Resources

- [Plane Documentation](https://docs.plane.so)
- [Plane GitHub](https://github.com/makeplane/plane)
- [Leantime Documentation](https://docs.leantime.io)
- [Leantime GitHub](https://github.com/Leantime/leantime)
- [Microsoft Entra ID SAML Documentation](https://learn.microsoft.com/en-us/entra/identity-platform/saml-protocol-reference)
