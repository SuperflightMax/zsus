# LLM Interpreter

Цей документ описує поточну реалізацію LLM Interpreter, що перетворює український текст у структуровані JSON-команди для ядра (core). LLM не виконує команди, не керує UX і не спілкується з користувачем напряму — він лише повертає інтерпретацію наміру.

## Папки та файли
- `src/llm/interpreter.py` — логіка виклику LLM і нормалізації відповіді до контракту.
- `src/llm/system_prompt.py` — окремий system prompt з правилами інтерпретації.
- `src/interfaces/cli/main.py` — plain-text введення йде через Interpreter, CLI може одразу виконати безпечну команду або попросити підтвердження.
- `tests/llm/test_interpreter.py` — покриття ключових сценаріїв (intake, consume, низька впевненість, unknown, вимкнений LLM).
- `tests/interfaces/test_cli_llm_flow.py` — перевірка інтеграції CLI з LLM (виконання без підтвердження, відмова, відсутній склад).

## Контракт відповіді
Інтерпретатор завжди повертає JSON:
```json
{
  "intent": "intake | move | consume | find | list | unknown",
  "confidence": 0.0,
  "needs_confirmation": false,
  "human_summary": "string",
  "command": { ... } | null,
  "questions": []
}
```

### Правила підтвердження
- `needs_confirmation = true`, якщо `intent = consume`, `intent = unknown`, відсутні критичні параметри, `confidence` нижче порогу або є неоднозначності (флаг від моделі).
- `needs_confirmation = false`, якщо команда однозначна, безпечна (`intake`, `find`, `list`), параметри повні й `confidence` достатній.

## Налаштування
Читаються з `.env` або середовища:
- `LLM_ENABLED` — вмикає інтерпретацію (1/true/yes/on).
- `OPENAI_API_KEY` — ключ для клієнта (обов’язковий коли LLM увімкнено).
- `OPENAI_BASE_URL` — альтернативний endpoint (необов’язково).
- `OPENAI_MODEL` — модель чату (за замовчуванням `gpt-4.1`, має збігатися з вимогою `OPENAI_MODEL = gpt-4.1`).
- `OPENAI_STT_MODEL` — зарезервовано для майбутньої роботи з аудіо.

З конфігу (`config/default.yaml`) використовується `core.confidence_threshold` (0.7 за замовчуванням) для правила підтвердження.

Встановлення залежностей:
- `pip install -e .` (встановить `openai`, `pyyaml`, `python-dotenv` із `pyproject.toml`).
- Або точково: `pip install openai pyyaml python-dotenv`.

## Потік роботи
1. `Interpreter.interpret(text)` перевіряє ввімкнення LLM (через `LLM_ENABLED` або `llm.enabled` у конфігу).
2. Викликається OpenAI Chat Completions з `SYSTEM_PROMPT` і `response_format=json_object`, `temperature=0`.
3. Відповідь нормалізується, фільтруються невірні `intent` і `command`, обрізаються значення за контрактом core.
4. Застосовуються правила підтвердження (поріг, `consume`, `unknown`, відсутній payload тощо).
5. Повертається словник у контракті вище; у разі помилки — `intent=unknown`, `needs_confirmation=true`, питання для уточнення.

### Потік у CLI
- Звичайний текст (не JSON і не адмін-команда) проходить через Interpreter; CLI виводить структурований результат.
- Якщо є `command` і `needs_confirmation=false` → команда виконується одразу з активним складом.
- Якщо `needs_confirmation=true` → CLI питає `Execute this command? [y/N]`; за відмови команда не виконується.
- Без активного складу команда не виконується (буде підказка).

## Розширення під голос/зображення
Модуль наразі текстовий, але залишає підготовлені точки:
- Системний prompt нагадує, що фото/аудіо не виконуються без підтвердження.
- Можна додати попередню обробку (транскрипцію/візуальний пайплайн) перед викликом `Interpreter`, залишаючи контракт незмінним.

## Верифікація
Основні тести: `tests/llm/test_interpreter.py`. Запуск: `pytest tests/llm/test_interpreter.py`.
