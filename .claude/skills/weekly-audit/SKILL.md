---
name: weekly-audit
description: "GOLD TIER: Weekly Business Audit & CEO Briefing Generator. Uses Odoo MCP to fetch financial data (revenue, expenses, customers, invoices) and generates executive briefing for business oversight."
version: 1.0.0
skill_type: reporter
tier: gold
architecture_role: business_intelligence
dependencies:
  mcp_servers:
    - odoo
called_by:
  - scheduler (Sunday 9am)
  - orchestrator (manual trigger)
---

# weekly-audit - WEEKLY BUSINESS AUDIT & CEO BRIEFING

## ⚠️ CRITICAL: ROLE DEFINITION

**This skill is a BUSINESS INTELLIGENCE REPORTER.**

### STRICT RESPONSIBILITIES

`weekly-audit` **DOES**:
- ✅ Call Odoo MCP tools to fetch financial data
- ✅ Aggregate revenue, expenses, profit metrics
- ✅ Identify top customers and overdue invoices
- ✅ Generate actionable insights and recommendations
- ✅ Create structured CEO briefing markdown file
- ✅ Save briefing to `/Briefings/CEO_Briefing_YYYY-MM-DD.md`
- ✅ Log audit completion to `/Logs/`

`weekly-audit` **MUST NEVER**:
- ❌ Modify financial data in Odoo
- ❌ Send emails or messages (only creates briefing file)
- ❌ Make business decisions autonomously
- ❌ Execute transactions or payments

---

## INPUT SPECIFICATION

### What weekly-audit Receives

```yaml
context:
  # Trigger information
  trigger: scheduler | manual
  trigger_time: 2026-02-15T09:00:00

  # Vault paths
  vault_path: /mnt/c/MY_EMPLOYEE
  briefings_dir: /mnt/c/MY_EMPLOYEE/Briefings

  # Audit parameters
  period_days: 30  # Default: last 30 days
  include_overdue: true
  min_days_overdue: 1
```

### Required Context Files

- `Business_Goals.md` - Business targets and KPIs
- `Company_Handbook.md` - Company policies and context
- `/Done/` folder - Completed tasks for the period

---

## EXECUTION WORKFLOW

### Phase 1: Data Collection (Odoo MCP)

```markdown
1. Call `get_financial_summary(days=30)`
   - Extract: revenue, expenses, profit, invoice_count
   - Calculate: profit_margin = (profit / revenue) * 100

2. Call `get_customers(limit=10)`
   - Extract: top customers by transaction volume
   - Identify: key accounts requiring attention

3. Call `get_overdue_invoices(min_days_overdue=1)`
   - Extract: invoice_number, customer, amount, days_overdue
   - Prioritize: by amount and overdue duration
   - Calculate: total_outstanding = sum(overdue_amounts)
```

### Phase 2: Context Analysis

```markdown
1. Read Business_Goals.md
   - Compare actual vs target metrics
   - Identify gaps and achievements

2. Scan /Done/ folder (last 7 days)
   - Count completed tasks by category
   - Identify productivity patterns

3. Check /Logs/ for system health
   - Watcher uptime
   - Error rates
   - MCP tool usage
```

### Phase 3: Insight Generation

```markdown
1. Financial Health Assessment
   - Revenue trend (up/down vs previous period)
   - Expense control (within budget?)
   - Cash flow risk (overdue invoices)

2. Customer Relationship Status
   - Top revenue contributors
   - At-risk accounts (overdue payments)
   - Growth opportunities

3. Operational Efficiency
   - Task completion rate
   - System reliability
   - Bottlenecks identified

4. Actionable Recommendations
   - Priority 1: Urgent actions (overdue follow-ups)
   - Priority 2: Strategic moves (growth opportunities)
   - Priority 3: Optimizations (process improvements)
```

### Phase 4: Briefing Generation

```markdown
1. Create file: /Briefings/CEO_Briefing_YYYY-MM-DD.md

2. Structure:
   ---
   type: ceo_briefing
   date: YYYY-MM-DD
   period: Last 30 days
   generated_by: weekly-audit skill
   data_source: Odoo MCP
   ---

   # CEO Briefing - [Date]

   ## 📊 Financial Summary (Last 30 Days)
   - **Total Revenue:** $X,XXX (↑/↓ X% vs previous period)
   - **Total Expenses:** $X,XXX
   - **Net Profit:** $X,XXX
   - **Profit Margin:** XX%
   - **Invoices Issued:** X

   ## 💰 Cash Flow Status
   - **Outstanding Invoices:** $X,XXX
   - **Overdue Payments:** X invoices, $X,XXX total
   - **Average Days Overdue:** XX days

   ## 👥 Top Customers (by Revenue)
   1. Customer Name - $X,XXX
   2. Customer Name - $X,XXX
   3. Customer Name - $X,XXX

   ## ⚠️ Action Items (Priority Order)

   ### 🔴 Urgent (This Week)
   - Follow up: Invoice #XXXX - Customer Name - $X,XXX (XX days overdue)
   - Review: Expense spike in [category]

   ### 🟡 Important (This Month)
   - Opportunity: Upsell to [Customer Name]
   - Process: Optimize [workflow bottleneck]

   ### 🟢 Strategic (This Quarter)
   - Growth: Explore [market/service expansion]
   - Efficiency: Automate [manual process]

   ## 📈 Trends & Insights
   [AI-generated analysis of patterns and recommendations]

   ## ✅ Completed This Week
   - X tasks completed
   - Key achievements: [list]

   ---
   **Generated:** YYYY-MM-DD HH:MM:SS
   **Next Briefing:** [Next Sunday date]
   **Data Period:** [Start date] to [End date]

3. Validate output:
   - All placeholders filled with real data
   - Numbers formatted correctly (currency, percentages)
   - Recommendations are specific and actionable
   - File saved successfully
```

### Phase 5: Logging & Completion

```markdown
1. Create audit log: /Logs/AUDIT_YYYY-MM-DD.log
   - Timestamp
   - Data sources accessed
   - Metrics collected
   - Briefing file path
   - Any errors or warnings

2. Output completion message:
   {
     "success": true,
     "briefing_file": "/Briefings/CEO_Briefing_2026-02-15.md",
     "metrics": {
       "revenue": 50000,
       "profit": 20000,
       "overdue_count": 3
     },
     "next_run": "2026-02-22T09:00:00"
   }
```

---

## OUTPUT SPECIFICATION

### Success Output

```json
{
  "success": true,
  "briefing_file": "/Briefings/CEO_Briefing_2026-02-15.md",
  "audit_log": "/Logs/AUDIT_2026-02-15.log",
  "metrics": {
    "revenue": 50000.00,
    "expenses": 30000.00,
    "profit": 20000.00,
    "profit_margin": 40.0,
    "invoice_count": 12,
    "customer_count": 45,
    "overdue_count": 3,
    "overdue_total": 8500.00
  },
  "recommendations_count": 7,
  "next_run": "2026-02-22T09:00:00"
}
```

### Error Handling

```json
{
  "success": false,
  "error": "ODOO_CONNECTION_FAILED",
  "message": "Could not connect to Odoo MCP server",
  "fallback": "Created briefing template with manual data entry instructions",
  "retry_at": "2026-02-15T10:00:00"
}
```

---

## MCP TOOLS USAGE

### Required MCP Server: `odoo`

```yaml
tools_used:
  - get_financial_summary:
      args:
        days: 30
      returns: {revenue, expenses, profit, invoice_count, customer_count}

  - get_customers:
      args:
        limit: 10
      returns: [{id, name, email, phone, city, country}]

  - get_overdue_invoices:
      args:
        min_days_overdue: 1
      returns: [{id, number, customer, amount, days_overdue}]
```

### Error Recovery

```markdown
If Odoo MCP fails:
1. Log error to /Logs/
2. Create briefing template with placeholders
3. Add note: "⚠️ Odoo data unavailable - manual entry required"
4. Schedule retry in 1 hour
5. Notify via /Needs_Action/ task
```

---

## SCHEDULING

### Default Schedule (Cron)

```
0 9 * * 0  # Every Sunday at 9:00 AM
```

### Manual Trigger

```bash
# Via orchestrator task
echo "---
action: weekly_audit
---
Generate weekly CEO briefing" > /Needs_Action/AUDIT_MANUAL.md
```

---

## GOLD TIER COMPLIANCE

This skill fulfills Gold Tier requirements:

✅ **Odoo Integration** - Uses Odoo MCP for financial data
✅ **Weekly Audit** - Automated financial analysis
✅ **CEO Briefing** - Executive summary with insights
✅ **Actionable Intelligence** - Priority-ordered recommendations
✅ **Business Oversight** - Cash flow, customers, operations

---

## EXAMPLE EXECUTION

```markdown
[2026-02-15 09:00:00] weekly-audit skill invoked by scheduler

[09:00:01] Connecting to Odoo MCP...
[09:00:02] ✅ Authenticated (uid=2)

[09:00:03] Fetching financial summary (last 30 days)...
[09:00:04] ✅ Revenue: $52,340 | Expenses: $31,200 | Profit: $21,140

[09:00:05] Fetching top customers...
[09:00:06] ✅ Found 10 customers

[09:00:07] Fetching overdue invoices...
[09:00:08] ✅ Found 3 overdue invoices ($8,500 total)

[09:00:09] Reading Business_Goals.md...
[09:00:10] ✅ Target: $50k/month | Actual: $52k | Status: ✅ On track

[09:00:11] Scanning /Done/ folder (last 7 days)...
[09:00:12] ✅ 23 tasks completed

[09:00:13] Generating insights and recommendations...
[09:00:15] ✅ 7 recommendations generated

[09:00:16] Writing briefing to /Briefings/CEO_Briefing_2026-02-15.md...
[09:00:17] ✅ Briefing saved (2,847 words)

[09:00:18] Creating audit log...
[09:00:19] ✅ Log saved to /Logs/AUDIT_2026-02-15.log

[09:00:20] ✅ Weekly audit complete
[09:00:20] Next run: 2026-02-22 09:00:00
```

---

## TESTING

### Manual Test

```bash
# 1. Ensure Odoo is running
docker ps | grep odoo

# 2. Test Odoo MCP connection
python test_odoo_mcp.py

# 3. Trigger weekly-audit manually
echo "---
action: weekly_audit
---
Generate CEO briefing for testing" > /mnt/c/MY_EMPLOYEE/Needs_Action/TEST_AUDIT.md

# 4. Check output
cat /mnt/c/MY_EMPLOYEE/Briefings/CEO_Briefing_*.md
```

### Validation Checklist

- [ ] Odoo MCP connection successful
- [ ] Financial data fetched correctly
- [ ] Customer list populated
- [ ] Overdue invoices identified
- [ ] Briefing file created
- [ ] All metrics have real values (no placeholders)
- [ ] Recommendations are specific and actionable
- [ ] Audit log created
- [ ] No errors in /Logs/

---

## VERSION HISTORY

- **1.0.0** (2026-02-15) - Initial Gold Tier implementation
  - Odoo MCP integration
  - CEO briefing generation
  - Weekly scheduling support
