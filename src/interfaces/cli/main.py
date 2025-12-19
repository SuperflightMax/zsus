"""Command-line interface with admin commands and scenario runner."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import uuid4

from ...infra import load_config
from ...infra.storage_registry import StorageRegistry
from ...core.engine import handle_command


def configure_logging(level_name: str) -> None:
    level = getattr(logging, level_name.upper(), logging.INFO)
    logging.basicConfig(level=level, format="%(levelname)s: %(message)s")


def run() -> None:
    config = load_config()
    configure_logging(config.get("logging", {}).get("level", "INFO"))

    prompt_template = _get_prompt_template(config)
    json_prompt = config.get("cli", {}).get("json_prompt", "... ")
    exit_commands = config.get("cli", {}).get("exit_commands", ["exit"])
    registry = StorageRegistry(config)
    active_storage_id: Optional[str] = None

    logging.info("CLI started. Type an exit command to quit.")

    collecting_json = False
    json_lines: List[str] = []
    brace_balance = 0

    try:
        while True:
            prompt = json_prompt if collecting_json else _format_prompt(prompt_template, active_storage_id)
            user_input = input(prompt)

            if not collecting_json:
                if user_input.strip() in exit_commands:
                    logging.info("Exiting CLI.")
                    break

                logging.info("Received input: %s", user_input)

                if user_input.startswith("+"):
                    active_storage_id = _handle_admin_command(
                        user_input,
                        registry=registry,
                        active_storage_id=active_storage_id,
                    )
                    continue

                if _starts_json(user_input):
                    if active_storage_id is None:
                        print("No active storage. Use +activatestorage first.")
                        continue

                    collecting_json = True
                    json_lines = [user_input]
                    brace_balance = _update_brace_balance(brace_balance, user_input)
                    if _json_complete(brace_balance, user_input):
                        _process_json_block("\n".join(json_lines), active_storage_id)
                        collecting_json = False
                        json_lines = []
                        brace_balance = 0
                else:
                    print(user_input)
            else:
                json_lines.append(user_input)
                brace_balance = _update_brace_balance(brace_balance, user_input)

                if _json_complete(brace_balance, user_input):
                    _process_json_block("\n".join(json_lines), active_storage_id)
                    collecting_json = False
                    json_lines = []
                    brace_balance = 0

    except KeyboardInterrupt:
        logging.info("CLI interrupted by user.")


def _get_prompt_template(config: Dict[str, Any]) -> str:
    cli_config = config.get("cli", {})
    return cli_config.get("prompt_template") or cli_config.get("prompt", "> ")


def _format_prompt(template: str, active_storage_id: Optional[str]) -> str:
    storage_suffix = f":{active_storage_id}" if active_storage_id else ""
    return template.replace("{storage}", storage_suffix)


def _handle_admin_command(
    command_line: str,
    registry: StorageRegistry,
    active_storage_id: Optional[str],
) -> Optional[str]:
    tokens = command_line[1:].strip().split()
    if not tokens:
        print("Unknown admin command.")
        return active_storage_id

    command = tokens[0].lower()
    args = tokens[1:]

    if command == "createstorage":
        if not args:
            print("Usage: +createstorage <storage_id>")
            return active_storage_id
        storage_id = args[0]
        created = registry.create_storage(storage_id)
        if created:
            print(f"Storage created: {storage_id}")
        else:
            print(f"Storage already exists: {storage_id}")
        return active_storage_id

    if command == "deletestorage":
        if not args:
            print("Usage: +deletestorage <storage_id>")
            return active_storage_id
        storage_id = args[0]
        deleted = registry.delete_storage(storage_id)
        if deleted:
            print(f"Storage deleted: {storage_id}")
            if active_storage_id == storage_id:
                return None
        else:
            print(f"Storage not found: {storage_id}")
        return active_storage_id

    if command == "liststorages":
        storages = registry.list_storages()
        if not storages:
            print("(no storages)")
            return active_storage_id

        for storage in storages:
            marker = " (active)" if storage == active_storage_id else ""
            print(f"- {storage}{marker}")
        return active_storage_id

    if command == "activatestorage":
        if not args:
            print("Usage: +activatestorage <storage_id>")
            return active_storage_id
        storage_id = args[0]
        if not registry.storage_exists(storage_id):
            print(f"Storage not found: {storage_id}")
            return active_storage_id
        print(f"Active storage set to: {storage_id}")
        return storage_id

    if command == "status":
        print("CLI status:")
        print(f"- Active storage: {active_storage_id or 'none'}")
        print("- Backend: in-memory")
        storages = registry.list_storages()
        print(f"- Known storages: {len(storages)}")
        return active_storage_id

    if command == "runscenario":
        isolated = False
        files: List[str] = []
        for arg in args:
            if arg == "--isolated":
                isolated = True
            else:
                files.append(arg)

        if not files:
            print("Usage: +runscenario [--isolated] <file>")
            return active_storage_id

        scenario_file = files[0]
        if not isolated and active_storage_id is None:
            print("No active storage. Use +activatestorage or --isolated.")
            return active_storage_id

        _run_scenario(scenario_file, registry, active_storage_id, isolated)
        return active_storage_id

    print(f"Unknown admin command: +{command}")
    return active_storage_id


def _starts_json(text: str) -> bool:
    """Return True if the input should be treated as JSON."""
    return text.strip().startswith("{")


def _json_complete(brace_balance: int, latest_line: str) -> bool:
    """Determine whether the collected JSON block is complete.

    Completion rules:
    - braces balanced (<= 0 to allow immediate single-line completion)
    - OR empty line
    """

    return brace_balance <= 0 or latest_line.strip() == ""


def _process_json_block(text: str, active_storage_id: str) -> None:
    """Parse and dispatch a collected JSON block."""

    if not active_storage_id:
        print("No active storage. Use +activatestorage first.")
        return

    parsed = _try_parse_json(text)
    if parsed is None:
        print("Не удалось прочитать JSON. Попробуйте ещё раз.")
        return

    parsed_with_storage = dict(parsed)
    parsed_with_storage["storage_id"] = active_storage_id
    response = handle_command(parsed_with_storage)
    print(json.dumps(response, ensure_ascii=False, indent=2))


def _try_parse_json(text: str) -> Dict[str, Any] | None:
    """Attempt to parse JSON input; return None on failure.

    JSON detection is intentionally simple: if the text starts with ``{`` and
    parses successfully, it is treated as a command for the core engine.
    Otherwise, the input is handled as plain text.
    """

    if not text.strip().startswith("{"):
        return None

    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        return None

    return parsed if isinstance(parsed, dict) else None


def _update_brace_balance(current_balance: int, text: str) -> int:
    """Update brace balance counter based on the provided text."""

    return current_balance + text.count("{") - text.count("}")


def _run_scenario(
    file_path: str,
    registry: StorageRegistry,
    active_storage_id: Optional[str],
    isolated: bool,
) -> None:
    """Execute a JSON scenario file step-by-step."""

    scenario_storage = active_storage_id
    created_temp_storage = False

    if isolated:
        scenario_storage = f"scenario_{uuid4().hex[:8]}"
        registry.create_storage(scenario_storage)
        handle_command({"command": "create_storage", "payload": {"storage_id": scenario_storage}})
        created_temp_storage = True
        print(f"[scenario] Temporary storage created: {scenario_storage}")

    try:
        payload = _load_scenario_file(file_path)
    except ValueError as exc:
        print(f"[scenario] Failed to load scenario: {exc}")
        if created_temp_storage:
            _cleanup_scenario_storage(registry, scenario_storage)
        return

    steps = payload.get("steps") or []
    name = payload.get("name") or Path(file_path).stem

    print(f"[scenario] Running: {name}")
    success = True

    for idx, step in enumerate(steps, start=1):
        command = step.get("command")
        expect = step.get("expect")

        if not isinstance(command, dict):
            print(f"[scenario] Step {idx}: invalid command format, expected object.")
            success = False
            break

        command_with_storage = dict(command)
        command_with_storage["storage_id"] = command.get("storage_id") or scenario_storage

        response = handle_command(command_with_storage)
        matches = _match_expect(expect, response)

        status_label = "OK" if matches else "FAIL"
        print(f"[scenario] Step {idx}")
        print("  command:", json.dumps(command_with_storage, ensure_ascii=False))
        print("  result :", json.dumps(response, ensure_ascii=False))
        print(f"  status : {status_label}")

        if not matches:
            success = False
            break

    if success:
        print("[scenario] Scenario PASSED")
    else:
        print("[scenario] Scenario FAILED")

    if created_temp_storage:
        _cleanup_scenario_storage(registry, scenario_storage)


def _cleanup_scenario_storage(registry: StorageRegistry, storage_id: Optional[str]) -> None:
    if not storage_id:
        return
    handle_command({"command": "delete_storage", "payload": {"storage_id": storage_id}})
    registry.delete_storage(storage_id)
    print(f"[scenario] Temporary storage deleted: {storage_id}")


def _load_scenario_file(file_path: str) -> Dict[str, Any]:
    path = Path(file_path)
    if not path.exists():
        raise ValueError(f"File not found: {file_path}")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON: {exc}") from exc


def _match_expect(expect: Any, response: Dict[str, Any]) -> bool:
    if expect == "ok":
        return response.get("status") == "ok"
    if isinstance(expect, dict):
        return _is_partial_match(expect, response)
    return False


def _is_partial_match(expected: Any, actual: Any) -> bool:
    """Recursively check if expected is a subset of actual."""
    if isinstance(expected, dict):
        if not isinstance(actual, dict):
            return False
        return all(key in actual and _is_partial_match(value, actual[key]) for key, value in expected.items())
    if isinstance(expected, list):
        if not isinstance(actual, list) or len(expected) > len(actual):
            return False
        return all(_is_partial_match(exp, act) for exp, act in zip(expected, actual))
    return expected == actual


if __name__ == "__main__":
    run()
