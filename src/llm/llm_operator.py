"""LLM operator that builds prompts, calls OpenAI, and validates JSON output."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from ..core.engine import handle_command
from .openai_client import OpenAIClient

ALLOWED_COMMANDS = {"list", "intake", "move", "consume"}


@dataclass
class LLMResult:
    ok: bool
    assistant_text: str
    commands: List[Dict[str, Any]]
    need_more_info: bool
    questions: List[str]
    raw_response: Optional[str] = None
    parsed: Optional[Dict[str, Any]] = None
    system_log: List[str] = None


@dataclass
class SnapshotResult:
    ok: bool
    snapshot_text: str
    snapshot_json: Optional[Dict[str, Dict[str, int]]] = None
    system_log: List[str] = None


class LLMOperator:
    """Builds prompts, calls OpenAI, and validates output schema."""

    def __init__(self, prompts_dir: Optional[Path] = None) -> None:
        repo_root = Path(__file__).resolve().parents[2]
        self._prompts_dir = prompts_dir or repo_root / "prompts"
        self._system_prompt = self._load_prompt("operator.system.md")
        self._user_prompt_template = self._load_prompt("operator.user.md")

    def run(self, *, user_text: str, active_storage_id: str) -> Tuple[LLMResult, SnapshotResult, str]:
        system_log: List[str] = []
        snapshot = self._build_snapshot(active_storage_id)
        system_log.extend(snapshot.system_log or [])

        api_key = os.getenv("OPENAI_API_KEY", "")
        model = os.getenv("OPENAI_MODEL", "")
        if not api_key:
            system_log.append("OpenAI API key missing (OPENAI_API_KEY not set).")
            return (
                LLMResult(
                    ok=False,
                    assistant_text="Вибач, зараз ШІ не налаштований. Звернись до адміністратора.",
                    commands=[],
                    need_more_info=False,
                    questions=[],
                    system_log=system_log,
                ),
                snapshot,
                model,
            )

        if not model:
            system_log.append("OpenAI model missing (OPENAI_MODEL not set).")
            return (
                LLMResult(
                    ok=False,
                    assistant_text="Вибач, зараз ШІ не налаштований. Звернись до адміністратора.",
                    commands=[],
                    need_more_info=False,
                    questions=[],
                    system_log=system_log,
                ),
                snapshot,
                model,
            )

        prompt = self._user_prompt_template.format(
            active_storage_id=active_storage_id,
            snapshot_text=snapshot.snapshot_text,
            user_text=user_text,
        )

        messages = [
            {"role": "system", "content": self._system_prompt},
            {"role": "user", "content": prompt},
        ]

        client = OpenAIClient(api_key=api_key, model=model)
        try:
            raw_response = client.create_chat_completion(messages)
        except Exception as exc:
            system_log.append(f"OpenAI request failed: {exc}")
            return (
                LLMResult(
                    ok=False,
                    assistant_text="Вибач, сталася помилка під час обробки запиту. Спробуй ще раз.",
                    commands=[],
                    need_more_info=False,
                    questions=[],
                    system_log=system_log,
                ),
                snapshot,
                model,
            )

        parsed, error = self._parse_response(raw_response)
        if error:
            system_log.append(error)
            system_log.append(f"Raw LLM response: {raw_response[:2000]}")
            return (
                LLMResult(
                    ok=False,
                    assistant_text="Вибач, я не зміг коректно обробити відповідь. Спробуй ще раз.",
                    commands=[],
                    need_more_info=False,
                    questions=[],
                    raw_response=raw_response,
                    parsed=parsed,
                    system_log=system_log,
                ),
                snapshot,
                model,
            )

        system_log.append("LLM response parsed and validated.")
        return (
            LLMResult(
                ok=True,
                assistant_text=parsed["assistant_text"],
                commands=parsed["commands"],
                need_more_info=parsed["need_more_info"],
                questions=parsed["questions"],
                raw_response=raw_response,
                parsed=parsed,
                system_log=system_log,
            ),
            snapshot,
            model,
        )

    def _load_prompt(self, filename: str) -> str:
        path = self._prompts_dir / filename
        return path.read_text(encoding="utf-8")

    def _build_snapshot(self, storage_id: str) -> SnapshotResult:
        system_log: List[str] = []
        response = handle_command({"command": "list", "payload": {}, "storage_id": storage_id})
        if not response.ok:
            system_log.append("Snapshot list command failed.")
            system_log.extend(response.system_log)
            return SnapshotResult(
                ok=False,
                snapshot_text="(не вдалося отримати стан складу)",
                snapshot_json=None,
                system_log=system_log,
            )

        snapshot = response.data or {}
        table_text, truncated, total_rows = _render_snapshot_table(snapshot, max_rows=30)
        system_log.append(f"Snapshot rows: {total_rows}")
        system_log.append(f"Snapshot JSON: {json.dumps(snapshot, ensure_ascii=False)}")
        if truncated:
            system_log.append(f"Snapshot truncated: {truncated} rows omitted")
        return SnapshotResult(
            ok=True,
            snapshot_text=table_text,
            snapshot_json=snapshot,
            system_log=system_log,
        )

    def _parse_response(self, raw_response: str) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        try:
            parsed = json.loads(raw_response)
        except json.JSONDecodeError as exc:
            return None, f"LLM response JSON parse error: {exc}"

        if not isinstance(parsed, dict):
            return parsed, "LLM response must be a JSON object."

        required_fields = ["assistant_text", "commands", "need_more_info", "questions"]
        for field in required_fields:
            if field not in parsed:
                return parsed, f"LLM response missing field: {field}"

        if not isinstance(parsed["assistant_text"], str):
            return parsed, "assistant_text must be a string."
        if not isinstance(parsed["commands"], list):
            return parsed, "commands must be a list."
        if not isinstance(parsed["need_more_info"], bool):
            return parsed, "need_more_info must be a boolean."
        if not isinstance(parsed["questions"], list) or not all(isinstance(q, str) for q in parsed["questions"]):
            return parsed, "questions must be a list of strings."

        if parsed["need_more_info"] and parsed["commands"]:
            return parsed, "commands must be empty when need_more_info is true."

        for command in parsed["commands"]:
            if not isinstance(command, dict):
                return parsed, "Each command must be an object."
            if command.get("command") not in ALLOWED_COMMANDS:
                return parsed, f"Unsupported command: {command.get('command')}"
            payload = command.get("payload")
            storage_id = command.get("storage_id")
            if not isinstance(payload, dict):
                return parsed, "Command payload must be an object."
            if not isinstance(storage_id, str) or not storage_id:
                return parsed, "Command storage_id must be a string."

        return parsed, None


def _render_snapshot_table(
    snapshot: Dict[str, Dict[str, int]],
    max_rows: int,
) -> Tuple[str, int, int]:
    if not snapshot:
        return "(склад порожній)", 0, 0

    rows: List[Tuple[str, str, int]] = []
    for item_id in sorted(snapshot.keys()):
        locations = snapshot[item_id]
        for location_key in sorted(locations.keys()):
            qty = locations[location_key]
            location_name = "склад" if location_key == "null" else str(location_key)
            rows.append((str(item_id), location_name, qty))

    total_rows = len(rows)
    truncated = 0
    if len(rows) > max_rows:
        truncated = len(rows) - max_rows
        rows = rows[:max_rows]

    item_width = max(len("Item"), max((len(row[0]) for row in rows), default=0))
    location_width = max(len("Location"), max((len(row[1]) for row in rows), default=0))
    qty_width = max(len("Qty"), max((len(str(row[2])) for row in rows), default=0))

    header = f"{'Item':<{item_width}} | {'Location':<{location_width}} | {'Qty':>{qty_width}}"
    separator = f"{'-' * item_width}-+-{'-' * location_width}-+-{'-' * qty_width}"
    lines = [header, separator]
    for item, location, qty in rows:
        lines.append(f"{item:<{item_width}} | {location:<{location_width}} | {qty:>{qty_width}}")

    if truncated:
        lines.append(f"...ще {truncated} рядків")

    return "\n".join(lines), truncated, total_rows
