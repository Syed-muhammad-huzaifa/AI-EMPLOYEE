# Hackathon-Context.md
Personal AI Employee Hackathon 0 – Building Autonomous FTEs (Full-Time Equivalent) in 2026

## Project Overview and Tagline
Your life and business on autopilot. Local-first, agent-driven, human-in-the-loop.  
This hackathon is about creating a proactive AI agent that acts as a "Digital FTE" – a full-time employee equivalent powered by Claude Code and Obsidian. It manages personal affairs (Gmail, WhatsApp, bank) and business operations (social media, payments, tasks, accounting) autonomously, with human oversight for sensitive actions.

## Core Objectives
- Build an autonomous system that runs 24/7 without constant user input.
- Focus on high-level reasoning, flexibility, and privacy (all data local).
- Transform AI from a reactive chatbot to a proactive partner (e.g., Monday Morning CEO Briefing for revenue audits and bottlenecks).
- Use Claude Code as the reasoning engine, Obsidian as the dashboard/memory, Python watchers for inputs, MCP servers for actions, and Ralph Wiggum loop for persistence.
- All AI functionality implemented as Agent Skills for reusability and consistency.

## Business Perspective and Value Proposition
Shift from software licenses to "headcount budgets." A Digital FTE is priced like a human employee but scales exponentially.

Human FTE vs Digital FTE Comparison Table:

| Feature              | Human FTE              | Digital FTE            |
|----------------------|------------------------|------------------------|
| Availability         | 40 hours/week          | 168 hours/week (24/7)  |
| Monthly Cost         | $4,000 – $8,000+       | $500 – $2,000          |
| Ramp-up Time         | 3–6 months             | Instant (via SKILL.md) |
| Consistency          | Variable (85–95%)      | Predictable (99%+)     |
| Scaling              | Linear (hire more)     | Exponential (duplicate)|
| Cost per Task        | ~$3–$6                 | ~$0.25–$0.50           |
| Annual Hours         | ~2,000                 | ~8,760                 |

Key Business Impact:
- 85–90% cost savings on tasks.
- Proactive features: Audit subscriptions, flag bottlenecks, suggest optimizations (e.g., "Cancel unused $200 software").
- Revenue focus: Auto-post on social for sales leads, track invoice payments.

## High-Level Architecture
Local-first design with privacy in mind. Components:
- **Brain**: Claude Code (reasoning + Agent Skills).
- **Memory/GUI**: Obsidian vault (Markdown files for state).
- **Senses**: Python watchers (monitor inputs, create /Needs_Action files).
- **Hands**: MCP servers (external actions like email/send or Odoo/create_invoice).
- **Loop**: Ralph Wiggum Stop Hook (autonomy until task complete).
- **Orchestrator**: Python script to coordinate watchers and trigger Claude.

Data Flow:
1. Watchers detect event → /Needs_Action/*.md file create.
2. Orchestrator detects → Ralph loop triggers Claude.
3. Claude reads vault (Handbook, Goals) → uses Agent Skills → creates Plan.md → calls MCP or approval file.
4. Human approves (if needed) → MCP executes.
5. Claude moves to /Done, logs action.

## Technical Guidelines Summary (Detailed in Separate Files)
- **MCP Servers**: Custom Node.js/Python servers for actions (e.g., email-mcp, odoo-mcp). Config in mcp.json. Always include dry-run mode.
- **Watchers**: Python scripts with BaseWatcher class. Run continuously via PM2.
- **Orchestrator**: Monitors folders, triggers loops, handles restarts (watchdog.py).
- **Retry Logic**: Exponential backoff for transient errors (e.g., network timeouts).
- **Edge Cases**: Handle API downtime, infinite loops, credential expiry, large file uploads (detailed in EdgeCases.md).
- **Security**: .env for secrets, audit logs, no auto-irreversible actions.

## Hackathon Tiers and Deliverables
Build incrementally:

**Bronze Tier (Foundation – 8–12 hours)**:
- Vault setup with core files (Dashboard.md, Company_Handbook.md).
- One watcher (e.g., filesystem).
- Claude vault read/write.
- Basic folders: /Needs_Action, /Plans, /Done.
- All as Agent Skills.

**Silver Tier (Functional – 20–30 hours)**:
- Multiple watchers (Gmail + WhatsApp + LinkedIn).
- Auto LinkedIn posts for sales.
- MCP server (e.g., email).
- Approval workflow.
- Scheduling (cron).

**Gold Tier (Autonomous – 40+ hours)**:
- Cross-domain (personal + business).
- Odoo Community setup + MCP integration (JSON-RPC APIs).
- FB/IG/X posts + summaries.
- Weekly audit + CEO Briefing.
- Ralph loop, error recovery, logging.
- Architecture docs + lessons learned.

**Platinum Tier (Always-On – 60+ hours)**:
- Cloud VM (Oracle free) for 24/7.
- Cloud/Local delegation (Git/Syncthing sync, no secrets).
- Claim-by-move rule.
- Full demo flow.

## Edge Cases Preview (Detailed in EdgeCases.md)
- Multiple tasks (10+): Sequential processing with priority sorting.
- API failures: Queue tasks, retry with backoff.
- Infinite loop: Max iterations in Ralph.
- Offline: Local queue, sync on reconnect.
- Security breach: Credential rotation, logs review.

## Prerequisites and Setup
- Software: Claude Code, Obsidian v1.10.6+, Python 3.13+, Node.js v24+, GitHub Desktop.
- Hardware: 8GB+ RAM, stable internet.
- Skills: CLI, APIs, no AI/ML needed.
- Checklist: Install software, create vault, test Claude --version, join Wednesday Zoom meetings.

## Key Resources
- Claude Code Docs: agentfactory.panaversity.org/docs/AI-Tool-Landscape/claude-code-features-and-workflows
- Odoo Docs: odoo.com/documentation/19.0
- YouTube Tutorials: Links from hackathon doc (e.g., Claude + Obsidian integration).

## Submission and Rules
- GitHub repo with README, demo video (5–10 min), tier declaration.
- All code original or attributed.
- Use Claude Code as primary engine.
- Submit via forms.gle/JR9T1SJq5rmQyGkGA

Last Updated: February 10, 2026  
This file serves as the central context for all Claude sessions. Always read this first.