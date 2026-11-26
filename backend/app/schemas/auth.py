from uuid import UUID

from pydantic import BaseModel, Field


class LoginIn(BaseModel):
    email: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=1, max_length=200)


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "Bearer"
    expires_in: int


class MeOut(BaseModel):
    id: UUID
    nombre: str
    apellidos: str
    email: str
    roles: list[str]
    estado: str


class PasswordChangeIn(BaseModel):
    password_actual: str = Field(min_length=1, max_length=200)
    # shortcut: política = longitud mínima de 12; ampliar cuando negocio la defina.
    password_nueva: str = Field(min_length=12, max_length=200)
