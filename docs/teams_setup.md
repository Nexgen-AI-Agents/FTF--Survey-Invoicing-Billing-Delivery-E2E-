# MS Teams Approval Channel — Setup Guide

**Purpose:** Connect the FTF Agentic AI to Teams so Robert and Ryan can approve or reject
estimates directly in the chat. Agent 4 posts an hourly digest; Robert/Ryan reply with
`APPROVE` or `REJECT`; the system processes the decision automatically.

---

## Architecture Overview

```
Agent 4 (hourly batch digest)
  │
  └─► TEAMS_APPROVAL_WEBHOOK_URL ──► Teams #approvals channel
                                           │
                                    Robert/Ryan type command
                                           │
                          Teams Outgoing Webhook (registered by admin)
                                           │
                                           ▼
                          Flask server  /teams/webhook  (port 5001)
                                           │
                                    HMAC-SHA256 verified
                                           │
                                    process_approval_reply()
                                           │
                                    DB status updated
                                           │
                          Confirmation card ──► #approvals channel
```

---

## Step 1 — Start the Approval Receiver (Server Side)

The receiver must be running BEFORE you register the webhook in Teams.

### Local dev (ngrok)

```bash
# Terminal 1 — start Flask receiver
cd code
python scripts/run_approval_receiver.py

# Terminal 2 — expose it publicly
ngrok http 5001
# Note the HTTPS URL: https://abc123.ngrok.io
```

### Production (VPS + nginx)

1. Run the receiver as a service (systemd, PM2, etc.)
2. Reverse-proxy HTTPS → `localhost:5001` via nginx
3. Your public endpoint will be `https://yourdomain.com/teams/webhook`

---

## Step 2 — Create the Approval Teams Channel

1. In Teams, open your NexGen workspace
2. Create a **private channel** named `#ftf-approvals` (or similar)
3. Add Robert and Ryan as members

---

## Step 3 — Register an Incoming Webhook (Outbound → Teams)

This is for Agent 4 to **POST** the hourly digest INTO Teams.

1. Open `#ftf-approvals` channel → **Connectors**
2. Add **Incoming Webhook** → name it `FTF Estimate Bot`
3. Copy the webhook URL
4. Set in `.env`:

```
TEAMS_APPROVAL_WEBHOOK_URL=https://nexgen.webhook.office.com/webhookb2/...
```

---

## Step 4 — Register an Outgoing Webhook (Teams → Server)

This lets Robert/Ryan's APPROVE/REJECT commands reach the Flask server.

1. Go to **Teams Admin Center** (or channel settings if you have permission):
   - Teams channel → **...** menu → **Manage channel** → **Connectors**
   - Add **Outgoing Webhook**

2. Fill in:
   - **Name:** `FTF Estimate Bot`
   - **Callback URL:** `https://yourdomain.com/teams/webhook` (or ngrok URL)
   - **Description:** `FTF estimate approve/reject commands`

3. Teams will display a **Security token** (base64-encoded HMAC secret).
   Copy it and set in `.env`:

```
TEAMS_OUTGOING_WEBHOOK_SECRET=<paste the token here>
```

4. Restart the Flask receiver after adding the secret.

---

## Step 5 — Set All Environment Variables

Add these to your `.env` (never commit to git):

```
# Approval channel (incoming webhook URL for Agent 4 to post the digest)
TEAMS_APPROVAL_WEBHOOK_URL=https://nexgen.webhook.office.com/webhookb2/...

# HMAC secret from the Outgoing Webhook registration (Teams admin panel)
TEAMS_OUTGOING_WEBHOOK_SECRET=<base64 token from Step 4>

# Flask receiver bind settings (defaults work for most deployments)
APPROVAL_RECEIVER_HOST=0.0.0.0
APPROVAL_RECEIVER_PORT=5001

# General Teams webhook (for non-approval alerts — can be same channel or different)
TEAMS_WEBHOOK_URL=https://nexgen.webhook.office.com/webhookb2/...
```

---

## Step 6 — Test the Connection

### Health check
```bash
curl http://localhost:5001/health
# Expected: {"status": "ok", "service": "teams_approval_receiver"}
```

### Manual approve test (CLI)
```bash
cd code
python -m sprint_03_human_gate.agents.agent_04_human_gate --approve ORD-001
# Expected: approved=ORD-001
```

### End-to-end Teams test
1. Post a message in `#ftf-approvals`: `APPROVE 1000276115`
2. The bot should reply: `✅ [YourName] approved order 1000276115. Estimate will be sent.`
3. Check DB: `SELECT status FROM processed_orders WHERE order_id = '1000276115';`
   — should be `approved`

---

## Commands Robert/Ryan Can Use

| Command | What it does |
|---|---|
| `APPROVE 1000276115` | Approve one estimate → status = approved |
| `APPROVE ALL` | Approve everything currently awaiting review |
| `REJECT 1000276115` | Reject one estimate → status = rejected |
| `REJECT 1000276115 wrong county` | Reject with reason logged |

Teams automatically prepends the `@EstimateBot` mention — the server strips it.

---

## Troubleshooting

| Problem | Fix |
|---|---|
| Bot doesn't respond | Check receiver is running (`/health`); check ngrok/public URL is live |
| `401 Unauthorized` | Wrong `TEAMS_OUTGOING_WEBHOOK_SECRET` — re-copy from Teams admin |
| `⚠️ Could not approve ORD-001: order not found` | Order ID not in DB; check with `--check ORD-001` |
| `⚠️ Could not approve ORD-001: not awaiting approval` | Order already approved/rejected or not yet in human gate |
| Digest not posting to Teams | Check `TEAMS_APPROVAL_WEBHOOK_URL` in `.env`; test with `--run` flag |

---

## Security Notes

- HMAC-SHA256 verification is active when `TEAMS_OUTGOING_WEBHOOK_SECRET` is set
- Without the secret (dev mode), any POST to `/teams/webhook` is accepted — set the secret before production
- The Flask server must be behind HTTPS in production (Teams rejects plain HTTP callback URLs)
- Secret is stored only in `.env` — never in git, never in source code
