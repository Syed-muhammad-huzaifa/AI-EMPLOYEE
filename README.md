# AI Employee 🤖

An autonomous business automation system that monitors your inbox, manages accounting, processes tasks, and handles invoicing — all with human-in-the-loop approval.

[![Python 3.13+](https://img.shields.io/badge/python-3.13+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![MCP](https://img.shields.io/badge/MCP-Enabled-green.svg)](https://modelcontextprotocol.io)

---

## What It Does

AI Employee is your autonomous business assistant that:

- **Monitors Gmail** — Classifies and routes emails automatically
- **Manages Odoo Accounting** — Creates invoices, tracks payments, generates reports
- **Automates Invoicing** — Email → Invoice → PDF → Send in ~30 seconds
- **Processes Tasks** — Executes tasks from your Obsidian vault via Claude
- **Weekly Audits** — Generates CEO briefings with financial insights
- **Human-in-the-Loop** — All sensitive actions require your approval

---

## Quick Start

```bash
# Clone the repository
git clone https://github.com/Syed-muhammad-huzaifa/AI-EMPLOYEE.git
cd AI-EMPLOYEE/Hackathon-0

# Install dependencies
pip install -e .

# Configure environment
cp .env.example .env
# Edit .env with your credentials

# Authenticate Gmail (one-time)
python scripts/authenticate_gmail.py

# Start the system
python main.py
```

For detailed setup instructions, see [Hackathon-0/README.md](Hackathon-0/README.md)

---

## Key Features

### 🔄 Automated Workflows
- Gmail monitoring and classification
- Invoice creation and PDF generation
- Payment tracking and reminders
- Weekly financial reporting

### 🛠️ MCP Integration
- **Gmail MCP**: 9 tools for email management
- **Odoo MCP**: 14 tools for accounting and invoicing

### 📊 Business Intelligence
- Real-time financial dashboards
- Overdue invoice tracking
- P&L reports and tax summaries
- Customer payment history

### 🔐 Security First
- Human-in-the-loop approval for all sensitive actions
- OAuth 2.0 for Gmail authentication
- Environment-based secrets management
- Audit trail for all operations

---

## Project Structure

```
AI-EMPLOYEE/
├── Hackathon-0/              # Main implementation
│   ├── src/                  # Core application modules
│   ├── mcp-servers/          # MCP servers (Gmail, Odoo)
│   ├── scripts/              # Utilities and demos
│   ├── tests/                # Unit and integration tests
│   └── docs/                 # Detailed documentation
│
├── specs/                    # Feature specifications
│   ├── 001-gmail-integration/
│   └── bronze-phase/
│
├── history/                  # Development history
│   ├── prompts/              # Prompt history records
│   └── adr/                  # Architecture decision records
│
├── context/                  # Project context and planning
└── .claude/                  # Claude Code skills
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

---

## Use Cases

### Invoice Automation
```
Email arrives: "Please send invoice for $500"
  ↓
AI creates invoice in Odoo
  ↓
Generates PDF
  ↓
Drafts email with attachment
  ↓
You approve → Email sent
```

### Collections Management
```
Weekly audit identifies overdue invoices
  ↓
AI drafts payment reminders
  ↓
You review and approve
  ↓
Reminders sent automatically
```

### Financial Reporting
```
Every Sunday at 9am
  ↓
AI pulls Odoo financial data
  ↓
Generates CEO briefing
  ↓
Saved to vault for review
```

---

## Technology Stack

- **Python 3.13+** — Core application
- **Claude API** — AI orchestration and task processing
- **MCP (Model Context Protocol)** — Tool integration
- **Odoo** — Accounting and invoicing
- **Gmail API** — Email management
- **Obsidian** — Task queue and knowledge base
- **PM2** — Production process management

---

## Documentation

- [Quick Start Guide](Hackathon-0/docs/quickstart.md)
- [Project Structure](Hackathon-0/docs/project-structure.md)
- [Odoo Tools Reference](Hackathon-0/docs/odoo-tools.md)
- [Invoice Workflow Guide](Hackathon-0/docs/invoice-guide.md)
- [Gold Tier Features](Hackathon-0/docs/gold-tier.md)

---

## Development

### Prerequisites
- Python 3.13+
- Docker Desktop (for Odoo)
- Google Cloud project with Gmail API enabled
- Anthropic API key

### Running Tests
```bash
# Unit tests
python -m pytest tests/unit/ -v

# Integration tests (requires Odoo running)
python -m pytest tests/integration/ -v
```

### Development Workflow
This project follows Spec-Driven Development (SDD):
1. Specifications in `specs/`
2. Implementation plans in `specs/*/plan.md`
3. Tasks in `specs/*/tasks.md`
4. Prompt history in `history/prompts/`

---

## Contributing

Contributions are welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Follow the SDD workflow
4. Submit a pull request

---

## License

MIT License - see [LICENSE](LICENSE) for details

---

## Acknowledgments

Built with:
- [Claude](https://claude.ai) by Anthropic
- [Model Context Protocol (MCP)](https://modelcontextprotocol.io)
- [Odoo](https://www.odoo.com)
- [Gmail API](https://developers.google.com/gmail/api)

---

## Support

For issues, questions, or feature requests, please open an issue on GitHub.

**Repository**: https://github.com/Syed-muhammad-huzaifa/AI-EMPLOYEE
