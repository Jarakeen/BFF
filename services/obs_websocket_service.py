from __future__ import annotations

import base64
import hashlib
import json
import uuid

from PySide6.QtCore import QObject, QTimer, QUrl, Signal
from PySide6.QtNetwork import QAbstractSocket
from PySide6.QtWebSockets import QWebSocket


class ObsWebSocketService(QObject):
    """A small OBS WebSocket v5 client used only for safe scene changes.

    OBS owns the switch on its WebSocket/UI path; the Lua polling timer is
    deliberately not involved.
    """

    scene_changed = Signal(str)
    failed = Signal(str)

    def __init__(self, host: str, port: int, password: str, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.host = host.strip() or "127.0.0.1"
        self.port = int(port or 4455)
        self.password = password
        self._scene_name = ""
        self._request_id = ""
        self._socket = QWebSocket()
        self._socket.textMessageReceived.connect(self._on_message)
        self._socket.errorOccurred.connect(self._on_error)
        self._timeout = QTimer(self)
        self._timeout.setSingleShot(True)
        self._timeout.timeout.connect(self._on_timeout)

    def switch_scene(self, scene_name: str) -> None:
        if not scene_name.strip():
            self.failed.emit("OBS scene name is empty")
            return
        if self._socket.state() != QAbstractSocket.SocketState.UnconnectedState:
            self._socket.abort()
        self._scene_name = scene_name.strip()
        self._timeout.start(6000)
        self._socket.open(QUrl(f"ws://{self.host}:{self.port}"))

    def _on_message(self, text: str) -> None:
        try:
            message = json.loads(text)
            op = message["op"]
            data = message["d"]
        except (KeyError, TypeError, json.JSONDecodeError):
            self._fail("OBS sent an unreadable WebSocket message")
            return

        if op == 0:  # Hello
            identify = {"rpcVersion": data.get("rpcVersion", 1)}
            authentication = data.get("authentication")
            if authentication:
                identify["authentication"] = self._authentication(authentication)
            self._socket.sendTextMessage(json.dumps({"op": 1, "d": identify}))
        elif op == 2:  # Identified
            self._request_id = str(uuid.uuid4())
            request = {
                "op": 6,
                "d": {
                    "requestType": "SetCurrentProgramScene",
                    "requestId": self._request_id,
                    "requestData": {"sceneName": self._scene_name},
                },
            }
            self._socket.sendTextMessage(json.dumps(request))
        elif op == 7 and data.get("requestId") == self._request_id:
            status = data.get("requestStatus", {})
            if status.get("result"):
                scene_name = self._scene_name
                self._finish()
                self.scene_changed.emit(scene_name)
            else:
                self._fail(status.get("comment") or "OBS rejected the scene change")

    def _authentication(self, details: dict) -> str:
        salt = details.get("salt", "")
        challenge = details.get("challenge", "")
        secret = base64.b64encode(hashlib.sha256((self.password + salt).encode("utf-8")).digest())
        return base64.b64encode(hashlib.sha256(secret + challenge.encode("utf-8")).digest()).decode("utf-8")

    def _on_error(self, _error: object) -> None:
        self._fail(f"Could not connect to OBS at {self.host}:{self.port}")

    def _on_timeout(self) -> None:
        self._fail("OBS did not respond within six seconds")

    def _finish(self) -> None:
        self._timeout.stop()
        self._socket.close()

    def _fail(self, message: str) -> None:
        if not self._timeout.isActive():
            return
        self._finish()
        self.failed.emit(message)
