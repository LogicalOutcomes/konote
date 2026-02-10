# Deploy KoNote on FullHost (Canadian Hosting)

This guide walks you through deploying your own KoNote instance on FullHost, a Canadian-owned hosting provider with data centres in Canada.

**Time required:** About 15 minutes
**Technical skill required:** None — just follow the steps
**Cost:** ~$23 CAD/month for a small nonprofit (see [Understanding Costs](#understanding-costs))

---

## Why FullHost?

- **Canadian data residency** — Your client data stays in Canada (Montreal data centre)
- **Canadian-owned company** — Based in Victoria, BC
- **Pay only for what you use** — No long-term contracts
- **Free trial** — $25 in credits to try it out (no credit card required)

---

## Before You Start

You'll need:

1. **An email address** — For your FullHost account and KoNote admin login
2. **Your organisation name** — As you want it displayed in KoNote
3. **A term for the people you serve** — clients, participants, members, etc.
4. **A password** — For your KoNote admin account (minimum 10 characters)

---

## Step 1: Create a FullHost Account

1. Go to [fullhost.com/cloud-paas](https://www.fullhost.com/cloud-paas/)
2. Click **"Get Started"** or **"Try for Free"**
3. Enter your email address
4. Check your inbox for a confirmation email
5. Click the link in the email to verify your account
6. Set a password for your FullHost account

**Note:** This creates your FullHost hosting account. You'll create a separate KoNote admin account later.

**Recommended:** Enable multi-factor authentication (MFA) on your FullHost account. Your FullHost login controls your entire KoNote environment — databases, encryption keys, and all client data. Go to your FullHost account settings and enable two-factor authentication before proceeding.

---

## Step 2: Deploy KoNote

### Option A: One-Click Deploy (Easiest)

1. Click this button:

   [![Deploy to FullHost](https://www.fullhost.com/deploy-button.svg)](https://app.fullhost.cloud/install?manifest=https://raw.githubusercontent.com/gilliankerr/KoNote-Redux/main/fullhost-manifest.jps)

2. If prompted, log in to your FullHost account

3. You'll see the **KoNote Setup** screen

### Option B: Manual Import

If the button doesn't work:

1. Log in to your FullHost dashboard at [app.fullhost.cloud](https://app.fullhost.cloud)
2. Click **"Import"** in the top menu
3. Select the **"URL"** tab
4. Paste this URL:
   ```
   https://raw.githubusercontent.com/gilliankerr/KoNote-Redux/main/fullhost-manifest.jps
   ```
5. Click **"Import"**

---

## Step 3: Configure Your Instance

On the setup screen, fill in:

| Field | What to Enter |
|-------|---------------|
| **Organisation Name** | Your nonprofit's name (e.g., "Community Support Services") |
| **Admin Email** | Your email address — you'll use this to log in |
| **Admin Password** | A secure password (minimum 10 characters) |
| **What do you call the people you serve?** | Select from the dropdown: Clients, Participants, Members, etc. |

Then click **"Install"**.

---

## Step 4: Wait for Installation

The installation takes about 5–10 minutes. You'll see a progress bar showing:

1. Creating databases...
2. Deploying application...
3. Running setup...
4. Creating admin account...

**Don't close the browser tab** until you see the success message.

---

## Step 5: Save Your Encryption Key

When installation completes, you'll see a success screen with an **encryption key**.

**This is critically important:**

```
Your encryption key (example — yours will be different):
xK9mP2nQ4rS6tU8vW0xY2zA4bC6dE8fG0hI2jK4lM6n=
```

**You must save this key:**

1. Copy the key
2. Save it somewhere secure (password manager, printed in a safe, etc.)
3. **Do not store it in the same place as your database backups**

If you ever need to restore KoNote from a backup, you'll need this key to decrypt client data. **If you lose this key, encrypted client data cannot be recovered.**

**Tip:** If you misplace the key, you can retrieve it later from your FullHost dashboard. Click on the KoNote App container, then **Variables** — look for `FIELD_ENCRYPTION_KEY`. But it's still best to save a copy outside of FullHost.

---

## Step 6: Enable SSL (HTTPS)

SSL must be enabled manually after installation. There are two parts:

### 6a. Enable SSL on the Load Balancer

1. In the FullHost dashboard, find your KoNote environment
2. Click **Settings** (gear icon) on the environment
3. Click **Custom SSL** in the left sidebar
4. At the top, click the **yellow link** that says "following the link and clicking Enable button"
5. In the topology editor that opens, check the **SSL** toggle, then click **Apply**

### 6b. Install a Let's Encrypt Certificate

1. In the FullHost dashboard, click on the **nginx load balancer** node (not the app container)
2. Click **Add-ons** in the panel that opens
3. Find **Let's Encrypt Free SSL** and click **Install**
4. Enter your environment's hostname (e.g., `konote-full.ca-east.onfullhost.cloud`)
5. Click **Install** — this creates the SSL configuration in nginx and enables port 443

Both steps are required. Step 6a enables the SSL toggle, but the load balancer won't actually listen on port 443 until the Let's Encrypt add-on in step 6b creates the nginx SSL configuration.

It may take a few minutes to activate. Once done, your site will be accessible over HTTPS. The certificate is valid for 90 days and **renews automatically** — you'll get an email notification one month before expiry. You can also manually renew or change domain names from the Let's Encrypt add-on panel.

**Note:** Login will not work until SSL is enabled — the app requires HTTPS for security.

**Important — Do NOT add a public IP to the app container.** If the KoNote App node has a public/external IP address, HTTPS will not work. The SSL certificate is managed by FullHost's Shared Load Balancer (SLB), which sits in front of your containers. A public IP on the app container makes traffic bypass the SLB, skipping SSL entirely. If you accidentally add one, go to the app node's settings and remove the public IP.

---

## Step 7: Log In to KoNote

1. Click the link in the success message, or go to your KoNote URL (shown on screen)
2. Your username is **admin** (not your email)
3. Enter the **password** you chose during setup
4. Click **"Log In"**

You're in! You'll see the KoNote dashboard.

---

## Step 8: Complete Initial Setup

After logging in for the first time:

1. **Review terminology settings** — Go to Admin → Settings to confirm your client term
2. **Create programs** — Set up the programs your organisation runs
3. **Invite staff** — Go to Admin → Users to add your team members
4. **Configure outcomes** — Define the outcomes you track for each program

See the [Getting Started Guide](getting-started.md) for detailed instructions.

---

## Moving to Production Use

Your KoNote instance comes pre-loaded with demo users and sample data so you can explore how everything works. When your organisation is ready to use it for real:

1. **Create real staff accounts** — Go to Admin → Users and invite your team. These are regular (non-demo) accounts.
2. **Real staff never see demo data** — Demo clients and demo users are completely separate. Your real staff will see an empty client list, ready for your actual clients.
3. **You don't need to delete demo data** — It stays invisible to real users. The demo login buttons on the login page remain available for training purposes.
4. **Optionally disable demo logins** — If you no longer want the demo login buttons on the login page, ask your administrator to set `DEMO_MODE` to `false` in the FullHost container environment variables and restart the app.

---

## Enable Automatic Backups

We strongly recommend enabling automatic backups for your client data:

1. In the FullHost dashboard, click on your KoNote environment
2. Click **Settings** (gear icon)
3. Click **Backup** in the left sidebar
4. Enable automatic backups and choose a schedule (daily recommended)
5. Set retention to at least 7 days

This protects against accidental data loss. You can also download manual backups at any time (see [Backing Up Your Data](#backing-up-your-data) below).

---

## Understanding Costs

FullHost charges based on resource usage. You pay for reserved resources (always on) plus dynamic resources (used during activity).

### Estimated Monthly Cost

*Calculated from FullHost pricing as of February 2026*

**Assumptions:**
- Small nonprofit: 5–10 staff users
- 100–500 clients in the system
- Light to moderate usage (a few hours of active use per day)
- 1–2 GB total database storage

| Component | Reserved (always on) | Dynamic (average usage) | Monthly |
|-----------|---------------------|------------------------|---------|
| App server | 2 cloudlets × $1.50 | ~2 cloudlets × $2.50 | $8.00 |
| Main database | 2 cloudlets × $1.50 | ~1 cloudlet × $2.50 | $5.50 |
| Audit database | 2 cloudlets × $1.50 | ~1 cloudlet × $2.50 | $5.50 |
| Storage | — | 2 GB × $0.20 | $0.40 |
| External IP | — | — | $3.50 |
| **Total** | | | **~$23 CAD/month** |

**What affects your costs:**
- More staff or heavier usage → higher dynamic cloudlet usage
- More clients/notes → more storage
- Minimum possible (idle system) → ~$13 CAD/month (reserved only + IP)
- Busy nonprofit with 20+ active users → could reach $35–45 CAD/month

### Pricing Reference

A "cloudlet" is FullHost's billing unit: 128 MB RAM + 200 MHz CPU.

| Type | Cost | When charged |
|------|------|--------------|
| Reserved cloudlet | $1.50/month | Always (guaranteed minimum) |
| Dynamic cloudlet | $2.50/month | Only when used |
| Storage | $0.20/GB/month | Based on actual usage |
| External IP | $3.50/month | Required for public access |

### Free Trial

New FullHost accounts receive **$25 in free credits** — enough for roughly 1 month at typical small-nonprofit usage levels.

### Monitoring Your Costs

1. Log in to [app.fullhost.cloud](https://app.fullhost.cloud)
2. Click on your KoNote environment
3. Click **"Statistics"** to see resource usage
4. Click **"Billing"** in the top menu to see current charges

---

## Custom Domain (Optional)

By default, your KoNote URL looks like:
```
https://konote2-abc123.jls-can1.cloudjiffy.net
```

To use your own domain (like `outcomes.mynonprofit.org`):

### Step 1: Add Domain in FullHost

1. Go to your KoNote environment in FullHost
2. Click **Settings** (gear icon)
3. Click **Custom Domains**
4. Enter your domain name
5. Click **"Bind"**

### Step 2: Update Your DNS

You'll see instructions like:
```
Add a CNAME record pointing to: node12345-konote2.jls-can1.cloudjiffy.net
```

Go to wherever you manage your domain (GoDaddy, Cloudflare, etc.) and add that CNAME record.

### Step 3: Wait for DNS

DNS changes can take 1–48 hours to take effect. Once working, you can access KoNote at your custom domain with automatic HTTPS.

---

## Backing Up Your Data

FullHost provides automatic backups, but you should also:

### Download a Manual Backup

1. In FullHost, click on your Main Database
2. Click **"Backup"**
3. Click **"Create"** to make a new backup
4. Click **"Download"** to save it to your computer

**Do the same for your Audit Database.**

### Backup Schedule

We recommend:
- **Weekly**: Download backups of both databases
- **Monthly**: Test that you can restore from a backup (optional but wise)
- **Always**: Keep your encryption key stored separately from backups

---

## Troubleshooting

### "Application Error" when visiting KoNote

1. In FullHost, check if all three containers are running (green status)
2. Click on the app container and check **Logs** for error messages
3. Try restarting the app container (click **Restart**)

### Forgot Admin Password

1. In FullHost, click on your app container (KoNote App)
2. Click **"Web SSH"** (or **"Terminal"**)
3. Run:
   ```
   python manage.py changepassword your-email@example.com
   ```
4. Enter a new password when prompted

### Running Out of Credits

1. Log in to FullHost
2. Click **"Billing"** → **"Add Funds"**
3. Add credits with a credit card

FullHost will email you when credits are running low.

### HTTPS Not Working / "Connection Refused" on HTTPS

If HTTP works but HTTPS doesn't, check these two things:

**1. Let's Encrypt add-on not installed on the load balancer**
- Click on the **nginx load balancer** node (not the app container)
- Click **Add-ons** — look for **Let's Encrypt Free SSL**
- If it's not installed, install it with your environment hostname
- This is the most common cause — without it, port 443 isn't listening at all

**2. App container has a public IP address**
- Check whether the **KoNote App** container has a **public IP address** assigned
- If it does, the public IP bypasses FullHost's SSL proxy
- Go to the app container → **Settings** → remove the public/external IP
- Wait a minute for DNS to update, then try HTTPS again

The FullHost Shared Load Balancer handles SSL. It only works when traffic goes through it (no public IP on the app container) and when the Let's Encrypt add-on has created the nginx SSL configuration.

### Need More Help?

- **KoNote Documentation:** [github.com/gilliankerr/KoNote-Redux/docs](https://github.com/gilliankerr/KoNote-Redux/docs)
- **FullHost Support:** [fullhost.com/support](https://www.fullhost.com/support/)

---

## Updating KoNote

When new versions of KoNote are released:

1. **Back up your data first** (see Backing Up section above)
2. In FullHost, click on your KoNote environment
3. Click on the **KoNote App** container
4. Click **"Redeploy"**
5. Ensure the image tag is set to `fullhost-latest`
6. Click **"Redeploy"** to pull the latest version

The container will restart automatically and run any new database migrations. This takes about 60 seconds.

7. **Verify HTTPS works** — After the redeploy, visit your site using `https://`. If you get a 502 error but `http://` works, SSL may need to be re-enabled:
   - Click **Settings** (gear icon) on the environment
   - Click **Custom SSL** in the left sidebar
   - Click the **yellow link** at the top and re-enable SSL
   - Wait a minute, then try HTTPS again

**Tip:** Always download a backup before updating.

---

## Deleting Your Instance

If you need to remove KoNote:

1. **Download your data first** (see Backing Up section)
2. In FullHost, go to your KoNote environment
3. Click **Settings** (gear icon)
4. Scroll to bottom and click **"Delete Environment"**
5. Confirm deletion

This removes all data permanently. FullHost will stop charging you.

---

## Getting Help

- **KoNote Issues:** [github.com/gilliankerr/KoNote-Redux/issues](https://github.com/gilliankerr/KoNote-Redux/issues)
- **FullHost Support:** [fullhost.com/support](https://www.fullhost.com/support/)
- **Community Forum:** [github.com/gilliankerr/KoNote-Redux/discussions](https://github.com/gilliankerr/KoNote-Redux/discussions)
