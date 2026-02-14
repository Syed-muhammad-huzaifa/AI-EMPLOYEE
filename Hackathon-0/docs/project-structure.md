# Personal AI Employee - Bronze Phase Documentation

## Project Overview

This project implements the Bronze Phase of the Personal AI Employee system, which acts as a 24/7 autonomous digital employee managing personal and business affairs. The system uses Claude Code as the reasoning engine, Obsidian as the memory/GUI, Python watchers for perception, MCP servers for actions, and the Ralph Wiggum loop for task persistence.

## Directory Structure

```
Hackathon-0/
├── pyproject.toml
├── .env
├── .env.example
├── README.md
├── main.py
├── config/
│   └── vault_config.json
├── docs/
│   └── quickstart.md
├── src/
│   ├── watchers/
│   │   ├── __init__.py
│   │   ├── base_watcher.py
│   │   └── filesystem_watcher.py
│   ├── vault/
│   │   ├── __init__.py
│   │   ├── constants.py
│   │   └── manager.py
│   ├── orchestrator/
│   │   ├── __init__.py
│   │   └── controller.py
│   ├── ralph/
│   │   ├── __init__.py
│   │   └── loop_manager.py
│   ├── skills/
│   │   ├── __init__.py
│   │   └── base_skill.py
│   └── utils/
│       ├── __init__.py
│       ├── logger.py
│       ├── config_loader.py
│       ├── secrets_manager.py
│       ├── file_lock.py
│       └── watchdog.py
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
└── .gitignore
```

## Detailed Folder and File Descriptions

### Root Directory Files

#### `pyproject.toml`
Project configuration file defining metadata, dependencies, and build settings. Contains project name, version, description, and required dependencies like watchdog, psutil, python-dotenv, and claude-code.

#### `.env` and `.env.example`
Environment variable files for storing sensitive information like API keys and vault paths. The `.env.example` serves as a template for users to configure their own environment variables.

#### `README.md`
Main documentation file explaining the project, architecture, components, usage instructions, and next steps.

#### `main.py`
Entry point for the application. Contains the main execution logic that allows running the system in different modes (watcher, orchestrator, or both).

### `config/` Directory

#### `vault_config.json`
Configuration file for vault-specific settings. Defines the vault path, folder mappings, polling intervals, and retry configurations.

### `docs/` Directory

#### `quickstart.md`
Quickstart guide with step-by-step instructions for setting up and running the system.

### `src/` Directory

The main source code is organized into functional modules:

#### `src/watchers/` - Perception Layer
Contains components that monitor external events and create actionable tasks.

- **`base_watcher.py`**: Abstract base class for all watchers implementing the BaseWatcher pattern. Defines the interface that all watchers must implement, including `check_for_updates()` and `create_action_file()` methods.

- **`filesystem_watcher.py`**: Concrete implementation of a filesystem watcher that monitors for file changes. Detects changes in monitored paths and creates action files in the Needs_Action folder.

#### `src/vault/` - Memory & GUI Layer
Handles the Obsidian vault, which serves as the centralized Markdown-based state.

- **`constants.py`**: Defines all vault-related constants including folder paths (In_Progress, Needs_Action, Plans, Done, Pending_Approval, Logs, etc.) and file paths (Company_Handbook.md, Dashboard.md, Business_Goals.md).

- **`manager.py`**: Core vault management class that handles reading and writing to the Obsidian vault. Provides methods for file operations, folder management, and activity logging.

#### `src/orchestrator/` - Orchestration Layer
Coordinates between components and triggers Claude processing.

- **`controller.py`**: Main orchestrator controller that monitors the Needs_Action folder for new tasks. Implements the claim-by-move pattern, calls Claude with appropriate prompts, and handles the approval workflow.

#### `src/ralph/` - Reasoning Layer
Implements the Ralph Wiggum loop for task persistence and autonomy.

- **`loop_manager.py`**: Manages the Ralph Wiggum loop pattern that ensures m
ulti-step tasks complete. Implements the stop-hook pattern with completion detection and handles Claude retries until task completion.

#### `src/skills/` - Agent Skills
Reusable components for specific functionalities.

- **`base_skill.py`**: Abstract base class for all agent skills. Defines the interface for creating reusable skills that Claude can auto-load and use.

#### `src/utils/` - Utility Functions
Various utility functions for supporting the main components.

- **`logger.py`**: Sets up logging infrastructure for the application with configurable log levels and file output.

- **`config_loader.py`**: Loads configuration from JSON files, specifically vault configuration.

- **`secrets_manager.py`**: Manages loading of secrets from environment variables using python-dotenv.

- **`file_lock.py`**: Implements file-based locking mechanisms for the claim-by-move pattern and preventing race conditions.

- **`watchdog.py`**: Implements process health monitoring and auto-restart for critical services.

### `tests/` Directory

Contains unit and integration tests for all components:

#### `tests/unit/` - Unit Tests
Unit tests for individual components organized by module:
- `test_watchers/` - Tests for watcher functionality
- `test_vault/` - Tests for vault operations
- `test_skills/` - Tests for skill functionality
- `test_orchestrator/` - Tests for orchestrator functionality
- `test_ralph/` - Tests for Ralph loop functionality

#### `tests/integration/` - Integration Tests
- `test_bronze_flow.py` - Integration tests for the complete Bronze phase flow

#### `tests/fixtures/` - Test Fixtures
- `vault_structure/` - Sample vault structures for testing

## Core Architecture Patterns

### 1. Claim-by-Move Pattern
First agent moves file from Needs_Action → In_Progress/<agent>/ → owns it, preventing duplicate processing.

### 2. Approval Workflow
Claude writes Pending_Approval/*.md → human moves to Approved/ → orchestrator triggers MCP.

### 3. Ralph Wiggum Loop
Ensures multi-step tasks complete using stop-hook pattern with completion detection.

### 4. Dry-Run Mode
All MCP servers respect DRY_RUN env var → log instead of execute.

### 5. Exponential Backoff Retry
For transient errors with configurable parameters.

### 6. Task Completion Detection
File moved to Done/ OR Claude outputs `<promise>TASK_COMPLETE</promise>`.

## Security Framework

- Local-first design with all sensitive data staying on device
- .env files for secrets management
- Human-in-the-loop for sensitive actions
- File-based locking to prevent race conditions
- Immutable JSON logs for audit trails

## Edge Cases Handled

- Multiple concurrent tasks with priority sorting
- API/network failures with local queuing and retry
- Ralph loop infinite execution with max iteration limits
- Offline operation with local queue and sync on reconnect
- Credential expiry detection and alerts
- Large file handling with truncation and manual review
- Process crashes with auto-restart mechanisms
- Vault corruption with backup and integrity checks
- External rate limiting with adaptive queuing
- Claude context overflow with chunking and summarization
- Duplicate tasks with unique ID and deduplication
- Concurrent human and AI edits with atomic writes and file locking
- Resource exhaustion with monitoring and auto-cleanup