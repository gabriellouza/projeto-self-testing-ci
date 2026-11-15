"""Envolve a mesma API para medir sobreposição no servidor de carga, sem inserir espera."""
import json
from time import perf_counter_ns

from src.main import app as wallet_app


async def app(scope, receive, send):
    if not (
        scope["type"] == "http" and scope["method"] == "POST" and scope["path"] == "/transfers"
    ):
        await wallet_app(scope, receive, send)
        return

    started_ns = perf_counter_ns()
    status = None

    async def record_status(message):
        nonlocal status
        if message["type"] == "http.response.start":
            status = message["status"]
        await send(message)

    try:
        await wallet_app(scope, receive, record_status)
    finally:
        print("TRANSFER_TRACE " + json.dumps({
            "start_ns": started_ns,
            "end_ns": perf_counter_ns(),
            "status": status,
        }), flush=True)
