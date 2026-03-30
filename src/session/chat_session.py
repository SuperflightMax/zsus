"""Chat session logic shared across interfaces."""

from __future__ import annotations

import json
import os
from typing import List, Optional

from ..core.engine import handle_command
from ..core.result import OperationResult
from ..llm.llm_operator import LLMOperator
from .action_log import append_action_log, normalize_optional_str, normalize_source


class ChatSession:
    """In-memory chat session that mirrors CLI dialog behavior."""

    def __init__(
        self,
        *,
        active_storage_id: Optional[str],
        llm_operator: Optional[LLMOperator] = None,
    ) -> None:
        self.active_storage_id = active_storage_id
        self.dialogue_context: List[str] = []
        self._llm_operator = llm_operator or LLMOperator()

    def set_active_storage_id(self, storage_id: Optional[str]) -> None:
        self.active_storage_id = storage_id

    def _trim_dialogue_context(self, max_entries: int = 6) -> None:
        if max_entries <= 0:
            self.dialogue_context.clear()
            return
        if len(self.dialogue_context) <= max_entries:
            return
        self.dialogue_context = self.dialogue_context[-max_entries:]

    def handle_text(
        self,
        user_text: str,
        *,
        operator_id: Optional[str] = None,
        client_id: Optional[str] = None,
        source: Optional[str] = None,
    ) -> OperationResult:
        system_log: List[str] = [f"Input: {user_text}"]
        if not self.active_storage_id:
            system_log.append("No active storage for LLM input.")
            return OperationResult.failure(
                user_text="Немає активного складу. Спочатку вибери склад через +activatestorage.",
                system_log=system_log,
            )

        self.dialogue_context.append(f"USER: {user_text}")
        dialogue_context_text = "\n".join(self.dialogue_context)

        llm_result, snapshot, model = self._llm_operator.run(
            user_text=user_text,
            active_storage_id=self.active_storage_id,
            dialogue_context=dialogue_context_text,
        )
        system_log.append(f"Active storage: {self.active_storage_id}")
        system_log.append(f"OpenAI model: {model or 'unknown'}")
        system_log.append("OpenAI key present: yes" if os.getenv("OPENAI_API_KEY") else "OpenAI key present: no")
        system_log.append("Dialogue context:")
        system_log.append(dialogue_context_text or "(empty)")
        system_log.append("Snapshot text:")
        system_log.append(snapshot.snapshot_text)
        system_log.extend(llm_result.system_log or [])
        if llm_result.raw_response:
            system_log.append(f"Raw LLM JSON: {llm_result.raw_response}")
        if llm_result.parsed:
            system_log.append(f"Parsed LLM: {json.dumps(llm_result.parsed, ensure_ascii=False)}")

        self.dialogue_context.append(f"ASSISTANT: {llm_result.assistant_text}")
        if not llm_result.ok:
            if not llm_result.need_more_info:
                self.dialogue_context.clear()
            return OperationResult.failure(user_text=llm_result.assistant_text, system_log=system_log)

        if llm_result.need_more_info:
            questions = "\n".join(f"- {q}" for q in llm_result.questions)
            response_text = llm_result.assistant_text
            if questions:
                response_text = f"{response_text}\n\nПитання:\n{questions}"
            return OperationResult.success(user_text=response_text, system_log=system_log)

        normalized_client_id = normalize_optional_str(client_id)
        normalized_operator_id = normalize_optional_str(operator_id)
        normalized_source = normalize_source(source, default="http")

        for command in llm_result.commands:
            payload = command.get("payload") or {}
            storage_id = command.get("storage_id")
            resolved_storage = self.active_storage_id if storage_id == "ACTIVE_STORAGE" else storage_id
            command_payload = {
                "command": command.get("command"),
                "payload": payload,
                "storage_id": resolved_storage,
            }
            system_log.append(f"Executing: {json.dumps(command_payload, ensure_ascii=False)}")
            response = handle_command(command_payload)
            append_action_log(
                command_payload,
                response,
                client_id=normalized_client_id,
                operator_id=normalized_operator_id,
                source=normalized_source,
                source_default="http",
            )
            system_log.append(f"Core result: {json.dumps(response.to_dict(), ensure_ascii=False)}")
            if not response.ok:
                self.dialogue_context.clear()
                user_text = (
                    f"{llm_result.assistant_text}\n\n"
                    "Сталася помилка під час виконання. Спробуй ще раз або уточни запит."
                )
                return OperationResult.failure(user_text=user_text, system_log=system_log)

        self._trim_dialogue_context(max_entries=6)
        return OperationResult.success(user_text=llm_result.assistant_text, system_log=system_log)
