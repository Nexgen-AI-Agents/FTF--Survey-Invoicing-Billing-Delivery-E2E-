# Glossary — Plain English

| Term | What it means |
|---|---|
| **FTF / FieldToFinish** | The survey order system where orders and invoices live |
| **Order** | One survey job for a property |
| **Invoice** | The bill sent to the client for a completed order |
| **Approvals sheet** | The OneDrive Excel tab where a person reviews and approves each draft |
| **Agent (A0–A7)** | A small AI worker that does one step of the job |
| **A0 Orchestrator** | The "conductor" that runs the other agents in order |
| **A1 Flag Hunter** | Finds orders that FTF has marked as needing an invoice |
| **A2 Data Collector** | Gathers the order's details (address, size, flood zone, etc.) |
| **A3 Invoice Compiler** | Drafts the invoice and suggests a price |
| **A4 Human Gate** | Reads your Approve / Reject / Hold decision |
| **A5 Finalizer** | Creates the real invoice in FTF once you approve |
| **A6 Sender** | Emails the invoice to the client |
| **A7 Feedback Learner** | Learns from your edits so future prices are better |
| **`ng_invoice_needed`** | The FTF flag that marks an order as "needs an invoice". The AI only brings flagged orders |
| **Service / Breakdown by User** | The blue column where you set what gets billed (`Name: $Amount`) |
| **Confidence** | How sure the AI is about a price (High / Medium / Low) |
| **Escalate** | The AI flags an unusual order for a manager to review |
| **Human-in-the-loop** | A person must approve before anything is sent |
| **Watermark** | A "start from here" marker so old historical orders are not re-processed |
| **Token** | The unit AI providers bill by (roughly ¾ of a word) |
| **Cron** | A timer that runs the pipeline automatically (every 5 minutes) |
