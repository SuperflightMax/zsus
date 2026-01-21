"""User text message handling pipeline."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional

from ..core.result import OperationResult
from ..llm.interpreter import Interpreter
from ..llm.responder import Responder


@dataclass
class ValidationResult:
    ok: bool
    reason: Optional[str]
    executable: Optional[Dict[str, Any]]


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

    if not validation.ok or not validation.executable:
        trace["executable_command"] = "blocked"
        trace["errors"] = errors
        return OperationResult.failure(user_text=DEFAULT_USER_FALLBACK, system_log=system_log, data=trace)

    executable = dict(validation.executable)
    executable["storage_id"] = active_storage_id
    trace["executable_command"] = executable
    system_log.append(f"executable_command: {json.dumps(executable, ensure_ascii=False)}")

    execution_result = core_handler(executable)
    trace["core_result"] = execution_result.to_dict()
    system_log.append(f"core_result: {json.dumps(execution_result.to_dict(), ensure_ascii=False)}")
    if not execution_result.ok and execution_result.user_text:
        errors.append(execution_result.user_text)

    inventory_data = None
    if executable.get("command") == "list" and execution_result.ok:
        inventory_data = execution_result.data or {}
        system_log.append(f"inventory_data: {json.dumps(inventory_data, ensure_ascii=False)}")

    template_reply = _build_template_reply(draft_command, execution_result, inventory_data)
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
        return ValidationResult(ok=False, reason="low_confidence", executable=None)

    intent = draft.get("intent")
    if intent not in {"intake", "move", "consume", "find", "list_inventory"}:
        return ValidationResult(ok=False, reason="unknown_intent", executable=None)

    if intent == "list_inventory":
        return ValidationResult(ok=True, reason=None, executable={"command": "list", "payload": {}})

    if intent == "intake":
        item_id = draft.get("item_id")
        qty = draft.get("qty")
        if qty is None:
            qty = 1
        location = draft.get("location") if "location" in draft else None
        if not isinstance(item_id, str) or not item_id:
            return ValidationResult(ok=False, reason="missing_item_id", executable=None)
        if not isinstance(qty, int) or qty <= 0:
            return ValidationResult(ok=False, reason="invalid_qty", executable=None)
        payload = {"items": [{"item_id": item_id, "qty": qty, "location": location}]}
        return ValidationResult(ok=True, reason=None, executable={"command": "intake", "payload": payload})

    if intent == "find":
        item_id = draft.get("item_id")
        if not isinstance(item_id, str) or not item_id:
            return ValidationResult(ok=False, reason="missing_item_id", executable=None)
        return ValidationResult(ok=True, reason=None, executable={"command": "find", "payload": {"item_id": item_id}})

    if intent in {"move", "consume"}:
        item_id = draft.get("item_id")
        qty = draft.get("qty")
        if qty is None:
            qty = 1
        if not isinstance(item_id, str) or not item_id:
            return ValidationResult(ok=False, reason="missing_item_id", executable=None)
        if not isinstance(qty, int) or qty <= 0:
            return ValidationResult(ok=False, reason="invalid_qty", executable=None)

        from_location = draft.get("from") if "from" in draft else None

        if intent == "move":
            to_location = draft.get("to") if "to" in draft else None
            if "to" not in draft:
                return ValidationResult(ok=False, reason="missing_to", executable=None)
            payload = {
                "item_id": item_id,
                "qty": qty,
                "from": from_location,
                "to": to_location,
            }
            return ValidationResult(ok=True, reason=None, executable={"command": "move", "payload": payload})

        if "from" not in draft:
            return ValidationResult(ok=False, reason="missing_from", executable=None)
        payload = {"item_id": item_id, "qty": qty, "from": from_location}
        return ValidationResult(ok=True, reason=None, executable={"command": "consume", "payload": payload})

    return ValidationResult(ok=False, reason="unsupported_intent", executable=None)


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


def _build_template_reply(draft: Dict[str, Any], execution: OperationResult, inventory_data: Dict[str, Any] | None) -> str:
    if not execution.ok:
        return "Операцію не виконано."

    intent = draft.get("intent")
    if intent == "list_inventory":
        return _format_inventory_summary(inventory_data or {})
    if intent == "find":
        item_id = draft.get("item_id")
        total = execution.data.get("total_qty") if isinstance(execution.data, dict) else None
        if total is not None:
            return f"Є {item_id}: {total}."
        return "Готово."
    if intent in {"intake", "move", "consume"}:
        return "Готово."
    return "Готово."


def _format_inventory_summary(snapshot: Dict[str, Dict[str, int]]) -> str:
    if not snapshot:
        return "Склад порожній."
    parts = []
    for item_id in sorted(snapshot.keys()):
        total = sum(snapshot[item_id].values())
        parts.append(f"{item_id} — {total}")
    joined = ", ".join(parts)
    return f"Є: {joined}."


def _trim_text(value: Any, limit: int = 500) -> str:
    if value is None:
        return ""
    text = str(value)
    return text if len(text) <= limit else text[:limit] + "..."
