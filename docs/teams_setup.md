# MS Teams Approval Channel — Setup Guide

**Purpose:** FTF Agentic AI posts hourly order digests to Teams. Robert and Ryan reply
`APPROVE` or `REJECT`; the system processes decisions automatically.

---

## Architecture Overview

```
Agent 4 (hourly batch digest)
  │
  └─► TEAMS_INCOMING_WEBHOOK_URL ──► Azure Logic App (HTTP trigger)
                                           │
                                    Logic App action:
                                    Post to Teams FTF-Approvals channel
                                           │
                                    Robert/Ryan type:
                                    APPROVE <order_id>
                                    REJECT  <order_id> reason
                                           │
                          poll_teams_approvals.py (runs every pipeline cycle)
                                    reads via Microsoft Graph API
                                           │
                                    process_approval_reply()
                                           │
                                    DB status updated
                                           │
                          Confirmation message ──► FTF-Approvals channel
```

**No public URL. No Flask server. No ngrok.**
Sending: Azure Logic App relay. Reading: Microsoft Graph API polling.

---

## Step 1 — Create the FTF-Approvals Channel

1. Open Teams → NexGen workspace
2. Create a **private channel** named `FTF-Approvals`
3. Add Robert and Ryan as members

---

## Step 2 — Create Azure Logic App Webhook (RECOMMENDED)

O365 Incoming Webhooks were retired by Microsoft in 2024 (403 errors).
Teams Workflows template requires Power Automate Plan 1.
Azure Logic Apps (Consumption) has a free HTTP trigger and works reliably.

### Create the Logic App

1. Go to **portal.azure.com**
2. Search "Logic Apps" → **Create**
3. Basics:
   - Subscription: your Azure subscription
   - Resource group: `ftf-rg` (create new if needed)
   - Logic App name: `ftf-teams-relay`
   - Region: East US (or nearest)
   - **Plan type: Consumption** (pay-per-execution, effectively free at our volume)
4. Click **Review + Create** → **Create** → wait ~30 sec → **Go to resource**

### Build the Flow

5. Click **Logic app designer** (left sidebar)
6. Search and choose: **"When a HTTP request is received"**
7. Set **Request Body JSON Schema** — paste exactly:
   ```json
   {
     "type": "object",
     "properties": {
       "subject": { "type": "string" },
       "text":    { "type": "string" }
     }
   }
   ```
8. Click **Save** — the **HTTP POST URL** appears under the trigger block. **Copy it now.**
9. Click **"+ New step"**
10. Search **"Microsoft Teams"** → choose **"Post message in a chat or channel"**
11. Sign in with your Microsoft 365 account when prompted (one-time)
12. Configure:
    - **Post as:** User
    - **Post in:** Channel
    - **Team:** NexGen Surveying
    - **Channel:** FTF-Approvals
    - **Message:** click in field → **Add dynamic content** → **`subject`** → type ` — ` → **Add dynamic content** → **`text`**
13. Click **Save**

### Add to .env

```
TEAMS_INCOMING_WEBHOOK_URL=https://prod-XX.eastus.logic.azure.com:443/workflows/...
```

The code auto-detects `logic.azure.com` URLs and sends `{"subject": "...", "text": "..."}` JSON.
The Logic App extracts those fields and posts the formatted message to Teams.

---

## Step 3 — Graph API Credentials (for reading approval commands)

Already configured in `.env`. The app uses `ChannelMessage.Read.All`
application permission to poll the channel for APPROVE/REJECT commands.

Required (already set):
```
TEAMS_TENANT_ID=<Azure AD tenant ID>
TEAMS_APP_ID=<app client ID>
TEAMS_CLIENT_SECRET=<app client secret>
TEAMS_TEAM_ID=<Teams group ID>
TEAMS_CHANNEL_ID=<channel ID>
```

---

## Step 4 — Test the Connection

```bash
python scripts/test_teams_connection.py
```

Expected output:
```
1. Config check         [PASS]
2. Authentication       [PASS]
3. Read channel         [PASS]
4. Webhook config       [PASS]  (type: logic_app)
5. Send test message    [PASS]
```

---

## Step 5 — Commands (Robert and Ryan)

Type directly in the FTF-Approvals Teams channel:

| Command | What it does |
|---------|-------------|
| `APPROVE 1000276115` | Approve one estimate |
| `APPROVE ALL` | Approve everything currently awaiting review |
| `REJECT 1000276115` | Reject one estimate |
| `REJECT 1000276115 wrong county` | Reject with reason logged |

No @mentions needed. The pipeline polls and finds APPROVE/REJECT anywhere in the message text.

### Manual poll:
```bash
python scripts/poll_teams_approvals.py --since-hours 1
```

### Dry run (no DB writes):
```bash
python scripts/poll_teams_approvals.py --dry-run
```

---

## Getting Channel + Team IDs

**In Teams (browser — teams.microsoft.com):**
1. Navigate to the channel → `...` → **Get link to channel**
2. URL contains: `?groupId=<teamId>&...` and `/channel/<channelId>/...`

**Via Graph API:**
```
GET https://graph.microsoft.com/v1.0/me/joinedTeams
GET https://graph.microsoft.com/v1.0/teams/{teamId}/channels
```

---

## Webhook Type Detection (code auto-selects payload format)

| URL pattern | Detected type | Payload format |
|-------------|--------------|----------------|
| `logic.azure.com` | `logic_app` | `{"subject": "...", "text": "..."}` |
| `webhook.office.com` | `o365_connector` | MessageCard (retired — 403 in most tenants) |
| other | `workflows` | Adaptive Card attachments |

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| Logic App POST fails | Check the Logic App run history in portal.azure.com for the error |
| Teams connection not authorized | Re-authorize the Teams connector inside the Logic App designer |
| HTTP 403 on webhook.office.com | O365 connectors retired Aug 2024; switch to Logic App |
| "Post to channel when webhook received" missing in Workflows | Requires Power Automate Plan 1; use Logic App instead |
| HTTP 401 on Graph API | Check TEAMS_CLIENT_SECRET not expired; regenerate in Azure portal |
| HTTP 403 on Graph API | ChannelMessage.Read.All must be Application permission with admin consent |
| No commands found in poll | Messages older than `--since-hours` window, or Graph API permissions issue |

---

## Step 6 — Power Automate: Real-Time Approval Trigger (Teams → GitHub)

**What this does:** The moment someone types APPROVE/REJECT/HOLD in the FTF-Approvals channel, this flow immediately triggers the invoice pipeline on GitHub Actions — instead of waiting up to 15 minutes for the cron to fire.

**What you need first — GitHub PAT:**
1. Go to **github.com → Settings → Developer settings → Personal access tokens → Tokens (classic)**
2. Click **Generate new token (classic)**
3. Name: `FTF Power Automate Trigger`
4. Expiry: 1 year
5. Scopes: tick **`workflow`** only
6. Click **Generate token** → copy the token immediately (shown once)
7. Save it — you'll paste it into Power Automate below

---

**Create the Power Automate flow:**

1. Go to **make.powerautomate.com** (sign in with your Microsoft 365 account)
2. Click **Create** → **Automated cloud flow**
3. Flow name: `FTF Invoice Approval Trigger`
4. Search for trigger: **"When a new channel message is added"** (Microsoft Teams)
5. Click **Create**

**Configure the trigger:**
- **Team:** NexGen Surveying (your team)
- **Channel:** FTF-Approvals

**Add a Condition step:**
6. Click **+ New step** → search **"Condition"**
7. In the condition builder, click **"Add row"** three times and set to OR logic:
   - Row 1: `Message body content` → **contains** → `APPROVE`
   - Row 2: `Message body content` → **contains** → `REJECT`
   - Row 3: `Message body content` → **contains** → `HOLD`
8. Change the top logic to **OR** (not AND)

**In the "If yes" branch — add HTTP action:**
9. Click **Add an action** → search **"HTTP"**
10. Configure:
    - **Method:** POST
    - **URI:**
      ```
      https://api.github.com/repos/Nexgen-AI-Agents/FTF--Survey-Invoicing-Billing-Delivery-E2E-/actions/workflows/invoice_pipeline.yml/dispatches
      ```
    - **Headers** (add each separately):
      | Key | Value |
      |-----|-------|
      | `Accept` | `application/vnd.github.v3+json` |
      | `Authorization` | `Bearer {paste your GitHub PAT here}` |
      | `Content-Type` | `application/json` |
    - **Body:**
      ```json
      {"ref": "main"}
      ```
11. Leave the "If no" branch empty
12. Click **Save**

**Test it:**
13. Post `APPROVE test` in the FTF-Approvals Teams channel
14. In Power Automate → go to the flow → **Run history** → confirm it shows a successful run
15. In GitHub → Actions → `Invoice Pipeline` → confirm a new run was triggered

---

**Result:** When Robert or Ryan type APPROVE/REJECT/HOLD, the pipeline starts within ~1–2 minutes (GitHub Actions runner startup time — unavoidable without a dedicated server).

The 15-minute cron in `invoice_pipeline.yml` stays as a safety net to catch anything the Power Automate flow might miss.

---

## Security Notes

- All credentials stored only in `.env` (gitignored — never committed)
- Graph API uses `client_credentials` flow — no user sign-in required
- Logic App HTTP trigger URL is a secret — treat like a password
- Rotate `TEAMS_CLIENT_SECRET` in Azure portal if compromised; update `.env`
- GitHub PAT in Power Automate: rotate annually; update the HTTP action header when renewed
