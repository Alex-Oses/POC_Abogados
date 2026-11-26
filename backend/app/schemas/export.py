from typing import Literal
from uuid import UUID

from pydantic import BaseModel


class ExportIn(BaseModel):
    numero_version: int | None = None
    modo: Literal["layout", "secuencial"] = "layout"


class ExportOut(BaseModel):
    documento_id: UUID
    numero_version: int
    hash_export: str
    ruta_pdf: str
