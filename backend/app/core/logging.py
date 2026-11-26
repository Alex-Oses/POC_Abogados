import json
import logging
import sys
import uuid
from contextvars import ContextVar
from datetime import UTC, datetime

request_id: ContextVar[str] = ContextVar("request_id", default="-")

log = logging.getLogger("icat")


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        base = {
            "ts": datetime.now(UTC).isoformat(),
            "nivel": record.levelname,
            "mensaje": record.getMessage(),
            "request_id": request_id.get(),
        }
        for clave in ("metodo", "ruta", "estado", "ms", "detalle"):
            if hasattr(record, clave):
                base[clave] = getattr(record, clave)
        if record.exc_info:
            base["excepcion"] = self.formatException(record.exc_info)
        return json.dumps(base, ensure_ascii=False)


def setup_logging() -> None:
    if log.handlers:
        return
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    log.addHandler(handler)
    log.setLevel("INFO")
    log.propagate = False


def nuevo_request_id() -> str:
    return uuid.uuid4().hex
