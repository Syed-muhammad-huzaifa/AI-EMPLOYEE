---
name: financial-health-check
description: "GOLD TIER: Daily Financial Health Snapshot. Pulls live data from Odoo (balance sheet, AR aging, cash collected, overdue invoices) and writes a concise one-page dashboard to Briefings/. Designed to run every morning so the business owner has a financial pulse before the day starts."
version: 1.0.0
skill_type: reporter
tier: gold
architecture_role: daily_intelligence
dependencies:
  mcp_servers:
    - odoo
called_by:
  - scheduler (daily, 8am weekdays)
  - orchestrator (manual trigger)
---

# financial-health-check — DAILY FINANCIAL HEALTH SNAPSHOT

## ⚠️ CRITICAL: ROLE DEFINITION

**This skill is a READ-ONLY FINANCIAL REPORTER.**

### STRICT RESPONSIBILITIES

`financial-health-check` **DOES**:
- ✅ Fetch balance sheet snapshot (assets, liabilities, equity)
- ✅ Fetch bank/cash balance
- ✅ Compute AR aging summary (how much is owed, how overdue)
- ✅ Compute cash collected today and this week
- ✅ Count unpaid/overdue invoices by tier
- ✅ Write daily snapshot to `Briefings/Financial_Health_YYYY-MM-DD.md`
- ✅ Flag RED/YELLOW/GREEN health status per metric
- ✅ Surface top 3 actions needed

`financial-health-check` **MUST NEVER**:
- ❌ Modify any financial data in Odoo
- ❌ Send emails or notifications directly
- ❌ Make payment decisions
- ❌ Run longer than 60 seconds (it's a snapshot, not a full audit)

---

## INPUT SPECIFICATION

### Trigger (via scheduler or Needs_Action/)

```yaml
---
action: financial_health_check
task_id: HEALTH_CHECK_YYYYMMDD
created: 2026-02-15T08:00:00
risk_level: low
skill: financial-health-check
---
Run daily financial health check.
```

### Parameters (optional, in task body)
```yaml
period_days: 7        # lookback for cash flow (default: 7)
alert_threshold:
  overdue_amount: 5000   # flag RED if total overdue > this
  cash_runway_days: 30   # flag RED if cash < 30 days of expenses
```

---

## EXECUTION WORKFLOW

### Phase 1: Balance Sheet Snapshot (≤5s)

```markdown
1. Call `get_balance_sheet()`
   - Extract: total_assets, total_liabilities, total_equity, net_worth
   - Compute: debt_ratio = total_liabilities / total_assets (if assets > 0)
   - Status:
     - 🟢 GREEN: debt_ratio < 0.5 and net_worth > 0
     - 🟡 YELLOW: debt_ratio 0.5-0.7 or net_worth just positive
     - 🔴 RED: debt_ratio > 0.7 or net_worth negative
```

### Phase 2: Cash Position (≤5s)

```markdown
1. Call `get_bank_balance()`
   - Extract: total_bank_balance, accounts list
   - Compare to: average monthly expenses (from Business_Goals.md if available)

2. Call `get_cash_flow_summary(start_date=7_days_ago, end_date=today)`
   - Extract: cash_collected (this week), cash_paid (this week), net_cash_flow
   - Status:
     - 🟢 GREEN: net_cash_flow > 0
     - 🟡 YELLOW: net_cash_flow slightly negative (< 10% of cash_collected)
     - 🔴 RED: net_cash_flow strongly negative
```

### Phase 3: AR Health (≤5s)

```markdown
1. Call `get_ar_aging_report()`
   - Extract all aging buckets
   - Compute:
     - total_overdue = days_1_30 + days_31_60 + days_61_90 + days_91_120 + days_120_plus
     - overdue_ratio = total_overdue / (current + total_overdue)
   - Status:
     - 🟢 GREEN: total_overdue < $5,000 and overdue_ratio < 0.15
     - 🟡 YELLOW: total_overdue $5,000–$15,000 or overdue_ratio 0.15–0.30
     - 🔴 RED: total_overdue > $15,000 or overdue_ratio > 0.30

2. Call `get_overdue_invoices(min_days_overdue=1)`
   - Count invoices by tier
   - Surface top 3 largest overdue invoices for action section
```

### Phase 4: Today's Activity (≤5s)

```markdown
1. Call `get_payment_history(start_date=today, end_date=today)`
   - Total payments received today
   - Count of payments processed

2. Call `search_invoices(status="draft", start_date=today, end_date=today, limit=20)`
   - Count new invoices created today

3. Compute:
   - invoices_issued_today: count of today's invoices
   - payments_received_today: total from payment history
```

### Phase 5: Generate Report

```markdown
Write to: Briefings/Financial_Health_{YYYY-MM-DD}.md

Template:
---
type: financial_health_check
date: {YYYY-MM-DD}
generated_at: {HH:MM}
overall_status: GREEN|YELLOW|RED
---

# 💰 Financial Health Check — {Day, Month DD YYYY}
> Generated at {HH:MM} | Status: {OVERALL_EMOJI} {OVERALL_STATUS}

---

## 📊 Health Dashboard

| Metric | Value | Status |
|--------|-------|--------|
| **Net Worth** | ${net_worth} | {status_emoji} |
| **Bank Balance** | ${total_bank_balance} | {status_emoji} |
| **Cash This Week** | ${net_cash_flow} ({direction}) | {status_emoji} |
| **Total AR Overdue** | ${total_overdue} | {status_emoji} |
| **Overdue Invoices** | {overdue_count} invoices | {status_emoji} |

---

## 💵 Cash Position

- **Bank Balance:** ${total_bank_balance}
  {accounts breakdown}
- **Cash Collected (7 days):** ${cash_collected}
- **Cash Paid Out (7 days):** ${cash_paid}
- **Net Cash Flow:** ${net_cash_flow} {direction_arrow}

---

## 📋 AR Aging Summary

| Bucket | Amount | Count |
|--------|--------|-------|
| Current (not yet due) | ${current} | - |
| 1-30 days overdue | ${days_1_30} | - |
| 31-60 days overdue | ${days_31_60} | - |
| 61-90 days overdue | ${days_61_90} | - |
| 91-120 days overdue | ${days_91_120} | - |
| 120+ days overdue | ${days_120_plus} | - |
| **TOTAL OVERDUE** | **${total_overdue}** | **{count}** |

---

## ⚡ Today's Activity

- Payments received: ${payments_received_today} ({payment_count} payments)
- New invoices: {invoices_issued_today}

---

## 🚨 Top 3 Actions Needed

{Derived from data — examples:}
1. 🔴 **Collect $X from {Customer}** — Invoice #{num}, {days} days overdue
2. 🟡 **Follow up with {Customer}** — Invoice #{num}, {days} days overdue
3. 🟢 **Run collections-agent** — {N} invoices need reminders

---

_Auto-generated by financial-health-check skill_
_Next check: Tomorrow 8:00 AM_
```

### Overall Status Logic
```markdown
OVERALL = worst of all individual statuses:
- Any 🔴 RED → overall is RED
- Any 🟡 YELLOW (no RED) → overall is YELLOW
- All 🟢 GREEN → overall is GREEN
```

---

## MCP TOOLS USAGE

```yaml
tools_used:
  - get_balance_sheet:
      args: {}
      returns: {total_assets, total_liabilities, total_equity, net_worth, is_balanced}

  - get_bank_balance:
      args: {}
      returns: {total_bank_balance, accounts: [{name, balance}]}

  - get_cash_flow_summary:
      args:
        start_date: "YYYY-MM-DD"  # 7 days ago
        end_date: "YYYY-MM-DD"    # today
      returns: {cash_collected, cash_paid, net_cash_flow, payment_count}

  - get_ar_aging_report:
      args: {}
      returns: {current, days_1_30, days_31_60, days_61_90, days_91_120, days_120_plus}

  - get_overdue_invoices:
      args:
        min_days_overdue: 1
      returns: [{id, number, customer, amount, days_overdue}]

  - get_payment_history:
      args:
        start_date: "YYYY-MM-DD"  # today
        end_date: "YYYY-MM-DD"    # today
      returns: {payments: [...], total_collected}

  - search_invoices:
      args:
        status: "draft"
        start_date: "YYYY-MM-DD"
        end_date: "YYYY-MM-DD"
        limit: 20
      returns: {invoices: [...], total_count}
```

---

## OUTPUT SPECIFICATION

### Success Output
```json
{
  "success": true,
  "date": "2026-02-15",
  "overall_status": "YELLOW",
  "metrics": {
    "net_worth": 45200.00,
    "bank_balance": 12800.00,
    "net_cash_flow_7d": 3200.00,
    "total_ar_overdue": 8400.00,
    "overdue_invoice_count": 5
  },
  "briefing_file": "Briefings/Financial_Health_2026-02-15.md",
  "actions_count": 3
}
```

---

## SCHEDULING

```
0 8 * * 1-5  # Weekdays at 8:00 AM
```

Manual trigger:
```bash
echo "---
action: financial_health_check
skill: financial-health-check
---" > /mnt/c/MY_EMPLOYEE/Needs_Action/HEALTH_$(date +%Y%m%d).md
```

---

## VERSION HISTORY

- **1.0.0** (2026-02-15) - Initial implementation
  - Balance sheet + cash + AR aging snapshot
  - RED/YELLOW/GREEN traffic light system
  - Daily briefing file generation
  - Top 3 actionable items surfaced
