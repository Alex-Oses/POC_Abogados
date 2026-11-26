from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

Rol = Literal["transcriptor", "revisor", "admin"]
Estado = Literal["activo", "bloqueado", "baja"]


class UserOut(BaseModel):
    id: UUID
    email: str
    nombre: str
    apellidos: str
    roles: list[str]
    estado: str


class UserListOut(BaseModel):
    items: list[UserOut]
    page: int
    limit: int
    total: int


class UserPatchIn(BaseModel):
    roles: list[Rol] | None = None
    estado: Estado | None = None
    motivo_baja: str | None = Field(default=None, max_length=1000)
