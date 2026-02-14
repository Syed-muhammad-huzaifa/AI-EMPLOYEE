# Data Model: Gmail Integration for AI Employee

**Feature**: 001-gmail-integration
**Date**: 2026-02-12
**Source**: Extracted from spec.md Key Entities section

## Overview

This document defines the data structures and relationships for the Gmail integration feature. The model supports email detection, classification, state persistence, and sending workflows.

---

## Entity Definitions

### 1. Email Message

**Purpose**: Represents an email detected in Gmail inbox

**Attributes**:

| Field | Type | Required | Description | Validation Rules |
|-------|------|----------|-------------|------------------|
| message_id | string | Yes | Unique Gmail message ID | Non-empty, format: alphanumeric |
| sender_email | string | Yes | Email address of sender | RFC 5322 format |
| sender_name | string | No | Display name of sender | Max 200 chars |
| subject | string | Yes | Email subject line | Max 500 chars |
| body_snippet | string | Yes | First 200 characters of body | Exactly 200 chars or less |
| received_timestamp | datetime | Yes | When email was received | ISO 8601 format |
| importance_flag | boolean | Yes | Gmail importance marker | true/false |
| thread_id | string | No | Gmail thread ID if part of conversation | Alphanumeric |
| classification | enum | Yes | Actionable or non-actionable | "actionable" \| "non-actionable" |
| classification_reason | string | Yes | Why it was classified this way | One of: "domain_pattern", "keyword_match", "handbook_client", "default_actionable" |

**Relationships**:
- Part of an EmailThread (via thread_id)
- May have Attachments (metadata only, not downloaded)

**State Transitions**:
```
[Detected] → [Classified] → [Action File Created] (if actionable)
                         → [Labeled in Gmail] (if non-actionable)
```

**Example**:
```json
{
  "message_id": "18d4f2a3b5c6d7e8",
  "sender_email": "client@example.com",
  "sender_name": "John Client",
  "subject": "Project update needed",
  "body_snippet": "Hi, I wanted to follow up on the project timeline...",
  "received_timestamp": "2026-02-12T10:30:00Z",
  "importance_flag": true,
  "thread_id": "18d4f2a3b5c6d7e0",
  "classification": "actionable",
  "classification_reason": "handbook_client"
}
```

---

### 2. Email Draft

**Purpose**: Represents a composed email ready to be sent

**Attributes**:

| Field | Type | Required | Description | Validation Rules |
|-------|------|----------|-------------|------------------|
| draft_id | string | Yes | Unique identifier for draft | UUID v4 format |
| recipient_email | string | Yes | Email address of recipient | RFC 5322 format, non-empty |
| subject | string | Yes | Email subject line | Max 500 chars, non-empty |
| body_content | string | Yes | Full email body (plain text or HTML) | Max 50KB |
| approval_status | enum | Yes | Current approval state | "pending" \| "approved" \| "rejected" |
| created_timestamp | datetime | Yes | When draft was created | ISO 8601 format |
| expires_timestamp | datetime | Yes | When draft expires if not approved | ISO 8601, must be > created_timestamp |
| in_reply_to_message_id | string | No | If replying to an email | Gmail message ID |
| thread_id | string | No | If part of existing thread | Gmail thread ID |

**Relationships**:
- May be in response to an EmailMessage (via in_reply_to_message_id)
- Part of approval workflow (file in /Pending_Approval/ or /Approved/)

**State Transitions**:
```
[Created] → [Pending Approval] → [Approved] → [Sent] → [Archived to /Done/]
                               → [Rejected] → [Archived to /Rejected/]
                               → [Expired] → [Archived to /Rejected/]
```

**File Naming Convention**:
- Pending: `/Pending_Approval/EMAIL_DRAFT_{draft_id}_{timestamp}.md`
- Approved: `/Approved/EMAIL_DRAFT_{draft_id}_{timestamp}.md`

**Example**:
```json
{
  "draft_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "recipient_email": "client@example.com",
  "subject": "Re: Project update needed",
  "body_content": "Hi John,\n\nThank you for reaching out...",
  "approval_status": "pending",
  "created_timestamp": "2026-02-12T11:00:00Z",
  "expires_timestamp": "2026-02-13T11:00:00Z",
  "in_reply_to_message_id": "18d4f2a3b5c6d7e8",
  "thread_id": "18d4f2a3b5c6d7e0"
}
```

---

### 3. Watcher State

**Purpose**: Tracks the watcher's progress and prevents duplicate processing

**Attributes**:

| Field | Type | Required | Description | Validation Rules |
|-------|------|----------|-------------|------------------|
| last_checked_message_id | string | Yes | Most recent message ID processed | Gmail message ID format |
| last_check_timestamp | datetime | Yes | When last check completed | ISO 8601 format |
| processed_message_ids | array[string] | Yes | List of all processed message IDs | Max 1000 entries (rolling window) |
| classification_stats | object | Yes | Statistics for monitoring | See ClassificationStats below |

**ClassificationStats Object**:
```json
{
  "total_processed": integer,
  "actionable": integer,
  "non_actionable": integer,
  "domain_pattern_filtered": integer,
  "keyword_filtered": integer,
  "handbook_matched": integer,
  "default_actionable": integer
}
```

**Persistence**:
- Stored in: `config/gmail_watcher_state.json`
- Updated: After each successful check cycle
- Backup: Previous state kept as `gmail_watcher_state.json.bak`

**State Transitions**:
```
[Initial] → [Running] → [Updated after each cycle] → [Persisted on shutdown]
```

**Example**:
```json
{
  "last_checked_message_id": "18d4f2a3b5c6d7e8",
  "last_check_timestamp": "2026-02-12T10:35:00Z",
  "processed_message_ids": [
    "18d4f2a3b5c6d7e8",
    "18d4f2a3b5c6d7e7",
    "18d4f2a3b5c6d7e6"
  ],
  "classification_stats": {
    "total_processed": 150,
    "actionable": 45,
    "non_actionable": 105,
    "domain_pattern_filtered": 60,
    "keyword_filtered": 30,
    "handbook_matched": 35,
    "default_actionable": 10
  }
}
```

---

### 4. MCP Send Request

**Purpose**: Represents an email send action invoked via MCP server

**Attributes**:

| Field | Type | Required | Description | Validation Rules |
|-------|------|----------|-------------|------------------|
| request_id | string | Yes | Unique request identifier | UUID v4 format |
| to | string | Yes | Recipient email address | RFC 5322 format, non-empty |
| subject | string | Yes | Email subject line | Max 500 chars, non-empty |
| body | string | Yes | Email body content | Max 50KB |
| dry_run | boolean | No | Simulate send without delivery | Default: false |
| timestamp | datetime | Yes | When request was received | ISO 8601 format |
| status | enum | Yes | Current request status | "pending" \| "sent" \| "failed" |
| error_message | string | No | Error details if status=failed | Max 1000 chars |
| approval_file_path | string | Yes | Path to approval file in /Approved/ | Absolute path |

**Relationships**:
- Linked to approval file in `/Approved/` folder
- May reference an EmailDraft (via approval file content)

**State Transitions**:
```
[Received] → [Validated] → [Pending] → [Sent] → [Logged to /Done/]
                        → [Failed] → [Retry] → [Sent] or [Permanently Failed]
```

**Example**:
```json
{
  "request_id": "b2c3d4e5-f6a7-8901-bcde-f12345678901",
  "to": "client@example.com",
  "subject": "Re: Project update needed",
  "body": "Hi John,\n\nThank you for reaching out...",
  "dry_run": false,
  "timestamp": "2026-02-12T11:05:00Z",
  "status": "sent",
  "error_message": null,
  "approval_file_path": "/home/user/vault/Approved/EMAIL_DRAFT_a1b2c3d4_20260212.md"
}
```

---

## Validation Rules Summary

### Email Address Validation (RFC 5322)
```python
import re

EMAIL_REGEX = re.compile(
    r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
)

def validate_email(email: str) -> bool:
    return bool(EMAIL_REGEX.match(email))
```

### Classification Rules (Applied in Order)

1. **Domain Pattern Check** (non-actionable if matches):
   ```python
   NON_ACTIONABLE_PATTERNS = [
       r'^noreply@',
       r'^no-reply@',
       r'^notifications@',
       r'^donotreply@',
       r'@facebookmail\.com$',
       r'@linkedin\.com$',
       r'@twitter\.com$'
   ]
   ```

2. **Keyword Check** (non-actionable if subject contains):
   ```python
   NON_ACTIONABLE_KEYWORDS = [
       'unsubscribe',
       'promotional',
       'sponsored',
       'newsletter',
       'marketing'
   ]
   ```

3. **Handbook Lookup** (actionable if sender domain in handbook):
   - Parse `Company_Handbook.md` for `## Clients` section
   - Extract domain list
   - Match sender domain against list

4. **Default**: If no rules match → classify as "actionable"

---

## Relationships Diagram

```
EmailMessage
    ├─ has classification (actionable/non-actionable)
    ├─ may be part of EmailThread
    └─ may trigger EmailDraft creation (if actionable)

EmailDraft
    ├─ may reply to EmailMessage
    ├─ has approval_status (pending/approved/rejected)
    └─ triggers MCPSendRequest (if approved)

WatcherState
    ├─ tracks processed EmailMessages
    └─ maintains classification statistics

MCPSendRequest
    ├─ linked to EmailDraft (via approval file)
    └─ has status (pending/sent/failed)
```

---

## Storage Locations

| Entity | Storage Type | Location | Gitignored |
|--------|-------------|----------|------------|
| EmailMessage | Action file (.md) | `/Needs_Action/EMAIL_{message_id}_{timestamp}.md` | No |
| EmailDraft | Approval file (.md) | `/Pending_Approval/` or `/Approved/` | No |
| WatcherState | JSON file | `config/gmail_watcher_state.json` | Yes |
| MCPSendRequest | Log entry | `/Logs/YYYY-MM-DD.md` | No |
| OAuth2 Tokens | JSON file | `credentials/gmail_token.json` | Yes |

---

## Data Retention Policy

- **Action Files**: Moved to `/Done/` after processing, retained indefinitely
- **Approval Files**: Moved to `/Done/` or `/Rejected/` after decision, retained for 90 days
- **Watcher State**: Rolling window of last 1000 processed message IDs
- **Logs**: Retained for 1 year, rotated daily
- **OAuth2 Tokens**: Retained until manually revoked

---

## Security Considerations

- **PII Protection**: Email bodies stored as snippets only (200 chars max) in action files
- **Credential Isolation**: OAuth2 tokens in separate gitignored file
- **No Plaintext Secrets**: All credentials loaded from .env at runtime
- **Audit Trail**: All classification decisions logged with reasoning
