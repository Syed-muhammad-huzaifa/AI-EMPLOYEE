# Tasks: Gmail Integration for AI Employee

**Input**: Design documents from `/specs/001-gmail-integration/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: Tests are OPTIONAL - not explicitly requested in specification, so test tasks are omitted.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

**Implementation Approach**: Minimal extension to existing Bronze phase in `Hackathon-0/` - adding only 2 new files that leverage existing infrastructure.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Base directory**: `Hackathon-0/` (existing Bronze phase)
- **Watcher**: `Hackathon-0/src/watchers/`
- **MCP Server**: `Hackathon-0/email-mcp/`
- **Config**: `Hackathon-0/config/`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Install dependencies and prepare environment for Gmail integration

- [X] T001 Install Gmail API dependencies: `pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client`
- [X] T002 Create mcp-servers/email-mcp directory: `mkdir -p Hackathon-0/mcp-servers/email-mcp`
- [X] T003 Verify Gmail credentials in Hackathon-0/.env (GMAIL_CLIENT_ID, GMAIL_CLIENT_SECRET already added)
- [X] T004 Create config directory if not exists: `mkdir -p Hackathon-0/config`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: One-time OAuth2 authentication to obtain Gmail API tokens

**⚠️ CRITICAL**: This phase MUST be complete before ANY user story can be implemented. Both watcher and MCP server require valid OAuth2 tokens.

- [X] T005 Create OAuth2 authentication script in Hackathon-0/scripts/authenticate_gmail.py
- [ ] T006 Run authentication script to obtain OAuth2 tokens and save to Hackathon-0/config/gmail_token.pickle
- [ ] T007 Verify token file exists and contains valid credentials: `ls -la Hackathon-0/config/gmail_token.pickle`

**Checkpoint**: OAuth2 tokens obtained - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Email Detection with Intelligent Filtering (Priority: P1) 🎯 MVP

**Goal**: Implement Gmail watcher that monitors inbox, classifies emails as actionable/non-actionable using intelligent filtering, and creates action files only for actionable emails.

**Independent Test**: Send 3 test emails to monitored Gmail account (1 from real client, 1 sponsored email with "promotional" keyword, 1 from noreply@linkedin.com). Mark all as important. Verify within 5 minutes that only the client email creates an action file in `Needs_Action/`, while the other 2 are labeled "non-actionable" in Gmail.

### Implementation for User Story 1

- [X] T008 [US1] Create GmailWatcher class skeleton in Hackathon-0/src/watchers/gmail_watcher.py extending BaseWatcher
- [X] T009 [US1] Implement OAuth2 credential loading in gmail_watcher.py using token from config/gmail_token.pickle
- [X] T010 [US1] Implement Gmail API service initialization in gmail_watcher.py with automatic token refresh
- [X] T011 [US1] Implement check_for_updates() method in gmail_watcher.py to fetch unread important emails from Gmail API
- [X] T012 [US1] Implement email classification logic in gmail_watcher.py: domain pattern matching (noreply@, no-reply@, notifications@, donotreply@, *@facebookmail.com, *@linkedin.com, *@twitter.com)
- [X] T013 [US1] Implement email classification logic in gmail_watcher.py: subject keyword matching (unsubscribe, promotional, sponsored, newsletter, marketing) - case-insensitive
- [X] T014 [US1] Implement email classification logic in gmail_watcher.py: Company_Handbook.md parsing for known client domains under "## Clients" section
- [X] T015 [US1] Implement default classification behavior in gmail_watcher.py: if no negative signals, classify as "actionable" (conservative approach)
- [X] T016 [US1] Implement Gmail labeling in gmail_watcher.py: apply "actionable" or "non-actionable" labels to classified emails using Gmail API modify
- [X] T017 [US1] Implement create_action_file() method in gmail_watcher.py to create EMAIL_{message_id}_{timestamp}.md files in Needs_Action/ for actionable emails only
- [X] T018 [US1] Implement action file content generation in gmail_watcher.py: include sender, subject, body snippet (200 chars), received timestamp, classification reason
- [X] T019 [US1] Implement state persistence in gmail_watcher.py: save/load watcher state to/from Hackathon-0/config/gmail_watcher_state.json
- [X] T020 [US1] Implement duplicate detection in gmail_watcher.py: track processed_message_ids in state to prevent duplicate action files
- [X] T021 [US1] Implement classification statistics tracking in gmail_watcher.py: total_processed, actionable, non_actionable, domain_pattern_filtered, keyword_filtered, handbook_matched, default_actionable
- [X] T022 [US1] Add error handling in gmail_watcher.py: catch Gmail API errors, network errors, token expiry with exponential backoff (1s, 2s, 4s, 8s, max 60s)
- [X] T023 [US1] Add logging in gmail_watcher.py: log all detection activities, classification decisions with reasoning using existing logger utilities
- [X] T024 [US1] Set check_interval to 120 seconds (2 minutes) in gmail_watcher.py constructor

**Checkpoint**: At this point, User Story 1 should be fully functional. Test by running `python Hackathon-0/src/watchers/gmail_watcher.py` and sending test emails.

---

## Phase 4: User Story 2 - Email Reply Sending with Approval (Priority: P2)

**Goal**: Implement MCP server with send_email tool that sends emails via Gmail API after human approval, with rate limiting and retry logic.

**Independent Test**: Create an approval file in `/Approved/` with email draft content (to, subject, body). Invoke MCP server's send_email tool. Verify email is sent via Gmail API and confirmation is logged to `/Done/`.

### Implementation for User Story 2

- [X] T025 [US2] Create MCP server skeleton in Hackathon-0/mcp-servers/email-mcp/email-mcp.py with stdio communication
- [X] T026 [US2] Implement OAuth2 credential loading in email-mcp.py using python-dotenv to load .env
- [X] T027 [US2] Implement OAuth2 token loading in email-mcp.py from Hackathon-0/config/gmail_token.pickle with automatic refresh
- [X] T028 [US2] Implement Gmail API service initialization in email-mcp.py for sending emails
- [X] T029 [US2] Implement send_email tool registration in email-mcp.py with MCP protocol: tool name, description, parameters (to, subject, body, dry_run)
- [X] T030 [US2] Implement email address validation in email-mcp.py: RFC 5322 format using regex pattern
- [X] T031 [US2] Implement parameter validation in email-mcp.py: subject max 500 chars, body max 50KB, to non-empty
- [X] T032 [US2] Implement rate limiting in email-mcp.py: token bucket algorithm with 20 emails/hour and 100 API calls/day limits
- [X] T033 [US2] Implement email sending logic in email-mcp.py: create MIME message, encode base64, call Gmail API users().messages().send()
- [X] T034 [US2] Implement retry logic in email-mcp.py: exponential backoff (1s, 2s, 4s, 8s, max 60s) for network errors and API timeouts, max 3 retries
- [X] T035 [US2] Implement DRY_RUN mode in email-mcp.py: check DRY_RUN environment variable and dry_run parameter, simulate send without actual delivery
- [X] T036 [US2] Implement error handling in email-mcp.py: return structured error responses (INVALID_EMAIL, RATE_LIMIT_EXCEEDED, AUTHENTICATION_FAILED, GMAIL_API_ERROR, NETWORK_ERROR)
- [X] T037 [US2] Implement success response in email-mcp.py: return success=true, message_id, timestamp, dry_run flag
- [X] T038 [US2] Implement logging in email-mcp.py: log all send attempts, rate limit hits, errors with timestamps
- [X] T039 [US2] Add MCP server startup and main loop in email-mcp.py: listen on stdio, handle tool invocations, graceful shutdown

**Checkpoint**: At this point, User Stories 1 AND 2 should both work independently. Test MCP server with: `echo '{"tool":"send_email","parameters":{"to":"test@example.com","subject":"Test","body":"Test body","dry_run":true}}' | python Hackathon-0/email-mcp/email-mcp.py`

---

## Phase 5: User Story 3 - Email Thread Context Management (Priority: P3)

**Goal**: Enhance Gmail watcher to include email thread context in action files so replies can reference previous conversations.

**Independent Test**: Send a reply to an existing email thread. Verify the action file includes thread_id and references to previous messages in the thread.

### Implementation for User Story 3

- [X] T040 [US3] Modify check_for_updates() in Hackathon-0/src/watchers/gmail_watcher.py to fetch thread_id for each email
- [X] T041 [US3] Implement thread context fetching in gmail_watcher.py: if thread_id exists, fetch previous messages in thread using Gmail API threads().get()
- [X] T042 [US3] Modify create_action_file() in gmail_watcher.py to include thread_id in action file metadata
- [X] T043 [US3] Modify action file content generation in gmail_watcher.py to include "## Thread Context" section with previous message snippets (if thread exists)
- [X] T044 [US3] Add thread context to state tracking in gmail_watcher.py: store thread_id in processed messages

**Checkpoint**: All user stories should now be independently functional. Test with email threads to verify context is captured.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Deployment configuration, documentation, and end-to-end validation

- [X] T045 [P] Create PM2 configuration in Hackathon-0/ecosystem.config.js for gmail-watcher daemon
- [X] T046 [P] Add MCP server configuration to Hackathon-0/mcp.json for email-mcp server
- [X] T047 [P] Update Hackathon-0/.gitignore to include config/gmail_token.pickle and config/gmail_watcher_state.json
- [X] T048 [P] Add "## Clients" section to Company_Handbook.md in vault
- [ ] T049 Run end-to-end test: Start watcher with PM2, send test emails, verify action files created, move draft to Approved/, verify MCP sends email
- [ ] T050 Validate against quickstart.md: Follow setup steps and verify all commands work

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3+)**: All depend on Foundational phase completion
  - User stories can then proceed in parallel (if staffed)
  - Or sequentially in priority order (P1 → P2 → P3)
- **Polish (Phase 6)**: Depends on all desired user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) - No dependencies on other stories
- **User Story 2 (P2)**: Can start after Foundational (Phase 2) - Independent of US1 (different file)
- **User Story 3 (P3)**: Depends on User Story 1 completion (modifies gmail_watcher.py)

### Within Each User Story

- **US1**: Tasks T008-T024 must be done sequentially (all in same file gmail_watcher.py)
- **US2**: Tasks T025-T039 must be done sequentially (all in same file email-mcp.py)
- **US3**: Tasks T040-T044 must be done sequentially (modifies gmail_watcher.py)

### Parallel Opportunities

- **Phase 1**: All setup tasks (T001-T004) can run in parallel
- **Phase 2**: Tasks T005-T007 must be sequential (authentication flow)
- **Phase 3 & 4**: User Story 1 (gmail_watcher.py) and User Story 2 (email-mcp.py) can be implemented in parallel by different developers (different files, no dependencies)
- **Phase 6**: Tasks T045-T048 marked [P] can run in parallel

---

## Parallel Example: User Stories 1 & 2

```bash
# After Foundational phase completes, launch both user stories in parallel:

# Developer A works on User Story 1:
Task: "Implement gmail_watcher.py extending BaseWatcher"

# Developer B works on User Story 2:
Task: "Implement email-mcp.py MCP server"

# Both can work simultaneously - different files, no conflicts
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001-T004)
2. Complete Phase 2: Foundational (T005-T007) - CRITICAL
3. Complete Phase 3: User Story 1 (T008-T024)
4. **STOP and VALIDATE**: Test gmail_watcher.py independently with test emails
5. Deploy watcher with PM2 and monitor

**MVP Deliverable**: Gmail watcher that detects important emails, filters out noise (sponsored/newsletters/platform notifications), and creates action files only for actionable emails.

### Incremental Delivery

1. **Foundation** (Phases 1-2): Setup + OAuth2 authentication → Ready for development
2. **MVP** (Phase 3): User Story 1 → Test independently → Deploy watcher (Email detection working!)
3. **V2** (Phase 4): User Story 2 → Test independently → Deploy MCP server (Email sending working!)
4. **V3** (Phase 5): User Story 3 → Test independently → Deploy enhancement (Thread context working!)
5. **Production** (Phase 6): Polish → End-to-end validation → Full deployment

Each increment adds value without breaking previous functionality.

### Parallel Team Strategy

With 2 developers:

1. **Together**: Complete Setup + Foundational (Phases 1-2)
2. **Split work** (after Phase 2 completes):
   - Developer A: User Story 1 (gmail_watcher.py) - T008-T024
   - Developer B: User Story 2 (email-mcp.py) - T025-T039
3. **Merge**: Both stories complete independently
4. **Together**: User Story 3 (modifies gmail_watcher.py) - T040-T044
5. **Together**: Polish (Phase 6) - T045-T050

---

## Task Summary

**Total Tasks**: 50
- Phase 1 (Setup): 4 tasks
- Phase 2 (Foundational): 3 tasks
- Phase 3 (User Story 1 - P1): 17 tasks
- Phase 4 (User Story 2 - P2): 15 tasks
- Phase 5 (User Story 3 - P3): 5 tasks
- Phase 6 (Polish): 6 tasks

**Parallel Opportunities**:
- Phase 1: 4 tasks can run in parallel
- Phase 3 & 4: 2 user stories can be developed in parallel (32 tasks total)
- Phase 6: 4 tasks can run in parallel

**MVP Scope**: Phases 1-3 (24 tasks) delivers email detection with intelligent filtering

**Independent Test Criteria**:
- US1: Send 3 test emails (client, sponsored, platform notification) → verify only client creates action file
- US2: Create approval file → invoke send_email tool → verify email sent and logged
- US3: Reply to email thread → verify action file includes thread context

---

## Notes

- All tasks follow strict checklist format: `- [ ] [ID] [P?] [Story?] Description with file path`
- [P] tasks = different files, no dependencies, can run in parallel
- [Story] label (US1, US2, US3) maps task to specific user story for traceability
- Each user story is independently completable and testable
- Minimal approach: Only 2 new files (gmail_watcher.py, email-mcp.py) leverage existing Bronze phase infrastructure
- No test tasks included (not explicitly requested in specification)
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
