# Web client (MVP)

## Цель

Простой чат-клиент прямо в репозиторії, без окремого хостингу.

Працює через існуючий HTTP сервер проекту.

Красивий мінімалізм: форма, кнопка, читабельний лог.

## URL та структура

Веб-статикa лежить у папці: `./web`

Сервер віддає:

- `GET /` -> `web/index.html` (або редирект)
- `GET /web/*` -> статичні файли (js/css)

## API

`POST /api/chat`

### API контракт

**Request JSON:**

- `text: string` (обов’язково)
- `client_id: string` (опціонально)

**Response JSON:**

- `ok: true/false`
- `client_id: string` (повертається завжди при `ok:true`)
- `reply: string` (відповідь бота, тільки USER)

Вебклиент использует относительные пути (api/chat, api/config, web/*), чтобы корректно работать при хостинге в подпапке (например /zsus/) за reverse proxy.

## client_id / user_id правило

Клієнт зберігає `client_id` у localStorage.

Якщо `client_id` відсутній (перший запуск), клієнт робить запит без `client_id`:

- сервер згенерує `client_id`
- клієнт збереже його в localStorage

Опціонально можна задати `user_id` у URL:

- приклад: `http://host:8123/?user_id=coocoo`
- тоді клієнт використовує `client_id = "coocoo"`
- цей `client_id` зберігається в localStorage (поки не зміниться `user_id`)

`user_id` потрібен для ручного “іменування” тестових користувачів без логіну.

## UX / Поведінка

Поле вводу + кнопка Send.

Enter -> відправити.

Після відправки:

- показати повідомлення користувача в чаті
- показати “…” / “thinking” поки чекаємо відповідь
- потім замінити на reply

Помилки:

- якщо сервер недоступний або `ok:false` -> показати короткий рядок помилки в чаті.

Без форматування markdown, просто текст.


## Voice input (Web Speech)

Вебклиент поддерживает голосовой ввод через Web Speech API (SpeechRecognition).

### Поведение:

Кнопка 🎤 показывается только если audio_web_speech_enabled=true (из /api/config) и браузер поддерживает SpeechRecognition.

### UX: hold-to-talk:

нажал и удерживаешь → идёт распознавание
отпустил (или достигли лимита времени) → распознавание останавливается

Язык распознавания: audio_web_speech_lang (default: uk-UA)
Максимальная длительность удержания: audio_web_speech_max_seconds (default: 30)

Если audio_autosend=true:
после распознавания текст автоматически отправляется как обычное сообщение

Если audio_autosend=false:
текст вставляется в поле ввода, пользователь отправляет вручную

### Ошибки доступа к микрофону:

До первого отказа (“Deny”) ничего не показываем.
Если пользователь нажал Deny — показываем подсказку 1 раз (и не спамим дальше).

### overrrides

Значения берутся из дефолтов и могут быть переопределены через .env:

AUDIO_WEB_SPEECH_ENABLED (default: true)
AUDIO_AUTOSEND (default: true)
AUDIO_WEB_SPEECH_LANG (default: uk-UA)
AUDIO_WEB_SPEECH_MAX_SECONDS (default: 30)

Правила:
AUDIO_WEB_SPEECH_MAX_SECONDS валидируется (например 10..120), иначе fallback на default

