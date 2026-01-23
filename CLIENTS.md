# Clients / Interfaces Integration

## Purpose
Make the system client-agnostic:
- CLI, Web, Telegram, Android, etc. must plug in without changing core/LLM logic.
- Each user has an isolated dialogue context ("session").
- CLI can show both SYSTEM and USER outputs.
- Any user-facing client receives ONLY USER output.

This is a prototype: keep it simple, elegant, no premature “what if…”.

## Key rule (contract)
The only universal output is `OperationResult`:
- `user_text`  -> what any client must show to a user (chat UI)
- `system_log` -> diagnostics; CLI may show it, clients must ignore it
- `ok`         -> success/failure

## Architecture (layers)

### 1) Core (domain)
`src/core/*`
- Executes commands and returns `OperationResult`.
- Knows nothing about chat, sessions, transports.

### 2) LLM operator
`src/llm/*`
- Converts (user input + dialogue context + snapshot) into:
  - assistant text
  - commands[]
  - questions / need_more_info
- Knows nothing about transports.

### 3) Session layer (the universal “chat brain”)
New package: `src/session/*`

#### ChatSession
A ChatSession represents one user conversation context (in-memory).
Responsibilities:
- store `dialogue_context` (same format as CLI today, e.g. "USER: ...", "ASSISTANT: ...")
- call `LLMOperator.run(...)`
- execute returned commands via `core.engine.handle_command`
- produce `OperationResult` with:
  - user_text = assistant reply (and questions if needed)
  - system_log = debug trace (context, snapshot, raw JSON, executed commands etc.)
- keep semantics identical to current CLI UX:
  - if need_more_info -> keep context (do not clear)
  - if success without need_more_info -> clear context after execution (current behavior)
  - on LLM failure without need_more_info -> clear context (current behavior)

ChatSession should be input-type ready:
- MVP uses only text input
- future inputs: image/audio will be handled by adding "USER_IMAGE:" / "USER_AUDIO:" records in the same context.

#### SessionManager
Stores multiple ChatSessions in memory:
- map: `client_id -> ChatSession`
- returns existing session or creates a new one
- (prototype) no persistence; losing sessions on restart is OK

## Interfaces (clients)

### CLI interface
`src/interfaces/cli/*`
- CLI remains a full-featured interface (admin commands, scenarios, system output).
- CLI uses ChatSession for "regular user text" flow.
- CLI can print:
  - SYSTEM block from OperationResult.system_log (toggle)
  - USER block from OperationResult.user_text

### User clients (Web/Telegram/Android)
- Must only display `OperationResult.user_text` to the user.
- Must never rely on system_log formatting.
- Must not implement dialogue context logic. Ever.

## Minimal client contract
Any client must provide:
- `client_id` (string)
  - MVP: random UUID stored locally, no auth required
- `text` (string) for MVP

Flow:
1) receive text from user
2) session = session_manager.get(client_id)
3) result = session.handle_text(text)
4) display result.user_text only

## Future (not in MVP)
- auth / roles / permissions: SessionManager maps client_id -> user_id -> permissions
- attachments: upload -> file_ref -> session.handle_input(type=image/audio, file_ref=...)
- persistence: ContextStore(sqlite) for sessions (optional later)
