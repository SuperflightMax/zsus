# last change always at the top here (under this line)

# 38
- Added a separate `operator_id`/callsign flow to the shared web client with localStorage persistence, first-open prompt, and in-UI callsign switching, while keeping the existing `client_id` session flow intact.
- Extended the HTTP adapter to accept optional `operator_id` and forward audit context (`operator_id`, `client_id`, `source="http"`) into `ChatSession` without adding business logic to the transport layer.
- Expanded `logs/actions.log` entries for executed commands to include `operator_id`, `client_id`, `source`, and `core_error` on failed core execution, plus added backend tests and docs updates for web/Android/HTTP behavior.
- Clarified the web callsign bootstrap so `operator_id`/`callsign` is not only persisted to localStorage but also no longer needs to remain in the address bar after the first load.

# 37
- Updated OPERATIONS.md to document path-based multi-instance routing, localhost-only ports, and the new ~/zs layout with nginx snippets.

# 36
- Added `/api/meta` to the HTTP adapter so clients can fetch storage title/subtitle and server version from env defaults.
- Updated the web client to load storage metadata on startup while keeping HTML fallback text intact.
- Added multi-instance ops tooling: `ops/update_all.sh`, PM2 ecosystem generation, and wrapper scripts.
- Documented multi-instance VPS layout, instance setup, and proxy/redirect notes in OPERATIONS.md.

# 35
- Normalized core location inputs so "склад" (trimmed, case-insensitive) is treated as the null/main location for intake, move, and consume.
- Added a core unit test that verifies intake, move, and consume work correctly when "склад" is provided as the location.

# 34
- Added unit tracking to storage entries with default `"од"` and enabled fractional quantities throughout core validation and arithmetic.
- Implemented automatic SQLite migration to add the `unit` column on activation and updated list snapshot payloads to include `{qty, unit}` per location.
- Adjusted CLI/LLM snapshot tables to render unit/quantity formatting consistently and expanded tests/scenarios/documentation for the new behavior.

# 33
- Removed the web client startup microphone permission probe so mic prompts and warnings only happen after user interaction.
- Updated Android WebView permission handling to wait for runtime audio permission results before granting or denying audio capture, preventing false warnings.

# 32
- Removed the checked-in Gradle wrapper JAR from the Android client so it can be added locally for builds.

# 31
- Added a minimal Android WebView client under `/android` with a Gradle wrapper, single-activity WebView shell, and required permissions per CLIENT_ANDROID.md.
- Documented manual Android Studio APK build steps and distribution notes in OPERATIONS.md.

# 30
- Prevented the web client from refocusing the text input after voice autosend, avoiding mobile keyboard pop-ups during voice input.

# 29
- Added VPS-friendly HTTP server lifecycle scripts (`start.sh`, `stop.sh`, `restart.sh`, `status.sh`) with PID/log handling and status reporting.
- Updated `update.sh` to stop and restart the HTTP server automatically during updates unless opt-out is set.
- Documented new VPS scripts and update behavior in operations guide.

# 28
- Requested microphone permission on web client load to make voice input UX smoother.
- Prevented long-press selection on the mic button and added a “listening...” placeholder plus a hold-to-talk hint below the mic UI.

# 27
- Added `/api/config` to expose client configuration flags with safe env parsing and defaults.
- Added web client Web Speech hold-to-talk mic UI, autosend control, and one-time permission denial message driven by `/api/config`.

# 26
- Switched web client asset and API paths to relative URLs so the UI works from the root or a reverse-proxy subpath.

# 25
- Fixed web chat auto-scroll to use the scrollable chat container so new messages stay visible after user input and async replies.

# 24
- Made chat auto-scroll fire on every DOM update so the latest message is always fully visible.

# 23
- Fixed SQLite backend usage for threaded HTTP requests by allowing cross-thread connections and serializing access per storage.
- Added chat UI auto-scroll after responses and error updates to keep the latest message visible.

# 22
- Added built-in static web client assets (`/web`) and served them from the HTTP server, with `/` loading the chat UI.
- Added `/api/chat` as the primary HTTP endpoint while keeping `/chat` as a backward-compatible alias, including static content types and safe path handling.
- Updated Windows HTTP helper to open the root URL and refreshed HTTP documentation to cover the new web client routes.

# 21
- Added a minimal HTTP interface package with `/health` and `/chat` endpoints, using standard library HTTP server and per-client sessions.
- Added HTTP runner scripts (`http.sh`, `httpw.bat`) and documented the HTTP adapter in a structured Markdown spec.
- Added a non-critical doctor check for `ZSUS_HTTP_PORT` validity to catch bad env values.

# 20
- Added root-level VPS helper scripts (`boot.sh`, `update.sh`, `cli.sh`, `doctor.sh`) to streamline Ubuntu 24.04 prototype deployments.
- Scripted bootstrap, update, CLI execution, and environment health checks with minimal dependencies and clear failure signaling.
- Documented the new operational flow in OPERATIONS.md.

# 19
- Added session layer (ChatSession + SessionManager) to centralize LLM dialogue context and command execution for client-agnostic interfaces.
- Refactored CLI to delegate normal text handling to ChatSession while keeping admin commands, scenario runner, and output formatting unchanged.
- Added tests covering ChatSession context retention/clearing behavior and updated change logs.

# 18
- Escaped JSON examples in the LLM operator prompt template to avoid format errors after adding dialogue context formatting.

# 17
- Added in-memory dialogue context tracking in CLI sessions and passed it to LLM requests for short follow-up replies.
- Logged the exact dialogue context in the CLI SYSTEM output alongside snapshots for debugging.
- Documented the dialogue context lifecycle (retain on need_more_info, clear on completion) in LLM design notes.

# 16
- Added CLI admin toggles `+outsystemshow`/`+outsystemhide` (`+oss`/`+osh`) to control SYSTEM output visibility for LLM responses only, leaving admin and core outputs unchanged.
- Added `cli.show_system_llm` config default (false) and documented the new behavior in CLI docs.

# 15
- Escaped literal braces in the operator user prompt template to avoid format-time KeyError when rendering LLM prompts.

# 14
- Implemented OpenAI-backed LLM operator pipeline for CLI: builds a snapshot via core list, formats operator prompts, calls OpenAI, strictly parses/validates JSON, and returns assistant text plus command list or clarification questions.
- Added minimal OpenAI client with timeout and single retry on 429/5xx, plus explicit SYSTEM logging of model usage and key presence without leaking the key.
- Integrated LLM flow into CLI for non-admin, non-JSON input, emitting full SYSTEM traces (snapshot, raw/parsed LLM JSON, commands, core results) and USER Ukrainian responses.
- Added append-only action journal at `logs/actions.log` with one JSON line per executed command for later audits.
- Added operator prompts and updated README/CLI/MVP/ROADMAP docs to align with dialog-capable LLM usage and quick-start instructions.

# 13
- CLI now reads `DEFAULT_STORAGE` from `.env` on startup, activating the storage if it exists and logging a warning if it does not.
- Removed the LLM enable/disable flag so the interpreter always responds, and cleaned up the default config/env templates accordingly.

# 12
- Introduced `OperationResult` as the unified response object for core and interfaces, carrying `ok`, `user_text`, `system_log`, and `data`, and refactored the CLI to render distinct `-------- SYSTEM:` / `-------- USER:` blocks.
- Centralized command defaults (`DEFAULT_QTY`, `DEFAULT_LOCATION`) and routed all incoming commands through a policy layer that applies defaults, validates required fields, and returns structured failures without raising for user scenarios.
- Added tests for the new result shape, policy defaults, and updated expectation matcher to support the new `ok` contract while preserving partial data checks.

# 11
- Added short admin aliases `+ls` (list storages), `+li` (list items of active storage), and `+as` (activate storage) to reduce typing in the CLI.
- Added a Windows helper script `cliw.bat` that creates/activates `.venv` and runs `python -m src.interfaces.cli.main` from the repository root.

# 10
- Implemented a SQLite storage backend that follows the existing StorageBackend contract, using per-storage database files (`storages/<storage_id>/storage.db` by default) to persist state across CLI runs.
- CLI now loads the backend from configuration (`storage.backend`, `storage.sqlite_filename`), reports it via `+status`, and keeps in-memory as the default for tests and quick runs.

# 9
- Added admin CLI command `+listitems` that prints active storage contents as a readable table, with `(unplaced)` shown for `null` locations and truncation for long values based on `cli.table_max_width` (default 24).
- Documented the core `list` command contract and updated CLI documentation to cover the new admin output and truncation behavior.
- Introduced a CLI configuration option `table_max_width` in `config/default.yaml` to tune table readability without code changes.

# 8
- Relaxed scenario runner expectation checks: `"ok"` now verifies only status, and dict expectations validate only specified keys inside `data` while allowing extra fields, keeping status required to be `ok`.
- Added targeted tests for the new expectation semantics to lock in the partial-match behavior.

# 7
- Implemented a comprehensive pytest suite for the core engine validating intake, move, consume, find, list, storage isolation, and unknown command handling while enforcing response invariants and state immutability on errors.
- Added CLI scenario runner (`+runscenario` with optional `--isolated`) that reads JSON scenarios, injects storage_id, executes steps with partial matching, reports per-step status, and cleans up temporary storages in isolated mode.
- Updated testing documentation to reflect the implemented unit tests and the JSON-based scenario workflow, plus documented the new CLI command.

# 6
- Deferred the new core engine test suite for a later task while keeping the in-memory core implementation intact.
- Documented the temporary removal to keep change tracking aligned with current scope.

# 5
- Implemented a real in-memory `CoreEngine` with a `StorageBackend` abstraction and default `InMemoryStorageBackend`, enabling deterministic stateful operations without external storage.
- Added full command handling for `intake`, `move`, `consume`, `list`, and `find`, including validation, error responses, and per-location aggregation.
- Provided module-level `handle_command` for interfaces while keeping `CoreEngine` instantiable for tests and development.
- Added core tests covering the new command behaviors and edge cases.

# 4
- Added admin CLI commands (`+createstorage`, `+deletestorage`, `+liststorages`, `+activatestorage`, `+status`) that manage storages through the infrastructure registry without touching core logic.
- Introduced in-memory `active_storage_id` handling with automatic `storage_id` injection into JSON commands and a guard message when no storage is active.
- Implemented dynamic CLI prompt templating that reflects the active storage (`bot>` vs `bot:<storage_id>`).
- Documented the new CLI behaviors and updated defaults for prompt configuration.

# 3
- Added multiline JSON input mode to the CLI: when input starts with `{`, the CLI collects a JSON block with a dedicated prompt, finishes when braces balance or on an empty line, and forwards parsed commands to the core.
- Added neutral error handling for malformed JSON while preserving normal text echo behavior.
- Documented the updated CLI flow.

# 2
- Added minimal passthrough from CLI to core: JSON input is parsed, forwarded to `core.engine.handle_command`, and responses are printed back to the user while plain text is echoed unchanged.
- Simplified `core.engine.handle_command` to validate structure (presence of `command`) and return a stub `{ "status": "ok", "data": {} }` response.
- Updated CLI documentation and tracked changes in HISTORY and CHANGELOG.

# 1

- Introduced a Python skeleton aligned with repository architecture: `core`, `llm`, `media`, `knowledge`, `interfaces/cli`, and `infra` packages with placeholder modules ready for future logic.
- Implemented configuration loading via `.env`, default YAML, and optional override path to support cascading storage-specific settings without hardcoding values.
- Added CLI stub that reads prompt/exit commands from config, echoes user input, and gracefully exits on configured commands (`exit`, `quit`).
- Restored documented default parameters for storages, core settings (audit, confidence threshold, language), media limits, and knowledge paths to avoid magic values.
- Documented available CLI commands in `CLI.md` and initialized change tracking files for ongoing documentation and release notes.
- start 2025-12-19
