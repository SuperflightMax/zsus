"""Minimal HTTP adapter for ChatSession."""

from __future__ import annotations

import json
import logging
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict, Optional
from urllib.parse import urlparse
from uuid import uuid4

from ...core.engine import set_default_backend
from ...infra import load_config
from ...infra.backend_factory import create_backend
from ...infra.storage_registry import StorageRegistry
from ...session import SessionManager

DEFAULT_HOST = "0.0.0.0"
DEFAULT_PORT = 8123
WEB_ROOT = Path(__file__).resolve().parents[3] / "web"
CLIENT_CONFIG_DEFAULTS = {
    "audio_web_speech_enabled": True,
    "audio_autosend": True,
    "audio_web_speech_lang": "uk-UA",
    "audio_web_speech_max_seconds": 30,
}
CLIENT_MAX_SECONDS_RANGE = (5, 120)
DEFAULT_STORAGE_TITLE = 'СКЛАД "ШВЕЙНА МАЙСТЕРНЯ"'
DEFAULT_STORAGE_SUBTITLE = "ШІ оператор online."


class ChatHandler(BaseHTTPRequestHandler):
    """HTTP handler for health checks and chat requests."""

    server_version = "zsus-http/0.1"

    def do_GET(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        if path == "/health":
            self._send_json(200, {"ok": True})
            return
        if path == "/api/config":
            self._send_json(200, {"ok": True, "client": _get_client_config()})
            return
        if path == "/api/meta":
            title, subtitle = _get_storage_titles()
            response = {
                "ok": True,
                "storage": {
                    "id": self.server.default_storage_id,
                    "title": title,
                    "subtitle": subtitle,
                },
                "server": {"version": self.server_version},
            }
            self._send_json(200, response)
            return

        if path == "/":
            self._send_file(WEB_ROOT / "index.html")
            return

        if path == "/web" or path.startswith("/web/"):
            rel_path = path[len("/web") :]
            self._send_static(rel_path)
            return

        self._send_json(404, {"ok": False, "error": "not_found", "message": "not found"})

    def do_POST(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        if path not in ("/chat", "/api/chat"):
            self._send_json(404, {"ok": False, "error": "not_found", "message": "not found"})
            return

        try:
            payload = self._read_json()
        except ValueError as exc:
            self._send_json(400, {"ok": False, "error": "bad_request", "message": str(exc)})
            return

        text = payload.get("text")
        if not isinstance(text, str) or not text.strip():
            self._send_json(400, {"ok": False, "error": "bad_request", "message": "text is required"})
            return

        client_id = payload.get("client_id")
        if not isinstance(client_id, str) or not client_id.strip():
            client_id = str(uuid4())
        else:
            client_id = client_id.strip()

        operator_id = payload.get("operator_id")
        if isinstance(operator_id, str):
            operator_id = operator_id.strip() or None
        else:
            operator_id = None

        try:
            session = self.server.session_manager.get(client_id)
            if session.active_storage_id is None and self.server.default_storage_id:
                session.set_active_storage_id(self.server.default_storage_id)
            result = session.handle_text(
                text,
                operator_id=operator_id,
                client_id=client_id,
                source="http",
            )
            response = {"ok": True, "client_id": client_id, "reply": result.user_text}
            self._send_json(200, response)
        except Exception as exc:  # noqa: BLE001
            logging.exception("Unhandled error in %s", path)
            self._send_json(500, {"ok": False, "error": "internal_error", "message": str(exc)})

    def _read_json(self) -> Dict[str, Any]:
        length_header = self.headers.get("Content-Length")
        if length_header is None:
            raise ValueError("missing request body")
        try:
            length = int(length_header)
        except ValueError as exc:
            raise ValueError("invalid Content-Length") from exc

        raw_body = self.rfile.read(length).decode("utf-8")
        if not raw_body:
            raise ValueError("empty request body")
        try:
            data = json.loads(raw_body)
        except json.JSONDecodeError as exc:
            raise ValueError("invalid json") from exc

        if not isinstance(data, dict):
            raise ValueError("json body must be an object")
        return data

    def _send_json(self, status: int, payload: Dict[str, Any]) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_static(self, raw_path: str) -> None:
        rel_path = raw_path.lstrip("/")
        if rel_path in ("", "/"):
            rel_path = "index.html"
        if rel_path.endswith("/"):
            rel_path = f"{rel_path}index.html"

        candidate = (WEB_ROOT / rel_path).resolve()
        try:
            candidate.relative_to(WEB_ROOT)
        except ValueError:
            self._send_json(404, {"ok": False, "error": "not_found", "message": "not found"})
            return

        if not candidate.is_file():
            self._send_json(404, {"ok": False, "error": "not_found", "message": "not found"})
            return

        self._send_file(candidate)

    def _send_file(self, path: Path) -> None:
        if not path.exists() or not path.is_file():
            self._send_json(404, {"ok": False, "error": "not_found", "message": "not found"})
            return

        content_type = self._content_type(path.suffix.lower())
        data = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _content_type(self, suffix: str) -> str:
        if suffix == ".html":
            return "text/html; charset=utf-8"
        if suffix == ".js":
            return "text/javascript; charset=utf-8"
        if suffix == ".css":
            return "text/css; charset=utf-8"
        return "application/octet-stream"

    def log_message(self, format: str, *args: Any) -> None:  # noqa: A002
        logging.info("%s - %s", self.address_string(), format % args)


class ChatHTTPServer(ThreadingHTTPServer):
    """Threaded HTTP server carrying shared session manager."""

    def __init__(
        self,
        server_address: tuple[str, int],
        handler_class: type[BaseHTTPRequestHandler],
        *,
        session_manager: SessionManager,
        default_storage_id: Optional[str],
    ) -> None:
        super().__init__(server_address, handler_class)
        self.session_manager = session_manager
        self.default_storage_id = default_storage_id


def _load_default_storage_id(registry: StorageRegistry) -> Optional[str]:
    storage_id = os.getenv("DEFAULT_STORAGE")
    if not storage_id:
        return None
    if registry.storage_exists(storage_id):
        return storage_id
    logging.warning("Default storage not found: %s", storage_id)
    return None


def _resolve_port(raw_port: Optional[str]) -> int:
    if raw_port is None or raw_port == "":
        return DEFAULT_PORT
    port = int(raw_port)
    if port < 1 or port > 65535:
        raise ValueError("ZSUS_HTTP_PORT must be between 1 and 65535")
    return port


def _parse_bool_env(value: Optional[str], default: bool) -> bool:
    if value is None:
        return default
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes"}:
        return True
    if normalized in {"0", "false", "no"}:
        return False
    return default


def _parse_int_range(value: Optional[str], default: int, minimum: int, maximum: int) -> int:
    if value is None:
        return default
    try:
        parsed = int(value.strip())
    except ValueError:
        return default
    if parsed < minimum or parsed > maximum:
        return default
    return parsed


def _get_client_config() -> Dict[str, Any]:
    min_seconds, max_seconds = CLIENT_MAX_SECONDS_RANGE
    return {
        "audio_web_speech_enabled": _parse_bool_env(
            os.getenv("AUDIO_WEB_SPEECH_ENABLED"),
            CLIENT_CONFIG_DEFAULTS["audio_web_speech_enabled"],
        ),
        "audio_autosend": _parse_bool_env(
            os.getenv("AUDIO_AUTOSEND"),
            CLIENT_CONFIG_DEFAULTS["audio_autosend"],
        ),
        "audio_web_speech_lang": os.getenv(
            "AUDIO_WEB_SPEECH_LANG",
            CLIENT_CONFIG_DEFAULTS["audio_web_speech_lang"],
        ),
        "audio_web_speech_max_seconds": _parse_int_range(
            os.getenv("AUDIO_WEB_SPEECH_MAX_SECONDS"),
            CLIENT_CONFIG_DEFAULTS["audio_web_speech_max_seconds"],
            min_seconds,
            max_seconds,
        ),
    }


def _get_storage_titles() -> tuple[str, str]:
    title = os.getenv("STORAGE_TITLE", DEFAULT_STORAGE_TITLE)
    subtitle = os.getenv("STORAGE_SUBTITLE", DEFAULT_STORAGE_SUBTITLE)
    return title, subtitle


def run() -> None:
    config = load_config()
    logging_level = config.get("logging", {}).get("level", "INFO")
    logging.basicConfig(level=getattr(logging, logging_level.upper(), logging.INFO))

    _, backend = create_backend(config)
    set_default_backend(backend)

    registry = StorageRegistry(config)
    default_storage_id = _load_default_storage_id(registry)

    host = os.getenv("ZSUS_HTTP_HOST", DEFAULT_HOST)
    port = _resolve_port(os.getenv("ZSUS_HTTP_PORT"))

    server = ChatHTTPServer(
        (host, port),
        ChatHandler,
        session_manager=SessionManager(),
        default_storage_id=default_storage_id,
    )

    logging.info("HTTP server listening on %s:%s", host, port)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logging.info("HTTP server stopped.")


if __name__ == "__main__":
    run()
