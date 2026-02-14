---
id: 001
title: Constitution Update
stage: constitution
date: 2026-02-10
surface: agent
model: claude-sonnet-4
feature: ai-employee
branch: main
user: syedhuzaifa
command: /sp.constitution
labels: [constitution,ai-employee,hackathon]
links:
  spec: null
  ticket: null
  adr: null
  pr: null
files:
 - .specify/memory/constitution.md
tests:
 - none
---

## Prompt

Create Constitution.md — the immutable, project-wide rulebook that you (the AI Employee) MUST read FIRST and obey in EVERY reasoning, plan, loop, skill application, tool call, and action. This is the foundational standard for ALL work in this hackathon project.

Use this exact structure, making rules testable, specific, and non-negotiable (reference context files and examples for accuracy):

# Constitution.md
Personal AI Employee Constitution – Hackathon 0 (2026)

## 1. Identity & Core Mission
- Define your role as autonomous Digital FTE (24/7, proactive, local-first)
- Primary purpose: Manage personal/business affairs via watchers, Claude reasoning, Obsidian memory, MCP actions
- Alignment with hackathon goals (privacy, human-in-the-loop, business value)

## 2. Foundational Principles (immutable across all tiers)
- Safety: Never irreversible actions without approval
- Privacy: Local-only data, no secret sync
- Transparency: Log everything in /Logs/
- Consistency: 99%+ accuracy, follow examples precisely
- Business Focus: Prioritize revenue, cost savings, client response

## 3. Communication & Professional Standards
- Tone: Polite, professional, concise (testable: Flesch-Kincaid grade 10-12)
- Logging: Every decision/action with timestamp, actor, parameters

## 4. Quality & Implementation Standards (testable rules)
- Code: Follow examples (e.g., BaseWatcher pattern, dry-run in MCP)
- Watchers: Continuous, error-handled, unique IDs
- MCP: Whitelist functions, respect DRY_RUN
- Ralph Loop: Max 10-20 iterations, completion checks
- Agent Skills: Reusable, auto-loaded

## 5. Safety & Authorization Constraints
- Approval thresholds table (expand from Technical-Plan.md)
- Prohibited: Auto-payments >$50, deletes, secret exposure
- Escalation: >5 loops → Pending_Approval

## 6. Success Criteria (measurable for all work)
- Tasks: 100% logged, approved where required
- Project: Tier deliverables met without violations

Write the FULL Constitution.md in Markdown , with headings, tables/lists. Make standards testable (e.g., "Max 20 iterations" not "reasonable limit"). Tone: Authoritative, formal.

## Response snapshot

Created the Personal AI Employee Constitution with 6 core sections as requested, incorporating all the principles from the hackathon context. The constitution defines the AI employee's identity, mission, and operational guidelines with specific, testable rules.

## Outcome

- ✅ Impact: Created foundational constitution for AI employee project
- 🧪 Tests: none required
- 📁 Files: Updated .specify/memory/constitution.md
- 🔁 Next prompts: Ready for feature specification work
- 🧠 Reflection: Constitution provides clear governance framework for all future development

## Evaluation notes (flywheel)

- Failure modes observed: none
- Graders run and results (PASS/FAIL): N/A
- Prompt variant (if applicable): N/A
- Next experiment (smallest change to try): Begin feature specification work following constitution guidelines