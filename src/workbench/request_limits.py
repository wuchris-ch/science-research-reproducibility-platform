"""Bound incoming bytes before parsing, including chunked requests without a length."""

from starlette.responses import JSONResponse


class RequestLimit:
    def __init__(self, app, max_bytes: int):
        self.app = app
        self.max_bytes = max_bytes

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        try:
            length = int(dict(scope["headers"]).get(b"content-length", b"0"))
            if length < 0:
                raise ValueError
        except ValueError:
            return await JSONResponse({"detail": "Invalid content length"}, 400)(scope, receive, send)
        if length > self.max_bytes:
            return await JSONResponse({"detail": "Request too large"}, 413)(scope, receive, send)
        messages, size = [], 0
        while True:
            message = await receive()
            if message["type"] == "http.disconnect":
                return
            size += len(message.get("body", b""))
            if size > self.max_bytes:
                return await JSONResponse({"detail": "Request too large"}, 413)(scope, receive, send)
            messages.append(message)
            if not message.get("more_body", False):
                break
        iterator = iter(messages)

        async def replay():
            return next(iterator, None) or await receive()

        await self.app(scope, replay, send)
