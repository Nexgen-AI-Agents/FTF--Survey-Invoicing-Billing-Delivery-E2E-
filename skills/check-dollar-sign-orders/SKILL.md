# check-dollar-sign-orders

Find all orders with no invoice amount (`estimate_amount` is null / "" / 0).
These are the orders visible in FTF with a `$` symbol but no dollar value filled in.

## How to run

```bash
# All orders with no amount
python skills/check-dollar-sign-orders/run.py

# Filter to a specific status
python skills/check-dollar-sign-orders/run.py --status invoice_draft_posted
python skills/check-dollar-sign-orders/run.py --status data_collected
```

## Output

```
================================================================================
  ORDERS WITH NO INVOICE AMOUNT  (147 found)
================================================================================

  [details_missing] — 82 orders
  Order ID        Client Name                         Address
  ---------------------------------------------------------------------------
  1000284561      Unknown                             Unknown
  ...

  TOTAL: 147 orders missing invoice amount
================================================================================
```

## When to use

- Prateek says "check the orders with dollar sign" → run this
- After a pipeline fix, re-run to see if the count went down
- Investigating why invoices weren't generated for a batch
- Whenever you see orders in FTF with `$` but no amount
