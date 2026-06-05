# requeue-orders

Reset specific orders (or all orders in a status) to a target status.
Clears named columns. Safe — never touches orders you don't name.

## How to run

```bash
# Reset 3 specific orders to invoice_needed, clear invoice_draft and data_sources
python skills/requeue-orders/run.py \
  --orders 1000283728,1000283564,1000283486 \
  --target-status invoice_needed \
  --clear invoice_draft,data_sources

# Reset ALL details_missing orders back to invoice_needed
python skills/requeue-orders/run.py \
  --from-status details_missing \
  --target-status invoice_needed

# Dry-run: see what would change without writing
python skills/requeue-orders/run.py \
  --orders 1000283728 \
  --target-status invoice_needed \
  --dry-run
```

## Parameters

| Flag | Required | Description |
|------|----------|-------------|
| `--orders` | One of these | Comma-separated order IDs |
| `--from-status` | One of these | Reset every order currently in this status |
| `--target-status` | Yes | Status to set (e.g. `invoice_needed`, `data_collected`) |
| `--clear` | No | Comma-separated column names to blank out |
| `--dry-run` | No | Print what would change; don't save |

## When to use

- After fixing a bug in A2 or A3, re-queue affected orders to reprocess
- Unstick orders that got stranded in a wrong status
- Prateek says "reset these orders and re-run"
