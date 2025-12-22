# 11
- Added LLM Interpreter that converts український текст у структурований JSON контракт core (intake/move/consume/find/list/unknown) з правилами підтвердження.
- Introduced dedicated system prompt file and configuration via environment (`LLM_ENABLED`, `OPENAI_*`, `OPENAI_MODEL=gpt-4.1`), plus OpenAI dependency.
- Documented LLM flow and tests; added targeted unit tests for ключові сценарії.

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
