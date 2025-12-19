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
