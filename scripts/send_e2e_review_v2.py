"""
send_e2e_review_v2.py â€” E2E gap-analysis review message to team.
Deep analysis: technical + business + AI-identified gaps.
"""

import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "code", "shared"))

from core.teams_graph_client import send_channel_message, send_email_notification

# â”€â”€ TEAMS MESSAGE â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

teams_html = """
<h2>ðŸ” FTF Agentic AI â€” E2E Gap Analysis &amp; Review (Sprint 0-11)</h2>

<p>This is a <strong>deep review request</strong> â€” not a "please test" ping. I've analyzed the full codebase, sprint files, issues log, and approval flow docs. Below are specific gaps, questions, and items that need your eyes before we go to Sprint 12 (Full Production). Please read every section.</p>

<hr/>

<h3>ðŸ“ WHERE WE ACTUALLY ARE RIGHT NOW</h3>
<table>
<tr><th>Loop</th><th>Status</th><th>Notes</th></tr>
<tr><td>Estimate Generation (Agents 2â€“8)</td><td>ðŸŸ¡ Sprint 11 â€” In Progress</td><td>Production credentials NOT yet swapped in GitHub Actions. Still hitting <strong>staging</strong> FTF URL.</td></tr>
<tr><td>Approval Monitor (GitHub Actions)</td><td>ðŸŸ¢ Live (every 5 min, 24/7)</td><td>poll_approval_monitor.yml deployed. But reads last 60 min every 5-min cycle.</td></tr>
<tr><td>AR Follow-Up (Agents 10â€“11)</td><td>ðŸ”´ Staging only</td><td>Not in production. Jessica hasn't confirmed exclusion list.</td></tr>
<tr><td>Monthly Statements (Agents 15â€“17)</td><td>ðŸ”´ Staging only</td><td>Wyatt hasn't reviewed format. No real B2B delivery yet.</td></tr>
<tr><td>Email Monitor (nesa@nexgenlogix.com)</td><td>â“ Built but where deployed?</td><td>Agent 12 built (I-061) â€” is it actually running anywhere?</td></tr>
</table>

<hr/>

<h3>ðŸš¨ BLOCKERS BEFORE SPRINT 12 CAN START</h3>

<p><strong>1. Production credential swap in GitHub Actions is NOT done.</strong><br/>
Sprint 11 has 5 unchecked tasks. The first: set <code>FTF_API_BASE_URL</code> to production URL. Until this is done, the estimate loop hits staging â€” <em>no real estimates are being generated for real customers</em>. Robert/Mark: have you received any AI-generated estimates yet? If no â†’ this is why.<br/>
ðŸ‘‰ <strong>Action: Confirm production secrets are set. If not, Prateek to set them now.</strong></p>

<p><strong>2. Zero real estimates reviewed by Robert/Mark.</strong><br/>
Sprint 11 test results show all ðŸ”² â€” no real estimates sent, none reviewed. We cannot get Ryan's Sprint 12 GO/NO-GO without Robert/Mark signing off on 5 real estimates.<br/>
ðŸ‘‰ <strong>Action: Robert + Mark â€” once credentials are live, monitor first 5 with <code>python scripts/monitor_first5_estimates.py --teams</code>.</strong></p>

<p><strong>3. The LLM classifier has never made a real AI call.</strong><br/>
Agent 3 (Classifier) is PURE rule-based. The Claude model is configured but never called. For any order that doesn't clearly match a rule â€” it passes through unclassified. This is fine for known service types. But what happens to an order with service_type="Custom" or a future new service type?<br/>
ðŸ‘‰ <strong>Question: Should LLM classification be enabled in Sprint 12? Or after we see production data patterns?</strong></p>

<hr/>

<h3>ðŸ” TECHNICAL GAPS I FOUND (from code analysis)</h3>

<p><strong>Gap A â€” Approval polling window vs. cron mismatch:</strong><br/>
GitHub Actions fires every 5 min, but reads <code>--since-hours 1</code> = 60 minutes of messages per run. In 1 hour, the same reply message is read 12 times. The deduplication mechanism (pending_confirmations.json + DB state) should prevent double-processing â€” but has this been tested with a real multi-cycle approval scenario? If deduplication breaks â†’ an order could be approved/rejected multiple times.<br/>
ðŸ‘‰ <strong>Test: Send APPROVE for one order. Wait 10 min. Verify it wasn't processed twice.</strong></p>

<p><strong>Gap B â€” No error alerting when GitHub Actions workflow itself fails:</strong><br/>
If the poll_approval_monitor.yml fails at 3 AM (DB timeout, API rate limit, network error) â€” nobody gets notified. The workflow silently fails. Orders sit pending with no approvals until someone manually checks GitHub Actions.<br/>
ðŸ‘‰ <strong>Suggestion: Add a workflow failure notification. On failure â†’ post to Teams channel automatically.</strong></p>

<p><strong>Gap C â€” Approval queue has no aging escalation:</strong><br/>
If an order lands in "awaiting_approval" at 9 AM and nobody acts on it all day â€” there's no nudge. The daily reminder fires at 9 AM ET weekdays only. If the order arrives at 10 AM, the next reminder is next morning.<br/>
ðŸ‘‰ <strong>Question: Should we add a "4-hour no-response" alert during business hours?</strong></p>

<p><strong>Gap D â€” APPROVED_SENDERS only has Robert, Ryan, Prateek:</strong><br/>
What happens when Robert is out? Is Ryan the backup approver? Should Mark be added? If nobody on the whitelist sees the message â†’ orders queue up forever with no override path.<br/>
ðŸ‘‰ <strong>Robert: who should be backup approver when you're unavailable?</strong></p>

<p><strong>Gap E â€” Customer reply flow incomplete:</strong><br/>
When a quote email goes out to a customer, their reply goes to nesa@nexgenlogix.com. Agent 12 (email monitor) was built to catch "approved / go ahead / move forward" replies. But: (1) Where is Agent 12 deployed? (2) Is it running continuously or triggered manually? (3) If a customer replies with a question (not an approval), what happens to their email?<br/>
ðŸ‘‰ <strong>Action: Confirm Agent 12 deployment status.</strong></p>

<p><strong>Gap F â€” Website chat conversion (I-062) is OPEN with no sprint assigned:</strong><br/>
Ryan said in the May 26 call: "If a customer goes on website chat and says I want to move forward â€” it asks for property or order number." This feature has no sprint, no design, no timeline.<br/>
ðŸ‘‰ <strong>Ryan: Is this a Sprint 13 item or post-launch?</strong></p>

<hr/>

<h3>ðŸ’¡ BUSINESS LOGIC GAPS</h3>

<p><strong>Gap 1 â€” Bobby approval UX: Teams commands vs. spreadsheet:</strong><br/>
The current human gate sends a batch digest to Teams (table with all pending orders). Robert approves by typing APPROVE ALL or APPROVE [id] as a reply. But Ryan said in the May 26 call: "Bobby should get that spreadsheet every hour with an Approve/Deny column." Typing in Teams is NOT a spreadsheet. Is Robert actually OK with the command-based Teams approach? Or does he want a real Excel/email with a reply mechanism?<br/>
ðŸ‘‰ <strong>Robert: Do you prefer typing APPROVE in Teams OR receiving a spreadsheet email?</strong></p>

<p><strong>Gap 2 â€” Dynamic pricing factors not in the pricing engine code:</strong><br/>
The knowledge base doc has complexity factors (pools +$100-200, sheds +$75-150, multiple driveways +$100-200, etc.) but the <em>actual pricing engine code</em> does NOT read these factors. They're documented but not wired in. The pricing engine uses base price + county modifier only.<br/>
ðŸ‘‰ <strong>Robert: When should we add pool/shed/driveway complexity to live pricing?</strong></p>

<p><strong>Gap 3 â€” AR exclusion list is empty and Jessica hasn't confirmed it:</strong><br/>
When AR loop goes live, automated day-30/60/90 emails go to ALL unpaid customers. Jessica may have specific clients she wants excluded (e.g., large B2B accounts with custom payment terms). If not confirmed before AR loop goes live â†’ the wrong clients could receive automated reminders.<br/>
ðŸ‘‰ <strong>Jessica / Robert: Who should be on the AR exclusion list? Even if empty is fine, please confirm.</strong></p>

<p><strong>Gap 4 â€” Change order clause not reviewed by Ryan yet:</strong><br/>
The clause is already included in every AI-generated estimate (Sprint 4+). Ryan's sign-off is tracked as a pre-Sprint-12 requirement. This means estimates going out in Sprint 11 include a clause Ryan hasn't approved.<br/>
ðŸ‘‰ <strong>Ryan: Please review <code>config/knowledge_base/change_order_clause.txt</code> and confirm or redline before Sprint 12.</strong></p>

<p><strong>Gap 5 â€” 15 stakeholder recordings never conducted:</strong><br/>
Robert, Mark, Jessica, and Wyatt AI agents are all still STUB (operating on assumptions). Key decisions â€” exact service type list, full flag logic, AR reminder specifics, statement format â€” were made without Robert/Mark/Jessica/Wyatt's real input. Sprint 12 full production means these STUBs go live on real customers.<br/>
ðŸ‘‰ <strong>When can we schedule at minimum: Robert (Recording 1), Jessica (Recording 10)?</strong></p>

<hr/>

<h3>ðŸ’¡ AI SUGGESTIONS (from me â€” take or leave)</h3>

<p><strong>Idea 1 â€” Approval visibility dashboard:</strong><br/>
A simple live page showing: how many orders are currently awaiting approval, average queue time this week, which flag trigger fires most (e.g., "Competitor flag" vs "Monroe County" vs "ALTA"). Would help Ryan see if the AI is over-flagging or under-flagging without reading logs.<br/>
â†’ I can build this in 1-2 hours. Want it?</p>

<p><strong>Idea 2 â€” Approval queue age tracker in the batch digest:</strong><br/>
When the batch approval digest goes to Teams, add an "Age" column showing how long each order has been waiting (e.g., "4h 22m"). This makes it obvious if something has been stuck overnight.<br/>
â†’ 30-minute code change. Should I add it?</p>

<p><strong>Idea 3 â€” Staged flag tuning after 1 week of production data:</strong><br/>
After Sprint 11 runs for 1 week with real orders, export: total orders â†’ how many auto-quoted vs. flagged â†’ which flag triggers fired â†’ how many flags were overridden with APPROVE. If >60% of flags are being approved instantly, that trigger may be too aggressive. Ryan + Robert review this together. A data-driven flag calibration session.<br/>
â†’ I'll build the data export script so this is ready after week 1.</p>

<p><strong>Idea 4 â€” "DEFER" command in Teams:</strong><br/>
Currently only APPROVE and REJECT. What if Robert wants to say "hold this one until I talk to the client"? He'd either have to reject it (losing context) or leave it queued (polluting the list). A DEFER [id] [reason] command would move it to a "deferred" status and exclude it from the batch digest until tomorrow.<br/>
â†’ Worth building? Or is REJECT + manual re-entry fine?</p>

<hr/>

<h3>ðŸŽ¯ WHAT I NEED FROM EACH PERSON</h3>

<table>
<tr><th>Person</th><th>Action Required</th><th>Priority</th></tr>
<tr><td><strong>Ryan</strong></td><td>Review change order clause text. Confirm I-062 (website chat) sprint timeline. GO/NO-GO on Bobby approval UX (commands vs. spreadsheet).</td><td>ðŸ”´ Before Sprint 12</td></tr>
<tr><td><strong>Robert</strong></td><td>Confirm: (1) backup approver when you're out, (2) Teams command UX vs. spreadsheet preference, (3) dynamic pricing factors timeline, (4) AR exclusion list (even if empty = fine).</td><td>ðŸ”´ Sprint 11 observation week</td></tr>
<tr><td><strong>Both</strong></td><td>Once production credentials are set â†’ monitor first 5 real estimates and report back: correct service? correct price? professional tone? any edge case?</td><td>ðŸ”´ Immediate</td></tr>
</table>

<p><em>Reply in this thread or email ai@nexgen.enterprises â€” all findings get logged as issues.</em></p>
"""

# â”€â”€ EMAIL â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

email_html = """
<h2>FTF Agentic AI â€” E2E Gap Analysis (Sprint 0-11 Complete)</h2>

<p>Hi Ryan and Robert,</p>

<p>This is a deeper review request than before. I've read through the full codebase, sprint files, issues log, and approval flow â€” and found specific gaps that need your answers before we can move to Sprint 12 (Full Production). Please read through and reply to whatever applies to you.</p>

<hr/>

<h3>WHERE WE ACTUALLY ARE</h3>
<ul>
  <li><strong>Estimate loop:</strong> Sprint 11 in progress. Production credentials NOT yet set in GitHub Actions â†’ still on staging. No real estimates sent yet.</li>
  <li><strong>Approval monitor:</strong> LIVE 24/7 via GitHub Actions (every 5 min).</li>
  <li><strong>AR reminders + Monthly statements:</strong> Staging only â€” not in production.</li>
  <li><strong>Email intake monitor (nesa@nexgenlogix.com):</strong> Built but deployment unclear.</li>
</ul>

<hr/>

<h3>IMMEDIATE BLOCKERS</h3>
<ol>
  <li><strong>Production credentials not swapped</strong> â€” GitHub Actions still hits staging FTF URL. Prateek needs to set FTF_API_BASE_URL + FTF_API_KEY secrets to production values before the estimate loop generates real output.</li>
  <li><strong>Zero real estimates reviewed</strong> â€” Sprint 11 milestone requires Robert + Mark to review 5 real estimates. None have happened yet.</li>
  <li><strong>Change order clause not Ryan-approved</strong> â€” Going into every estimate already. Please confirm or redline the text in <code>config/knowledge_base/change_order_clause.txt</code>.</li>
</ol>

<hr/>

<h3>QUESTIONS FOR ROBERT</h3>
<ol>
  <li>Approval UX: Do you want to approve orders by typing APPROVE/REJECT in Teams (current), or do you prefer a spreadsheet email where you mark Approve/Deny and reply?</li>
  <li>If you're out of office â€” who should be backup approver? (Currently only Robert, Ryan, Prateek can approve.)</li>
  <li>Dynamic pricing (pools, sheds, driveways, wall count) â€” when should we wire this into the actual pricing code vs. leaving it as AI knowledge-base context only?</li>
  <li>AR exclusion list â€” any clients who should NEVER receive automated AR reminders? (Even confirming the list is intentionally empty helps.)</li>
  <li>Recording sessions 1â€“8 (service types, flag logic, edge cases) â€” still all pending. Can we schedule at least one this week?</li>
</ol>

<hr/>

<h3>QUESTIONS FOR RYAN</h3>
<ol>
  <li>Website chat integration (I-062) â€” customer says "go ahead" on site chat â†’ AI converts quote to pending. Is this Sprint 13, or post-launch?</li>
  <li>The "Bobby hourly spreadsheet" you described on May 26 â€” current build sends a Teams message with a table. Robert approves by typing in Teams. Is this acceptable, or do you still want the email spreadsheet format?</li>
  <li>Weather monitoring agent (daily check â†’ proactive customer delay alerts) â€” what's the priority level? Sprint 13 or further out?</li>
  <li>Please review the change order clause text and confirm or redline before Sprint 12.</li>
</ol>

<hr/>

<h3>GAPS I FOUND (no action needed â€” just FYI)</h3>
<ul>
  <li>GitHub Actions workflow failure = silent. If it fails at 3 AM, nobody is alerted. Suggest: add failure notification to Teams.</li>
  <li>Approval queue has no aging escalation. Orders can sit for 20+ hours with no nudge after the 9 AM daily reminder.</li>
  <li>LLM classifier (Claude AI) is never called in the classifier â€” it's rule-based only. Fine for now but ambiguous future orders won't get AI analysis.</li>
  <li>Agent 12 (email monitor for nesa@nexgenlogix.com) was built but I can't confirm where it's actually deployed and running.</li>
</ul>

<hr/>

<h3>SUGGESTIONS (from me)</h3>
<ul>
  <li>Build an approval visibility dashboard: live queue size, average approval time, which flag triggers most. 1-2 hours of work. Want it?</li>
  <li>After 1 week of Sprint 11 production data: export flag trigger stats. If >60% of flagged orders are instantly approved, that trigger is too aggressive. Tune it with real data.</li>
  <li>Add a DEFER command to Teams: DEFER [order_id] [reason] â€” hold it for next day without rejecting. Prevents queue clutter.</li>
</ul>

<hr/>

<p>Please reply here or in Teams (FTF-Approvals channel). Every finding gets logged and actioned.<br/>
Reply-to: <a href="mailto:ai@nexgen.enterprises">ai@nexgen.enterprises</a></p>

<p>â€” FTF Agentic AI System</p>
"""

print("Sending Teams channel message...")
r1 = send_channel_message(teams_html)
print(f"  Teams: {r1}")

print("Sending email...")
r2 = send_email_notification(
    email_html,
    subject="FTF Agentic AI â€” E2E Gap Analysis & Review (Your Input Required)"
)
print(f"  Email: {r2}")

print("Done.")

