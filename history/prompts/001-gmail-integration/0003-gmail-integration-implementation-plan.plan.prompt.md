---
id: 0003
title: gmail-integration-implementation-plan
stage: plan
date: 2026-02-12
surface: agent
model: claude-sonnet-4-5
feature: 001-gmail-integration
branch: 001-gmail-integration
user: syedhuzaifa
command: /sp.plan
labels: ["gmail", "implementation-plan", "architecture", "design", "phase-0", "phase-1"]
links:
  spec: ../spec.md
  ticket: null
  adr: null
  pr: null
files:
  - specs/001-gmail-integration/plan.md
  - specs/001-gmail-integration/research.md
  - specs/001-gmail-integration/data-model.md
  - specs/001-gmail-integration/contracts/mcp-server.json
  - specs/001-gmail-integration/quickstart.md
  - CLAUDE.md
tests:
  - N/A (planning phase)
---

## Prompt

/sp.plan

## Response snapshot

Completed full implementation planning workflow for Gmail integration feature (Phases 0-1):

**Phase 0: Research & Technical Decisions**

Created `research.md` documenting 6 key technical decisions:

1. **Gmail API OAuth2 Authentication**: Chose OAuth2 with offline access and automatic token refresh using google-api-python-client. Rejected service accounts (requires domain-wide delegation) and manual refresh (adds complexity).

2. **Email Classification Algorithm**: Chose rule-based three-tier filtering (domain patterns → keywords → handbook lookup). Deterministic, explainable, no ML training required. Filters noreply@, notifications@, promotional keywords, checks Company_Handbook.md for known clients.

3. **MCP Server Implementation**: Chose MCP SDK for Python with JSON-RPC protocol. Tool-based architecture allows Claude to discover send_email capability. Rejected REST API (network complexity) and gRPC (overkill).

4. **Python Daemon Management**: Chose PM2 for process management with graceful shutdown and state persistence. Provides auto-restart, log rotation, cross-platform support. Rejected systemd (Linux-only) and Docker (overkill).

5. **Rate Limiting Strategy**: Chose token bucket algorithm with 20/hour and 100/day limits. Allows burst traffic while enforcing average rate. Prevents Gmail API quota errors.

6. **State Persistence**: Chose JSON file with atomic writes and file locking. Simple, human-readable, crash-safe. Rejected SQLite (overkill) and pickle (not human-readable).

**Phase 1: Design & Contracts**

Created `data-model.md` with 4 entities:
- **EmailMessage**: 10 attributes including classification and classification_reason
- **EmailDraft**: 9 attributes with approval workflow states
- **WatcherState**: Tracks progress with classification stats
- **MCPSendRequest**: 9 attributes for send action tracking

Created `contracts/mcp-server.json`:
- MCP tool schema for send_email with input/output validation
- 6 error codes (INVALID_EMAIL, RATE_LIMIT_EXCEEDED, etc.)
- Rate limits: 20/hour, 100/day
- 4 usage examples including dry-run and error cases
- 5 contract tests for validation

Created `quickstart.md`:
- 9-step setup guide (Google Cloud, .env config, OAuth2 auth, testing)
- Troubleshooting section for common issues
- Monitoring and maintenance procedures
- Reference commands for watcher management

**Technical Context Filled**:
- Language: Python 3.13+
- Dependencies: google-auth, google-api-python-client, MCP SDK, python-dotenv
- Storage: File-based (Obsidian vault + JSON state)
- Testing: pytest with unit/integration/contract tests
- Performance: 5min detection, 99% send success, 95% classification accuracy

**Constitution Check**: ✅ ALL GATES PASSED
- Privacy: Credentials in .env, email snippets only
- HITL: Approval workflow enforced
- Modularity: BaseWatcher extension, MCP protocol
- Observability: Comprehensive logging
- Error Handling: Exponential backoff, token refresh
- Folder Organization: Standardized folders

**Project Structure Defined**:
- Single project structure (watcher + MCP server)
- Source: src/watchers/, mcp_servers/gmail/, src/utils/
- Tests: unit/, integration/, contract/
- Config: config/, credentials/ (gitignored)

**Agent Context Updated**: CLAUDE.md updated with Python 3.13+, google-auth, MCP SDK, file-based storage

## Outcome

- ✅ Impact: Created comprehensive implementation plan with research decisions, data model, API contracts, and quickstart guide for Gmail integration feature
- 🧪 Tests: N/A (planning phase - test strategy defined in data-model.md and contracts/mcp-server.json)
- 📁 Files: Created plan.md, research.md (6 decisions), data-model.md (4 entities), contracts/mcp-server.json (MCP schema), quickstart.md (9-step guide), updated CLAUDE.md
- 🔁 Next prompts: `/sp.tasks` to generate actionable task list from plan, or `/sp.adr` if architectural decisions need documentation
- 🧠 Reflection: Planning phase successfully completed with all constitution gates passed. Research phase resolved all technical unknowns (OAuth2, classification, MCP, daemon management, rate limiting, state persistence). Design phase produced concrete data model with validation rules, MCP contract with error handling, and practical quickstart guide. Ready for task generation and implementation.

## Evaluation notes (flywheel)

- Failure modes observed: None - planning workflow completed successfully through Phase 0 and Phase 1
- Graders run and results (PASS/FAIL): Constitution Check PASSED (all gates), Technical Context COMPLETE (no NEEDS CLARIFICATION markers), Design Artifacts COMPLETE (research.md, data-model.md, contracts/, quickstart.md)
- Prompt variant (if applicable): N/A
- Next experiment (smallest change to try): N/A
