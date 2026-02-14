# Silver Tier Setup Guide

## ✅ Silver Tier Complete

All Silver tier requirements have been implemented:

1. ✅ **Multiple Watchers**: Gmail, Filesystem, WhatsApp (Playwright), LinkedIn, Twitter, Facebook
2. ✅ **LinkedIn Auto-posting**: Scheduler + HITL approval workflow
3. ✅ **Claude Planning Loop**: Creates Plan.md files via task-planner skill
4. ✅ **MCP Server**: Gmail MCP for email sending
5. ✅ **HITL Workflow**: /Pending_Approval/ → /Approved/ → execution
6. ✅ **Scheduling**: JobScheduler with cron-style expressions
7. ✅ **Agent Skills**: task-planner + process-needs-action

---

## Quick Start

### 1. First-Time Social Media Login

Each platform needs a one-time login to save the session:

```bash
# WhatsApp (scan QR code with your phone)
python -m src.watchers.whatsapp_watcher --login

# LinkedIn
python -m src.social.linkedin --login

# Twitter/X
python -m src.social.twitter --login

# Facebook
python -m src.social.facebook --login
```

After login, sessions are saved in `config/sessions/<platform>/` and future runs are headless.

### 2. Configure Environment Variables

Add to `.env`:

```bash
# Vault path
VAULT_PATH=/mnt/c/MY_EMPLOYEE

# LinkedIn (optional - for message monitoring + posting)
LINKEDIN_EMAIL=your@email.com
LINKEDIN_PASSWORD=yourpassword

# Twitter/X (optional)
TWITTER_EMAIL=your@email.com
TWITTER_PASSWORD=yourpassword
TWITTER_USERNAME=yourhandle

# Facebook (optional)
FACEBOOK_EMAIL=your@email.com
FACEBOOK_PASSWORD=yourpassword
```

### 3. Start the System

```bash
# Start with PM2 (recommended)
pm2 restart ai-employee

# Or run directly
python main.py --mode both --vault-path /mnt/c/MY_EMPLOYEE
```

### 4. Stop/Restart

```bash
pm2 stop ai-employee      # Stop
pm2 restart ai-employee   # Restart
pm2 logs ai-employee      # View logs
pm2 status                # Check status
```

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    SILVER TIER SYSTEM                        │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                    WATCHERS (Perception)                     │
├─────────────────────────────────────────────────────────────┤
│  Gmail Watcher          → monitors Gmail (every 120s)       │
│  Filesystem Watcher     → monitors Inbox/ (every 10s)       │
│  WhatsApp Watcher       → Playwright Web (every 30s)        │
│  LinkedIn Watcher       → via Scheduler (every 30min)       │
│  Twitter Watcher        → via Scheduler (optional)          │
│  Facebook Watcher       → via Scheduler (optional)          │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                  VAULT (Obsidian Memory)                     │
├─────────────────────────────────────────────────────────────┤
│  /Needs_Action/     ← Watchers write here                   │
│  /In_Progress/      ← Orchestrator claims tasks             │
│  /Plans/            ← task-planner creates plans            │
│  /Pending_Approval/ ← process-needs-action writes drafts    │
│  /Approved/         ← Human moves files here                │
│  /Done/             ← Completed tasks                        │
│  /Logs/             ← Audit trail                           │
│  /Briefings/        ← Monday CEO briefings                  │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│              ORCHESTRATOR (Claude Code Loop)                 │
├─────────────────────────────────────────────────────────────┤
│  1. Scan /Needs_Action/ (every 10s)                         │
│  2. Claim task → move to /In_Progress/orchestrator/         │
│  3. Invoke task-planner skill → creates /Plans/<task>.md    │
│  4. Invoke process-needs-action skill → executes plan       │
│  5. HITL: writes to /Pending_Approval/ for sensitive actions│
│  6. Move task to /Done/ when complete                       │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│            APPROVED SENDER (Action Executor)                 │
├─────────────────────────────────────────────────────────────┤
│  Polls /Approved/ (every 15s)                               │
│  Routes by action type:                                      │
│    - send_email       → Gmail API                           │
│    - send_whatsapp    → Playwright WhatsApp Web             │
│    - post_linkedin    → Playwright LinkedIn                 │
│    - post_twitter     → Playwright Twitter/X                │
│    - post_facebook    → Playwright Facebook                 │
│  Moves file to /Done/ after execution                       │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│              JOB SCHEDULER (Periodic Tasks)                  │
├─────────────────────────────────────────────────────────────┤
│  daily_briefing     → Monday 8am CEO briefing               │
│  linkedin_check     → Every 30min message check             │
│  linkedin_post      → Monday 10am post suggestion           │
└─────────────────────────────────────────────────────────────┘
```

---

## Workflow Examples

### Example 1: WhatsApp Lead Inquiry

1. **Trigger**: Client sends WhatsApp: "Hi, what's your pricing for a website?"
2. **WhatsApp Watcher** detects keyword "pricing", creates `/Needs_Action/WA_client_20260213.md`
3. **Orchestrator** claims task, invokes `task-planner` → creates `/Plans/WA_client_20260213.md`
4. **process-needs-action** skill executes plan, drafts reply, writes to `/Pending_Approval/WA_client_20260213.md`
5. **Human** reviews draft in Obsidian, moves to `/Approved/`
6. **ApprovedEmailSender** detects approval, sends via Playwright WhatsApp Web
7. Task moved to `/Done/`

### Example 2: LinkedIn Business Post

1. **Trigger**: Monday 10am, JobScheduler creates `/Needs_Action/LINKEDIN_POST_20260217.md`
2. **Orchestrator** claims task, invokes `task-planner`
3. **process-needs-action** reads recent `/Done/` tasks, drafts LinkedIn post about completed projects
4. Draft written to `/Pending_Approval/` with `action: post_linkedin`
5. **Human** reviews, edits if needed, moves to `/Approved/`
6. **ApprovedEmailSender** posts to LinkedIn via Playwright
7. Post published, task moved to `/Done/`

### Example 3: Monday Morning CEO Briefing

1. **Trigger**: Monday 8am, JobScheduler creates `/Needs_Action/BRIEFING_20260217.md`
2. **Orchestrator** claims task
3. **Claude** reads:
   - `Business_Goals.md` for targets
   - `/Done/` folder for completed tasks
   - `/Logs/` for activity patterns
4. Generates `/Briefings/2026-02-17_Monday_Briefing.md` with:
   - Revenue summary
   - Completed tasks
   - Bottlenecks identified
   - Proactive suggestions (e.g., "Cancel unused subscription")
5. Task moved to `/Done/`

---

## File Structure

```
Hackathon-0/
├── src/
│   ├── watchers/
│   │   ├── base_watcher.py
│   │   ├── gmail_watcher.py
│   │   ├── filesystem_watcher.py
│   │   ├── whatsapp_watcher.py          ← NEW (Playwright)
│   │   └── approved_email_sender.py     ← UPDATED (social posts)
│   ├── social/                           ← NEW
│   │   ├── browser_manager.py           ← Playwright session manager
│   │   ├── linkedin.py                  ← LinkedIn watcher + poster
│   │   ├── twitter.py                   ← Twitter watcher + poster
│   │   └── facebook.py                  ← Facebook watcher + poster
│   ├── scheduler/                        ← NEW
│   │   └── job_scheduler.py             ← Cron-style scheduler
│   ├── orchestrator/
│   │   └── controller.py                ← UPDATED (social actions)
│   └── ralph/
│       └── loop_manager.py
├── config/
│   └── sessions/                         ← NEW (Playwright sessions)
│       ├── whatsapp/
│       ├── linkedin/
│       ├── twitter/
│       └── facebook/
├── .claude/
│   └── skills/
│       ├── task-planner/
│       └── process-needs-action/
├── main.py                               ← UPDATED (scheduler integration)
├── start.sh
└── ecosystem.config.js
```

---

## Troubleshooting

### WhatsApp QR Code Not Appearing

```bash
# Run with headed browser
python -m src.watchers.whatsapp_watcher --login
```

Wait for QR code, scan with phone, press Enter when chats load.

### LinkedIn/Twitter Login Fails

- Check credentials in `.env`
- Some platforms require 2FA — run `--login` manually to handle
- Sessions expire after ~30 days, re-run `--login`

### Scheduler Not Running

```bash
# Check PM2 logs
pm2 logs ai-employee | grep Scheduler

# Verify scheduler is enabled
python -c "from src.scheduler.job_scheduler import JobScheduler; print('OK')"
```

### Social Posts Not Executing

1. Check `/Approved/` folder — file should have correct `action:` field
2. Check PM2 logs: `pm2 logs ai-employee | grep -i linkedin`
3. Verify Playwright session exists: `ls config/sessions/linkedin/Default`

---

## Next Steps (Gold Tier)

To reach Gold tier, add:

1. **Odoo Integration**: Self-hosted accounting system + MCP server
2. **Instagram Integration**: Post scheduling + story management
3. **Weekly Business Audit**: Automated financial analysis
4. **Error Recovery**: Graceful degradation + retry logic
5. **Comprehensive Logging**: Full audit trail with retention policy

---

## Security Notes

- **Sessions**: Playwright sessions stored in `config/sessions/` — DO NOT commit to git
- **Credentials**: All passwords in `.env` — add to `.gitignore`
- **HITL**: All outbound actions require human approval via `/Approved/` folder
- **Dry Run**: Use `--dry-run` flag for testing without real sends/posts

---

## Support

- **Hackathon Doc**: `/home/syedhuzaifa/AI-EMPLOYEE/context/hackathon_full_doc.md`
- **Wednesday Meetings**: Zoom link in hackathon doc
- **GitHub Issues**: Report bugs at hackathon repo

---

**Status**: ✅ Silver Tier Complete
**Date**: 2026-02-13
**System**: AI Employee v0.2 (Silver)
