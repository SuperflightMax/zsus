"""User text message handling pipeline."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional

from ..core.result import OperationResult
from ..llm.interpreter import Interpreter
from ..llm.responder import Responder
from .formatting import render_inventory_table


@dataclass
class ValidationResult:
    ok: bool
    reason: Optional[str]
    executable: Optional[Dict[str, Any]]
    normalized_draft: Optional[Dict[str, Any]]


DEFAULT_USER_FALLBACK = "Не зрозумів запит. Переформулюй, будь ласка."
DEFAULT_STORAGE_MISSING = "Склад не налаштований. Звернись до адміністратора."
DEFAULT_FAILURE_MESSAGE = "Сталася помилка. Спробуй ще раз пізніше."
DEFAULT_CORE_FAILURE = "Не вдалося виконати запит."


def handle_user_message(
    text: str,
    active_storage_id: Optional[str],
    config: Dict[str, Any],
    core_handler: Callable[[Dict[str, Any]], OperationResult],
    interpreter: Interpreter | None = None,
    responder: Responder | None = None,
) -> OperationResult:
    system_log: list[str] = []
    errors: list[str] = []
    trace: Dict[str, Any] = {
        "input_text": text,
        "active_storage_id": active_storage_id,
        "active_storage_source": "cli_active_storage",
    }

    system_log.append(f"input: {text}")

    if not active_storage_id:
        reason = "Active storage missing for user-text pipeline."
        system_log.append(f"active_storage_id: none ({reason})")
        errors.append(reason)
        trace["errors"] = errors
        return OperationResult.failure(user_text=DEFAULT_STORAGE_MISSING, system_log=system_log, data=trace)

    system_log.append(f"active_storage_id: {active_storage_id} (source: cli_active_storage)")

    snapshot_result = core_handler({"command": "list", "storage_id": active_storage_id, "payload": {}})
    if snapshot_result.ok and isinstance(snapshot_result.data, dict):
        snapshot = snapshot_result.data
        system_log.append("snapshot: ok")
    else:
        snapshot = {}
        system_log.append("snapshot: failed")
        if snapshot_result.system_log:
            system_log.extend([f"snapshot_error: {line}" for line in snapshot_result.system_log])
        errors.append("snapshot_failed")

    snapshot_summary = _build_snapshot_summary(snapshot)
    trace["snapshot_summary"] = snapshot_summary
    system_log.append(f"snapshot_summary: {json.dumps(snapshot_summary, ensure_ascii=False)}")

    interaction_context = {
        "interaction_id": "cli-single-turn",
        "language_policy": {"input": "any", "output": "uk"},
        "turns": [{"role": "user", "content": text}],
    }

    interpreter = interpreter or Interpreter(config)
    interpret_result = interpreter.interpret(text, interaction_context, snapshot_summary)
    trace["interpret_raw"] = _trim_text(interpret_result.get("raw"))
    trace["interpret_parsed"] = interpret_result.get("parsed")
    trace["interpret_error"] = interpret_result.get("error")

    system_log.append(f"llm_interpret_raw: {trace['interpret_raw']}")
    system_log.append(f"llm_interpret_parsed: {json.dumps(trace['interpret_parsed'], ensure_ascii=False)}")
    if trace.get("interpret_error"):
        system_log.append(f"llm_interpret_error: {trace['interpret_error']}")
        errors.append(trace["interpret_error"])

    if not interpret_result.get("ok"):
        trace["validation"] = {"status": "rejected", "reason": "interpret_failed"}
        system_log.append("validation: rejected (interpret_failed)")
        trace["errors"] = errors
        return OperationResult.failure(user_text=DEFAULT_USER_FALLBACK, system_log=system_log, data=trace)

    parsed = interpret_result.get("parsed") or {}
    confidence = parsed.get("confidence")
    draft_command = parsed.get("draft_command") or {}

    trace["confidence"] = confidence
    trace["draft_command"] = draft_command
    system_log.append(f"llm_interpret_confidence: {trace.get('confidence')}")

    validation = _validate_draft(draft_command, confidence, config)
    trace["validation"] = {
        "status": "passed" if validation.ok else "rejected",
        "reason": validation.reason,
    }
    system_log.append(f"validation: {'passed' if validation.ok else 'rejected'} ({validation.reason})")

    if not validation.ok:
        trace["executable_command"] = "blocked"
        trace["errors"] = errors
        return OperationResult.failure(user_text=DEFAULT_USER_FALLBACK, system_log=system_log, data=trace)

    normalized_draft = validation.normalized_draft or draft_command
    trace["normalized_draft_command"] = normalized_draft

    expansion_commands, preflight_error, expansion_log = _expand_draft_to_executables(
        normalized_draft,
        active_storage_id,
        core_handler,
        system_log,
    )
    trace["expansion"] = expansion_log
    trace["expanded_commands"] = expansion_commands

    execution_results: List[OperationResult] = []
    executed_commands: List[Dict[str, Any]] = []
    if preflight_error is None:
        for command in expansion_commands:
            executable = dict(command)
            executable["storage_id"] = active_storage_id
            executed_commands.append(executable)
            system_log.append(f"executable_command: {json.dumps(executable, ensure_ascii=False)}")
            result = core_handler(executable)
            execution_results.append(result)
            system_log.append(f"core_result: {json.dumps(result.to_dict(), ensure_ascii=False)}")
            if not result.ok:
                break

    if executed_commands:
        trace["executable_command"] = executed_commands[0] if len(executed_commands) == 1 else executed_commands
    else:
        trace["executable_command"] = expansion_commands or "none"

    execution_result = preflight_error or _aggregate_execution_results(execution_results)
    trace["core_result"] = execution_result.to_dict()
    if not execution_result.ok and execution_result.user_text:
        errors.append(execution_result.user_text)

    inventory_data = None
    inventory_table = None
    if normalized_draft.get("intent") == "list_inventory" and execution_result.ok:
        inventory_data = execution_result.data or {}
        table_max_width = config.get("cli", {}).get("table_max_width", 24)
        inventory_table = render_inventory_table(
            inventory_data,
            max_width=table_max_width,
            unplaced_label="склад",
            empty_message="Склад порожній.",
        )
        system_log.append(f"inventory_data: {json.dumps(inventory_data, ensure_ascii=False)}")
        system_log.append("inventory_table: ok")

    action_summary = _build_action_summary(normalized_draft, execution_result, executed_commands, inventory_data)
    trace["action_summary"] = action_summary
    system_log.append(f"action_summary: {json.dumps(action_summary, ensure_ascii=False)}")

    template_reply = _build_template_reply(
        normalized_draft,
        execution_result,
        action_summary,
        inventory_table,
    )
    trace["template_reply"] = template_reply
    system_log.append(f"template_reply: {template_reply}")

    responder = responder or Responder(config)
    respond_context = {
        "input_text": text,
        "validation": trace.get("validation"),
        "execution": {
            "status": "ok" if execution_result.ok else "error",
            "data": execution_result.data,
            "error": execution_result.user_text if not execution_result.ok else None,
        },
        "inventory_summary": inventory_data,
        "inventory_table": inventory_table,
        "action_summary": action_summary,
        "template_reply": template_reply,
    }
    response = responder.respond(respond_context)
    trace["respond_raw"] = _trim_text(response.get("raw"))
    trace["respond_text"] = response.get("text")
    trace["respond_error"] = response.get("error")
    system_log.append(f"llm_respond_raw: {trace['respond_raw']}")
    system_log.append(f"llm_respond_text: {trace['respond_text']}")
    if response.get("error"):
        system_log.append(f"llm_respond_error: {response['error']}")
        errors.append(response["error"])

    trace["errors"] = errors

    if not response.get("ok") or not response.get("text"):
        fallback_text = DEFAULT_FAILURE_MESSAGE if execution_result.ok else DEFAULT_CORE_FAILURE
        return OperationResult.failure(user_text=fallback_text, system_log=system_log, data=trace)

    return OperationResult.success(user_text=response.get("text"), system_log=system_log, data=trace)


def _validate_draft(draft: Dict[str, Any], confidence: Any, config: Dict[str, Any]) -> ValidationResult:
    threshold = config.get("core", {}).get("confidence_threshold", 0.7)
    if not isinstance(confidence, (int, float)) or confidence < threshold:
        return ValidationResult(ok=False, reason="low_confidence", executable=None, normalized_draft=None)

    intent = draft.get("intent")
    if intent not in {"intake", "move", "consume", "find", "list_inventory"}:
        return ValidationResult(ok=False, reason="unknown_intent", executable=None, normalized_draft=None)

    normalized = dict(draft)

    if intent == "list_inventory":
        return ValidationResult(
            ok=True,
            reason=None,
            executable={"command": "list", "payload": {}},
            normalized_draft=normalized,
        )

    if intent == "intake":
        item_id = draft.get("item_id")
        qty = draft.get("qty")
        if qty is None:
            qty = 1
        normalized["qty"] = qty
        location = draft.get("location") if "location" in draft else None
        normalized["location"] = location
        if not isinstance(item_id, str) or not item_id:
            return ValidationResult(ok=False, reason="missing_item_id", executable=None, normalized_draft=normalized)
        if not isinstance(qty, int) or qty <= 0:
            return ValidationResult(ok=False, reason="invalid_qty", executable=None, normalized_draft=normalized)
        payload = {"items": [{"item_id": item_id, "qty": qty, "location": location}]}
        return ValidationResult(
            ok=True,
            reason=None,
            executable={"command": "intake", "payload": payload},
            normalized_draft=normalized,
        )

    if intent == "find":
        item_id = draft.get("item_id")
        if not isinstance(item_id, str) or not item_id:
            return ValidationResult(ok=False, reason="missing_item_id", executable=None, normalized_draft=normalized)
        return ValidationResult(
            ok=True,
            reason=None,
            executable={"command": "find", "payload": {"item_id": item_id}},
            normalized_draft=normalized,
        )

    if intent in {"move", "consume"}:
        item_id = draft.get("item_id")
        qty = draft.get("qty")
        if qty is None:
            qty = 1
        normalized["qty"] = qty
        if not isinstance(item_id, str) or not item_id:
            return ValidationResult(ok=False, reason="missing_item_id", executable=None, normalized_draft=normalized)
        if not _is_all_qty(qty) and (not isinstance(qty, int) or qty <= 0):
            return ValidationResult(ok=False, reason="invalid_qty", executable=None, normalized_draft=normalized)

        from_present = "from" in draft
        from_location = draft.get("from") if from_present else None

        if intent == "move":
            to_location = draft.get("to") if "to" in draft else None
            if "to" not in draft:
                return ValidationResult(ok=False, reason="missing_to", executable=None, normalized_draft=normalized)
            normalized["to"] = to_location
            if _is_all_qty(qty) or not from_present:
                return ValidationResult(ok=True, reason=None, executable=None, normalized_draft=normalized)
            payload = {
                "item_id": item_id,
                "qty": qty,
                "from": from_location,
                "to": to_location,
            }
            return ValidationResult(ok=True, reason=None, executable={"command": "move", "payload": payload}, normalized_draft=normalized)

        if _is_all_qty(qty) or not from_present:
            return ValidationResult(ok=True, reason=None, executable=None, normalized_draft=normalized)
        payload = {"item_id": item_id, "qty": qty, "from": from_location}
        return ValidationResult(ok=True, reason=None, executable={"command": "consume", "payload": payload}, normalized_draft=normalized)

    return ValidationResult(ok=False, reason="unsupported_intent", executable=None, normalized_draft=normalized)


def _build_snapshot_summary(snapshot: Dict[str, Dict[str, int]]) -> Dict[str, Any]:
    item_ids = sorted(snapshot.keys())
    locations = sorted({loc for item in snapshot.values() for loc in item.keys()})
    top_items = []
    for item_id, locations_map in snapshot.items():
        total = sum(locations_map.values())
        top_items.append({"item_id": item_id, "total_qty": total})
    top_items = sorted(top_items, key=lambda x: x["total_qty"], reverse=True)[:5]
    return {
        "item_ids": item_ids[:20],
        "locations": locations[:20],
        "top_items": top_items,
    }


def _build_template_reply(
    draft: Dict[str, Any],
    execution: OperationResult,
    action_summary: Dict[str, Any],
    inventory_table: List[str] | None,
) -> str:
    if not execution.ok:
        return "Операцію не виконано."

    intent = draft.get("intent")
    if intent == "list_inventory":
        if inventory_table:
            return "\n".join(inventory_table)
        return "Склад порожній."
    if intent == "find":
        return _format_find_reply(action_summary, execution)
    if intent == "intake":
        return _format_intake_reply(action_summary)
    if intent == "move":
        return _format_move_reply(action_summary)
    if intent == "consume":
        return _format_consume_reply(action_summary)
    return "Операцію виконано."


def _expand_draft_to_executables(
    draft: Dict[str, Any],
    storage_id: str,
    core_handler: Callable[[Dict[str, Any]], OperationResult],
    system_log: List[str],
) -> tuple[List[Dict[str, Any]], Optional[OperationResult], Dict[str, Any]]:
    intent = draft.get("intent")
    if intent == "list_inventory":
        return ([{"command": "list", "payload": {}}], None, {"strategy": "single"})
    if intent == "find":
        return ([{"command": "find", "payload": {"item_id": draft.get("item_id")}}], None, {"strategy": "single"})
    if intent == "intake":
        payload = {
            "items": [
                {
                    "item_id": draft.get("item_id"),
                    "qty": draft.get("qty"),
                    "location": draft.get("location") if "location" in draft else None,
                }
            ]
        }
        return ([{"command": "intake", "payload": payload}], None, {"strategy": "single"})

    if intent not in {"move", "consume"}:
        return ([], OperationResult.failure(user_text=DEFAULT_CORE_FAILURE), {"strategy": "unsupported"})

    item_id = draft.get("item_id")
    qty = draft.get("qty")
    from_present = "from" in draft
    from_location = draft.get("from") if from_present else None
    to_location = draft.get("to") if intent == "move" else None

    needs_expansion = _is_all_qty(qty) or not from_present
    if not needs_expansion:
        payload = {"item_id": item_id, "qty": qty, "from": from_location}
        if intent == "move":
            payload["to"] = to_location
        return ([{"command": intent, "payload": payload}], None, {"strategy": "direct"})

    find_command = {"command": "find", "storage_id": storage_id, "payload": {"item_id": item_id}}
    system_log.append(f"expansion_find_command: {json.dumps(find_command, ensure_ascii=False)}")
    find_result = core_handler(find_command)
    system_log.append(f"expansion_find_result: {json.dumps(find_result.to_dict(), ensure_ascii=False)}")
    if not find_result.ok:
        return ([], find_result, {"strategy": "find_failed"})

    locations = {}
    if isinstance(find_result.data, dict):
        locations = find_result.data.get("locations") or {}

    entries = _extract_location_entries(locations)
    if from_present:
        normalized_from = _normalize_location_value(from_location)
        entries = [entry for entry in entries if entry[0] == normalized_from]
        if not entries:
            return ([], OperationResult.failure(user_text="Локацію не знайдено."), {"strategy": "from_missing"})

    if intent == "move":
        entries = [entry for entry in entries if entry[0] != _normalize_location_value(to_location)]

    total_available = sum(entry[1] for entry in entries)
    if not _is_all_qty(qty) and isinstance(qty, int) and total_available < qty:
        return ([], OperationResult.failure(user_text="Недостатньо предметів."), {"strategy": "insufficient_qty"})

    if total_available == 0:
        return ([], None, {"strategy": "no_sources"})

    commands: List[Dict[str, Any]] = []
    remaining = total_available if _is_all_qty(qty) else qty
    for location_key, available in _sort_locations_for_anywhere(entries):
        if remaining <= 0:
            break
        move_qty = available if _is_all_qty(qty) else min(available, remaining)
        if move_qty <= 0:
            continue
        payload = {"item_id": item_id, "qty": move_qty, "from": location_key}
        if intent == "move":
            payload["to"] = to_location
        commands.append({"command": intent, "payload": payload})
        remaining -= move_qty

    return (commands, None, {"strategy": "expanded", "total_available": total_available})


def _aggregate_execution_results(results: List[OperationResult]) -> OperationResult:
    if not results:
        return OperationResult.success(data={})
    for result in results:
        if not result.ok:
            return result
    return OperationResult.success(data=results[-1].data)


def _build_action_summary(
    draft: Dict[str, Any],
    execution_result: OperationResult,
    executed_commands: List[Dict[str, Any]],
    inventory_data: Dict[str, Any] | None,
) -> Dict[str, Any]:
    intent = draft.get("intent")
    summary: Dict[str, Any] = {"action_type": intent}

    if intent == "list_inventory":
        summary["items_count"] = len(inventory_data or {})
        return summary

    if intent == "find":
        if not execution_result.ok or not isinstance(execution_result.data, dict):
            return summary
        locations = execution_result.data.get("locations") or {}
        sorted_locations = sorted(
            ((_normalize_location_value(key), qty) for key, qty in locations.items()),
            key=lambda entry: (0 if entry[0] is not None else 1, "" if entry[0] is None else str(entry[0])),
        )
        summary["item_id"] = execution_result.data.get("item_id")
        summary["total_qty"] = execution_result.data.get("total_qty")
        summary["locations"] = [{"location": location, "qty": qty} for location, qty in sorted_locations]
        return summary

    if intent == "intake":
        summary["item_id"] = draft.get("item_id")
        summary["total_qty"] = draft.get("qty")
        summary["location"] = draft.get("location") if "location" in draft else None
        return summary

    if intent in {"move", "consume"}:
        summary["item_id"] = draft.get("item_id")
        summary["to"] = draft.get("to") if intent == "move" else None
        breakdown = _aggregate_breakdown(executed_commands)
        summary["breakdown"] = breakdown
        summary["total_qty"] = sum(entry["qty"] for entry in breakdown)
        return summary

    return summary


def _aggregate_breakdown(executed_commands: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    totals: Dict[Optional[str], int] = {}
    for command in executed_commands:
        payload = command.get("payload") or {}
        from_location = _normalize_location_value(payload.get("from"))
        qty = payload.get("qty")
        if not isinstance(qty, int):
            continue
        totals[from_location] = totals.get(from_location, 0) + qty

    breakdown = [
        {"location": location, "qty": qty}
        for location, qty in sorted(totals.items(), key=lambda entry: _location_sort_key(entry[0], entry[1]))
    ]
    return breakdown


def _location_sort_key(location: Optional[str], qty: int) -> tuple[int, int, str]:
    return (0 if location is None else 1, -qty, "" if location is None else str(location))


def _extract_location_entries(locations: Dict[str, Any]) -> List[tuple[Optional[str], int]]:
    entries: List[tuple[Optional[str], int]] = []
    for key, qty in locations.items():
        if not isinstance(qty, int) or qty <= 0:
            continue
        entries.append((_normalize_location_value(key), qty))
    return entries


def _sort_locations_for_anywhere(entries: List[tuple[Optional[str], int]]) -> List[tuple[Optional[str], int]]:
    return sorted(entries, key=lambda entry: _location_sort_key(entry[0], entry[1]))


def _normalize_location_value(location: Any) -> Optional[str]:
    if location is None or location == "null":
        return None
    return str(location)


def _format_find_reply(action_summary: Dict[str, Any], execution: OperationResult) -> str:
    if not execution.ok:
        return "Операцію не виконано."
    locations = action_summary.get("locations") or []
    item_id = action_summary.get("item_id") or ""
    if not locations:
        return "Операцію виконано."
    if len(locations) == 1:
        entry = locations[0]
        location_name = _format_location_for_find(entry.get("location"))
        return f"{entry.get('qty')} {item_id} на {location_name}.".replace("  ", " ")
    parts = []
    for entry in locations:
        location_name = _format_location_for_find(entry.get("location"))
        parts.append(f"{entry.get('qty')} на {location_name}")
    label = _capitalize_text(item_id)
    return f"{label}: {', '.join(parts)}."


def _format_intake_reply(action_summary: Dict[str, Any]) -> str:
    item_id = action_summary.get("item_id") or ""
    qty = action_summary.get("total_qty") or 0
    location = action_summary.get("location")
    location_text = _format_location_target(location)
    return f"Додав {qty} {item_id} {location_text}.".replace("  ", " ")


def _format_move_reply(action_summary: Dict[str, Any]) -> str:
    total_qty = action_summary.get("total_qty") or 0
    if total_qty == 0:
        return "Нічого не переміщено."
    item_id = action_summary.get("item_id") or ""
    to_location = action_summary.get("to")
    to_text = _format_move_target(to_location)
    breakdown = action_summary.get("breakdown") or []
    breakdown_text = _format_breakdown(breakdown)
    if breakdown_text:
        return f"Переклав {total_qty} {item_id} {to_text} ({breakdown_text}).".replace("  ", " ")
    return f"Переклав {total_qty} {item_id} {to_text}.".replace("  ", " ")


def _format_consume_reply(action_summary: Dict[str, Any]) -> str:
    total_qty = action_summary.get("total_qty") or 0
    if total_qty == 0:
        return "Нічого не списано."
    item_id = action_summary.get("item_id") or ""
    breakdown = action_summary.get("breakdown") or []
    breakdown_text = _format_breakdown(breakdown)
    if breakdown_text:
        return f"Списав {total_qty} {item_id} ({breakdown_text}).".replace("  ", " ")
    return f"Списав {total_qty} {item_id}.".replace("  ", " ")


def _format_breakdown(breakdown: List[Dict[str, Any]]) -> str:
    parts = []
    for entry in breakdown:
        location = entry.get("location")
        qty = entry.get("qty")
        location_text = _format_location_source(location)
        parts.append(f"{location_text}: {qty}")
    return ", ".join(parts)


def _format_location_for_find(location: Any) -> str:
    if location is None:
        return "складі"
    return str(location)


def _format_location_source(location: Any) -> str:
    if location is None:
        return "зі складу"
    return f"з {location}"


def _format_location_target(location: Any) -> str:
    if location is None:
        return "на склад"
    return f"на {location}"


def _format_move_target(location: Any) -> str:
    if location is None:
        return "на склад"
    return f"в {location}"


def _capitalize_text(value: str) -> str:
    if not value:
        return value
    return value[0].upper() + value[1:]


def _is_all_qty(qty: Any) -> bool:
    return isinstance(qty, str) and qty.lower() == "all"


def _trim_text(value: Any, limit: int = 500) -> str:
    if value is None:
        return ""
    text = str(value)
    return text if len(text) <= limit else text[:limit] + "..."
