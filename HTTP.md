# HTTP Interface (MVP)

## Goal

Provide a minimal HTTP adapter for `ChatSession` so web/Android/Telegram/other clients can connect
without changing core/LLM logic. The HTTP layer has **no business logic**: it only accepts input,
invokes `SessionManager`/`ChatSession`, and returns the USER response.

Prototype constraints are explicit and intentional: no auth, no persistence, server restart resets sessions.

## Core Concepts

- **client_id** — string identifier for a client session (dialogue context isolation).
  - If not provided, the server generates one and returns it.
  - The client must store it and send it on all subsequent requests.
- **storage_id** — single shared storage for now (`DEFAULT_STORAGE`). Context is still per-client.

## Bind / Network

- **Default host:** `0.0.0.0`
- **Default port:** `8123`
- Optional overrides:
  - `ZSUS_HTTP_HOST`
  - `ZSUS_HTTP_PORT`

## Endpoints

### `GET /health`

**Purpose:** liveness check.

**Response 200**
```json
{ "ok": true }
```

### `POST /api/chat`

**Purpose:** send a user message and receive assistant reply.

**Request JSON**
```json
{
  "text": "string (required)",
  "client_id": "string (optional)"
}
```

**Response 200**
```json
{
  "ok": true,
  "client_id": "<client_id>",
  "reply": "<OperationResult.user_text>"
}
```

### `POST /chat`

**Purpose:** backward-compatible alias for `/api/chat`.

## Errors

### 400 — Bad Request

Returned when:
- `text` is missing
- `text` is not a string or empty
- invalid JSON

**Response JSON**
```json
{
  "ok": false,
  "error": "bad_request",
  "message": "text is required"
}
```

### 500 — Internal Error

Unexpected server error.

**Response JSON**
```json
{
  "ok": false,
  "error": "internal_error",
  "message": "..."
}
```

## Output Rules

- HTTP adapter **must return only** `OperationResult.user_text`.
- `OperationResult.system_log` is **never** exposed to HTTP clients.
- Internal logs (`logs/actions.log`) continue as-is.

## Static Web Client

The HTTP server also serves a minimal static web client from `./web`:

- `GET /` -> `web/index.html`
- `GET /web/*` -> static assets (js/css)

## Prototype Limitations (MVP)

- No auth / roles / ACL.
- No session persistence (restart = new sessions).
- No streaming (single JSON response).
- Only text input (no audio/images yet).

## Future Extensions (non-breaking)

- `POST /upload` for image/audio with `file_ref` responses.
- `POST /chat` with `input.type` and attachments.
- SSE / streaming responses.
- Auth: `client_id` → `user_id`, permissions.
