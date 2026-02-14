# Feature Specification: Gmail Integration for AI Employee

**Feature Branch**: `001-gmail-integration`
**Created**: 2026-02-12
**Status**: Draft
**Input**: User description: "Gmail watcher and MCP server for email automation with detection and sending capabilities"

## Overview

This feature enables the AI Employee to autonomously monitor Gmail inbox for important emails, intelligently filter actionable messages from noise (sponsored emails, platform notifications, newsletters), and send email responses through an automated workflow. The system detects new emails, classifies them as actionable or non-actionable, creates tasks only for actionable emails, and executes email sending actions after human approval.

## User Scenarios & Testing

### User Story 1 - Email Detection with Intelligent Filtering (Priority: P1)

As a business owner, I want the system to automatically detect important unread emails in my Gmail inbox AND intelligently filter out non-actionable emails (sponsored content, platform notifications, newsletters) so that I only receive notifications for emails that genuinely require my attention or response.

**Why this priority**: This is the foundation of email automation. Without detection and intelligent filtering, the system would create noise by flagging every promotional email or newsletter. Smart filtering ensures only business-critical emails become actionable tasks, saving time and reducing cognitive load.

**Independent Test**: Can be fully tested by sending multiple test emails (1 from a real client, 1 sponsored email, 1 newsletter) marked as important to the monitored Gmail account and verifying that only the client email creates an action file in `/Needs_Action/` within 5 minutes, while non-actionable emails are labeled in Gmail but ignored.

**Acceptance Scenarios**:

1. **Given** Gmail inbox has 3 new unread important emails (1 from client, 1 sponsored, 1 newsletter), **When** the watcher runs its check cycle, **Then** only 1 action file is created for the client email, and the other 2 are labeled as "non-actionable" in Gmail

2. **Given** an email from "noreply@linkedin.com" arrives, **When** the watcher classifies it, **Then** it is marked as non-actionable (platform notification) and no action file is created

3. **Given** an email with subject containing "unsubscribe" or "promotional" keywords, **When** the watcher classifies it, **Then** it is marked as non-actionable and no action file is created

4. **Given** an email from a known client domain (listed in Company_Handbook.md), **When** the watcher classifies it, **Then** it is marked as actionable and an action file is created with client context

5. **Given** an email is already processed and moved to `/Done/`, **When** the watcher runs again, **Then** no duplicate action file is created for that email

6. **Given** Gmail API credentials are valid, **When** the watcher starts for the first time, **Then** it successfully authenticates and begins monitoring without errors

---

### User Story 2 - Email Reply Sending with Approval (Priority: P2)

As a business owner, I want to review and approve email drafts before they are sent so that I maintain control over business communications while benefiting from AI-drafted responses.

**Why this priority**: Sending emails is the action component that completes the automation loop. The approval workflow ensures safety and maintains human oversight for sensitive communications.

**Independent Test**: Can be tested by creating an approval file in `/Pending_Approval/` with email draft content, moving it to `/Approved/`, and verifying the email is sent via Gmail API with correct recipient, subject, and body.

**Acceptance Scenarios**:

1. **Given** an approved email draft in `/Approved/` folder, **When** the orchestrator detects it, **Then** the email is sent via Gmail API and a confirmation is logged to `/Done/`

2. **Given** an email draft for a new contact (not in Company_Handbook.md), **When** Claude generates a reply, **Then** the draft is written to `/Pending_Approval/` and waits for human approval

3. **Given** an email draft for a known client, **When** the reply is routine (e.g., "Thank you for your message"), **Then** the system may auto-approve based on rules in Company_Handbook.md

4. **Given** an email send fails due to network error, **When** the MCP server detects the failure, **Then** the system retries up to 3 times with exponential backoff before alerting the user

---

### User Story 3 - Email Thread Context Management (Priority: P3)

As a business owner, I want the system to understand email thread context so that replies are relevant and reference previous conversations appropriately.

**Why this priority**: This enhances reply quality but is not essential for basic functionality. Can be added after core detection and sending work reliably.

**Independent Test**: Can be tested by sending a reply to an existing email thread and verifying that the action file includes the thread ID and previous message context.

**Acceptance Scenarios**:

1. **Given** an email is part of an existing thread, **When** the watcher detects it, **Then** the action file includes the thread ID and references to previous messages in the thread

2. **Given** Claude is drafting a reply to a thread, **When** it accesses the action file, **Then** it can read the thread context to generate a contextually appropriate response

---

### Edge Cases

- **What happens when Gmail API rate limit is exceeded?**
  - System queues pending checks and retries after the rate limit window expires
  - Logs a warning to `/Logs/` indicating rate limit was hit
  - Does not crash or lose track of pending emails

- **How does the system handle token expiry?**
  - Detects expired OAuth2 token during API call
  - Attempts automatic token refresh using refresh token
  - If refresh fails, creates an alert file in `/Needs_Action/` for human intervention
  - Pauses watcher until credentials are renewed

- **What happens when network connection is lost?**
  - Watcher catches network errors and logs them
  - Continues retry loop with exponential backoff (1s, 2s, 4s, 8s, max 60s)
  - Does not create duplicate action files when connection is restored
  - Maintains state of last successfully checked email ID

- **How does the system handle large email attachments?**
  - Action file includes attachment metadata (filename, size, type) but not content
  - Attachments larger than 10MB are noted but not downloaded automatically
  - User can manually download attachments if needed for response

- **What happens when multiple watchers run simultaneously?**
  - Each watcher instance uses file locking on state file to prevent race conditions
  - Only one watcher can claim an email for processing
  - Duplicate detection prevents multiple action files for same email

- **How does the system handle malformed or spam emails?**
  - Watcher filters emails based on Gmail's spam classification
  - Only processes emails in inbox (not spam folder)
  - Malformed email headers are logged but don't crash the watcher

- **What happens when MCP server is unavailable during send?**
  - Orchestrator detects MCP connection failure
  - Email draft remains in `/Approved/` folder
  - System retries connection every 30 seconds
  - After 10 failed attempts, creates alert in `/Needs_Action/`

- **How does the system handle concurrent email sends?**
  - MCP server processes send requests sequentially
  - Rate limiter enforces maximum 20 emails per hour
  - Queue system holds pending sends if rate limit is reached

- **What happens when email classification is uncertain?**
  - System defaults to "actionable" classification (conservative approach to avoid missing important emails)
  - Logs uncertainty score to `/Logs/` for manual review
  - User can add sender domain to Company_Handbook.md to improve future classification

- **How does the system handle emails from unknown senders not in Company_Handbook.md?**
  - Applies keyword-based filtering (checks for promotional, unsubscribe, sponsored keywords)
  - Checks sender domain patterns (noreply@, notifications@, etc.)
  - If no negative signals detected, classifies as actionable
  - Creates action file with flag indicating "unknown sender" for human review

- **What happens if Company_Handbook.md is missing or empty?**
  - System continues with keyword and domain pattern filtering only
  - Logs warning to `/Logs/` indicating handbook is unavailable
  - All emails without negative signals are classified as actionable
  - Does not crash or stop monitoring

- **How does the system handle misclassified emails?**
  - User can manually move misclassified emails between folders
  - System logs classification decisions for audit trail
  - User can update Company_Handbook.md with new rules to prevent future misclassifications
  - No automatic learning or rule modification (requires human approval)

## Requirements

### Functional Requirements

- **FR-001**: System MUST authenticate with Gmail API using OAuth2 credentials (client_id, client_secret, and user-granted token)

- **FR-002**: System MUST monitor Gmail inbox for unread emails marked as important at configurable intervals (default: every 2 minutes)

- **FR-003**: System MUST create action files in `/Needs_Action/` folder with format `EMAIL_[message_id]_[timestamp].md` containing email metadata (sender, subject, received time, snippet)

- **FR-004**: System MUST track processed email IDs to prevent duplicate action file creation

- **FR-005**: System MUST persist watcher state (last checked email ID, last check timestamp) to survive restarts

- **FR-006**: System MUST provide an MCP server with a `send_email` tool that accepts parameters: to, subject, body, dry_run (optional)

- **FR-007**: System MUST support dry-run mode where email sending is simulated and logged without actual delivery

- **FR-008**: System MUST log all email detection and sending activities to `/Logs/YYYY-MM-DD.md` with timestamps

- **FR-009**: System MUST implement retry logic with exponential backoff for transient failures (network errors, API timeouts)

- **FR-010**: System MUST enforce rate limiting: maximum 20 emails sent per hour, maximum 100 API calls per day

- **FR-011**: System MUST handle OAuth2 token refresh automatically when access token expires

- **FR-012**: System MUST create alert files in `/Needs_Action/` when critical errors occur (authentication failure, persistent API errors)

- **FR-013**: Watcher MUST be implemented in Python and placed in `src/watchers/gmail_watcher.py` extending `BaseWatcher` class

- **FR-014**: MCP server MUST be implemented in Python and placed in `mcp_servers/gmail/server.py` following MCP protocol specification

- **FR-015**: System MUST validate email addresses before sending (proper format, not empty)

- **FR-016**: System MUST include email thread ID in action files when email is part of an existing conversation

- **FR-017**: System MUST classify each detected email as "actionable" or "non-actionable" before creating action files, using classification rules based on sender domain patterns (noreply@, no-reply@, notifications@), subject keywords (unsubscribe, promotional, sponsored, newsletter), and known client domains from Company_Handbook.md

- **FR-018**: System MUST apply Gmail labels to classified emails ("actionable" or "non-actionable") and ONLY create action files in `/Needs_Action/` for emails classified as actionable

- **FR-019**: System MUST load OAuth2 credentials (GMAIL_CLIENT_ID, GMAIL_CLIENT_SECRET) from .env file and NEVER expose credentials in code or logs

### Key Entities

- **Email Message**: Represents an email detected in Gmail inbox
  - Attributes: message_id (unique Gmail ID), sender email, sender name, subject, body snippet, received timestamp, importance flag, thread_id (if part of thread), classification (actionable/non-actionable), classification_reason (why it was classified this way)
  - Relationships: Part of an email thread, may have attachments

- **Email Draft**: Represents a composed email ready to be sent
  - Attributes: recipient email, subject, body content, approval status (pending/approved/rejected), created timestamp, expires timestamp
  - Relationships: May be in response to an Email Message (thread context)

- **Watcher State**: Tracks the watcher's progress
  - Attributes: last_checked_message_id, last_check_timestamp, processed_message_ids (list)
  - Persistence: Stored in `config/gmail_watcher_state.json`

- **MCP Send Request**: Represents an email send action
  - Attributes: to, subject, body, dry_run flag, timestamp, status (pending/sent/failed)
  - Relationships: Linked to approval file in `/Approved/` folder

## Success Criteria

### Measurable Outcomes

- **SC-001**: Important emails are detected and action files created within 5 minutes of arrival in Gmail inbox

- **SC-002**: Email sending success rate is 99% or higher (excluding user-rejected drafts)

- **SC-003**: Zero duplicate action files are created for the same email across watcher restarts

- **SC-004**: System recovers automatically from transient failures (network errors, API timeouts) within 3 retry attempts

- **SC-005**: OAuth2 token refresh succeeds automatically without human intervention 95% of the time

- **SC-006**: Approval workflow completes end-to-end (detection → draft → approval → send) in under 10 minutes for routine emails

- **SC-007**: System handles 50+ emails per day without performance degradation or missed detections

- **SC-008**: Rate limiting prevents exceeding Gmail API quotas (no quota exceeded errors in logs)

- **SC-009**: Email classification accuracy is 95% or higher for known patterns (sponsored emails, platform notifications, newsletters correctly identified as non-actionable)

- **SC-010**: False negative rate (actionable emails incorrectly marked as non-actionable) is less than 2% to ensure important emails are not missed

## Assumptions

- Gmail account has "important" label configured to mark priority emails
- User has created a Google Cloud project and enabled Gmail API
- OAuth2 credentials (client_id, client_secret) are available before first run
- User will manually authorize the application on first run (browser-based OAuth flow)
- Obsidian vault structure exists with required folders (/Needs_Action, /Approved, /Done, /Logs)
- Company_Handbook.md exists and contains client information for context
- Python 3.13+ is installed with required dependencies (google-auth, google-api-python-client)
- MCP protocol SDK is available for Python
- System has stable internet connection for API calls
- User checks `/Pending_Approval/` folder regularly (at least daily) to approve drafts

## Out of Scope

- Email composition/drafting logic (handled by Claude in separate component)
- Calendar integration for meeting scheduling
- Email filtering rules beyond Gmail's "important" label
- Attachment downloading and processing
- Email search functionality
- Multi-account support (only one Gmail account per instance)
- Email archiving or folder management
- Spam detection (relies on Gmail's built-in spam filter)
- Email encryption or S/MIME support
- Custom email templates or signatures (handled in Company_Handbook.md)

## Dependencies

- **External Services**: Gmail API (Google Cloud Platform)
- **Authentication**: OAuth2 credentials from Google Cloud Console
- **Existing Components**:
  - BaseWatcher class (`src/watchers/base_watcher.py`)
  - VaultManager (`src/vault/manager.py`)
  - Orchestrator (`src/orchestrator/controller.py`)
  - Company_Handbook.md (for client context)
- **Libraries**: google-auth, google-api-python-client, MCP SDK for Python
- **Infrastructure**: Obsidian vault with folder structure, .env file for credentials

## Security & Privacy Considerations

- OAuth2 credentials (GMAIL_CLIENT_ID, GMAIL_CLIENT_SECRET) MUST be loaded from `.env` file at runtime and NEVER hardcoded or exposed in source code, logs, or error messages
- OAuth2 tokens stored in `credentials/gmail_token.json` (gitignored)
- `.env` file MUST be gitignored to prevent credential leakage to version control
- Email content logged only as snippets (first 200 characters) to protect privacy
- Full email bodies not persisted in action files (only metadata)
- Email classification decisions logged without exposing sensitive email content
- MCP server validates all input parameters to prevent injection attacks
- Rate limiting prevents abuse and quota exhaustion
- Dry-run mode available for testing without sending real emails
- All API calls use HTTPS for encryption in transit
- Tokens automatically refreshed to minimize exposure window
