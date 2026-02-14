# Feature Specification: Bronze Phase - Core Infrastructure

**Feature Branch**: `001-bronze-phase`
**Created**: 2026-02-10
**Status**: Draft
**Input**: User description: "Bronze Tier (Foundation – 8–12 hours): Establish core infrastructure for Personal AI Employee"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Vault Integration (Priority: P1)

Integrate with the existing Obsidian vault to read and write task files for the AI employee system.

**Why this priority**: The vault serves as the central memory and state management system for the entire AI employee system. Claude needs to read from and write to the existing vault structure.

**Independent Test**: Can run Claude with vault context and verify it can read existing files and create new files in the vault.

**Acceptance Scenarios**:

1. **Given** Claude is pointed to the existing vault, **When** Claude runs, **Then** Claude can read vault files like Company_Handbook.md and Business_Goals.md
2. **Given** Claude processes a task, **When** Claude completes, **Then** Claude creates appropriate output files in the vault folders like Plans/ or Done/

---

### User Story 2 - Filesystem Watcher Implementation (Priority: P1)

Implement a filesystem watcher that monitors for changes and creates actionable tasks using the BaseWatcher pattern.

**Why this priority**: The watcher serves as the primary input mechanism for the AI employee, detecting changes and converting them into actionable tasks.

**Independent Test**: Can start the watcher, make a change to monitored files, and verify a corresponding .md file appears in the /Needs_Action folder.

**Acceptance Scenarios**:

1. **Given** the filesystem watcher is running, **When** a monitored file changes, **Then** a corresponding .md file is created in /Needs_Action/
2. **Given** the watcher is running, **When** the watcher encounters an error, **Then** the error is logged and the watcher continues running

---

### User Story 3 - Claude Vault Integration (Priority: P1)

Enable Claude to read from and write to the Obsidian vault, specifically reading Company_Handbook.md and Business_Goals.md as context.

**Why this priority**: Claude needs to access the vault to read context (Company_Handbook.md, Business_Goals.md) and write plans and results.

**Independent Test**: Can run Claude with vault context and verify it can read files and create new files in the vault.

**Acceptance Scenarios**:

1. **Given** Claude is pointed to the vault, **When** Claude runs, **Then** Claude can read vault files including Company_Handbook.md and Business_Goals.md
2. **Given** Claude processes a task, **When** Claude completes, **Then** Claude creates appropriate output files in the vault and follows the patterns defined in the handbook/goals

---

### User Story 4 - Orchestrator Implementation (Priority: P1)

Implement the orchestrator that monitors folders and triggers Claude loops when new tasks appear in /Needs_Action/.

**Why this priority**: The orchestrator is the glue that connects watchers to Claude, monitoring for new tasks and triggering processing.

**Independent Test**: Can place a file in /Needs_Action/, verify the orchestrator detects it, and confirms Claude is triggered to process the task.

**Acceptance Scenarios**:

1. **Given** a file exists in /Needs_Action/, **When** the orchestrator detects it, **Then** Claude is triggered to process the task
2. **Given** Claude completes processing, **When** the orchestrator detects completion, **Then** the task is moved to the appropriate next folder

---

### User Story 5 - Agent Skills Foundation (Priority: P2)

Establish the foundation for Agent Skills that will be used throughout the system, following the auto-loading pattern from ~/.claude/skills/.

**Why this priority**: Agent Skills provide the modular, reusable functionality that enables the AI employee to perform various tasks.

**Independent Test**: Can create and register a basic Agent Skill and verify Claude can discover and use it.

**Acceptance Scenarios**:

1. **Given** an Agent Skill is registered in ~/.claude/skills/, **When** Claude needs that functionality, **Then** Claude can auto-discover and use the skill
2. **Given** Claude uses an Agent Skill, **When** the skill executes, **Then** the skill performs its intended function

---

### User Story 6 - Folder Structure and Workflow (Priority: P1)

Implement the complete folder structure and workflow system including all required directories and the claim-by-move pattern.

**Why this priority**: The folder workflow provides the task lifecycle management that drives the entire system, with proper state management.

**Independent Test**: Can create a task in /Needs_Action, process it through the system using claim-by-move, and verify it ends up in /Done.

**Acceptance Scenarios**:

1. **Given** a task exists in /Needs_Action/, **When** processing begins, **Then** the task is moved to In_Progress/ using claim-by-move pattern
2. **Given** a task is completed, **When** processing finishes, **Then** the task is moved to /Done/ and logged appropriately

---

### User Story 7 - Ralph Wiggum Loop Foundation (Priority: P2)

Implement the foundation for the Ralph Wiggum loop mechanism for task persistence and completion detection.

**Why this priority**: The Ralph loop ensures multi-step tasks complete by intercepting Claude's exit and re-injecting the prompt until completion.

**Independent Test**: Can start a multi-step task with Claude and verify it continues until the <promise>TASK_COMPLETE</promise> marker is detected.

**Acceptance Scenarios**:

1. **Given** a multi-step task is initiated, **When** Claude processes it, **Then** the loop continues until <promise>TASK_COMPLETE</promise> is output
2. **Given** Claude exits prematurely, **When** the loop detects this, **Then** the prompt is re-injected until completion

---

### Edge Cases

- What happens when the vault directory doesn't exist initially?
- How does the system handle concurrent file access to the vault?
- What if Claude loses access to the vault during processing?
- How does the system handle malformed Markdown files?
- What happens when the filesystem watcher encounters permission errors?
- What if Claude enters an infinite loop during processing?
- How does the system handle multiple tasks arriving simultaneously?
- What happens when the orchestrator crashes or hangs?
- How does the system handle resource exhaustion (disk, memory)?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST integrate with existing Obsidian vault at "C:\MY_EMPLOYEE" with core files (dashboard.md, company_handbook.md) and folders (INBOX, NEEDS_ACTION, LOGS, DONE, PLAN)
- **FR-002**: Filesystem watcher MUST inherit from BaseWatcher class and follow the defined pattern
- **FR-003**: Filesystem watcher MUST create .md files in NEEDS_ACTION/ when changes are detected
- **FR-004**: Claude MUST read company_handbook.md and dashboard.md as context before processing any task
- **FR-005**: Claude MUST be able to write files to the vault directory following established patterns
- **FR-006**: Orchestrator MUST monitor NEEDS_ACTION/ folder and trigger Claude when new files appear
- **FR-007**: System MUST work with existing folder structure: INBOX/, NEEDS_ACTION/, PLAN/, DONE/, LOGS/ and future-proof for additional folders
- **FR-008**: System MUST implement claim-by-move pattern: NEEDS_ACTION → INBOX/<agent>/ → owns task
- **FR-009**: System MUST support Agent Skills auto-loading from ~/.claude/skills/ directory
- **FR-010**: System MUST implement Ralph Wiggum loop with <promise>TASK_COMPLETE</promise> completion detection
- **FR-011**: Filesystem watcher MUST run continuously as a daemon process (PM2/supervisord)
- **FR-012**: System MUST log all activities to LOGS/ in JSON format with timestamps
- **FR-013**: Claude MUST run in vault directory (--cwd .) to access all context files
- **FR-014**: System MUST implement retry logic with exponential backoff (base 1s, max 60s, 3-5 attempts) for transient errors
- **FR-015**: System MUST support dry-run mode for all operations where applicable

### Key Entities *(include if feature involves data)*

- **Vault**: The Obsidian vault directory containing all system state and memory
- **Watcher**: The filesystem monitoring component that detects changes and creates tasks using BaseWatcher pattern
- **Orchestrator**: The folder monitoring component that triggers Claude when new tasks appear
- **Task**: A .md file representing an actionable item in the workflow system
- **Agent Skill**: A reusable component providing specific functionality to Claude, auto-loaded from ~/.claude/skills/
- **Ralph Loop**: The mechanism ensuring multi-step tasks complete using stop-hook pattern
- **Claim-by-Move**: The task ownership mechanism preventing duplicate processing

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Complete vault structure with all required files and folders is accessible (100% success rate)
- **SC-002**: Filesystem watcher detects changes and creates .md files in /Needs_Action/ with 95% accuracy
- **SC-003**: Claude can read and write to the vault with 99% success rate, properly reading Company_Handbook.md and Business_Goals.md
- **SC-004**: Orchestrator detects new tasks in /Needs_Action/ and triggers Claude with 98% success rate
- **SC-005**: Basic folder workflow processes tasks from /Needs_Action/ to /Done/ with 90% success rate using claim-by-move pattern
- **SC-006**: Agent Skills can be registered and auto-discovered by Claude (100% success rate)
- **SC-007**: Ralph Wiggum loop correctly handles multi-step tasks and detects <promise>TASK_COMPLETE</promise> (95% success rate)
- **SC-008**: Filesystem watcher runs continuously for 24 hours without crashing (99% uptime)
- **SC-009**: All activities are logged to /Logs/ with appropriate detail and timestamping (100% logging rate)
- **SC-010**: Bronze phase success criterion: Dummy task → Plan.md → Done/ + log achieved (100% success rate)