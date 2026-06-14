from __future__ import annotations

import logging
import os
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from typing import Iterator


logger = logging.getLogger(__name__)
_active_scope: ContextVar["WriterScope | None"] = ContextVar("stage2_writer_scope", default=None)


class WriterRoutingError(RuntimeError):
    """Raised when runtime code bypasses the frozen Stage 2 writer boundary."""


@dataclass(frozen=True)
class WriterScope:
    domain: str
    application_service: str


def canonical_writer_enabled() -> bool:
    return os.getenv("STAGE2_CANONICAL_WRITER_ENABLED", "0").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


@contextmanager
def canonical_write_scope(domain: str, application_service: str) -> Iterator[None]:
    token = _active_scope.set(WriterScope(domain=domain, application_service=application_service))
    try:
        yield
    finally:
        _active_scope.reset(token)


def require_canonical_write(domain: str, location: str) -> None:
    if not canonical_writer_enabled():
        return
    scope = _active_scope.get()
    if scope is None or scope.domain != domain:
        logger.error(
            "canonical writer bypass rejected",
            extra={"domain": domain, "location": location, "scope": scope},
        )
        raise WriterRoutingError(
            f"{location} cannot write {domain}; use its canonical application service"
        )


def require_legacy_compatibility_write(domain: str, location: str) -> None:
    if not canonical_writer_enabled():
        return
    logger.error(
        "legacy compatibility write rejected",
        extra={"domain": domain, "location": location},
    )
    raise WriterRoutingError(
        f"{location} is compatibility-read-only while canonical writer routing is enabled"
    )
