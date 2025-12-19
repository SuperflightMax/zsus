# 2024-05-16
- CLI supports multiline JSON input with a dedicated prompt, finishing on balanced braces or an empty line, and keeps neutral handling of malformed JSON while preserving plain-text echo.

# 2024-05-15
- CLI now forwards JSON input directly to the core engine and prints JSON responses while echoing plain text.
- Core engine stub validates basic structure and returns an OK placeholder response.

# 2024-05-14
- Added skeleton modules, configuration loader with overrides, and CLI/documentation stubs.
