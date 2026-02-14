# AI Employee

An autonomous business automation system that monitors your inbox, manages Odoo accounting, processes tasks, and sends professional invoices with PDF attachments — all with human-in-the-loop approval.

---

## What It Does

| Capability | Description |
|------------|-------------|
| **Gmail Watcher** | Monitors inbox, classifies emails, routes them to the vault |
| **Odoo Integration** | Creates invoices, generates PDFs, tracks payments, P&L reports |
| **Invoice Automation** | Email → Invoice → PDF → Send in ~30 seconds |
| **Task Orchestration** | Processes tasks from vault folders via Claude |
| **Weekly Audit** | Pulls Odoo financials every Sunday and generates a CEO briefing |
| **Social Posting** | Publishes to LinkedIn / Facebook / Twitter |
| **WhatsApp Watcher** | Monitors WhatsApp for incoming task requests |
| **HITL Approval** | All sensitive actions require human sign-off before executing |

---

## Project Structure

```
Hackathon-0/
├── main.py                  # Entry point — starts all watchers + scheduler
├── ecosystem.config.js      # PM2 config (production process manager)
├── start.sh                 # Quick start script
├── pyproject.toml           # Python project metadata + dependencies
├── .env.example             # Copy to .env and fill in secrets
├── .mcp.json                # MCP server registration for Claude Code
│
├── src/                     # Core application modules
│   ├── orchestrator/        # Task orchestration + Claude API integration
│   ├── watchers/            # Event monitors (Gmail, WhatsApp, Filesystem)
│   ├── vault/               # Obsidian vault state management
│   ├── ralph/               # Task completion loop manager
│   ├── scheduler/           # Cron-style job scheduling
│   ├── social/              # Social media posting (LinkedIn, Facebook, Twitter)
│   ├── dashboard/           # Dashboard status updates
│   └── utils/               # Logging, config, secrets, watchdog
│
├── mcp-servers/             # MCP servers (used by Claude Code)
│   ├── email-mcp/           # Gmail: send, list, search, draft
│   └── odoo-mcp/            # Odoo: 14 tools for invoicing + accounting
│
├── scripts/                 # One-off utilities and demos
│   ├── authenticate_gmail.py    # Run once to set up Gmail OAuth
│   ├── populate_odoo_data.py    # Seed Odoo with test customers/invoices
│   ├── send_invoice.py          # End-to-end: create invoice + PDF + email
│   ├── demo_invoice.py          # Demo: invoice lifecycle walkthrough
│   ├── drop_test_task.py        # Drop a test task into the vault
│   └── post_social.py           # Post to social media manually
│
├── tests/
│   ├── unit/                # Unit tests per module
│   └── integration/         # End-to-end workflow tests
│       ├── test_odoo_mcp.py         # Odoo MCP connection + auth
│       ├── test_odoo_tools.py       # All 14 Odoo tools
│       ├── test_create_invoice.py   # Invoice creation
│       ├── test_invoice_pdf_email.py# PDF generation + email send
│       └── test_business_week.py    # Full week simulation
│
├── docs/
│   ├── quickstart.md        # First-time setup walkthrough
│   ├── project-structure.md # Architecture deep-dive
│   ├── odoo-tools.md        # All 14 Odoo MCP tools reference
│   ├── invoice-guide.md     # Invoice → PDF → Email workflow guide
│   ├── gold-tier.md         # Gold tier features + status
│   ├── bugs.md              # Known issues / bug log
│   └── archive/             # Previous tier docs (Silver)
│
└── config/                  # Runtime state (gitignored)
    ├── gmail_token.pickle       # Gmail OAuth token
    └── gmail_watcher_state.json # Last-seen email ID
```

---

## Quick Start

### 1. Prerequisites

- Python 3.13+
- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (for Odoo)
- A Google Cloud project with Gmail API enabled
- PM2 (`npm install -g pm2`) — optional, for production

### 2. Install Dependencies

```bash
cd Hackathon-0
pip install -e .
```

### 3. Configure Environment

```bash
cp .env.example .env
```

Edit `.env` and fill in:

```env
# Google / Gmail
GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=...

# Odoo (Docker)
ODOO_URL=http://localhost:8069
ODOO_DB=MYdb
ODOO_USER=your@email.com
ODOO_PASSWORD=yourpassword

# Vault path (Obsidian folder on your machine)
VAULT_PATH=/path/to/your/vault

# Anthropic
ANTHROPIC_API_KEY=sk-ant-...

# Optional
GMAIL_RATE_LIMIT_HOURLY=20
GMAIL_RATE_LIMIT_DAILY=100
DRY_RUN=false
```

### 4. Authenticate Gmail

Run this **once** to generate `config/gmail_token.pickle`:

```bash
python scripts/authenticate_gmail.py
```

A browser window opens — sign in with your Google account and grant permissions.

### 5. Start Odoo (Docker)

```bash
cd ~/odoo-docker
docker compose up -d
```

Odoo will be available at `http://localhost:8069`.

### 6. Run the System

**Development (single process):**
```bash
python main.py
```

**Production (PM2, auto-restart):**
```bash
pm2 start ecosystem.config.js
pm2 save
pm2 startup
```

---

## Vault Folder Structure

The system uses an Obsidian-style folder layout as its task queue:

```
VAULT_PATH/
├── Needs_Action/       # Incoming tasks (AI processes these)
├── Pending_Approval/   # Waiting for your sign-off
├── Approved/           # You approved — AI executes
├── In_Progress/        # Currently being worked on
├── Done/               # Completed tasks
├── Rejected/           # You rejected
├── Logs/               # Audit trail (JSON)
├── Briefings/          # CEO briefings from weekly audit
├── Plans/              # Generated plans
└── Accounting/         # Invoice and payment records
```

Drop a `.md` file into `Needs_Action/` and the system picks it up automatically.

**Example task file (`Needs_Action/invoice-client.md`):**
```markdown
---
action: create_invoice
priority: high
---
Create a $500 invoice for client@example.com
Description: Website redesign - Phase 1
Due: 30 days
```

---

## MCP Tools Reference

Register the MCP servers in Claude Code via `.mcp.json` (already configured).

### Gmail MCP (`mcp-servers/email-mcp/email-mcp.py`)

| Tool | Description |
|------|-------------|
| `send_email(to, subject, body)` | Send an email |
| `list_emails(query, max_results)` | List emails matching a query |
| `read_email(message_id)` | Fetch full email content |
| `get_thread(thread_id)` | Fetch all messages in a thread |
| `search_emails(query)` | Advanced Gmail search |
| `create_draft(to, subject, body)` | Save a draft |
| `mark_as_read(message_ids)` | Mark as read |
| `apply_label(message_id, label)` | Add a Gmail label |
| `get_email_stats()` | Classification statistics |

### Odoo MCP (`mcp-servers/odoo-mcp/odoo-mcp.py`) — 14 Tools

**Revenue Management**

| Tool | Description |
|------|-------------|
| `get_financial_summary(days)` | Revenue, expenses, profit for last N days |
| `create_invoice(customer_email, amount, description, due_days)` | Create + post an invoice |
| `get_invoice_pdf(invoice_id)` | Download invoice as PDF (base64) |
| `get_overdue_invoices(min_days_overdue)` | List unpaid + overdue invoices |
| `send_payment_reminder(invoice_id)` | Draft a payment reminder email |
| `get_invoice_status(invoice_id)` | Check payment state |

**Expense Management**

| Tool | Description |
|------|-------------|
| `create_expense(amount, description, category)` | Log a business expense |
| `get_accounts_payable()` | List vendor bills owed |
| `create_vendor_bill(vendor_name, amount, description, due_days)` | Record a vendor bill |

**Financial Reporting**

| Tool | Description |
|------|-------------|
| `get_profit_loss_report(start_date, end_date)` | Detailed P&L statement |
| `get_bank_balance()` | Current cash position |
| `get_tax_summary(start_date, end_date)` | Sales tax / VAT summary |

**Customer Management**

| Tool | Description |
|------|-------------|
| `get_customers(limit)` | List CRM customers |
| `record_payment(invoice_id, amount, payment_date)` | Mark invoice as paid |

---

## Common Workflows

### Send an Invoice with PDF

```bash
python scripts/send_invoice.py
```

Or tell Claude Code:

```
Create a $200 invoice for client@example.com and email it with the PDF attached.
```

The system will:
1. Find or create the customer in Odoo
2. Create and post the invoice
3. Download the PDF via Odoo's report engine
4. Email it with the PDF attached via Gmail

### Run the Weekly Audit

Runs automatically every Sunday at 9am. To trigger manually in Claude Code:

```
/weekly-audit
```

Generates a CEO briefing in `VAULT_PATH/Briefings/` covering:
- Revenue / expenses / profit (last 30 days)
- Overdue invoices needing follow-up
- Vendor bills due soon
- Cash position
- Tax liability summary

### Seed Odoo with Test Data

```bash
python scripts/populate_odoo_data.py
```

Creates 5 test customers, 6 invoices (~$40k total), and 4 expenses.

### Run All Tests

```bash
# Unit tests
python -m pytest tests/unit/ -v

# Integration tests (requires Odoo running)
python -m pytest tests/integration/ -v
```

---

## Skills (Claude Code)

Three custom skills are available in `.claude/skills/`:

| Skill | Trigger | Description |
|-------|---------|-------------|
| `weekly-audit` | `/weekly-audit` | Pull Odoo data + generate CEO briefing |
| `process-needs-action` | `/process-needs-action` | Process vault tasks (orchestrator) |
| `task-planner` | `/task-planner` | Plan multi-step tasks |

---

## Troubleshooting

**Odoo not reachable (`Connection refused` on port 8069)**
```bash
# Start Docker Desktop first, then:
cd ~/odoo-docker && docker compose up -d
# Wait ~15 seconds, then verify:
curl -s -o /dev/null -w "%{http_code}" http://localhost:8069/web/login
# Should print: 200
```

**Gmail auth failed (`Token not found`)**
```bash
python scripts/authenticate_gmail.py
```

**Emails not sending (`DRY_RUN` mode)**
```bash
# Check .env — must be:
DRY_RUN=false
```

**Odoo password forgotten**
```bash
docker exec odoo_db psql -U odoo -d MYdb \
  -c "UPDATE res_users SET password='newpassword' WHERE login='your@email.com';"
```

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                        main.py                          │
│   Starts watchers + scheduler + orchestration loop      │
└────────────┬────────────────────────────────────────────┘
             │
    ┌────────▼─────────────────────────────────┐
    │              Watchers                     │
    │  Gmail │ WhatsApp │ Filesystem (Vault)    │
    └────────┬─────────────────────────────────┘
             │ Events → Needs_Action/
    ┌────────▼─────────────────────────────────┐
    │        Orchestrator (Claude API)          │
    │  Reads task, calls MCP tools, writes      │
    └────────┬─────────────────────────────────┘
             │ Needs approval → Pending_Approval/
    ┌────────▼─────────────────────────────────┐
    │             HITL (You)                    │
    │  Move file: Approved/ or Rejected/        │
    └────────┬─────────────────────────────────┘
             │ Approved → execute
    ┌────────▼─────────────────────────────────┐
    │           MCP Servers                     │
    │  Gmail (9 tools) │ Odoo (14 tools)        │
    └──────────────────────────────────────────┘
```

**HITL (Human-in-the-Loop):** Every action that sends emails, creates invoices, or modifies records pauses for your review. Move the task file to `Approved/` to proceed or `Rejected/` to cancel.

---

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `ANTHROPIC_API_KEY` | ✅ | Claude API key |
| `GOOGLE_CLIENT_ID` | ✅ | Google OAuth client ID |
| `GOOGLE_CLIENT_SECRET` | ✅ | Google OAuth client secret |
| `VAULT_PATH` | ✅ | Path to your Obsidian vault folder |
| `ODOO_URL` | ✅ | Odoo URL (default: `http://localhost:8069`) |
| `ODOO_DB` | ✅ | Odoo database name |
| `ODOO_USER` | ✅ | Odoo login email |
| `ODOO_PASSWORD` | ✅ | Odoo password |
| `GMAIL_RATE_LIMIT_HOURLY` | ☑ | Max emails/hour (default: 20) |
| `GMAIL_RATE_LIMIT_DAILY` | ☑ | Max emails/day (default: 100) |
| `DRY_RUN` | ☑ | `true` = simulate without sending (default: false) |
