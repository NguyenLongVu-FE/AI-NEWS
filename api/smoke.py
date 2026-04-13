async def app(scope, receive, send):
    if scope.get("type") != "http":
        return

    body = b'{"ok": true, "service": "smoke"}'
    headers = [(b"content-type", b"application/json")]
    await send({"type": "http.response.start", "status": 200, "headers": headers})
    await send({"type": "http.response.body", "body": body})
