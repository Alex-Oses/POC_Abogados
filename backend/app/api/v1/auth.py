from fastapi import APIRouter, Depends, Request, Response
from psycopg import Connection

from app.api.deps import connection, current_user
from app.core.config import settings
from app.middleware.auth import COOKIE
from app.middleware.limit_rate import limitar_login, limpiar_login
from app.schemas.auth import LoginIn, MeOut, PasswordChangeIn, TokenOut
from app.services import auth as service

router = APIRouter(prefix="/user", tags=["identidad"])


@router.post("/login", response_model=TokenOut, dependencies=[Depends(limitar_login)])
def login(datos: LoginIn, request: Request, response: Response,
          conexion: Connection = Depends(connection)):
    resultado = service.login(conexion, datos.email, datos.password, request)
    limpiar_login(request)
    # Además del Bearer: cookie HttpOnly y SameSite=Strict para <img> y el visor del original.
    response.set_cookie(COOKIE, resultado["access_token"], httponly=True, samesite="strict",
                        secure=settings.entorno != "desarrollo",
                        max_age=settings.session_horas_max * 3600, path="/")
    return resultado


@router.post("/logout", status_code=204)
def logout(
    request: Request,
    response: Response,
    usuario: dict = Depends(current_user),
    conexion: Connection = Depends(connection),
) -> None:
    service.logout(conexion, usuario, request)
    response.delete_cookie(COOKIE, path="/")


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
