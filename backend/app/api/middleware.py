import json

from starlette.types import ASGIApp, Message, Receive, Scope, Send

MAX_BODY_BYTES = 1024 * 1024


class PayloadTooLarge(Exception):
    pass


class BodySizeLimitMiddleware:
    def __init__(
        self,
        app: ASGIApp,
        max_bytes: int = MAX_BODY_BYTES,
        exempt_prefixes: tuple[str, ...] = (),
        upload_max_bytes: int = 300 * 1024 * 1024,
    ) -> None:
        self._app = app
        self._max_bytes = max_bytes
        self._exempt = exempt_prefixes
        self._upload_max_bytes = upload_max_bytes

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            return await self._app(scope, receive, send)
        path = scope.get("path", "")
        is_upload = scope.get("method") == "POST" and any(path.rstrip("/") == p.rstrip("/") for p in self._exempt)
        max_bytes = self._upload_max_bytes if is_upload else self._max_bytes
        headers = {k.decode().lower(): v.decode() for k, v in scope.get("headers", [])}
        declared = headers.get("content-length", "")
        if declared.isdigit() and int(declared) > max_bytes:
            return await self._reject(send, max_bytes)
        received = 0

        async def limited_receive() -> Message:
            nonlocal received
            message = await receive()
            if message["type"] == "http.request":
                received += len(message.get("body", b""))
                if received > max_bytes:
                    raise PayloadTooLarge()
            return message

        try:
            await self._app(scope, limited_receive, send)
        except PayloadTooLarge:
            await self._reject(send, max_bytes)

    async def _reject(self, send: Send, max_bytes: int) -> None:
        payload = {
            "error": {
                "code": "payload_too_large",
                "message": f"Request body exceeds {max_bytes} bytes",
                "details": {},
            }
        }
        body = json.dumps(payload).encode()
        await send(
            {
                "type": "http.response.start",
                "status": 413,
                "headers": [(b"content-type", b"application/json"), (b"content-length", str(len(body)).encode())],
            }
        )
        await send({"type": "http.response.body", "body": body})
