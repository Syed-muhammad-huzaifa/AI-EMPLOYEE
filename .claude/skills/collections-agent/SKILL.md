---
name: collections-agent
description: "GOLD TIER: Automated Accounts Receivable Collections Workflow. Scans overdue invoices, prioritizes by amount/days, drafts personalized payment reminder emails, creates escalation tasks for high-value accounts, and moves completed actions to Done/."
version: 1.0.0
skill_type: workflow_agent
tier: gold
architecture_role: collections_automation
dependencies:
  mcp_servers:
    - odoo
    - gmail
called_by:
  - orchestrator (manual trigger via Needs_Action/)
  - scheduler (weekly, Monday 9am)
---

# collections-agent — AUTOMATED AR COLLECTIONS WORKFLOW

## ⚠️ CRITICAL: ROLE DEFINITION

**This skill is an AR COLLECTIONS AUTOMATION AGENT.**

### STRICT RESPONSIBILITIES

`collections-agent` **DOES**:
- ✅ Fetch all overdue invoices from Odoo
- ✅ Run AR aging analysis (30/60/90/120+ day buckets)
- ✅ Fetch full customer statement for each overdue account
- ✅ Draft personalized payment reminder emails by overdue tier
- ✅ Stage emails in `Pending_Approval/` for human review (HITL)
- ✅ Create escalation tasks in `Needs_Action/` for 90+ day accounts
- ✅ Log all collection actions to `Logs/`

`collections-agent` **MUST NEVER**:
- ❌ Send emails without human approval (use HITL via Pending_Approval/)
- ❌ Modify invoice amounts or payment terms in Odoo
- ❌ Write off bad debts autonomously
- ❌ Contact customers via channels other than email drafts

---

## INPUT SPECIFICATION

### Trigger Task Format (in Needs_Action/)

```yaml
---
action: collections_run
task_id: COLLECTIONS_YYYYMMDD
created: 2026-02-15T09:00:00
risk_level: medium
skill: collections-agent
---

# Collections Run

## Parameters
min_days_overdue: 1        # minimum days overdue to include
escalation_threshold: 90   # days overdue before escalation task
dry_run: false             # if true, log only — no drafts created
```

### Required Context
- Odoo MCP server accessible
- Gmail MCP server accessible (for email drafts)
- `Company_Handbook.md` — company name, contact details

---

## EXECUTION WORKFLOW

### Phase 1: Overdue Invoice Discovery

```markdown
1. Call `get_ar_aging_report()`
   - Extract buckets: current, days_1_30, days_31_60, days_61_90, days_91_120, days_120_plus
   - Compute total_overdue = sum of all overdue buckets (exclude current)
   - Log: "AR Aging: 30d=$X | 60d=$X | 90d=$X | 90+=$X"

2. Call `get_overdue_invoices(min_days_overdue=1)`
   - Build prioritized list sorted by: days_overdue DESC, amount DESC
   - Group by tier:
     - TIER_1 (1-30 days):   Friendly reminder
     - TIER_2 (31-60 days):  Second notice
     - TIER_3 (61-90 days):  Urgent notice
     - TIER_4 (90+ days):    Escalation required
```

### Phase 2: Customer Context

```markdown
For each overdue invoice:
1. Call `get_customer_statement(customer_email, days=90)`
   - Check payment history: is this a regular payer or chronic late?
   - Compute: total_open_balance, previous_payments

2. Classify customer payment behavior:
   - "good_payer": has paid invoices on time historically
   - "late_payer": consistently pays 15-30 days late
   - "chronic_late": repeatedly 60+ days overdue
   - "new_customer": < 3 invoices in system
```

### Phase 3: Draft Reminder Emails

```markdown
For TIER_1 (1-30 days overdue) — Friendly Reminder:
  Subject: "Invoice #{number} — Friendly Payment Reminder"
  Tone: polite, brief
  Body:
    - Reference invoice number, amount, original due date
    - Provide payment instructions
    - Offer to answer questions

For TIER_2 (31-60 days overdue) — Second Notice:
  Subject: "Invoice #{number} — Second Payment Notice ({days} days overdue)"
  Tone: professional, firm
  Body:
    - Reference invoice number, amount, days overdue
    - State total outstanding balance
    - Request payment within 7 days
    - Mention late payment policy (if in Company_Handbook.md)

For TIER_3 (61-90 days overdue) — Urgent Notice:
  Subject: "URGENT: Invoice #{number} — Payment Required Immediately"
  Tone: firm, urgent
  Body:
    - State account is seriously overdue
    - List all outstanding invoices with amounts
    - Request immediate payment or payment plan contact
    - Note potential suspension of services

For TIER_4 (90+ days overdue) — Escalation:
  DO NOT draft email automatically
  Create escalation task in Needs_Action/:
    action: escalation_collections
    customer: {name}
    total_overdue: ${amount}
    days_overdue: {days}
    recommendation: "Consider: collections agency / payment plan / legal notice"
```

### Phase 4: Stage for HITL Approval

```markdown
For each drafted email (TIER_1, TIER_2, TIER_3):
Create file in Pending_Approval/:

  COLLECTION_EMAIL_{invoice_number}_{YYYYMMDD}.md
  ---
  action: send_collection_email
  invoice_id: {id}
  invoice_number: {number}
  customer_email: {email}
  customer_name: {name}
  amount_overdue: {amount}
  days_overdue: {days}
  tier: TIER_1|TIER_2|TIER_3
  risk_level: low|medium|high
  ---

  # Payment Reminder: {invoice_number}

  **To:** {customer_email}
  **Subject:** {subject}

  {email_body}

  ---
  ## Review Instructions
  - ✅ Approve: Rename file to Approved/ (email will be sent)
  - ❌ Reject: Move to Rejected/ with rejection note
  - ✏️ Edit: Modify body before approving
```

### Phase 5: Summary Report

```markdown
Create file in Logs/:
  COLLECTIONS_RUN_{YYYYMMDD}.md

  # Collections Run — {date}

  ## Summary
  - Total Overdue: ${total_overdue}
  - Invoices Processed: {count}
  - Reminders Staged: {count}
  - Escalations Created: {count}

  ## By Tier
  | Tier | Invoices | Total Amount | Action |
  |------|----------|--------------|--------|
  | 1-30 days | X | $X | Friendly reminder staged |
  | 31-60 days | X | $X | Second notice staged |
  | 61-90 days | X | $X | Urgent notice staged |
  | 90+ days | X | $X | Escalation task created |

  ## Next Steps
  1. Review {count} emails in Pending_Approval/
  2. Review {count} escalation tasks in Needs_Action/
  3. Next collections run: [date]
```

---

## MCP TOOLS USAGE

```yaml
tools_used:
  - get_ar_aging_report:
      args: {}
      returns: {current, days_1_30, days_31_60, days_61_90, days_91_120, days_120_plus, total_customers}

  - get_overdue_invoices:
      args:
        min_days_overdue: 1
      returns: [{id, number, customer, customer_email, amount, days_overdue}]

  - get_customer_statement:
      args:
        customer_email: "{email}"
        days: 90
      returns: {invoices, payments, closing_balance, total_overdue}

  - send_payment_reminder:
      note: "NOT called directly — email drafted in Pending_Approval/ for human review"
```

---

## TIERED EMAIL TEMPLATES

### TIER_1 Template (1-30 days)
```
Hi {customer_name},

I hope this message finds you well. This is a friendly reminder that
invoice {invoice_number} for ${amount} was due on {due_date}.

Please arrange payment at your earliest convenience. If you have
already processed this payment, please disregard this notice.

Invoice details:
- Invoice #: {invoice_number}
- Amount: ${amount}
- Due date: {due_date}

If you have any questions, please don't hesitate to reach out.

Best regards,
{company_name}
```

### TIER_2 Template (31-60 days)
```
Dear {customer_name},

This is a second notice regarding invoice {invoice_number} for ${amount},
which is now {days_overdue} days past due.

Your current outstanding balance is ${total_outstanding}.

We kindly request payment within 7 business days. If you are
experiencing difficulties, please contact us to discuss payment options.

Outstanding invoices:
{invoice_list}

Best regards,
{company_name}
```

### TIER_3 Template (61-90 days)
```
Dear {customer_name},

URGENT: Your account has invoices that are now {days_overdue} days overdue,
totalling ${total_outstanding}.

Continued non-payment may result in suspension of services and/or
referral to a collections agency.

Please make immediate payment or contact us within 48 hours to
discuss a resolution.

Overdue invoices:
{invoice_list}

Regards,
{company_name} Accounts Team
```

---

## OUTPUT SPECIFICATION

### Success Output
```json
{
  "success": true,
  "run_date": "2026-02-15",
  "summary": {
    "total_overdue_amount": 15400.00,
    "total_overdue_invoices": 8,
    "tier_1_count": 4,
    "tier_2_count": 2,
    "tier_3_count": 1,
    "tier_4_count": 1,
    "reminders_staged": 7,
    "escalations_created": 1
  },
  "pending_approval_files": [
    "COLLECTION_EMAIL_INV2026001_20260215.md",
    "COLLECTION_EMAIL_INV2026002_20260215.md"
  ],
  "log_file": "Logs/COLLECTIONS_RUN_20260215.md"
}
```

### Error Handling
```json
{
  "success": false,
  "error": "ODOO_CONNECTION_FAILED",
  "partial_results": {
    "invoices_fetched": 0
  },
  "action": "Created Needs_Action task for manual review"
}
```

---

## SCHEDULING

```
0 9 * * 1  # Every Monday at 9:00 AM
```

Or trigger manually:
```bash
echo "---
action: collections_run
skill: collections-agent
---
Run collections workflow" > /mnt/c/MY_EMPLOYEE/Needs_Action/COLLECTIONS_$(date +%Y%m%d).md
```

---

## VERSION HISTORY

- **1.0.0** (2026-02-15) - Initial implementation
  - AR aging analysis
  - 4-tier email strategy
  - HITL approval workflow
  - Escalation task creation
