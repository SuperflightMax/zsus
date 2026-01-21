"""Two-pass LLM adapter for interpretation and response."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from ..core.defaults import DEFAULT_LOCATION, DEFAULT_QTY
from ..core.engine import CoreEngine, handle_command
from ..core.result import OperationResult
from .client import LLMClient, LLMUnavailableError


PROMPTS_DIR = Path(__file__).resolve().parent / "prompts"
SUPPORTED_INTENTS = {"add", "remove", "count", "locate", "move", "list"}


@dataclass
class InteractionContext:
    interaction_id: str
    language_policy: Dict[str, str]
    turns: List[Dict[str, str]]


@dataclass
class DraftCommand:
    intent: Optional[str] = None
    item: Optional[str] = None
    qty: Optional[int] = None
    location: Optional[str] = None
    from_location: Optional[str] = None
    to_location: Optional[str] = None


@dataclass
class ValidationResult:
    status: str
    reason: Optional[str] = None
    details: Optional[Dict[str, Any]] = None


@dataclass
class ExecutionSummary:
    status: str
    command: Optional[str] = None
    payload: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class LLMAdapter2Pass:
    """Interpret user input with PASS1 and respond with PASS2."""

    def __init__(
        self,
        *,
        llm_client: Optional[LLMClient],
        confidence_threshold: float,
        engine: Optional[CoreEngine] = None,
    ) -> None:
        self._llm_client = llm_client
        self._confidence_threshold = confidence_threshold
        self._engine = engine
        self._base_prompt = _load_prompt("system_prompt_base.txt")
        self._pass1_prompt = _load_prompt("system_prompt_pass1.txt")
        self._pass2_prompt = _load_prompt("system_prompt_pass2.txt")

    def run(
        self,
        *,
        interaction_context: InteractionContext,
        allowed_intents: List[str],
        mvp_mode: bool,
        storage_id: str,
    ) -> OperationResult:
        system_log: List[str] = []
        system_log.append(f"interaction_id: {interaction_context.interaction_id}")
        system_log.append(f"turns: {json.dumps(interaction_context.turns, ensure_ascii=False)}")

        try:
            draft, confidence, raw_pass1 = self._pass1(interaction_context, allowed_intents, mvp_mode)
        except LLMUnavailableError as exc:
            return _llm_unavailable_result(system_log, str(exc))

        system_log.append(f"pass1_raw: {raw_pass1}")
        system_log.append(f"draft: {json.dumps(asdict(draft), ensure_ascii=False)}")
        system_log.append(f"confidence: {confidence:.3f}")

        validation, executable = self._validate_and_build(draft, confidence, storage_id)
        system_log.append(f"validation: {json.dumps(asdict(validation), ensure_ascii=False)}")

        execution_summary: Optional[ExecutionSummary] = None
        if validation.status == "executed" and executable:
            execution_summary = self._execute(executable)
            system_log.append(f"execution: {json.dumps(asdict(execution_summary), ensure_ascii=False)}")
            if execution_summary.status == "rejected":
                validation = ValidationResult(
                    status="rejected",
                    reason="domain_error",
                    details={"message": execution_summary.error},
                )
                system_log.append(f"validation: {json.dumps(asdict(validation), ensure_ascii=False)}")
        else:
            system_log.append("execution: skipped")

        try:
            user_text = self._pass2(interaction_context, draft, confidence, validation, execution_summary)
        except LLMUnavailableError as exc:
            return _llm_unavailable_result(system_log, str(exc))
        system_log.append(f"pass2_raw: {user_text}")

        summary_lines = _build_system_summary(draft, confidence, validation, execution_summary)
        system_log = summary_lines + system_log

        ok = validation.status == "executed"
        return OperationResult(ok=ok, user_text=user_text, system_log=system_log)

    def _pass1(
        self,
        interaction_context: InteractionContext,
        allowed_intents: List[str],
        mvp_mode: bool,
    ) -> Tuple[DraftCommand, float, str]:
        payload = {
            "interaction_context": asdict(interaction_context),
            "allowed_intents": allowed_intents,
            "mvp_mode": mvp_mode,
        }
        raw = self._call_llm(self._base_prompt + self._pass1_prompt, payload)
        draft, confidence = _parse_pass1_output(raw)
        return draft, confidence, raw

    def _pass2(
        self,
        interaction_context: InteractionContext,
        draft: DraftCommand,
        confidence: float,
        validation: ValidationResult,
        execution_summary: Optional[ExecutionSummary],
    ) -> str:
        payload = {
            "interaction_context": asdict(interaction_context),
            "draft_command": asdict(draft),
            "confidence": confidence,
            "validation": asdict(validation),
            "execution_result": asdict(execution_summary) if execution_summary else None,
        }
        raw = self._call_llm(self._base_prompt + self._pass2_prompt, payload)
        return raw.strip() or "Сервіс тимчасово недоступний."

    def _call_llm(self, system_prompt: str, payload: Dict[str, Any]) -> str:
        if not self._llm_client:
            raise LLMUnavailableError("LLM client not configured.")
        try:
            return self._llm_client.generate(system_prompt, json.dumps(payload, ensure_ascii=False))
        except LLMUnavailableError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise LLMUnavailableError("LLM call failed.") from exc

    def _validate_and_build(
        self,
        draft: DraftCommand,
        confidence: float,
        storage_id: str,
    ) -> Tuple[ValidationResult, Optional[Dict[str, Any]]]:
        if draft.intent is None:
            return ValidationResult(status="rejected", reason="unknown_intent"), None
        if draft.intent not in SUPPORTED_INTENTS:
            return ValidationResult(status="rejected", reason="unknown_intent"), None

        if confidence < self._confidence_threshold:
            return ValidationResult(status="rejected", reason="low_confidence"), None

        missing_fields = _missing_required_fields(draft)
        if missing_fields:
            return (
                ValidationResult(
                    status="rejected",
                    reason="missing_required_fields",
                    details={"missing": missing_fields},
                ),
                None,
            )

        executable = _build_executable_command(draft, storage_id)
        return ValidationResult(status="executed"), executable

    def _execute(self, command: Dict[str, Any]) -> ExecutionSummary:
        if self._engine:
            result = self._engine.handle_command(command)
        else:
            result = handle_command(command)

        if result.ok:
            return ExecutionSummary(status="executed", command=command.get("command"), payload=command.get("payload"))

        error_message = result.user_text or "Domain error"
        return ExecutionSummary(status="rejected", error=error_message)


def _build_system_summary(
    draft: DraftCommand,
    confidence: float,
    validation: ValidationResult,
    execution_summary: Optional[ExecutionSummary],
) -> List[str]:
    status_label = "EXECUTED" if validation.status == "executed" else "REJECTED"
    summary = [f"status: {status_label}"]
    if validation.status == "rejected":
        summary.append(f"reason: {validation.reason}")
    summary.append(f"intent: {draft.intent}")
    summary.append(f"confidence: {confidence:.3f}")
    summary.append(f"params: {json.dumps(_draft_params_for_log(draft), ensure_ascii=False)}")

    if execution_summary and execution_summary.status == "executed":
        summary.append(
            f"command: {execution_summary.command} {json.dumps(execution_summary.payload, ensure_ascii=False)}"
        )
    if execution_summary and execution_summary.status == "rejected":
        summary.append(f"domain_error: {execution_summary.error}")
    if validation.details:
        summary.append(f"details: {json.dumps(validation.details, ensure_ascii=False)}")
    return summary


def _draft_params_for_log(draft: DraftCommand) -> Dict[str, Any]:
    return {
        "item": draft.item,
        "qty": draft.qty,
        "location": draft.location or "UNSPECIFIED",
        "from_location": draft.from_location or "UNSPECIFIED",
        "to_location": draft.to_location or "UNSPECIFIED",
    }


def _missing_required_fields(draft: DraftCommand) -> List[str]:
    if draft.intent in {"add", "remove", "count", "locate"}:
        return ["item"] if not draft.item else []
    if draft.intent == "move":
        missing = []
        if not draft.item:
            missing.append("item")
        if not draft.to_location:
            missing.append("to_location")
        return missing
    if draft.intent == "list":
        return []
    return ["intent"]


def _build_executable_command(draft: DraftCommand, storage_id: str) -> Dict[str, Any]:
    intent = draft.intent
    if intent == "add":
        return {
            "storage_id": storage_id,
            "command": "intake",
            "payload": {
                "items": [
                    {
                        "item_id": draft.item,
                        "qty": draft.qty if draft.qty is not None else DEFAULT_QTY,
                        "location": draft.location if draft.location is not None else DEFAULT_LOCATION,
                    }
                ]
            },
        }
    if intent == "remove":
        return {
            "storage_id": storage_id,
            "command": "consume",
            "payload": {
                "item_id": draft.item,
                "qty": draft.qty if draft.qty is not None else DEFAULT_QTY,
                "from": draft.from_location if draft.from_location is not None else DEFAULT_LOCATION,
            },
        }
    if intent == "move":
        return {
            "storage_id": storage_id,
            "command": "move",
            "payload": {
                "item_id": draft.item,
                "qty": draft.qty if draft.qty is not None else DEFAULT_QTY,
                "from": draft.from_location if draft.from_location is not None else DEFAULT_LOCATION,
                "to": draft.to_location,
            },
        }
    if intent in {"count", "locate"}:
        return {
            "storage_id": storage_id,
            "command": "find",
            "payload": {
                "item_id": draft.item,
            },
        }
    if intent == "list":
        return {
            "storage_id": storage_id,
            "command": "list",
            "payload": {},
        }
    return {"command": "unknown", "payload": {}}


def _parse_pass1_output(raw: str) -> Tuple[DraftCommand, float]:
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return DraftCommand(intent=None), 0.0

    if not isinstance(parsed, dict):
        return DraftCommand(intent=None), 0.0

    intent = parsed.get("intent") if isinstance(parsed.get("intent"), str) else None
    confidence = parsed.get("confidence")
    confidence_value = confidence if isinstance(confidence, (int, float)) else 0.0

    return (
        DraftCommand(
            intent=intent,
            item=_string_or_none(parsed.get("item")),
            qty=_int_or_none(parsed.get("qty")),
            location=_string_or_none(parsed.get("location")),
            from_location=_string_or_none(parsed.get("from_location")),
            to_location=_string_or_none(parsed.get("to_location")),
        ),
        float(confidence_value),
    )


def _string_or_none(value: Any) -> Optional[str]:
    return value if isinstance(value, str) and value else None


def _int_or_none(value: Any) -> Optional[int]:
    return value if isinstance(value, int) else None


def _load_prompt(filename: str) -> str:
    path = PROMPTS_DIR / filename
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def _llm_unavailable_result(system_log: List[str], message: str) -> OperationResult:
    validation = ValidationResult(status="rejected", reason="llm_unavailable", details={"message": message})
    summary = _build_system_summary(DraftCommand(intent=None), 0.0, validation, None)
    system_log = summary + system_log + [f"llm_error: {message}"]
    return OperationResult(ok=False, user_text="Сервіс тимчасово недоступний.", system_log=system_log)
