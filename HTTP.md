HTTP Interface (MVP)

Цель

Дать простой HTTP-адаптер для ChatSession, чтобы подключать любые клиенты (Web/Android/Telegram/…).

HTTP-слой не содержит логики: только принимает ввод, дергает SessionManager/ChatSession, возвращает USER-ответ.

Прототип: без авторизации, без персистентности, рестарт сервера = потеря сессий/контекстов (OK).

Базовые понятия

client_id: строковый идентификатор “клиентской сессии”. Нужен для изоляции диалогового контекста.

Если client_id не передан, сервер генерирует новый и возвращает его. Клиент обязан сохранить client_id и передавать в следующих запросах.

storage_id: на этом этапе один общий склад для всех (DEFAULT_STORAGE). Контекст всё равно у каждого свой.

Network / Bind

HTTP-сервер поднимается самим проектом, на отдельном порту.

Default порт: 8123

Опционально можно переопределить через .env (ZSUS_HTTP_PORT). Если переменной нет — используем дефолт.

Host по умолчанию: 0.0.0.0 (чтобы было доступно извне). Опционально: ZSUS_HTTP_HOST.

Endpoints

GET /health
Назначение: проверка, что сервис жив.
Ответ 200 JSON:

ok: true

POST /chat
Назначение: отправить “сообщение пользователя” и получить ответ ассистента.
Request JSON:

text: string (обязательно)

client_id: string (опционально)

Response 200 JSON:

ok: true

client_id: string (всегда возвращается; либо входной, либо сгенерированный сервером)

reply: string (это OperationResult.user_text и только он)

Ошибки

400: если нет text или text пустой/не строка
Response JSON:

ok: false

error: "bad_request"

message: "text is required"

500: внутренняя ошибка
Response JSON:

ok: false

error: "internal_error"

message: "..."

Правила вывода

HTTP-адаптер всегда возвращает только USER часть: OperationResult.user_text.

SYSTEM лог никогда не выдаётся наружу через /chat (даже в debug mode).

Внутренние логи (actions.log и т.п.) продолжают писаться как сейчас.

Прототипные ограничения (осознанно)

Нет авторизации, ролей, ACL.

Нет сохранения сессий на диск.

Нет стриминга ответа (всё одним JSON).

Нет аудио/картинок: пока только text.

Расширения (позже, без ломки контракта)

POST /upload (для image/audio) с возвращением file_ref

POST /chat с input.type и attachments

SSE / streaming endpoint для “печатания”

auth: client_id -> user_id, права