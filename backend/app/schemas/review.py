from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

EstadoAnotacion = Literal["pendiente", "aceptada", "rechazada", "corregida", "falso_negativo"]
EstadoRevision = Literal["pendiente", "en_curso", "aprobada", "rechazada"]


class AnonymizeIn(BaseModel):
    numero_version: int | None = None
    regla_ids: list[UUID] | None = None


class AnnotationOut(BaseModel):
    id: UUID
    version_id: UUID
    bloque_id: UUID
    categoria_id: UUID | None = None
    inicio: int
    fin: int
    texto_original: str
    texto_sustitucion: str | None = None
    estado: str


class AnnotationPatchIn(BaseModel):
    estado: EstadoAnotacion
    texto_sustitucion: str | None = Field(default=None, max_length=500)


class ReviewOut(BaseModel):
    id: UUID
    documento_id: UUID
    revisor_id: UUID | None = None
    estado: str
    motivo: str | None = None
    creado_en: datetime
    actualizado_en: datetime


class ReviewCreateIn(BaseModel):
    revisor_id: UUID | None = None


class ReviewAssignIn(BaseModel):
    revisor_id: UUID


class ReviewPatchIn(BaseModel):
    estado: Literal["aprobada", "rechazada"]
    motivo: str | None = Field(default=None, max_length=1000)


class ReopenIn(BaseModel):
    motivo: str = Field(min_length=3, max_length=1000)
