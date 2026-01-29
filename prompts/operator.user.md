ACTIVE_STORAGE: {active_storage_id}

КОНТЕКСТ ДІАЛОГУ (останні репліки; може бути порожнім):
{dialogue_context}

SNAPSHOT (актуальний стан складу):
{snapshot_text}

ДОСТУПНІ КОМАНДИ CORE (коротко, щоб ти формував правильний JSON):

intake
Додає предмети. Формат payload:
{{
"items": [
{{ "item_id": "string", "qty": 1, "unit": "string", "location": "string або null (склад)" }}
]
}}
storage_id завжди ACTIVE_STORAGE.

move
Переміщує предмети. Формат payload:
{{
"item_id": "string",
"qty": 1,
"from": "string або null (склад)",
"to": "string або null (склад)"
}}

consume
Списує/забирає предмет(и). Формат payload:
{{
"item_id": "string",
"qty": 1,
"from": "string або null (склад)"
}}

qty — число, може бути дробовим.

ЗАПИТ КОРИСТУВАЧА:
{user_text}

ПОВЕРНИ ЛИШЕ JSON У ВКАЗАНІЙ СХЕМІ. НІЯКОГО ТЕКСТУ ПОЗА JSON.
