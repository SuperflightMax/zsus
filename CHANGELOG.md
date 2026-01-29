# last change always at the top here (under this line)

# 34
- Added unit tracking and fractional quantities in core storage with automatic SQLite migration for the new `unit` column, plus updated list snapshots to return `{qty, unit}` entries.
- Updated LLM/CLI snapshot tables to show Unit with consistent quantity formatting, and refreshed tests/docs to match the new behavior.

# 33
- Removed the web client startup microphone permission probe so audio permission is only requested on user mic action.
- Updated Android WebView permission handling to defer audio capture grants/denials until runtime permission is resolved, avoiding false-deny warnings on startup.

# 32
- Removed the checked-in Gradle wrapper JAR from the Android client to allow local addition during builds.

# 31
- Added a minimal Android WebView client project under `/android` with Gradle wrapper, permissions, and WebView configuration per CLIENT_ANDROID.md.
- Documented manual Android Studio APK build steps in OPERATIONS.md.

# 30
- Prevented the web client from refocusing the text input after voice autosend, avoiding mobile keyboard pop-ups during voice input.

# 29
- Added VPS-friendly HTTP server lifecycle scripts with PID/log handling.
- Updated `update.sh` to stop and restart the HTTP server around updates unless opted out.
- Documented the new VPS scripts and update behavior in operations guide.

# 28
- Polished web mic UX: request mic permission on load, prevent long-press selection menu, show listening placeholder, and add a hold-to-talk hint.

# 27
- Added `/api/config` with environment-driven client flags and safe parsing for web speech defaults.
- Added web client Web Speech hold-to-talk mic UI with autosend toggle, permission-deny messaging, and config fetch.

# 26
- Switched web client asset and API paths to relative URLs so the UI works from the root or a reverse-proxy subpath.

# 25
- Fixed web chat auto-scroll to target the scrollable chat container so new messages stay in view after user input and async replies.


# 24
- Made chat auto-scroll fire on every DOM update so the latest message is always visible.

# 23
- Fixed SQLite backend usage for threaded HTTP requests by allowing cross-thread connections and serializing access per storage.
- Added chat UI auto-scroll so the latest reply stays visible after updates.

# 22
- Added a built-in static web client served by the HTTP server at `/` and `/web/*`.
- Added `/api/chat` as the primary HTTP endpoint while keeping `/chat` as a compatibility alias.
- Updated `httpw.bat` and HTTP documentation to reflect the new web client routing.

# 21
- Added a minimal HTTP interface (`/health`, `/chat`) using the standard library HTTP server and per-client sessions.
- Added `http.sh` and `httpw.bat` helpers for launching the HTTP adapter.
- Added a non-critical doctor check for `ZSUS_HTTP_PORT` validity and formatted HTTP.md as a proper spec.

# 20
- Added root-level VPS helper scripts (boot, update, CLI, doctor) for Ubuntu 24.04 prototype deployments.
- Documented the new scripts in OPERATIONS.md.

# 19
- Introduced session layer (ChatSession + SessionManager) to handle LLM dialogue context and command execution for client-agnostic interfaces.
- Updated CLI to use ChatSession for normal text input while preserving admin commands and output formatting.
- Added ChatSession unit tests for context retention and clearing behavior.

# 18
- Escaped JSON examples in the LLM operator prompt template to prevent format-time KeyError when rendering dialogue context prompts.

# 17
- Added CLI-scoped dialogue context memory that is sent with each LLM request and cleared after completion when need_more_info is false.
- Included the dialogue context in CLI SYSTEM output for traceability and updated LLM design documentation.

# 16
- Added CLI admin commands `+outsystemshow`/`+outsystemhide` (`+oss`/`+osh`) to toggle SYSTEM output for LLM responses without affecting admin/core output.
- Added `cli.show_system_llm` default config (false) and documented the new CLI behavior.

# 15
- Escaped literal braces in operator prompt template to prevent Python format errors during LLM prompt rendering.

# 14
- Added OpenAI-powered LLM operator pipeline with strict JSON parsing, snapshot context, command execution tracing, and action journal logging for CLI debug runs.
- Added operator prompts and CLI routing updates so natural language goes through the LLM while admin commands and JSON passthrough remain unchanged.
- Updated docs (README, CLI, MVP, ROADMAP) to reflect the new LLM dialog behavior and quick-start instructions.

# 13
- Added `DEFAULT_STORAGE` support for CLI startup to auto-activate an existing storage from `.env` and documented the behavior.
- Removed the LLM enable/disable switch so the interpreter always runs, and trimmed related config/env toggles.

# 12
- Unified command responses under `OperationResult` with explicit `ok`, `user_text`, `system_log`, and `data`, and updated CLI to print separated SYSTEM/USER blocks with structured logs.
- Centralized defaults (`DEFAULT_QTY`, `DEFAULT_LOCATION`) and applied them via a policy layer before the core engine, plus standardized user-facing error texts without raises/prints.

# 10
- Added SQLite storage backend that mirrors in-memory semantics while persisting state with per-storage database files inside each storage directory.
- CLI now selects backend via config (`storage.backend` / `storage.sqlite_filename`) and reports the active backend in `+status`.

# 9
- Added admin CLI command `+listitems` to print the active storage contents as a readable table with configurable truncation (`cli.table_max_width`, default 24).
- Documented the core `list` command and updated CLI docs to cover the new admin command.

# 8
- Adjusted scenario runner expectation matching to treat dict expectations as partial checks against `data` (status must be `ok`, extra fields allowed) and keep `"ok"` as a status-only check.
- Added unit tests covering the relaxed expectation semantics to prevent regressions.

# 7
- Added full pytest suite for the core engine covering intake, move, consume, find, list, storage isolation, and unknown commands with invariant checks.
- Extended CLI with JSON scenario runner (`+runscenario` / `--isolated`) that executes steps with per-step output and temporary storage lifecycle.

# 6
- Deferred the new core engine tests for now; core functionality remains available via the in-memory backend.

# 5
- Added in-memory `CoreEngine` with `StorageBackend` abstraction, implementing `intake`, `move`, `consume`, `list`, and `find` commands with validation and deterministic responses, plus core tests.

# 4
- Added admin CLI commands for storage management, active storage tracking, and dynamic prompt templating that injects `storage_id` into JSON commands and blocks core calls when no storage is active.

# 3
- CLI supports multiline JSON input with a dedicated prompt, finishing on balanced braces or an empty line, and keeps neutral handling of malformed JSON while preserving plain-text echo.

# 2
- CLI now forwards JSON input directly to the core engine and prints JSON responses while echoing plain text.
- Core engine stub validates basic structure and returns an OK placeholder response.

# 1
- Added skeleton modules, configuration loader with overrides, and CLI/documentation stubs.
