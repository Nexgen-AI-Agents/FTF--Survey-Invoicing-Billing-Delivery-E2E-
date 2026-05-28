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

## Security Notes

- All credentials stored only in `.env` (gitignored — never committed)
- Graph API uses `client_credentials` flow — no user sign-in required
- Logic App HTTP trigger URL is a secret — treat like a password
- Rotate `TEAMS_CLIENT_SECRET` in Azure portal if compromised; update `.env`
