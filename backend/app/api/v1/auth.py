from fastapi import APIRouter, Depends, Request
from psycopg import Connection

from app.api.deps import connection, current_user
from app.middleware.limit_rate import limitar_login, limpiar_login
from app.schemas.auth import LoginIn, MeOut, PasswordChangeIn, TokenOut
from app.services import auth as service

router = APIRouter(prefix="/user", tags=["identidad"])


@router.post("/login", response_model=TokenOut, dependencies=[Depends(limitar_login)])
def login(datos: LoginIn, request: Request, conexion: Connection = Depends(connection)):
    resultado = service.login(conexion, datos.email, datos.password, request)
    limpiar_login(request)
    return resultado


@router.post("/logout", status_code=204)
def logout(
    request: Request,
    usuario: dict = Depends(current_user),
    conexion: Connection = Depends(connection),
) -> None:
    service.logout(conexion, usuario, request)


@router.get("/me", response_model=MeOut)
def me(usuario: dict = Depends(current_user)):
    return usuario


@router.post("/password/change", status_code=204)
def cambiar_password(
    datos: PasswordChangeIn,
    request: Request,
    usuario: dict = Depends(current_user),
    conexion: Connection = Depends(connection),
) -> None:
    service.cambiar_password(
        conexion, usuario, datos.password_actual, datos.password_nueva, request
    )
