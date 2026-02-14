---
name: month-end-close
description: "GOLD TIER: Month-End Closing Automation. Runs a structured accounting close checklist: verifies all invoices are posted, reconciles payments, generates P&L report, computes tax summary, checks AR/AP aging, flags discrepancies, and produces a sign-off report for the accountant/owner."
version: 1.0.0
skill_type: workflow_agent
tier: gold
architecture_role: accounting_close
dependencies:
  mcp_servers:
    - odoo
called_by:
  - orchestrator (manual trigger, last day of month)
  - scheduler (0 18 28-31 * * — last 4 days of month at 6pm)
---

# month-end-close — MONTH-END CLOSING AUTOMATION

## ⚠️ CRITICAL: ROLE DEFINITION

**This skill is an ACCOUNTING CLOSE WORKFLOW AGENT.**

### STRICT RESPONSIBILITIES

`month-end-close` **DOES**:
- ✅ Run structured close checklist (17 checks)
- ✅ Fetch P&L report for the closing month
- ✅ Compute tax summary (VAT/sales tax collected vs paid)
- ✅ Check AR aging — identify uncollected revenue
- ✅ Check AP aging — identify unpaid vendor bills
- ✅ Verify payment completeness against invoices
- ✅ Surface discrepancies and missing items
- ✅ Generate sign-off report for accountant review
- ✅ Stage close report in `Pending_Approval/` for human sign-off
- ✅ Log all checks to `Logs/`

`month-end-close` **MUST NEVER**:
- ❌ Post, reverse, or modify journal entries in Odoo
- ❌ Lock the accounting period (requires accountant action)
- ❌ File tax returns
- ❌ Approve its own sign-off report

---

## INPUT SPECIFICATION

### Trigger Task Format

```yaml
---
action: month_end_close
task_id: MONTH_CLOSE_YYYYMM
created: 2026-02-28T18:00:00
risk_level: medium
skill: month-end-close
---

# Month-End Close — February 2026

## Parameters
month: 2026-02          # YYYY-MM format (defaults to current month)
include_tax_summary: true
include_expense_breakdown: true
```

### Required Context
- Odoo MCP server accessible and current month data complete
- `Business_Goals.md` — monthly revenue targets
- `Company_Handbook.md` — tax rates, accounting policies

---

## EXECUTION WORKFLOW

### Phase 1: Period Setup

```markdown
1. Parse closing month from task (default: current month)
2. Compute:
   - start_date = YYYY-MM-01
   - end_date = last day of month (e.g., 2026-02-28)
   - month_label = "February 2026"

3. Log: "Starting month-end close for {month_label}"
```

### Phase 2: Revenue & Expense Analysis

```markdown
1. Call `get_profit_loss_report(start_date, end_date)`
   - Extract: total_revenue, total_expenses, net_profit, profit_margin
   - Compare against Business_Goals.md monthly target
   - Compute: target_achievement = (actual / target) * 100

2. Call `get_revenue_by_customer(start_date, end_date, limit=20)`
   - Identify top revenue sources
   - Flag any single customer > 50% of revenue (concentration risk)

3. Call `get_expense_by_category(start_date, end_date)`
   - List top expense categories
   - Flag any category > 30% of total expenses
   - Compute expense growth vs prior month (if data available)
```

### Phase 3: AR/AP Verification

```markdown
1. Call `get_ar_aging_report()`
   - Identify invoices that should have been collected this month
   - Flag: uncollected invoices with due dates in the closing month

2. Call `get_overdue_invoices(min_days_overdue=1)`
   - List all invoices overdue as of month end
   - Total: outstanding_ar_balance

3. Call `get_ap_aging_report()`
   - Identify vendor bills due this month
   - Flag: unpaid bills with due dates in the closing month
   - Total: outstanding_ap_balance

4. Call `search_invoices(status="draft", start_date, end_date, limit=50)`
   - CRITICAL: Any draft invoices = NOT POSTED = revenue not recorded
   - Flag as: ACTION_REQUIRED if count > 0
```

### Phase 4: Cash Reconciliation

```markdown
1. Call `get_payment_history(start_date, end_date)`
   - Total cash collected during month
   - Verify against: posted invoices marked as paid

2. Call `get_cash_flow_summary(start_date, end_date)`
   - cash_collected, cash_paid, net_cash_flow
   - Cross-check: cash_collected should ≈ payments received on AR

3. Call `get_bank_balance()`
   - Current closing bank balance
   - Note: for full reconciliation, compare to bank statement
```

### Phase 5: Tax Summary

```markdown
1. Call `get_tax_summary(start_date, end_date)`
   (if available, else derive from revenue * effective tax rate)

   Output:
   - tax_collected (from customers)
   - tax_paid (to vendors/suppliers)
   - net_tax_liability = tax_collected - tax_paid
   - Note: "Consult accountant before filing"
```

### Phase 6: Close Checklist Evaluation

```markdown
Run 17 checks — each is PASS / FAIL / WARNING:

Revenue Checks:
  [1] All invoices posted (no drafts remaining)
  [2] Revenue matches business target (within 10%)
  [3] No single customer > 50% of revenue
  [4] Customer payments recorded correctly

Expense Checks:
  [5] Vendor bills entered for all known expenses
  [6] No single category > 40% unexplained spike
  [7] Payroll/contractor payments recorded

AR Checks:
  [8] No invoices > 90 days without contact note
  [9] AR aging healthy (overdue_ratio < 30%)
  [10] Collections-agent run this month

AP Checks:
  [11] No vendor bills > 60 days unpaid
  [12] All due-this-month bills paid or scheduled

Cash Checks:
  [13] Bank balance positive
  [14] Net cash flow positive for month
  [15] No unexplained large cash outflows

Reporting Checks:
  [16] P&L report generated and saved
  [17] Tax summary computed and saved

For each FAIL: add to Action Items with specific fix instructions
For each WARNING: add to Review Items
```

### Phase 7: Generate Sign-Off Report

```markdown
Create file in Pending_Approval/:
  MONTH_END_CLOSE_{YYYY_MM}.md

---
action: approve_month_end_close
period: {YYYY-MM}
month_label: {Month YYYY}
risk_level: medium
checklist_pass: {X}/17
checklist_fail: {Y}/17
net_profit: {amount}
---

# Month-End Close Report — {Month YYYY}

## ✅ Close Checklist ({pass_count}/17 passed)

| # | Check | Status |
|---|-------|--------|
| 1 | All invoices posted | ✅ PASS / ❌ FAIL |
| 2 | Revenue vs target | ✅ PASS |
...

## 📊 Financial Summary

| Metric | Amount | vs Target |
|--------|--------|-----------|
| Revenue | ${revenue} | {target_pct}% |
| Expenses | ${expenses} | - |
| Net Profit | ${net_profit} | {margin}% margin |
| Cash Flow | ${net_cash_flow} | ↑/↓ |

## 💰 Tax Summary

- Tax Collected: ${tax_collected}
- Tax Paid: ${tax_paid}
- **Net Tax Liability: ${net_tax_liability}**
- ⚠️ Consult accountant before filing

## 📋 AR Summary

- Total Outstanding: ${outstanding_ar}
- Overdue: ${total_overdue} ({overdue_count} invoices)
- Largest Overdue: Invoice #{num} — ${amount} — {days} days

## 🏦 AP Summary

- Total AP Outstanding: ${outstanding_ap}
- Overdue Bills: ${ap_overdue}

## 🚨 Action Items (Must Fix Before Close)

{List of FAILed checks with specific remediation steps}

## 📝 Review Items (Accountant Attention)

{List of WARNINGs}

## 🔐 Sign-Off Instructions

To approve this close:
- Review all Action Items above
- Confirm remediation or note exceptions
- Move this file to Approved/ to signal close complete
- Accountant should then lock the period in Odoo

---
Generated by month-end-close skill | {timestamp}
```

### Phase 8: Save Supporting Reports

```markdown
1. Save P&L to: Briefings/PL_Report_{YYYY-MM}.md
2. Save expense breakdown to: Briefings/Expense_Report_{YYYY-MM}.md
3. Save tax summary to: Briefings/Tax_Summary_{YYYY-MM}.md
4. Save close log to: Logs/MONTH_CLOSE_{YYYYMM}.log
```

---

## MCP TOOLS USAGE

```yaml
tools_used:
  - get_profit_loss_report:
      args:
        start_date: "YYYY-MM-01"
        end_date: "YYYY-MM-DD"
      returns: {revenue, expenses, net_profit, profit_margin}

  - get_revenue_by_customer:
      args:
        start_date: "YYYY-MM-01"
        end_date: "YYYY-MM-DD"
        limit: 20
      returns: {customers: [{name, email, revenue}], total_revenue}

  - get_expense_by_category:
      args:
        start_date: "YYYY-MM-01"
        end_date: "YYYY-MM-DD"
      returns: {categories: [{name, amount, percentage}], total_expenses}

  - get_ar_aging_report:
      args: {}
      returns: {current, days_1_30, days_31_60, days_61_90, days_91_120, days_120_plus}

  - get_ap_aging_report:
      args: {}
      returns: {current, days_1_30, days_31_60, days_61_90, days_91_120, days_120_plus}

  - get_overdue_invoices:
      args:
        min_days_overdue: 1
      returns: [{id, number, customer, amount, days_overdue}]

  - search_invoices:
      args:
        status: "draft"
        start_date: "YYYY-MM-01"
        end_date: "YYYY-MM-DD"
        limit: 50
      returns: {invoices: [...], total_count}

  - get_payment_history:
      args:
        start_date: "YYYY-MM-01"
        end_date: "YYYY-MM-DD"
      returns: {payments: [...], total_collected}

  - get_cash_flow_summary:
      args:
        start_date: "YYYY-MM-01"
        end_date: "YYYY-MM-DD"
      returns: {cash_collected, cash_paid, net_cash_flow}

  - get_bank_balance:
      args: {}
      returns: {total_bank_balance, accounts: [{name, balance}]}

  - get_tax_summary:
      args:
        start_date: "YYYY-MM-01"
        end_date: "YYYY-MM-DD"
      returns: {tax_collected, tax_paid, net_tax_liability}
```

---

## OUTPUT SPECIFICATION

### Success Output
```json
{
  "success": true,
  "period": "2026-02",
  "month_label": "February 2026",
  "checklist": {
    "total": 17,
    "passed": 14,
    "failed": 2,
    "warnings": 1
  },
  "financials": {
    "revenue": 52340.00,
    "expenses": 31200.00,
    "net_profit": 21140.00,
    "profit_margin": 40.4,
    "net_tax_liability": 4200.00
  },
  "action_items_count": 2,
  "sign_off_file": "Pending_Approval/MONTH_END_CLOSE_2026_02.md",
  "supporting_reports": [
    "Briefings/PL_Report_2026-02.md",
    "Briefings/Tax_Summary_2026-02.md"
  ]
}
```

### Error Handling
```json
{
  "success": false,
  "error": "ODOO_DATA_INCOMPLETE",
  "message": "Could not fetch P&L report — Odoo returned empty dataset",
  "partial_checklist": "8/17 checks completed",
  "action": "Created partial report in Pending_Approval/ — manual completion required"
}
```

---

## SCHEDULING

```
# Last calendar day of month at 6pm (runs days 28-31, checks if last day)
0 18 28-31 * *  # scheduler should check: is today the last day of the month?
```

Manual trigger:
```bash
echo "---
action: month_end_close
skill: month-end-close
month: 2026-02
---
Run month-end close for February 2026" > /mnt/c/MY_EMPLOYEE/Needs_Action/MONTH_CLOSE_202602.md
```

---

## ACCOUNTANT HANDOFF

After this skill completes:
1. Accountant reviews `Pending_Approval/MONTH_END_CLOSE_{YYYY_MM}.md`
2. Fixes any ACTION ITEMS flagged
3. Approves by moving to `Approved/`
4. Manually locks the period in Odoo (Accounting → Settings → Lock Date)
5. Files taxes based on Tax Summary report

This skill does NOT lock periods or file taxes — those require human authorization.

---

## VERSION HISTORY

- **1.0.0** (2026-02-15) - Initial implementation
  - 17-check close checklist
  - P&L + AR/AP + cash reconciliation
  - Tax summary computation
  - HITL sign-off via Pending_Approval/
  - Supporting reports to Briefings/
