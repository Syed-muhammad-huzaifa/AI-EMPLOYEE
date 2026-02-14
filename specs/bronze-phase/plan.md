# Implementation Plan: Bronze Phase - Core Infrastructure

**Branch**: `001-bronze-phase` | **Date**: 2026-02-10 | **Spec**: [specs/bronze-phase/spec.md](../specs/bronze-phase/spec.md)
**Input**: Feature specification from `/specs/bronze-phase/spec.md`

## Summary

Implement the foundational infrastructure for the Personal AI Employee system as defined in the Bronze Tier requirements. This includes integrating with the existing Obsidian vault at "C:\MY_EMPLOYEE", implementing a filesystem watcher using the BaseWatcher pattern, enabling Claude vault integration with proper context reading, establishing the orchestrator to monitor NEEDS_ACTION/ and trigger Claude, implementing the Agent Skills foundation, and creating the complete folder workflow with claim-by-move pattern.

All development will take place within the existing `hackathon-0` project initialized with uv.

## Technical Context

**Language/Version**: Python 3.13+, Claude Code
**Primary Dependencies**: watchdog, obsidian-api (or direct file manipulation), claude-code, psutil, python-dotenv
**Storage**: File-based (existing Obsidian vault at "C:\MY_EMPLOYEE")
**Testing**: pytest for unit tests, manual verification for integration
**Target Platform**: Windows/Linux/macOS (hackathon environment)
**Project Type**: Single project with modular components
**Performance Goals**: Watcher responds to file changes within 2 seconds, Claude vault operations complete within 5 seconds
**Constraints**: Local-first architecture, no external dependencies for core functionality, privacy-focused, must work with existing vault structure
**Scale/Scope**: Single-user personal AI employee, local vault storage

## Reference Examples

The implementation should follow patterns demonstrated in the example files located in `/context/Examples/`:

- **Base Watcher Pattern**: `/context/Examples/base-watcher.py` - Reference for BaseWatcher implementation
- **Filesystem Watcher**: `/context/Examples/filesystem-watcher.py` - Reference for filesystem monitoring implementation
- **Ralph Loop**: `/context/Examples/ralgph-loop.sh` - Reference for Ralph Wiggum loop implementation
- **Watchdog**: `/context/Examples/watchdog.py` - Reference for process monitoring and restart
- **MCP Configuration**: `/context/Examples/.mcp.json` - Reference for MCP server configuration
- **Gmail Watcher**: `/context/Examples/gmail-watcher.py` - Reference for email watcher implementation
- **WhatsApp Watcher**: `/context/Examples/whatsaap-watcher.py` - Reference for WhatsApp watcher implementation

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- ✅ Safety First: No irreversible actions without approval (not applicable at this stage)
- ✅ Privacy by Design: All data stays local in vault (core requirement)
- ✅ Transparency: All operations logged to LOGS/ (requirement FR-012)
- ✅ Modular Architecture: Agent Skills foundation (requirement FR-009)
- ✅ Human-in-the-Loop: Not required for core infrastructure setup
- ✅ Code Patterns: Follow BaseWatcher pattern (requirement FR-002)
- ✅ Watchers: Run continuously as daemons (requirement FR-011)
- ✅ Obsidian Integration: Core requirement for vault
- ✅ Process Health: Watcher should be resilient to errors
- ✅ Retry Logic: Implement exponential backoff (requirement FR-014)
- ✅ Claim-by-Move: Implement task ownership pattern (requirement FR-008)

## Security and Configuration

### Secrets Management
- All sensitive information (API keys, credentials, etc.) MUST be stored in `.env` file at the project root
- Use `python-dotenv` library to load environment variables securely
- `.env` file MUST be added to `.gitignore` to prevent committing secrets
- Provide a `.env.example` template with placeholder values for documentation

### Configuration Management
- Obsidian vault configuration MUST be stored in a dedicated config file: `hackathon-0/config/vault_config.json`
- Configuration file should include vault path, folder mappings, and other vault-specific settings
- Python module names SHOULD be contextually relevant to their function (e.g., `filesystem_watcher.py`, `vault_manager.py`, `orchestrator_controller.py`)

## Project Structure

### Documentation (this feature)

```text
hackathon-0/specs/bronze-phase/
├── plan.md              # This file (/sp.plan command output)
├── spec.md              # Feature specification
├── research.md          # Phase 0 output (/sp.plan command)
├── data-model.md        # Phase 1 output (/sp.plan command)
├── quickstart.md        # Phase 1 output (/sp.plan command)
├── contracts/           # Phase 1 output (/sp.plan command)
└── tasks.md             # Phase 2 output (/sp.tasks command - NOT created by /sp.plan)
```

### Source Code (hackathon-0 project root)

```text
hackathon-0/
├── pyproject.toml       # uv project configuration
├── .env                 # Environment variables (gitignored)
├── .env.example         # Environment variables template
├── config/
│   └── vault_config.json # Obsidian vault configuration
├── src/
│   ├── watchers/
│   │   ├── __init__.py
│   │   ├── base_watcher.py      # Base class for all watchers (BaseWatcher pattern)
│   │   └── filesystem_watcher.py # Bronze phase implementation
│   ├── vault/
│   │   ├── __init__.py
│   │   ├── manager.py           # Vault operations for C:\MY_EMPLOYEE
│   │   └── constants.py         # Vault folder paths (NEEDS_ACTION, LOGS, etc.)
│   ├── skills/
│   │   ├── __init__.py
│   │   └── base_skill.py        # Base skill implementation
│   ├── orchestrator/
│   │   ├── __init__.py
│   │   └── controller.py        # Folder monitoring and Claude triggering
│   ├── ralph/
│   │   ├── __init__.py
│   │   └── loop_manager.py      # Ralph Wiggum loop implementation
│   └── utils/
│       ├── __init__.py
│       ├── logger.py            # Logging utilities for LOGS/ folder
│       ├── config_loader.py     # Configuration loading utilities
│       ├── secrets_manager.py   # Secure secrets loading from .env
│       └── file_lock.py         # File locking for claim-by-move pattern
├── tests/
│   ├── unit/
│   │   ├── test_watchers/
│   │   ├── test_vault/
│   │   ├── test_skills/
│   │   ├── test_orchestrator/
│   │   └── test_ralph/
│   ├── integration/
│   │   └── test_bronze_flow.py
│   └── fixtures/
│       └── vault_structure/
└── docs/
    └── quickstart.md
```

**Structure Decision**: Single project structure within hackathon-0 with modular components organized by functionality. The existing Obsidian vault at C:\MY_EMPLOYEE is accessed by Claude and the system but not recreated.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| None identified | | |