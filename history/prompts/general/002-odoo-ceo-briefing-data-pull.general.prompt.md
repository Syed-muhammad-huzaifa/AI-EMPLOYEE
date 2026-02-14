---
id: 002
title: Odoo CEO Briefing Data Pull
stage: general
date: 2026-02-15
surface: agent
model: claude-sonnet-4-5-20250929
feature: none
branch: 001-gmail-integration
user: syedhuzaifa
command: "get_financial_summary(days=30), get_customers(limit=10), get_overdue_invoices(min_days_overdue=1)"
labels: ["odoo","financial","ceo-briefing","read-only","data-collection"]
links:
  spec: null
  ticket: null
  adr: null
  pr: null
files:
  - Hackathon-0/mcp-servers/odoo-mcp/odoo-mcp.py
tests:
  - none
---

## Prompt

You need to call the Odoo MCP tool `get_financial_summary` with `days=30`, then call `get_customers` with `limit=10`, then call `get_overdue_invoices` with `min_days_overdue=1`.

Return ALL raw data from each tool call in your response so I can use it to generate a CEO briefing. Do not summarize — include every field returned.

If any tool fails, note the error clearly and return whatever partial data you can get.

This is read-only data collection only.

## Response snapshot

All three Odoo tool calls succeeded. The Odoo MCP server is not a registered MCP tool in this Claude Code session; the tools were executed by invoking the OdooClient logic directly against the live Odoo instance at http://localhost:8069.

- get_financial_summary(days=30): revenue=309365.0 PKR, expenses=2915.1 PKR, profit=306449.9 PKR, 14 invoices, 8 customers
- get_customers(limit=10): 8 customers returned (total customer base = 8)
- get_overdue_invoices(min_days_overdue=1): 4 overdue invoices, all for Acme Corporation, totalling 129,897.5 PKR outstanding

## Outcome

- Impact: Read-only financial data collected from live Odoo instance for CEO briefing generation
- Tests: none (read-only data retrieval)
- Files: Hackathon-0/mcp-servers/odoo-mcp/odoo-mcp.py (inspected, not modified)
- Next prompts: Generate CEO briefing document from raw data
- Reflection: Odoo MCP tools are defined in the server script but are not registered in the active Claude Code MCP session — direct Python invocation was used as the correct fallback

## Evaluation notes (flywheel)

- Failure modes observed: Odoo MCP server not available as a registered tool in session; resolved by direct invocation of OdooClient logic
- Graders run and results (PASS/FAIL): All three tool calls PASS
- Prompt variant (if applicable): none
- Next experiment: Register odoo MCP server in .claude/mcp.json for the project root to make tools natively callable in future sessions
