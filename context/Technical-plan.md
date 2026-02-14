# Technical-Plan.md
Personal AI Employee System – Final Technical Plan  
Hackathon: Building Autonomous FTEs (Full-Time Equivalent) in 2026

**Version:** 1.2  
**Last Updated:** February 10, 2026  
**Author:** Inovyn

## Executive Summary

This document describes a proactive, 24/7 autonomous Digital FTE built with:  
- **Claude Code** → reasoning engine  
- **Obsidian vault** → memory, dashboard & state  
- **Python watchers** → perception  
- **MCP servers** → action execution  
- **Ralph Wiggum loop** → task persistence & autonomy  
- **Human-in-the-loop** → safety for sensitive actions  

Goal: Achieve high reliability, privacy (local-first), auditability, and incremental development via tiers (Bronze → Platinum).

## System Architecture Overview

1. **Perception Layer (Watchers)**  
   Continuous Python daemons detecting events and creating .md files in `/Needs_Action/`.  
   Tech: watchdog, google-api-python-client, playwright  
   Examples: GmailWatcher, WhatsAppWatcher, FinanceWatcher, FilesystemWatcher  
   Reliability: PM2 / supervisord for daemonization

2. **Memory & GUI Layer (Obsidian Vault)**  
   Centralized Markdown-based state.  
   Folders: `/Needs_Action/`, `/Plans/`, `/In_Progress/`, `/Pending_Approval/`, `/Approved/`, `/Rejected/`, `/Done/`, `/Accounting/`, `/Briefings/`, `/Logs/`  
   Core files: `Dashboard.md`, `Company_Handbook.md`, `Business_Goals.md`

3. **Orchestration Layer**  
   `orchestrator.py` → folder monitoring & Claude trigger  
   `watchdog.py` → process health & auto-restart  
   Cron → scheduled tasks (e.g. weekly audit)

4. **Reasoning Layer (Claude Code)**  
   - Agent Skills (reusable, auto-loaded)  
   - Ralph Wiggum Loop (stop hook for multi-step completion)  
   - Reads Handbook + Goals + Plans before acting

5. **Action Layer (MCP Servers)**  
   Node.js / Python servers exposing safe functions  
   Examples: email-mcp, browser-mcp (Playwright), social-mcp, odoo-mcp (JSON-RPC)  
   Security: DRY_RUN env var, input validation

6. **Human-in-the-Loop**  
   File-based: Claude writes to `/Pending_Approval/` → human moves to `/Approved/` or `/Rejected/`

7. **Logging & Audit**  
   Append-only JSON in `/Logs/` → every action, decision, error

## Core Patterns

- Claim-by-Move (ownership)  
- Approval Workflow (file move trigger)  
- Dry-Run Mode  
- Exponential Backoff Retry  
- Graceful Degradation & Local Queuing  
- Task Completion: Done/ folder OR `<promise>TASK_COMPLETE</promise>`

## Implementation Phases & Success Criteria

**Bronze Tier (8–12 hours)**  
Objective: Core infrastructure  
Deliverables: Vault setup, filesystem watcher, Claude vault R/W, basic folders, foundational Agent Skills  
Success: Dummy task → Plan.md → Done/ + log

**Silver Tier (20–30 hours)**  
Objective: External integrations  
Deliverables: Gmail/WhatsApp watchers, LinkedIn auto-post, email-mcp, approval flow, cron scheduling  
Success: Email detected → draft → approval → send (dry-run)

**Gold Tier (40+ hours)**  
Objective: Full autonomy  
Deliverables: Odoo + MCP, FB/IG/X integration, weekly CEO Briefing, Ralph loop, error recovery, logging  
Success: WhatsApp invoice request → Odoo invoice → approval → email → Briefing generated

**Platinum Tier (60+ hours)**  
Objective: Production-grade always-on  
Deliverables: Cloud VM, Git/Syncthing sync (no secrets), cloud/local delegation, full demo  
Success: Offline draft → online approval → execution + sync

## Edge Cases & Failure Handling (Prioritized)

| #  | Scenario                              | Severity | Solution Summary                              | Key Implementation                  |
|----|---------------------------------------|----------|-----------------------------------------------|-------------------------------------|
| 1  | 10+ concurrent tasks                  | Medium   | Priority sort + batch (5–10/loop)             | YAML priority + prompt instruction  |
| 2  | API/network failure                   | High     | Backoff retry + local queue                   | retry_handler decorator             |
| 3  | Ralph loop infinite                   | High     | Max iterations + /Failed/ move                | Loop counter in script              |
| 4  | Offline / no internet                 | Medium   | Local queue + sync on reconnect               | /Retry_Queue/ folder                |
| 5  | Credential expiry                     | High     | Detect → alert file in Pending_Approval       | Auth error catch in watchers        |
| 6  | Large attachments / inputs            | Medium   | Truncate + manual-review flag                 | Size check in watcher               |
| 7  | Process crash / hang                  | High     | Auto-restart (PM2 + watchdog)                 | Health monitoring                   |
| 8  | Vault corruption / inconsistency      | High     | Git backups + integrity checks                | Git commit + hash validation        |
| 9  | External rate limiting                | Medium   | Adaptive queue + scheduling                   | Rate counter in MCP                 |
| 10 | Claude context overflow               | Medium   | Chunking + summarization                      | Prompt: "Summarize first..."        |
| 11 | Duplicate tasks                       | Low      | Unique ID + processed set                     | Watcher deduplication               |
| 12 | Human + AI concurrent edits           | Medium   | Atomic writes + file locking                  | Python file lock                    |
| 13 | Watcher startup failure               | High     | Validation + detailed logs                    | Startup checks                      |
| 14 | Claude partial / abandoned task       | Medium   | Checkpoints + timeout reset                   | Task status monitoring              |
| 15 | Resource exhaustion (disk/RAM)        | High     | Monitoring + auto-cleanup                     | psutil in watchdog                  |

## Security Framework

1. **Privacy & Storage**  
   Local-first + optional vault encryption  
   No secrets in vault/git

2. **Credentials**  
   .env only + rotation alerts  
   OAuth refresh where supported

3. **Authorization**  
   Human approval for sensitive actions  
   Least privilege + function whitelisting in MCP

4. **Input Validation**  
   Sanitize external inputs  
   No eval/exec on untrusted data

5. **Audit & Monitoring**  
   Immutable JSON logs  
   Weekly human review

6. **Network & Process**  
   HTTPS/TLS external  
   Firewall + isolated processes

## Auto-Approval Thresholds

| Category              | Auto-Approve                          | Always Require Approval                  |
|-----------------------|---------------------------------------|------------------------------------------|
| Email replies         | Known contacts, low-risk              | New contacts, bulk, >1MB attachments     |
| Payments              | Recurring < $50                       | New payees, >$100, unusual               |
| Social posts          | Scheduled business content            | Replies, DMs, personal accounts          |
| File ops              | Create/read inside vault              | Delete, move outside vault               |

## Conclusion & Next Steps

This plan delivers a secure, observable, and incrementally buildable autonomous AI employee.  
Next actions:
1. Finalize remaining speckit files (Handbook, Goals, etc.)
2. Start Bronze tier implementation
3. Test dummy end-to-end flow
4. Iterate based on Wednesday research meetings

This document serves as the single source of truth for architecture and implementation decisions.