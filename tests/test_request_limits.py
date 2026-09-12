import asyncio

from workbench.request_limits import RequestLimit


def test_chunked_request_limit_rejects_before_route_is_called():
    sent = []
    called = []

    async def app(*args):
        called.append(True)

    chunks = iter(
        [
            {"type": "http.request", "body": b"abc", "more_body": True},
            {"type": "http.request", "body": b"def", "more_body": False},
        ]
    )

    async def receive():
        return next(chunks)

    async def send(message):
        sent.append(message)

    asyncio.run(RequestLimit(app, 5)({"type": "http", "headers": []}, receive, send))
    assert not called
    assert sent[0]["status"] == 413
