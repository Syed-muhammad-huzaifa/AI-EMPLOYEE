---
id: "0010"
title: Vault Reset and Company Handbook
stage: green
date: 2026-02-15
surface: agent
model: claude-sonnet-4-5-20250929
feature: 001-gmail-integration
branch: 001-gmail-integration
user: syedhuzaifa
command: "check my obsidian vault clear all the things like task related make them empty task like fresh vault and then write a company_handbook again assume as a fake company so write companyhanbook file like best so claude work best, write proper business goal file fix all the things"
labels: ["vault", "cleanup", "company-handbook", "business-goals", "dashboard", "fresh-start"]
links:
  spec: null
  ticket: null
  adr: null
  pr: null
files:
  - /mnt/c/MY_EMPLOYEE/Company_Handbook.md
  - /mnt/c/MY_EMPLOYEE/Business_Goals.md
  - /mnt/c/MY_EMPLOYEE/Dashboard.md
tests:
  - All 9 vault task folders verified empty after cleanup
  - Company_Handbook.md written (full company context for Claude)
  - Business_Goals.md written (monthly targets + KPIs + risk flags)
  - Dashboard.md reset to clean state
---

## Prompt

check my obsidian vault clear all the things like task related make them empty task like fresh vault and then write a company_handbook again assume as a fake company so write companyhanbook file like best so claude work best, write proper business goal file fix all the things

## Response snapshot

**Vault cleared:**
- Removed all files from: Needs_Action, In_Progress, Pending_Approval, Approved, Done (28 files), Failed (2), Rejected (8), Inbox (3 + 6 in _processed), Logs (18 files), Briefings (1), Plans (23), Temp (5), Accounting
- All 9 task folders now at 0 items

**Company_Handbook.md rewritten** — fake company: Nexus Digital Solutions (web dev + digital marketing agency, Lahore Pakistan, CEO Huzaifa Syed)
- 10 sections: company overview, mission/values, AI Employee operating instructions, email templates (5 templates), client tiers/workflow, payment terms, vault folder guide, tools, brand voice, legal/compliance
- Autonomy table: what Claude auto-executes vs what requires approval vs what is never autonomous
- Escalation rules: 7 conditions that require immediate CEO notification
- Task risk levels: low/medium/high defined

**Business_Goals.md rewritten** — comprehensive 2026 goals:
- Monthly revenue targets: $3,000 (Jan) → $8,500 (Dec) = $69,000 annual
- 12 financial KPIs, 6 client KPIs, 5 operational KPIs
- Quarterly goals Q1–Q4 with checkboxes
- Risk flag table: 8 conditions with RED/YELLOW/GREEN thresholds for Claude to use in briefings
- Services revenue breakdown by category
- 2026 milestones calendar

**Dashboard.md** — reset to clean state with 0 items, February targets shown

## Outcome

- ✅ Impact: Fresh vault ready for real business use; Claude now has complete company context
- 🧪 Tests: All 9 folders verified empty; all 3 files verified written
- 📁 Files: Company_Handbook.md, Business_Goals.md, Dashboard.md
- 🔁 Next prompts: Test end-to-end with a real email to see Claude apply company tone; schedule financial-health-check to run daily 8am; fill in actual Odoo revenue data to populate February actuals

## Evaluation notes (flywheel)

- The Company_Handbook is now a first-class AI context document — every Claude decision (tone, escalation, pricing) is grounded in it
- Business_Goals now has explicit risk thresholds Claude can evaluate against (e.g., total AR > $2,000 → trigger collections run)
- Dashboard reset means metrics will repopulate from real data once system is running
