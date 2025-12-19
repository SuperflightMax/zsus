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