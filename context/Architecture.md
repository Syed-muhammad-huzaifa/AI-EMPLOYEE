# Architecture.md
Personal AI Employee – Full System Architecture  
Hackathon: Building Autonomous FTEs (Full-Time Equivalent) in 2026

## 1. Design Principles
- Local-first & privacy-centric (all sensitive data stays on device)
- Agent-driven with high-level reasoning (Claude Code as core brain)
- Human-in-the-loop for irreversible / sensitive actions
- Autonomous & proactive (Ralph Wiggum loop + watchers)
- Modular & reusable (everything implemented as Agent Skills)
- Observable & auditable (comprehensive logging + weekly CEO briefing)
- Graceful degradation & retry logic on failures

## 2. High-Level System Diagram (ASCII)
┌──────────────────────────────────────────────────────────────────────────────┐
│                           PERSONAL AI EMPLOYEE SYSTEM                        │
└──────────────────────────────────────────────────────────────────────────────┘
EXTERNAL WORLD                                      CLOUD (Platinum only)
┌───────────────┬───────────────┬───────────────┬───────────────┐     ┌───────────────┐
│     Gmail     │   WhatsApp    │   Bank APIs   │  Social Sites │     │   Odoo Cloud  │
│  (IMAP/API)   │   (Web)       │   (CSV/API)   │ (FB/IG/X/LinkedIn)│     │   (optional)  │
└───────┬───────┴───────┬───────┴───────┬───────┴───────────────┘     └───────┬───────┘
│               │               │                                     │
▼               ▼               ▼                                     ▼
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                           PERCEPTION LAYER (Watchers)                           │
│  Lightweight, always-on Python daemons (PM2 / supervisord recommended)          │
│  - GmailWatcher          - WhatsAppWatcher (Playwright persistent)              │
│  - FinanceWatcher        - FilesystemWatcher (watchdog)                         │
└───────────────────────────────────────┬─────────────────────────────────────────────┘
│
▼ creates .md files
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                           OBSIDIAN VAULT (Local State & Memory)                 │
│  Core files: Dashboard.md, Company_Handbook.md, Business_Goals.md               │
│  Folders:                                                                               │
│    • Needs_Action/     • Plans/          • Done/                                        │
│    • In_Progress/      • Pending_Approval/  • Approved/  • Rejected/                    │
│    • Accounting/       • Briefings/      • Logs/                                        │
└───────────────────────────────────────┬─────────────────────────────────────────────┘
│ read / write
▼
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                           ORCHESTRATION LAYER                                       │
│  • orchestrator.py (folder watcher + Ralph loop trigger)                            │
│  • watchdog.py (process health monitoring & auto-restart)                           │
│  • cron / Task Scheduler → weekly Sunday audit trigger                              │
└───────────────────────────────────────┬─────────────────────────────────────────────┘
│ triggers
▼
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                           REASONING LAYER (Claude Code)                             │
│  • Runs in vault directory (--cwd .)                                                │
│  • Agent Skills loaded from ~/.claude/skills/ (auto-invoked by description match)   │
│  • Ralph Wiggum Loop: Stop hook intercepts exit → re-injects prompt until complete  │
│  • Always reads: Company_Handbook.md + Business_Goals.md + relevant Plan.md         │
└───────────────────────────────┬───────────────────────────────┬─────────────────────┘
┌───────────────┘               └───────────────┐
▼                                               ▼
┌─────────────────────────────┐                   ┌─────────────────────────────┐
│   HUMAN-IN-THE-LOOP         │                   │      ACTION LAYER           │
│   (Obsidian-based)          │                   │   MCP Servers (local)       │
│   • Review Pending_Approval │                   │   • email-mcp               │
│   • Move file → Approved    │                   │   • browser-mcp (Playwright)│
│   • Move file → Rejected    │                   │   • social-mcp (FB/IG/X)    │
└─────────────────────────────┘                   │   • odoo-mcp (JSON-RPC)     │
└─────────────────────────────┘
│
▼
EXTERNAL ACTIONS
• Send email   • Post social media
• Create/update Odoo records
• Browser automation (payments, logins)

## 3. Key Component Responsibilities

| Layer/Component          | Primary Responsibility                                      | Tech Stack                     | Always-On? |
|--------------------------|---------------------------------------------------------------------|--------------------------------|------------|
| Watchers                 | Detect external events, create actionable .md files         | Python (watchdog, google-api, playwright) | Yes       |
| Orchestrator             | Monitor Needs_Action, trigger Claude loops, manage restarts | Python                         | Yes       |
| Claude Code + Skills     | High-level reasoning, planning, decision making             | Claude Code + Agent Skills     | On-demand |
| Ralph Wiggum Loop        | Ensure multi-step tasks complete (stop hook pattern)        | Custom bash / plugin           | During task|
| MCP Servers              | Execute concrete actions safely                             | Node.js / Python (FastMCP)     | On-demand / persistent |
| Human-in-the-Loop        | Safety gate for sensitive / irreversible actions            | File move in Obsidian          | Manual    |
| Logging & Audit          | Record every action for review                              | JSON logs in /Logs/            | Yes       |

## 4. Important Patterns & Mechanisms

- **Claim-by-Move** (multi-agent safety): First agent moves file from Needs_Action → In_Progress/<agent>/ → owns it
- **Approval Workflow**: Claude writes Pending_Approval/*.md → human moves to Approved/ → orchestrator triggers MCP
- **Dry-Run Mode**: All MCP servers respect DRY_RUN env var → log instead of execute
- **Retry Logic**: Exponential backoff (base 1s, max 60s, 3–5 attempts) on transient errors
- **Graceful Degradation**: API down → queue in local folder, process when back
- **Task Completion Detection**: File moved to Done/ OR Claude outputs <promise>TASK_COMPLETE</promise>

## 5. Tier-Specific Architecture Notes

- **Bronze**: Filesystem watcher only + manual Claude runs + basic skills
- **Silver**: Gmail/WhatsApp watchers + email-mcp + cron scheduling
- **Gold**: Odoo Community (localhost:8069) + odoo-mcp + multiple social MCPs + full Ralph loop + weekly audit
- **Platinum**: Oracle Cloud Free VM + Git/Syncthing vault sync (no secrets) + cloud owns drafts, local owns approvals

## 6. Security Boundaries

| Action Category       | Auto-Approve Threshold          | Always Require Approval                  |
|-----------------------|----------------------------------|------------------------------------------|
| Email replies         | Known contacts, low-risk        | New contacts, bulk, attachments >1MB     |
| Payments              | Recurring < $50                 | All new payees, >$100, unusual amounts   |
| Social media posts    | Scheduled business content      | Replies, DMs, personal accounts          |
| File operations       | Create/read inside vault        | Delete, move outside vault               |

Last Updated: February 10, 2026  
This document is the canonical architecture reference for the entire project.