from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class AuditOut(BaseModel):
    id: UUID
    usuario_id: UUID | None = None
    accion: str
    entidad: str | None = None
    entidad_id: str | None = None
    detalles: dict[str, Any] | None = None
    hash_anterior: str | None = None
    hash_actual: str
    creado_en: datetime


class ConfigPutIn(BaseModel):
    valor: str = Field(min_length=0, max_length=4000)
    descripcion: str | None = Field(default=None, max_length=500)


class ConfigOut(BaseModel):
    clave: str
    valor: str
    descripcion: str | None = None
    actualizado_en: datetime | None = None
