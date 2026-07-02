"""Logging centralizado para la web Retro76 y sondas al OT."""
from __future__ import annotations

import logging
import os
import sys
import time
import traceback
from logging.handlers import RotatingFileHandler
from pathlib import Path

LOG_DIR = Path(os.environ.get("WEB_LOG_DIR", Path(__file__).resolve().parent / "logs"))
LOG_FILE = Path(os.environ.get("WEB_LOG_FILE", LOG_DIR / "retro76-web.log"))
MAX_BYTES = int(os.environ.get("WEB_LOG_MAX_BYTES", str(5 * 1024 * 1024)))
BACKUP_COUNT = int(os.environ.get("WEB_LOG_BACKUP_COUNT", "5"))
LOG_LEVEL = os.environ.get("WEB_LOG_LEVEL", "INFO").upper()

_CONFIGURED = False


def setup_logging() -> None:
    global _CONFIGURED
    if _CONFIGURED:
        return
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    root = logging.getLogger("retro76")
    root.setLevel(getattr(logging, LOG_LEVEL, logging.INFO))
    root.handlers.clear()

    fmt = logging.Formatter(
        "%(asctime)s UTC [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    fmt.converter = time.gmtime  # type: ignore[method-assign]

    file_handler = RotatingFileHandler(
        LOG_FILE,
        maxBytes=MAX_BYTES,
        backupCount=BACKUP_COUNT,
        encoding="utf-8",
    )
    file_handler.setFormatter(fmt)
    root.addHandler(file_handler)

    if os.environ.get("WEB_LOG_STDOUT", "").lower() in {"1", "true", "yes"}:
        stream = logging.StreamHandler(sys.stdout)
        stream.setFormatter(fmt)
        root.addHandler(stream)

    _CONFIGURED = True


def get_logger(name: str) -> logging.Logger:
    setup_logging()
    return logging.getLogger(f"retro76.{name}")


def log_ot_probe(
    host: str,
    port: int,
    *,
    ok: bool,
    elapsed_ms: float,
    players_online: int | None = None,
    error: str = "",
    cached: bool = False,
) -> None:
    log = get_logger("ot")
    extra = f" players={players_online}" if players_online is not None else ""
    cache = " cache=1" if cached else ""
    if ok:
        log.info(
            "probe OK %s:%s %.0fms%s%s",
            host,
            port,
            elapsed_ms,
            extra,
            cache,
        )
    else:
        log.warning(
            "probe FAIL %s:%s %.0fms error=%s%s",
            host,
            port,
            elapsed_ms,
            error or "unknown",
            cache,
        )


def log_http(
    method: str,
    path: str,
    status: int,
    elapsed_ms: float,
    client_ip: str,
    *,
    detail: str = "",
) -> None:
    log = get_logger("http")
    msg = f"{method} {path} {status} {elapsed_ms:.0f}ms ip={client_ip}"
    if detail:
        msg += f" {detail}"
    if status >= 500 or elapsed_ms >= 3000:
        log.warning(msg)
    elif status >= 400:
        log.info(msg)
    else:
        log.debug(msg)


def log_exception(component: str, exc: BaseException, *, context: str = "") -> None:
    log = get_logger(component)
    tb = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
    if context:
        log.error("exception context=%s\n%s", context, tb.rstrip())
    else:
        log.error("exception\n%s", tb.rstrip())
