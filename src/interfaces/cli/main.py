"""Command-line interface with admin commands and scenario runner."""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from uuid import uuid4

from ...infra import load_config
from ...infra.storage_registry import StorageRegistry
from ...infra.backend_factory import create_backend
from ...core.engine import handle_command, set_default_backend
from ...core.result import OperationResult
from ...session import SessionManager


def configure_logging(level_name: str) -> None:
    level = getattr(logging, level_name.upper(), logging.INFO)
    logging.basicConfig(level=level, format="%(levelname)s: %(message)s")


def _init_backend(config: Dict[str, Any]) -> Tuple[str, Any]:
    backend_name, backend = create_backend(config)
    logging.info("Using backend: %s", backend_name)
    return backend_name, backend


def run() -> None:
    config = load_config()
    configure_logging(config.get("logging", {}).get("level", "INFO"))
    backend_name, backend = _init_backend(config)
    set_default_backend(backend)

    prompt_template = _get_prompt_template(config)
    json_prompt = config.get("cli", {}).get("json_prompt", "... ")
    exit_commands = config.get("cli", {}).get("exit_commands", ["exit"])
    table_max_width = config.get("cli", {}).get("table_max_width", 24)
    show_system_llm = config.get("cli", {}).get("show_system_llm", False)
    registry = StorageRegistry(config)

    active_storage_id: Optional[str] = None
    session_manager = SessionManager()
    session = session_manager.get("cli")
    default_storage_id = os.getenv("DEFAULT_STORAGE")
    if default_storage_id:
        if registry.storage_exists(default_storage_id):
            active_storage_id = default_storage_id
            session.set_active_storage_id(active_storage_id)
            logging.info("Default storage activated: %s", default_storage_id)
        else:
            logging.warning("Default storage not found: %s", default_storage_id)


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
                    active_storage_id, show_system_llm = _handle_admin_command(
                        user_input,
                        registry=registry,
                        active_storage_id=active_storage_id,
                        table_max_width=table_max_width,
                        backend_name=backend_name,
                        show_system_llm=show_system_llm,
                    )
                    session.set_active_storage_id(active_storage_id)
                    continue

                if _starts_json(user_input):
                    if active_storage_id is None:
                        _print_operation_result(OperationResult.failure(user_text="No active storage. Use +activatestorage first."))
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
                    session.set_active_storage_id(active_storage_id)
                    result = session.handle_text(user_input)
                    _print_operation_result(result, show_system=show_system_llm)
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


def _resolve_default_storage_id(registry: StorageRegistry) -> Optional[str]:
    default_storage = os.getenv("DEFAULT_STORAGE")
    if not default_storage:
        return None

    if not registry.storage_exists(default_storage):
        registry.create_storage(default_storage)
        logging.info("Default storage created: %s", default_storage)

    handle_command({"command": "create_storage", "payload": {"storage_id": default_storage}})
    logging.info("Default storage set to: %s", default_storage)
    return default_storage


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
    table_max_width: int,
    backend_name: str,
    show_system_llm: bool,
) -> Tuple[Optional[str], bool]:
    tokens = command_line[1:].strip().split()
    if not tokens:
        _print_operation_result(OperationResult.failure(user_text="Невідома адмін-команда."))
        return active_storage_id, show_system_llm

    command_aliases = {
        "ls": "liststorages",
        "li": "listitems",
        "as": "activatestorage",
        "oss": "outsystemshow",
        "osh": "outsystemhide",
    }

    command = command_aliases.get(tokens[0].lower(), tokens[0].lower())
    args = tokens[1:]

    if command == "createstorage":
        if not args:
            _print_operation_result(OperationResult.failure(user_text="Usage: +createstorage <storage_id>"))
            return active_storage_id, show_system_llm
        storage_id = args[0]
        created = registry.create_storage(storage_id)
        if created:
            result = handle_command({"command": "create_storage", "payload": {"storage_id": storage_id}})
            _print_operation_result(result.with_prepended_logs([f"Storage created: {storage_id}"]))
        else:
            _print_operation_result(OperationResult.failure(user_text=f"Storage already exists: {storage_id}"))
        return active_storage_id, show_system_llm

    if command == "deletestorage":
        if not args:
            _print_operation_result(OperationResult.failure(user_text="Usage: +deletestorage <storage_id>"))
            return active_storage_id, show_system_llm
        storage_id = args[0]
        result = handle_command({"command": "delete_storage", "payload": {"storage_id": storage_id}})
        deleted = registry.delete_storage(storage_id)
        if deleted:
            _print_operation_result(result.with_prepended_logs([f"Storage deleted: {storage_id}"]))
            if active_storage_id == storage_id:
                return None, show_system_llm
        else:
            _print_operation_result(OperationResult.failure(user_text=f"Storage not found: {storage_id}"))
        return active_storage_id, show_system_llm

    if command == "liststorages":
        storages = registry.list_storages()
        lines: List[str] = []
        if not storages:
            lines.append("(no storages)")
        else:
            for storage in storages:
                marker = " (active)" if storage == active_storage_id else ""
                lines.append(f"- {storage}{marker}")
        _print_operation_result(OperationResult.success(user_text="\n".join(lines), system_log=lines))
        return active_storage_id, show_system_llm

    if command == "activatestorage":
        if not args:
            _print_operation_result(OperationResult.failure(user_text="Usage: +activatestorage <storage_id>"))
            return active_storage_id, show_system_llm
        storage_id = args[0]
        if not registry.storage_exists(storage_id):
            _print_operation_result(OperationResult.failure(user_text=f"Storage not found: {storage_id}"))
            return active_storage_id, show_system_llm
        _print_operation_result(OperationResult.success(user_text=f"Active storage set to: {storage_id}"))
        return storage_id, show_system_llm

    if command == "listitems":
        if not active_storage_id:
            _print_operation_result(OperationResult.failure(user_text="No active storage. Use +activatestorage first."))
            return active_storage_id, show_system_llm

        response = handle_command({"command": "list", "storage_id": active_storage_id, "payload": {}})
        if not response.ok:
            _print_operation_result(response)
            return active_storage_id, show_system_llm

        table_lines = _render_storage_table(response.data or {}, max_width=table_max_width)
        _print_operation_result(OperationResult.success(user_text="\n".join(table_lines), system_log=table_lines, data=response.data))
        return active_storage_id, show_system_llm

    if command == "status":
        storages = registry.list_storages()
        lines = [
            "CLI status:",
            f"- Active storage: {active_storage_id or 'none'}",
            f"- Backend: {backend_name}",
            f"- Known storages: {len(storages)}",
        ]
        _print_operation_result(OperationResult.success(user_text="\n".join(lines), system_log=lines))
        return active_storage_id, show_system_llm

    if command == "runscenario":
        isolated = False
        files: List[str] = []
        for arg in args:
            if arg == "--isolated":
                isolated = True
            else:
                files.append(arg)

        if not files:
            _print_operation_result(OperationResult.failure(user_text="Usage: +runscenario [--isolated] <file>"))
            return active_storage_id, show_system_llm

        scenario_file = files[0]
        if not isolated and active_storage_id is None:
            _print_operation_result(OperationResult.failure(user_text="No active storage. Use +activatestorage or --isolated."))
            return active_storage_id, show_system_llm

        _run_scenario(scenario_file, registry, active_storage_id, isolated)
        return active_storage_id, show_system_llm

    if command == "outsystemshow":
        show_system_llm = True
        _print_operation_result(OperationResult.success(user_text="SYSTEM output for LLM is now ON."))
        return active_storage_id, show_system_llm

    if command == "outsystemhide":
        show_system_llm = False
        _print_operation_result(OperationResult.success(user_text="SYSTEM output for LLM is now OFF."))
        return active_storage_id, show_system_llm

    _print_operation_result(OperationResult.failure(user_text=f"Unknown admin command: +{command}"))
    return active_storage_id, show_system_llm


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
        _print_operation_result(OperationResult.failure(user_text="No active storage. Use +activatestorage first."))
        return

    parsed = _try_parse_json(text)
    if parsed is None:
        _print_operation_result(OperationResult.failure(user_text="Не удалось прочитать JSON. Попробуйте ещё раз."))
        return

    parsed_with_storage = dict(parsed)
    parsed_with_storage["storage_id"] = active_storage_id
    response = handle_command(parsed_with_storage)
    _print_operation_result(response)


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
        _print_operation_result(OperationResult.success(user_text=f"[scenario] Temporary storage created: {scenario_storage}"))

    try:
        payload = _load_scenario_file(file_path)
    except ValueError as exc:
        _print_operation_result(OperationResult.failure(user_text=f"[scenario] Failed to load scenario: {exc}"))
        if created_temp_storage:
            _cleanup_scenario_storage(registry, scenario_storage)
        return

    steps = payload.get("steps") or []
    name = payload.get("name") or Path(file_path).stem

    _print_operation_result(OperationResult.success(user_text=f"[scenario] Running: {name}"))
    success = True

    for idx, step in enumerate(steps, start=1):
        command = step.get("command")
        expect = step.get("expect")

        if not isinstance(command, dict):
            _print_operation_result(
                OperationResult.failure(
                    user_text=f"[scenario] Step {idx}: invalid command format, expected object.",
                    system_log=[f"Invalid step format at {idx}"],
                )
            )
            success = False
            break

        command_with_storage = dict(command)
        command_with_storage["storage_id"] = command.get("storage_id") or scenario_storage

        response = handle_command(command_with_storage)
        matches = _match_expect(expect, response.to_dict())

        status_label = "OK" if matches else "FAIL"
        system_lines = [
            f"[scenario] Step {idx}",
            f"  command: {json.dumps(command_with_storage, ensure_ascii=False)}",
            f"  result : {json.dumps(response.to_dict(), ensure_ascii=False)}",
            f"  status : {status_label}",
        ]
        _print_operation_result(
            OperationResult(
                ok=matches,
                user_text="\n".join(system_lines),
                system_log=system_lines + list(response.system_log),
                data=response.data,
            )
        )

        if not matches:
            success = False
            break

    if success:
        _print_operation_result(OperationResult.success(user_text="[scenario] Scenario PASSED"))
    else:
        _print_operation_result(OperationResult.failure(user_text="[scenario] Scenario FAILED"))

    if created_temp_storage:
        _cleanup_scenario_storage(registry, scenario_storage)


def _cleanup_scenario_storage(registry: StorageRegistry, storage_id: Optional[str]) -> None:
    if not storage_id:
        return
    handle_command({"command": "delete_storage", "payload": {"storage_id": storage_id}})
    registry.delete_storage(storage_id)
    _print_operation_result(OperationResult.success(user_text=f"[scenario] Temporary storage deleted: {storage_id}"))


def _load_scenario_file(file_path: str) -> Dict[str, Any]:
    path = Path(file_path)
    if not path.exists():
        raise ValueError(f"File not found: {file_path}")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON: {exc}") from exc


def _match_expect(expect: Any, response: Dict[str, Any]) -> bool:
    payload = response.to_dict() if isinstance(response, OperationResult) else dict(response)
    status_ok = payload.get("ok")
    if status_ok is None and "status" in payload:
        status_ok = payload.get("status") == "ok"

    if expect == "ok":
        return bool(status_ok)

    if isinstance(expect, dict):
        if not status_ok:
            return False

        data = payload.get("data")
        if not isinstance(data, dict):
            return False

        return all(key in data and data[key] == value for key, value in expect.items())
    return False


def _render_storage_table(snapshot: Dict[str, Dict[str, int]], max_width: int) -> List[str]:
    if not snapshot:
        return ["(storage is empty)"]

    rows = []
    for item_id in sorted(snapshot.keys()):
        locations = snapshot[item_id]
        for location_key in sorted(locations.keys()):
            qty = locations[location_key]
            item_display = _truncate_text(item_id, max_width)
            location_display = "(unplaced)" if location_key == "null" else _truncate_text(str(location_key), max_width)
            rows.append((item_display, location_display, qty))

    item_width = max([len("Item")] + [len(row[0]) for row in rows])
    location_width = max([len("Location")] + [len(row[1]) for row in rows])
    qty_width = max([len("Qty")] + [len(str(row[2])) for row in rows])

    header = f"{'Item':<{item_width}}  {'Location':<{location_width}}  {'Qty':>{qty_width}}"
    separator = f"{'-' * item_width}  {'-' * location_width}  {'-' * qty_width}"
    lines = [header, separator]
    for item_display, location_display, qty in rows:
        lines.append(f"{item_display:<{item_width}}  {location_display:<{location_width}}  {qty:>{qty_width}}")
    return lines


def _print_operation_result(result: OperationResult, *, show_system: bool = True) -> None:
    system_lines = list(result.system_log)
    if result.data is not None:
        try:
            system_lines.append(f"data: {json.dumps(result.data, ensure_ascii=False)}")
        except TypeError:
            system_lines.append(f"data: {result.data}")
    system_block = "\n".join(system_lines) if system_lines else "(empty)"
    user_block = result.user_text or ""
    if show_system:
        print("-------- SYSTEM:")
        print(system_block)
    print("-------- USER:")
    print(user_block)


def _truncate_text(value: str, max_width: int) -> str:
    if max_width < 4:
        return value[:max_width]
    return value if len(value) <= max_width else value[: max_width - 3] + "..."


if __name__ == "__main__":
    run()
