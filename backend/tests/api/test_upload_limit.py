from app.api.middleware import BodySizeLimitMiddleware


async def test_upload_body_limit_is_bounded_and_other_routes_stay_small():
    async def app(scope, receive, send):
        await send({"type": "http.response.start", "status": 202, "headers": []})
        await send({"type": "http.response.body", "body": b""})

    middleware = BodySizeLimitMiddleware(app, exempt_prefixes=("/api/domain/meetings",))
    for path, size, expected in [
        ("/api/domain/meetings", 2 * 1024 * 1024, 202),
        ("/api/domain/meetings", 301 * 1024 * 1024, 413),
        ("/api/domain/meetings/one/transcribe", 2 * 1024 * 1024, 413),
        ("/api/runs", 2 * 1024 * 1024, 413),
    ]:
        messages = []

        async def send(message, messages=messages):
            messages.append(message)

        async def receive():
            return {"type": "http.request", "body": b""}

        await middleware(
            {"type": "http", "path": path, "method": "POST", "headers": [(b"content-length", str(size).encode())]},
            receive,
            send,
        )
        assert messages[0]["status"] == expected
