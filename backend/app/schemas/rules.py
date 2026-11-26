from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class RuleIn(BaseModel):
    nombre: str = Field(min_length=1, max_length=150)
    descripcion: str | None = Field(default=None, max_length=1000)
    patron: str | None = Field(default=None, max_length=500)
    activa: bool = True
    categoria_ids: list[UUID] = Field(default_factory=list)


class RulePatchIn(BaseModel):
    nombre: str | None = Field(default=None, min_length=1, max_length=150)
    descripcion: str | None = Field(default=None, max_length=1000)
    patron: str | None = Field(default=None, max_length=500)
    activa: bool | None = None
    categoria_ids: list[UUID] | None = None


class RuleOut(BaseModel):
    id: UUID
    nombre: str
    descripcion: str | None = None
    patron: str | None = None
    activa: bool
    categorias: list[Any] = Field(default_factory=list)


class CategoryIn(BaseModel):
    codigo: str = Field(min_length=1, max_length=80)
    nombre: str = Field(min_length=1, max_length=150)
    descripcion: str | None = Field(default=None, max_length=1000)
    activa: bool = True


class CategoryPatchIn(BaseModel):
    nombre: str | None = Field(default=None, min_length=1, max_length=150)
    descripcion: str | None = Field(default=None, max_length=1000)
    activa: bool | None = None


class CategoryOut(BaseModel):
    id: UUID
    codigo: str
    nombre: str
    descripcion: str | None = None
    activa: bool
