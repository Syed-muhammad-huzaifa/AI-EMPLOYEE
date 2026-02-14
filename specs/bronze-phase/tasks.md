---

description: "Task list for Bronze Phase - Core Infrastructure implementation"
---

# Tasks: Bronze Phase - Core Infrastructure

**Input**: Design documents from `/specs/bronze-phase/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: The examples below include test tasks. Tests are OPTIONAL - only include them if explicitly requested in the feature specification.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Single project**: `src/`, `tests/` at repository root
- Paths shown below assume single project - adjust based on plan.md structure

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

- [X] T001 Create project structure per implementation plan in Hackathon-0 directory
- [X] T002 Initialize Python project with required dependencies (watchdog, psutil, etc.)
- [X] T003 [P] Configure logging and error handling infrastructure

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

Examples of foundational tasks (adjust based on your project):

- [X] T004 Create vault constants and configuration module for C:\MY_EMPLOYEE
- [X] T005 [P] Implement basic vault manager with read/write operations for existing vault
- [X] T006 Configure logging infrastructure to write to Logs/ folder in vault
- [X] T007 Implement file locking mechanism for claim-by-move pattern

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Vault Integration (Priority: P1) 🎯 MVP

**Goal**: Integrate with the existing Obsidian vault to read and write task files for the AI employee system

**Independent Test**: Can run Claude with vault context and verify it can read existing files and create new files in the vault.

### Tests for User Story 1 (OPTIONAL - only if tests requested) ⚠️

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [ ] T010 [P] [US1] Contract test for vault structure access in tests/contract/test_vault_structure.py
- [ ] T011 [P] [US1] Unit test for vault manager in tests/unit/test_vault/test_manager.py

### Implementation for User Story 1

- [X] T012 [P] [US1] Create vault constants in src/vault/constants.py for C:\MY_EMPLOYEE paths
- [X] T013 [US1] Implement vault manager in src/vault/manager.py with read/write operations
- [X] T014 [US1] Add vault initialization function to verify C:\MY_EMPLOYEE accessibility
- [X] T015 [US1] Create utility functions to verify Company_Handbook.md and Dashboard.md exist

**Checkpoint**: At this point, User Story 1 should be fully functional and testable independently

---

## Phase 4: User Story 2 - Filesystem Watcher Implementation (Priority: P1)

**Goal**: Implement a filesystem watcher that monitors for changes and creates actionable tasks using the BaseWatcher pattern

**Independent Test**: Can start the watcher, make a change to monitored files, and verify a corresponding .md file appears in the Needs_Action folder.

### Tests for User Story 2 (OPTIONAL - only if tests requested) ⚠️

- [ ] T016 [P] [US2] Contract test for filesystem watcher in tests/contract/test_filesystem_watcher.py
- [ ] T017 [P] [US2] Unit test for base watcher in tests/unit/test_watchers/test_base_watcher.py

### Implementation for User Story 2

- [X] T018 [P] [US2] Create base watcher class in src/watchers/base_watcher.py (BaseWatcher pattern)
- [X] T019 [US2] Implement filesystem watcher in src/watchers/filesystem_watcher.py
- [X] T020 [US2] Add watcher configuration and startup logic for C:\MY_EMPLOYEE monitoring
- [X] T021 [US2] Implement error handling and logging for watcher to Logs/ folder
- [X] T022 [US2] Add daemonization support for continuous operation (PM2/supervisord)

**Checkpoint**: At this point, User Stories 1 AND 2 should both work independently

---

## Phase 5: User Story 3 - Claude Vault Integration (Priority: P1)

**Goal**: Enable Claude to read from and write to the Obsidian vault, specifically reading Company_Handbook.md and Dashboard.md as context

**Independent Test**: Can run Claude with vault context and verify it can read files and create new files in the vault.

### Tests for User Story 3 (OPTIONAL - only if tests requested) ⚠️

- [ ] T023 [P] [US3] Contract test for Claude vault integration in tests/contract/test_claude_integration.py
- [ ] T024 [P] [US3] Integration test for vault read/write in tests/integration/test_vault_operations.py

### Implementation for User Story 3

- [X] T025 [P] [US3] Create utility to ensure Claude reads Company_Handbook.md as context
- [X] T026 [US3] Create utility to ensure Claude reads Dashboard.md as context
- [X] T027 [US3] Add Claude context reading functionality for vault files
- [X] T028 [US3] Implement Claude task processing workflow (Needs_Action → Plans → Done)

**Checkpoint**: At this point, User Stories 1, 2 AND 3 should all work independently

---

## Phase 6: User Story 4 - Orchestrator Implementation (Priority: P1)

**Goal**: Implement the orchestrator that monitors folders and triggers Claude loops when new tasks appear in Needs_Action/

**Independent Test**: Can place a file in Needs_Action/, verify the orchestrator detects it, and confirms Claude is triggered to process the task.

### Tests for User Story 4 (OPTIONAL - only if tests requested) ⚠️

- [ ] T029 [P] [US4] Contract test for orchestrator in tests/contract/test_orchestrator.py
- [ ] T030 [P] [US4] Unit test for orchestrator controller in tests/unit/test_orchestrator/test_controller.py

### Implementation for User Story 4

- [X] T031 [P] [US4] Implement orchestrator controller in src/orchestrator/controller.py
- [X] T032 [US4] Add folder monitoring logic for Needs_Action/ folder
- [X] T033 [US4] Implement Claude triggering mechanism when new files appear
- [X] T034 [US4] Add task completion detection and folder movement logic
- [X] T035 [US4] Implement retry logic with exponential backoff for transient errors

**Checkpoint**: At this point, User Stories 1-4 should all work independently

---

## Phase 7: User Story 5 - Agent Skills Foundation (Priority: P2)

**Goal**: Establish the foundation for Agent Skills that will be used throughout the system, following the auto-loading pattern from ~/.claude/skills/

**Independent Test**: Can create and register a basic Agent Skill and verify Claude can discover and use it.

### Tests for User Story 5 (OPTIONAL - only if tests requested) ⚠️

- [ ] T036 [P] [US5] Contract test for Agent Skills in tests/contract/test_agent_skills.py
- [ ] T037 [P] [US5] Unit test for base skill in tests/unit/test_skills/test_base_skill.py

### Implementation for User Story 5

- [X] T038 [P] [US5] Create base skill class in src/skills/base_skill.py
- [X] T039 [US5] Implement skill registration and discovery mechanism
- [X] T040 [US5] Create example skill demonstrating the pattern
- [X] T041 [US5] Add skill loading from ~/.claude/skills/ directory

**Checkpoint**: At this point, User Stories 1-5 should all work independently

---

## Phase 8: User Story 6 - Folder Structure and Workflow (Priority: P1)

**Goal**: Implement the complete folder structure and workflow system including all required directories and the claim-by-move pattern

**Independent Test**: Can create a task in Needs_Action, process it through the system using claim-by-move, and verify it ends up in Done.

### Tests for User Story 6 (OPTIONAL - only if tests requested) ⚠️

- [ ] T042 [P] [US6] Contract test for folder workflow in tests/contract/test_workflow.py
- [ ] T043 [P] [US6] Integration test for complete workflow in tests/integration/test_complete_workflow.py

### Implementation for User Story 6

- [X] T044 [P] [US6] Implement task movement logic (Needs_Action → In_Progress → Plans → Done)
- [X] T045 [US6] Add claim-by-move pattern implementation using file locking
- [X] T046 [US6] Add workflow state tracking and validation
- [X] T047 [US6] Create orchestrator integration for folder management
- [X] T048 [US6] Add completion detection using <promise>TASK_COMPLETE</promise> pattern

**Checkpoint**: At this point, User Stories 1-6 should all work independently

---

## Phase 9: User Story 7 - Ralph Wiggum Loop Foundation (Priority: P2)

**Goal**: Implement the foundation for the Ralph Wiggum loop mechanism for task persistence and completion detection

**Independent Test**: Can start a multi-step task with Claude and verify it continues until the <promise>TASK_COMPLETE</promise> marker is detected.

### Tests for User Story 7 (OPTIONAL - only if tests requested) ⚠️

- [ ] T049 [P] [US7] Contract test for Ralph loop in tests/contract/test_ralph_loop.py
- [ ] T050 [P] [US7] Unit test for loop manager in tests/unit/test_ralph/test_loop_manager.py

### Implementation for User Story 7

- [X] T051 [P] [US7] Implement Ralph loop manager in src/ralph/loop_manager.py
- [X] T052 [US7] Add stop-hook pattern implementation for Claude
- [X] T053 [US7] Implement <promise>TASK_COMPLETE</promise> detection logic
- [X] T054 [US7] Add loop continuation and re-injection mechanism
- [X] T055 [US7] Add loop timeout and failure handling

**Checkpoint**: All user stories should now be integrated and functional

---

## Phase N: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [X] T056 [P] Documentation updates in docs/
- [X] T057 Code cleanup and refactoring
- [X] T058 Performance optimization across all components
- [X] T059 [P] Additional unit tests (if requested) in tests/unit/
- [X] T060 Security hardening
- [X] T061 Run quickstart.md validation
- [X] T062 Create quickstart guide for Bronze phase
- [X] T063 Test complete Bronze phase flow: Dummy task → Plan.md → Done/ + log
- [X] T064 Implement watchdog.py for process health monitoring and auto-restart
- [X] T065 Update configuration to match architecture folder names (Needs_Action, Plans, Done, etc.)
- [X] T066 Implement approval workflow handling in orchestrator
- [X] T067 Add Business_Goals.md support to vault manager

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3+)**: All depend on Foundational phase completion
  - User stories can then proceed in parallel (if staffed)
  - Or sequentially in priority order (P1 → P2 → P3)
- **Polish (Final Phase)**: Depends on all desired user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) - No dependencies on other stories
- **User Story 2 (P1)**: Depends on US1 (needs vault structure)
- **User Story 3 (P1)**: Depends on US1 (needs vault structure)
- **User Story 4 (P1)**: Depends on US1 (needs vault structure) and US2 (needs watcher to understand folder monitoring)
- **User Story 5 (P2)**: Can start after Foundational (Phase 2) - No dependencies on other stories
- **User Story 6 (P1)**: Depends on US1 (needs vault structure) and US4 (needs orchestrator)
- **User Story 7 (P2)**: Depends on US1 (needs vault structure) and US3 (needs Claude integration)

### Within Each User Story

- Tests (if included) MUST be written and FAIL before implementation
- Models before services
- Services before endpoints
- Core implementation before integration
- Story complete before moving to next priority

### Parallel Opportunities

- All Setup tasks marked [P] can run in parallel
- All Foundational tasks marked [P] can run in parallel (within Phase 2)
- Once Foundational phase completes, all user stories can start in parallel (if team capacity allows)
- All tests for a user story marked [P] can run in parallel
- Models within a story marked [P] can run in parallel
- Different user stories can be worked on in parallel by different team members

---

## Parallel Example: User Story 1

```bash
# Launch all tests for User Story 1 together (if tests requested):
Task: "Contract test for vault structure access in tests/contract/test_vault_structure.py"
Task: "Unit test for vault manager in tests/unit/test_vault/test_manager.py"

# Launch all components for User Story 1 together:
Task: "Create vault constants in src/vault/constants.py for C:\MY_EMPLOYEE paths"
Task: "Implement vault manager in src/vault/manager.py with read/write operations"
```

---

## Implementation Strategy

### MVP First (User Stories 1-4 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL - blocks all stories)
3. Complete Phase 3: User Story 1 (Vault Integration)
4. Complete Phase 4: User Story 2 (Filesystem Watcher)
5. Complete Phase 5: User Story 3 (Claude Integration)
6. Complete Phase 6: User Story 4 (Orchestrator)
7. **STOP and VALIDATE**: Test the core workflow independently
8. Deploy/demo if ready

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready
2. Add User Story 1 → Test independently → Deploy/Demo (Vault access!)
3. Add User Story 2 → Test independently → Deploy/Demo (Watcher working!)
4. Add User Story 3 → Test independently → Deploy/Demo (Claude integration!)
5. Add User Story 4 → Test independently → Deploy/Demo (Orchestrator working!)
6. Add User Stories 5-7 → Test independently → Deploy/Demo (Complete Bronze!)

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together
2. Once Foundational is done:
   - Developer A: User Story 1 (Vault Integration)
   - Developer B: User Story 2 (Watcher)
   - Developer C: User Story 3 (Claude Integration)
3. Once P1 stories complete:
   - Developer A: User Story 4 (Orchestrator)
   - Developer B: User Story 6 (Workflow)
   - Developer C: User Story 5 (Skills)
4. Once P1 stories complete:
   - Developer A: User Story 7 (Ralph Loop)
5. Stories complete and integrate independently

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Verify tests fail before implementing
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- Avoid: vague tasks, same file conflicts, cross-story dependencies that break independence
- Pay special attention to the existing vault structure at C:\MY_EMPLOYEE
- Ensure all components work with the specific folder names: In_Progress, Needs_Action, Logs, Done, Plans, Pending_Approval
- Ensure all components work with the specific file names: Company_Handbook.md, Dashboard.md, Business_Goals.md