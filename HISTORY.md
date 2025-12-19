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
