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
