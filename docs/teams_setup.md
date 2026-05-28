# MS Teams Approval Channel — Setup Guide

**Purpose:** Connect the FTF Agentic AI to Teams so Robert and Ryan can approve or reject
estimates directly in the chat. Agent 4 posts an hourly digest; Robert/Ryan reply with
`APPROVE` or `REJECT`; the system processes the decision automatically.

---

## Architecture Overview

```
Agent 4 (hourly batch digest)
  │
  └─► TEAMS_INCOMING_WEBHOOK_URL ──► Teams #ftf-approvals channel
                                           │
                                    Robert/Ryan type:
                                    APPROVE <order_id>
                                    REJECT  <order_id> reason
                                           │
                          poll_teams_approvals.py (runs every cycle)
                                    reads via Graph API
                                           │
                                    process_approval_reply()
                                           │
                                    DB status updated
                                           │
                          Confirmation message ──► #ftf-approvals channel
```

**No public URL. No Flask server. No ngrok required.**
The pipeline polls the channel directly via Microsoft Graph API.

---

## Step 1 — Create the FTF-Approvals Channel

1. Open Teams → your NexGen workspace
2. Create a **private channel** named `FTF-Approvals`
3. Add Robert and Ryan as members

---

## Step 2 — Create Incoming Webhook (for sending messages TO Teams)

### Option A — O365 Incoming Webhook Connector (RECOMMENDED — no license needed)

This works with any Microsoft 365 / Teams subscription. No Power Automate license required.

1. Open the `FTF-Approvals` channel
2. Click `...` (three dots next to channel name) → **Manage channel**
3. Scroll to **Connectors** → click **Edit**
4. Search for **Incoming Webhook** → click **Configure**
5. Name: `FTF Estimate Bot` → click **Create**
6. Copy the webhook URL (looks like `https://nexgen.webhook.office.com/webhookb2/...`)
7. Click **Done**

Add to `.env`:
```
TEAMS_INCOMING_WEBHOOK_URL=https://nexgen.webhook.office.com/webhookb2/...
```

The code automatically detects the `webhook.office.com` URL and sends MessageCard format.

---

### Option B — Teams Workflows (requires Power Automate Plan 1)

If Option A is unavailable, and you have Power Automate:

1. Open the `FTF-Approvals` channel → `...` → **Workflows**
2. Search for **"Post to a channel when a webhook request is received"**
3. Click it → follow the setup → copy the webhook URL
4. Add to `.env` as `TEAMS_INCOMING_WEBHOOK_URL=<url>`

The code automatically detects Logic Apps / Workflows URLs and sends Adaptive Card format.

---

## Step 3 — Graph API Credentials (for reading approval commands)

These are already configured in `.env`. The app uses `ChannelMessage.Read.All`
application permission to poll the channel for APPROVE/REJECT commands.

Required (already set):
```
TEAMS_TENANT_ID=<your Azure AD tenant ID>
TEAMS_APP_ID=<your app client ID>
TEAMS_CLIENT_SECRET=<your app client secret>
TEAMS_TEAM_ID=<Teams group ID>
TEAMS_CHANNEL_ID=<channel ID>
```

---

## Step 4 — Test the Connection

```bash
cd "path\to\FTF- Survey Invoicing & Billing Delivery (E2E)"
python scripts/test_teams_connection.py
```

Expected output:
```
1. Config check         [PASS]
2. Authentication       [PASS]
3. Read channel         [PASS]
4. Webhook config       [PASS]  (type: O365 Incoming Webhook connector)
5. Send test message    [PASS]
```

Check the `FTF-Approvals` channel in Teams — a test message should appear.

To test read + auth only (no send):
```bash
python scripts/test_teams_connection.py --read-only
```

---

## Step 5 — How Approvals Work (Polling Model)

Robert or Ryan types in the `FTF-Approvals` channel:

| Command | What it does |
|---------|-------------|
| `APPROVE 1000276115` | Approve one estimate → status = approved |
| `APPROVE ALL` | Approve everything currently awaiting review |
| `REJECT 1000276115` | Reject one estimate → status = rejected |
| `REJECT 1000276115 wrong county` | Reject with reason logged to DB |

The pipeline polls the channel every run cycle via Graph API. No @mentions or bots required.
Commands work even if typed anywhere in the message — the parser finds APPROVE/REJECT anywhere in the text.

### Manual poll (test commands immediately):
```bash
python scripts/poll_teams_approvals.py --since-hours 1
```

### Dry run (see what would be processed without writing to DB):
```bash
python scripts/poll_teams_approvals.py --dry-run
```

---

## Step 6 — Getting Channel + Team IDs

If you need to find the Team ID and Channel ID:

**In Teams (browser):**
1. Open Teams in browser (teams.microsoft.com)
2. Navigate to the channel
3. Click `...` → **Get link to channel**
4. The URL contains the IDs:
   `https://teams.microsoft.com/l/channel/<channelId>/...?groupId=<teamId>&...`

**Via Graph API:**
```
GET https://graph.microsoft.com/v1.0/me/joinedTeams
GET https://graph.microsoft.com/v1.0/teams/{teamId}/channels
```

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| "Post to channel when webhook received" not in Workflows | Use Option A (O365 Incoming Webhook Connector) instead |
| Connector not available | Check Teams admin hasn't disabled connectors; or use Power Automate |
| HTTP 400 on webhook POST | Wrong payload format — code auto-detects, but verify URL is copied correctly |
| HTTP 401 on Graph API | Check TEAMS_CLIENT_SECRET not expired; regenerate in Azure portal |
| HTTP 403 on Graph API | Ensure ChannelMessage.Read.All is an **Application** permission (not Delegated) and admin consent granted |
| No commands found in poll | Messages older than `--since-hours` window; or Graph API permissions issue |
| "TEAMS_TEAM_ID and TEAMS_CHANNEL_ID must be set" | Add both to .env; see Step 6 above |

---

## Security Notes

- All credentials are stored only in `.env` — never in git (`.env` is gitignored)
- The Graph API uses `client_credentials` flow — no user sign-in required
- The incoming webhook URL is a secret — treat it like a password
- Rotate `TEAMS_CLIENT_SECRET` in Azure portal if compromised; update `.env` immediately
