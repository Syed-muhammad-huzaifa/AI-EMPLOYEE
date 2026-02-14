---
id: 0004
title: gmail-integration-task-generation
stage: tasks
date: 2026-02-12
surface: agent
model: claude-sonnet-4-5
feature: 001-gmail-integration
branch: 001-gmail-integration
user: syedhuzaifa
command: /sp.tasks
labels: ["gmail", "task-generation", "user-stories", "implementation-tasks", "bronze-phase-extension"]
links:
  spec: ../spec.md
  ticket: null
  adr: null
  pr: null
files:
  - specs/001-gmail-integration/tasks.md
tests:
  - N/A (task generation phase)
---

## Prompt

/sp.tasks

## Response snapshot

Generated comprehensive task list for Gmail integration feature organized by 3 user stories (P1, P2, P3) with minimal Bronze phase extension approach:

**Task Organization by User Story**:

**Phase 1: Setup** (4 tasks)
- Install Gmail API dependencies (google-auth, google-api-python-client)
- Create email-mcp directory
- Verify Gmail credentials in .env
- Create config directory

**Phase 2: Foundational** (3 tasks) - BLOCKS all user stories
- Create OAuth2 authentication script
- Run authentication to obtain tokens (gmail_token.pickle)
- Verify token file exists

**Phase 3: User Story 1 - Email Detection with Intelligent Filtering (P1)** (17 tasks) 🎯 MVP
- T008-T024: Implement gmail_watcher.py extending BaseWatcher
- Email classification logic: domain patterns, keywords, Company_Handbook.md lookup
- Gmail labeling: apply "actionable" or "non-actionable" labels
- Action file creation for actionable emails only
- State persistence and duplicate detection
- Classification statistics tracking
- Error handling with exponential backoff
- Independent test: Send 3 emails (client, sponsored, platform notification) → verify only client creates action file

**Phase 4: User Story 2 - Email Reply Sending with Approval (P2)** (15 tasks)
- T025-T039: Implement email-mcp.py MCP server
- OAuth2 credential and token loading
- send_email tool registration with MCP protocol
- Email validation (RFC 5322), parameter validation
- Rate limiting: token bucket (20/hour, 100/day)
- Email sending via Gmail API with MIME encoding
- Retry logic with exponential backoff (max 3 retries)
- DRY_RUN mode support
- Error handling with structured responses
- Independent test: Create approval file → invoke send_email → verify sent and logged

**Phase 5: User Story 3 - Email Thread Context Management (P3)** (5 tasks)
- T040-T044: Enhance gmail_watcher.py with thread context
- Fetch thread_id and previous messages
- Include thread context in action files
- Independent test: Reply to thread → verify action file includes thread context

**Phase 6: Polish & Cross-Cutting Concerns** (6 tasks)
- PM2 configuration for watcher daemon
- MCP server configuration in mcp.json
- Update .gitignore for token and state files
- Company_Handbook.md template creation
- End-to-end testing
- Quickstart validation

**Key Design Decisions**:
- Minimal approach: Only 2 new files (gmail_watcher.py, email-mcp.py)
- Leverage existing Bronze phase infrastructure (BaseWatcher, VaultManager, secrets_manager, logging)
- No test tasks (not explicitly requested in specification)
- User Stories 1 & 2 can be developed in parallel (different files)
- User Story 3 depends on US1 (modifies same file)

**Parallel Opportunities**:
- Phase 1: All 4 setup tasks
- Phase 3 & 4: US1 and US2 can run in parallel (32 tasks total, different files)
- Phase 6: 4 polish tasks

**MVP Scope**: Phases 1-3 (24 tasks) delivers email detection with intelligent filtering

## Outcome

- ✅ Impact: Generated actionable task list with 50 tasks organized by 3 user stories, enabling independent implementation and testing of Gmail integration feature as minimal Bronze phase extension
- 🧪 Tests: N/A (task generation phase - test tasks omitted as not explicitly requested in specification)
- 📁 Files: Created tasks.md with 50 tasks across 6 phases (Setup, Foundational, US1-P1, US2-P2, US3-P3, Polish)
- 🔁 Next prompts: `/sp.implement` to execute tasks, or manually implement tasks starting with Phase 1 (Setup) and Phase 2 (Foundational)
- 🧠 Reflection: Task generation successfully organized by user stories to enable independent implementation. Minimal approach (2 files) leverages existing Bronze phase infrastructure. Clear MVP scope (US1 only = 24 tasks) provides incremental delivery path. Parallel opportunities identified for US1 & US2 (different files). All tasks follow strict checklist format with IDs, story labels, and file paths.

## Evaluation notes (flywheel)

- Failure modes observed: None - task generation completed successfully with proper user story organization
- Graders run and results (PASS/FAIL): Format validation PASSED (all 50 tasks follow checklist format with checkbox, ID, optional [P], story label, file path), User story organization PASSED (3 stories independently testable), Dependency graph PASSED (clear phase dependencies, parallel opportunities identified)
- Prompt variant (if applicable): N/A
- Next experiment (smallest change to try): N/A
