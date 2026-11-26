from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class TransformPlainTextIn(BaseModel):
    documento_id: UUID | None = None
    titulo: str = Field(min_length=1, max_length=255)
    texto: str = Field(min_length=1)
    idioma: str = Field(default="es", max_length=10)


class TransformBuildIn(BaseModel):
    documento_id: UUID
    numero_version: int | None = None
    texto: str = Field(min_length=1)


class DocumentOut(BaseModel):
    id: UUID
    titulo: str
    estado: str
    creado_por: UUID
    creado_en: datetime
    actualizado_en: datetime
    exportado_en: datetime | None = None


class PageOut(BaseModel):
    id: UUID
    documento_id: UUID
    numero_pagina: int
    semaforo: str
    avisos: list[Any] | dict[str, Any] | None = None


class VersionOut(BaseModel):
    id: UUID
    documento_id: UUID
    numero_version: int
    es_actual: bool
    texto_contenido: str | None = None
    metadatos_proceso: dict[str, Any] | None = None
    creado_en: datetime


class BlockOut(BaseModel):
    id: UUID
    version_id: UUID
    pagina: int
    orden: int
    tipo: str
    texto: str
    bbox: dict[str, Any] | None = None
