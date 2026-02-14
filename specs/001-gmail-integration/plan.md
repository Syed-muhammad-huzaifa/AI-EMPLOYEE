# Implementation Plan: Gmail Integration for AI Employee

**Branch**: `001-gmail-integration` | **Date**: 2026-02-12 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/001-gmail-integration/spec.md`

**Note**: This template is filled in by the `/sp.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

This feature extends the existing Bronze phase system in `Hackathon-0/` with Gmail integration capabilities. The implementation adds ONLY 2 new files to the existing infrastructure:

1. **Gmail Watcher** (`Hackathon-0/src/watchers/gmail_watcher.py`): Extends the existing `BaseWatcher` class to monitor Gmail inbox, classify emails as actionable/non-actionable (filtering sponsored emails, newsletters, platform notifications), and create action files in `Needs_Action/` for actionable emails only.

2. **Email MCP Server** (`Hackathon-0/email-mcp/email-mcp.py`): Standalone MCP server providing a `send_email` tool for Claude to send emails via Gmail API after human approval.

**Key Design Principle**: Leverage all existing Bronze phase infrastructure (BaseWatcher, VaultManager, secrets_manager, logging) - no new utilities or helpers needed. Gmail credentials (GMAIL_CLIENT_ID, GMAIL_CLIENT_SECRET) are already added to `Hackathon-0/.env`.

## Technical Context

**Existing Infrastructure (Bronze Phase - Hackathon-0/)**:
- BaseWatcher class with check_for_updates(), create_action_file(), run() methods
- VaultManager for vault operations and logging
- secrets_manager.load_secrets() for .env credential loading
- Logging utilities and error handling
- Obsidian vault with Needs_Action/ folder structure

**New Components (Minimal Extension)**:
- **Language/Version**: Python 3.13+ (same as Bronze phase)
- **Primary Dependencies**: google-auth, google-api-python-client (NEW), python-dotenv (EXISTING)
- **Storage**: File-based using existing VaultManager (Needs_Action/, Approved/, Done/, Logs/); state persistence: Hackathon-0/config/gmail_watcher_state.json
- **Testing**: pytest (existing Bronze phase test infrastructure)
- **Target Platform**: Linux server with PM2 daemon management (existing Bronze phase setup)
- **Project Type**: Extension to existing single project (Bronze phase)
- **Performance Goals**: Email detection within 5 minutes, 99% send success, 95% classification accuracy
- **Constraints**: Gmail API rate limiting (20 emails/hour, 100 API calls/day), <2% false negative rate
- **Scale/Scope**: Handle 50+ emails/day, single Gmail account, 2-minute check intervals

**Implementation Approach**:
- gmail_watcher.py extends BaseWatcher (same pattern as filesystem_watcher.py)
- email-mcp.py is standalone MCP server (no dependencies on watcher)
- All email classification logic embedded in gmail_watcher.py (no separate utility files)
- OAuth2 token management embedded in email-mcp.py (no separate credential loader)
- Reuse existing VaultManager, secrets_manager, logging from Bronze phase

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Privacy & Security (§2, §5)
- ✅ **PASS**: OAuth2 credentials (GMAIL_CLIENT_ID, GMAIL_CLIENT_SECRET) loaded from .env file, never hardcoded
- ✅ **PASS**: credentials/gmail_token.json gitignored, no secrets in version control
- ✅ **PASS**: Email content logged as snippets only (200 chars max), full bodies not persisted
- ✅ **PASS**: All API calls use HTTPS encryption

### Human-in-the-Loop (§2, §5)
- ✅ **PASS**: Email sending requires approval workflow (Pending_Approval → Approved → send)
- ✅ **PASS**: New contacts always require approval per safety matrix (§5, table row 1)
- ✅ **PASS**: Auto-approve only for known contacts with low-risk content
- ✅ **PASS**: Classification defaults to "actionable" when uncertain (conservative approach)

### Modularity & Reusability (§2, §4)
- ✅ **PASS**: Watcher extends BaseWatcher class with standard methods (check_for_updates, create_action_file, run)
- ✅ **PASS**: MCP server follows MCP protocol specification
- ✅ **PASS**: Respects DRY_RUN environment variable for testing
- ✅ **PASS**: Rate limiting implemented (20 emails/hour, 100 API calls/day)

### Observability & Auditability (§2, §3)
- ✅ **PASS**: All detection and sending activities logged to /Logs/YYYY-MM-DD.md with timestamps
- ✅ **PASS**: Email classification decisions logged with reasoning
- ✅ **PASS**: Action files created in /Needs_Action/ with metadata
- ✅ **PASS**: State persistence in config/gmail_watcher_state.json for restart recovery

### Error Handling & Graceful Degradation (§2, §4, §7)
- ✅ **PASS**: Exponential backoff retry logic (1s, 2s, 4s, 8s, max 60s) for transient failures
- ✅ **PASS**: OAuth2 token auto-refresh with fallback to human intervention
- ✅ **PASS**: Network failures handled with retry loop, no duplicate action files
- ✅ **PASS**: Rate limit exceeded triggers queuing and retry after window expires
- ✅ **PASS**: Alert files created in /Needs_Action/ for critical errors

### Folder Organization (§3)
- ✅ **PASS**: Uses standardized folders: /Needs_Action/, /Pending_Approval/, /Approved/, /Done/, /Logs/
- ✅ **PASS**: Claim-by-move pattern for task ownership
- ✅ **PASS**: Company_Handbook.md used for client context and classification rules

**Constitution Compliance**: ✅ ALL GATES PASSED - No violations detected

**Post-Phase 1 Re-evaluation** (after design artifacts created):
- ✅ **Privacy**: data-model.md confirms email bodies stored as snippets only (200 chars), credentials in gitignored files
- ✅ **HITL**: quickstart.md documents approval workflow, contracts/mcp-server.json enforces validation before send
- ✅ **Modularity**: Project structure shows BaseWatcher extension, MCP protocol compliance, reusable utilities
- ✅ **Observability**: data-model.md defines comprehensive logging schema, classification stats tracking
- ✅ **Error Handling**: research.md documents exponential backoff, token refresh, rate limiting with token bucket
- ✅ **Folder Organization**: Project structure confirms standardized folders, claim-by-move pattern

**Final Verdict**: ✅ Design maintains full constitution compliance. No new violations introduced during Phase 1.

## Project Structure

### Documentation (this feature)

```text
specs/001-gmail-integration/
├── plan.md              # This file (/sp.plan command output)
├── research.md          # Phase 0 output (/sp.plan command)
├── data-model.md        # Phase 1 output (/sp.plan command)
├── quickstart.md        # Phase 1 output (/sp.plan command)
├── contracts/           # Phase 1 output (/sp.plan command)
│   └── mcp-server.json  # MCP server tool schema
└── tasks.md             # Phase 2 output (/sp.tasks command - NOT created by /sp.plan)
```

### Source Code (Hackathon-0 Bronze Phase - Extending Existing System)

**IMPORTANT**: This feature extends the existing Bronze phase in `Hackathon-0/`. We are adding ONLY 2 new files to the existing structure.

```text
Hackathon-0/
├── .env                              # EXISTING - Gmail credentials already added
├── src/
│   ├── watchers/
│   │   ├── base_watcher.py          # EXISTING - Base class for all watchers
│   │   ├── filesystem_watcher.py    # EXISTING - Bronze phase watcher
│   │   └── gmail_watcher.py         # NEW - Gmail monitoring daemon (extends BaseWatcher)
│   ├── vault/
│   │   └── manager.py               # EXISTING - VaultManager for vault operations
│   └── utils/
│       ├── secrets_manager.py       # EXISTING - Load secrets from .env
│       └── logger.py                # EXISTING - Logging utilities
├── email-mcp/                        # NEW FOLDER - MCP server for email sending
│   └── email-mcp.py                 # NEW - MCP server with send_email tool
└── config/
    └── gmail_watcher_state.json     # NEW - Created at runtime by watcher
```

**Structure Decision**: Minimal extension to existing Bronze phase. We add:
1. **ONE watcher file**: `Hackathon-0/src/watchers/gmail_watcher.py` that extends existing `BaseWatcher` class
2. **ONE MCP folder**: `Hackathon-0/email-mcp/` with `email-mcp.py` implementing the send_email tool

The watcher will use existing infrastructure:
- `BaseWatcher` class for watcher pattern
- `VaultManager` for creating action files in `Needs_Action/`
- `secrets_manager.load_secrets()` to load Gmail credentials from `.env`
- Existing logging utilities

No new utilities or helpers needed - everything already exists in Bronze phase.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

**Status**: N/A - No constitution violations detected. All gates passed in Constitution Check section above.
