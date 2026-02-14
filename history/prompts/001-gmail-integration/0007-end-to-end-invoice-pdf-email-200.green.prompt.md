---
id: "0007"
title: End-to-End Invoice PDF Email $200
stage: green
date: 2026-02-15
surface: agent
model: claude-sonnet-4-5-20250929
feature: 001-gmail-integration
branch: 001-gmail-integration
user: syedhuzaifa
command: "send_invoice_to_client.py"
labels: ["odoo","invoice","pdf","gmail","end-to-end","automation"]
links:
  spec: null
  ticket: null
  adr: null
  pr: null
files:
  - Hackathon-0/send_invoice_to_client.py
  - Hackathon-0/mcp-servers/odoo-mcp/odoo-mcp.py
  - Hackathon-0/INVOICE_PDF_EMAIL_GUIDE.md
  - Hackathon-0/GOLD_TIER_PDF_COMPLETE.md
  - Hackathon-0/INV_2026_00014.pdf
tests:
  - send_invoice_to_client.py (full end-to-end run — PASSED)
---

## Prompt

drop a task like client needed a invoice of 200$ and their email is hafizsyedhuzaifa5@gmail.com now test this end to end workflow end result must be i receive invoice in this email i mention now drop a task

## Response snapshot

Created task #1 "Invoice $200 end-to-end: Odoo → PDF → Email" and executed it fully:

1. Started Odoo Docker containers (Docker Desktop was stopped — launched via PowerShell)
2. Authenticated to Odoo (http://localhost:8069)
3. Created new customer: Hafiz Syed Huzaifa (ID 50) for hafizsyedhuzaifa5@gmail.com
4. Created and posted invoice INV/2026/00014 — $200.00 — due 2026-03-17
5. Downloaded PDF via Odoo HTTP report endpoint: INV_2026_00014.pdf (32.2 KB)
6. Sent email with PDF attachment via Gmail API (MIMEMultipart)
   → Gmail message ID: 19c5e4044b423985
   → Delivered to: hafizsyedhuzaifa5@gmail.com

## Outcome

- ✅ Impact: Real $200 invoice with PDF delivered to hafizsyedhuzaifa5@gmail.com in ~30 seconds end-to-end
- 🧪 Tests: send_invoice_to_client.py — all 5 steps PASSED
- 📁 Files: send_invoice_to_client.py created; odoo-mcp.py updated with get_invoice_pdf tool (14th tool)
- 🔁 Next prompts: Automate recurring invoices; add payment link in email; scheduler integration
- 🧠 Reflection: Gmail MCP send_email lacks attachment support — worked around by calling Gmail API directly with MIMEMultipart. Docker Desktop must be running for Odoo; added PowerShell launch step.

## Evaluation notes (flywheel)

- Failure modes observed: Docker not running (connection refused on port 8069); fixed by launching Docker Desktop via PowerShell and waiting for containers to boot
- Graders run and results (PASS/FAIL): Full workflow PASS — invoice created, PDF generated, email delivered
- Prompt variant (if applicable): none
- Next experiment: Add attachment support to Gmail MCP send_email tool so workflow can run entirely via MCP tools
