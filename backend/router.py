"""FastAPI router for the GET /api/scan endpoint.

Implements in-flight deduplication: if a scan is already in progress when a
second request arrives, the second request awaits the same asyncio.Future
rather than launching a duplicate scan.
"""

from __future__ import annotations

import asyncio
from datetime import datetime

import pytz
from fastapi import APIRouter
from fastapi.responses import JSONResponse

from .scanner import run_scan

router = APIRouter()

_IST = pytz.timezone("Asia/Kolkata")
_scan_lock = asyncio.Lock()
_in_flight: asyncio.Future | None = None


@router.get("/api/scan")
async def scan_endpoint() -> JSONResponse:
    """Trigger a Nifty 100 scan and return the ranked picks.

    Concurrent requests share a single in-progress scan via an
    ``asyncio.Future``.  Once the scan completes all waiters receive the
    same payload.

    Returns:
        HTTP 200 with ``scan_timestamp`` (ISO 8601, IST), ``total_qualified``
        (int), and ``picks`` (array of Top Pick objects) on success.

        HTTP 503 with ``{"error": ...}`` when the scan encounters a fatal
        error (e.g. all symbols fail data retrieval).
    """
    global _in_flight

    async with _scan_lock:
        if _in_flight is None or _in_flight.done():
            loop = asyncio.get_event_loop()
            _in_flight = loop.create_future()
            should_run = True
        else:
            should_run = False
        fut = _in_flight

    if should_run:
        try:
            result = await run_scan()
            ts = datetime.now(_IST).isoformat()
            payload = {
                "scan_timestamp": ts,
                "total_qualified": result["total_qualified"],
                "picks": [vars(p) for p in result["picks"]],
            }
            fut.set_result(payload)
        except Exception as exc:  # noqa: BLE001
            fut.set_exception(exc)

    try:
        payload = await asyncio.shield(fut)
        return JSONResponse(content=payload, status_code=200)
    except Exception as exc:  # noqa: BLE001
        return JSONResponse(content={"error": str(exc)}, status_code=503)
