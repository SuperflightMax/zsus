import json
import sys
import types
from http.client import HTTPConnection
from threading import Thread

from src.core.result import OperationResult

sys.modules.setdefault("yaml", types.SimpleNamespace(safe_load=lambda *args, **kwargs: {}))
sys.modules.setdefault("dotenv", types.SimpleNamespace(load_dotenv=lambda *args, **kwargs: None))

from src.interfaces.http.server import ChatHandler, ChatHTTPServer


class RecordingSession:
    def __init__(self) -> None:
        self.calls = []
        self.active_storage_id = None

    def handle_text(self, text, *, operator_id=None, client_id=None, source=None):
        self.calls.append(
            {
                "text": text,
                "operator_id": operator_id,
                "client_id": client_id,
                "source": source,
            }
        )
        return OperationResult.success(user_text="ok", system_log=[])

    def set_active_storage_id(self, storage_id):
        self.active_storage_id = storage_id


class RecordingSessionManager:
    def __init__(self, session: RecordingSession) -> None:
        self._session = session
        self.client_ids = []

    def get(self, client_id: str):
        self.client_ids.append(client_id)
        return self._session


def _start_test_server(session_manager: RecordingSessionManager) -> tuple[ChatHTTPServer, Thread]:
    server = ChatHTTPServer(
        ("127.0.0.1", 0),
        ChatHandler,
        session_manager=session_manager,
        default_storage_id=None,
    )
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, thread


def test_http_chat_forwards_operator_id_client_id_and_source():
    session = RecordingSession()
    manager = RecordingSessionManager(session)
    server, thread = _start_test_server(manager)
    host, port = server.server_address

    try:
        conn = HTTPConnection(host, port, timeout=3)
        payload = {"text": "test", "client_id": " abc ", "operator_id": " Falcon "}
        conn.request("POST", "/api/chat", body=json.dumps(payload), headers={"Content-Type": "application/json"})
        response = conn.getresponse()
        body = json.loads(response.read().decode("utf-8"))
        conn.close()

        assert response.status == 200
        assert body["ok"] is True
        assert body["client_id"] == "abc"
        assert session.calls == [
            {
                "text": "test",
                "operator_id": "Falcon",
                "client_id": "abc",
                "source": "http",
            }
        ]
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_http_chat_normalizes_non_string_operator_id_to_none():
    session = RecordingSession()
    manager = RecordingSessionManager(session)
    server, thread = _start_test_server(manager)
    host, port = server.server_address

    try:
        conn = HTTPConnection(host, port, timeout=3)
        payload = {"text": "test", "client_id": "abc", "operator_id": {"bad": "type"}}
        conn.request("POST", "/api/chat", body=json.dumps(payload), headers={"Content-Type": "application/json"})
        response = conn.getresponse()
        body = json.loads(response.read().decode("utf-8"))
        conn.close()

        assert response.status == 200
        assert body["ok"] is True
        assert session.calls == [
            {
                "text": "test",
                "operator_id": None,
                "client_id": "abc",
                "source": "http",
            }
        ]
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
