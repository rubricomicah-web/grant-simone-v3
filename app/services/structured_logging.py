"""Structured logging helpers for Mogul Grant System.

Inspired by the MCP grant hunter request-observability pattern, but adapted
for the Mogul product. These helpers keep external API calls debuggable
without leaking raw logs to client-facing screens.
"""
from __future__ import annotations

import logging
import time
import uuid
from contextlib import contextmanager
from typing import Iterator

logger = logging.getLogger("mogul")


def request_id(prefix: str = "mgs") -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


@contextmanager
def timed_external_call(service: str, **fields) -> Iterator[dict]:
    start = time.perf_counter()
    rid = fields.pop("request_id", None) or request_id(service.replace(".", "_"))
    ctx = {"request_id": rid, "service": service, **fields}
    logger.info("external_call_start service=%s request_id=%s fields=%s", service, rid, fields)
    try:
        yield ctx
        duration_ms = (time.perf_counter() - start) * 1000
        logger.info("external_call_success service=%s request_id=%s duration_ms=%.2f", service, rid, duration_ms)
    except Exception as exc:
        duration_ms = (time.perf_counter() - start) * 1000
        logger.warning(
            "external_call_failed service=%s request_id=%s duration_ms=%.2f error=%s",
            service,
            rid,
            duration_ms,
            str(exc),
        )
        raise


def log_business_match(opportunity_title: str, score: int, reasons: list[str] | None = None) -> None:
    logger.info(
        "business_match title=%s score=%s reasons=%s",
        opportunity_title,
        score,
        "; ".join(reasons or []),
    )
