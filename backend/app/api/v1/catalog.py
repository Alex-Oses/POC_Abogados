"""Catálogo (reglas y categorías), configuración, auditoría e informes."""

import json
import re
from datetime import datetime
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from psycopg import Connection
from pydantic import BaseModel, Field

from app.api.deps import connection, require_role
from app.core.errors import AppError
from app.db.queries import SQL
from app.services import audit

router = APIRouter(tags=["catálogo, auditoría e informes"])
# Lectura del catálogo abierta a todos los roles: el panel de anonimización la necesita.
TODOS = require_role("transcriptor", "revisor", "admin")
ADMIN = require_role("admin")

NIVEL = Literal["alto", "medio", "bajo"]


class CategoriaIn(BaseModel):
    codigo: str = Field(min_length=1, max_length=50, pattern=r"^[a-z0-9_]+$")
    nombre: str = Field(min_length=1, max_length=150)
    descripcion: str | None = Field(default=None, max_length=2000)
    regex_patron: str | None = Field(default=None, max_length=500)
    prioridad: int = Field(default=100, ge=0, le=1000)
    nivel_riesgo: NIVEL
    rgpd_especial: bool = False


class CategoriaPatchIn(BaseModel):
    nombre: str | None = Field(default=None, min_length=1, max_length=150)
    descripcion: str | None = Field(default=None, max_length=2000)
    regex_patron: str | None = Field(default=None, max_length=500)
    prioridad: int | None = Field(default=None, ge=0, le=1000)
    nivel_riesgo: NIVEL | None = None
    rgpd_especial: bool | None = None
    activa: bool | None = None


class ReglaCategoriaIn(BaseModel):
    categoria_id: UUID
    configuracion: dict = Field(default_factory=dict)


class ReglaIn(BaseModel):
    codigo: str = Field(min_length=1, max_length=50, pattern=r"^[a-z0-9_]+$")
    nombre: str = Field(min_length=1, max_length=200)
    descripcion: str | None = Field(default=None, max_length=2000)
    configuracion: dict = Field(default_factory=dict)
    categorias: list[ReglaCategoriaIn] = Field(default_factory=list, max_length=200)


class ReglaPatchIn(BaseModel):
    nombre: str | None = Field(default=None, min_length=1, max_length=200)
    descripcion: str | None = Field(default=None, max_length=2000)
    configuracion: dict | None = None
    activa: bool | None = None
    categorias: list[ReglaCategoriaIn] | None = None


class ConfigIn(BaseModel):
    valor: dict
    descripcion: str | None = Field(default=None, max_length=2000)


def _regex(patron: str | None) -> None:
    """`POST /categories`: la expresión tiene que compilar (contrato §7, 400)."""
    if patron:
        try:
            re.compile(patron)
        except re.error as error:
            raise AppError("REGEX_INVALIDA", f"La expresión no compila: {error}", 400) from error


def _poner_categorias(conexion: Connection, regla_id, categorias: list[ReglaCategoriaIn]) -> None:
    conexion.execute(SQL["regla_categorias_borrar"], {"regla_id": regla_id})
    for categoria in categorias:
        if not conexion.execute(SQL["categoria_por_id"], {"id": categoria.categoria_id}).fetchone():
            raise AppError("CATEGORIA_NO_ENCONTRADA", "La categoría no existe", 404)
        conexion.execute(SQL["regla_categoria_insertar"], {
            "regla_id": regla_id, "categoria_id": categoria.categoria_id,
            "configuracion": json.dumps(categoria.configuracion)})


@router.get("/categories")
def categorias(activa: bool | None = None, _u: dict = Depends(TODOS),
               conexion: Connection = Depends(connection)):
    return {"items": conexion.execute(SQL["categorias_listar"], {"activa": activa}).fetchall()}


@router.post("/categories", status_code=201)
def crear_categoria(datos: CategoriaIn, request: Request, usuario: dict = Depends(ADMIN),
                    conexion: Connection = Depends(connection)):
    _regex(datos.regex_patron)
    if conexion.execute(SQL["categoria_por_codigo"], {"codigo": datos.codigo}).fetchone():
        raise AppError("CATEGORIA_DUPLICADA", "Ya existe una categoría con ese código", 409)
    fila = conexion.execute(SQL["categoria_insertar"], {
        "codigo": datos.codigo, "nombre": datos.nombre, "descripcion": datos.descripcion,
        "regex_patron": datos.regex_patron, "prioridad": datos.prioridad,
        "nivel_riesgo": datos.nivel_riesgo, "rgpd_especial": datos.rgpd_especial}).fetchone()
    audit.registrar(conexion, "CATEGORIA_CREADA", request=request, usuario_id=usuario["usuario_id"],
                    entidad_tipo="categoria", entidad_id=fila["id"],
                    detalle={"codigo": datos.codigo})
    return fila


@router.patch("/categories/{categoria_id}")
def editar_categoria(categoria_id: UUID, datos: CategoriaPatchIn, request: Request,
                     usuario: dict = Depends(ADMIN), conexion: Connection = Depends(connection)):
    _regex(datos.regex_patron)
    cambios = datos.model_dump(exclude_unset=True)
    if not cambios:
        raise AppError("SIN_CAMBIOS", "No hay nada que cambiar", 422)
    params = {campo: None for campo in ("nombre", "descripcion", "regex_patron", "prioridad",
                                        "nivel_riesgo", "rgpd_especial", "activa")}
    params |= cambios | {"id": categoria_id}
    fila = conexion.execute(SQL["categoria_actualizar"], params).fetchone()
    if not fila:
        raise AppError("CATEGORIA_NO_ENCONTRADA", "La categoría no existe", 404)
    audit.registrar(conexion, "CATEGORIA_EDITADA", request=request, usuario_id=usuario["usuario_id"],
                    entidad_tipo="categoria", entidad_id=categoria_id,
                    detalle={"campos": sorted(cambios)})
    return fila


@router.get("/rules")
def reglas(activa: bool | None = None, _u: dict = Depends(TODOS),
           conexion: Connection = Depends(connection)):
    return {"items": conexion.execute(SQL["reglas_listar"], {"activa": activa}).fetchall()}


@router.post("/rules", status_code=201)
def crear_regla(datos: ReglaIn, request: Request, usuario: dict = Depends(ADMIN),
                conexion: Connection = Depends(connection)):
    previa = conexion.execute(SQL["regla_por_codigo"], {"codigo": datos.codigo}).fetchone()
    if previa and previa["activa"]:
        raise AppError("REGLA_ACTIVA",
                       "Ya hay una regla activa con ese código; edítala o desactívala antes", 409)
    fila = conexion.execute(SQL["regla_insertar"], {
        "codigo": datos.codigo, "nombre": datos.nombre, "descripcion": datos.descripcion,
        "configuracion": json.dumps(datos.configuracion),
        "creado_por": usuario["usuario_id"]}).fetchone()
    _poner_categorias(conexion, fila["id"], datos.categorias)
    audit.registrar(conexion, "REGLA_CREADA", request=request, usuario_id=usuario["usuario_id"],
                    entidad_tipo="regla", entidad_id=fila["id"],
                    detalle={"codigo": datos.codigo, "version": fila["version"]})
    return fila


@router.patch("/rules/{regla_id}")
def editar_regla(regla_id: UUID, datos: ReglaPatchIn, request: Request,
                 usuario: dict = Depends(ADMIN), conexion: Connection = Depends(connection)):
    regla = conexion.execute(SQL["regla_por_id_completa"], {"id": regla_id}).fetchone()
    if not regla:
        raise AppError("REGLA_NO_ENCONTRADA", "La regla no existe", 404)
    if datos.activa and not regla["activa"]:
        otra = conexion.execute(SQL["regla_activa_codigo"],
                                {"codigo": regla["codigo"], "id": regla_id}).fetchone()
        if otra:
            raise AppError("REGLA_ACTIVA", "Ya hay otra regla activa con ese código", 409)
    fila = conexion.execute(SQL["regla_actualizar"], {
        "id": regla_id, "nombre": datos.nombre, "descripcion": datos.descripcion,
        "configuracion": None if datos.configuracion is None else json.dumps(datos.configuracion),
        "activa": datos.activa}).fetchone()
    if datos.categorias is not None:
        _poner_categorias(conexion, regla_id, datos.categorias)
    audit.registrar(conexion, "REGLA_EDITADA", request=request, usuario_id=usuario["usuario_id"],
                    entidad_tipo="regla", entidad_id=regla_id,
                    detalle={"campos": sorted(datos.model_dump(exclude_unset=True))})
    return fila


@router.get("/config")
def configuracion(_u: dict = Depends(ADMIN), conexion: Connection = Depends(connection)):
    return {"items": conexion.execute(SQL["config_listar"]).fetchall()}


@router.put("/config/{clave}")
def configurar(clave: str, datos: ConfigIn, request: Request, usuario: dict = Depends(ADMIN),
               conexion: Connection = Depends(connection)):
    fila = conexion.execute(SQL["config_upsert"], {
        "clave": clave, "valor": json.dumps(datos.valor), "descripcion": datos.descripcion,
        "usuario_id": usuario["usuario_id"]}).fetchone()
    audit.registrar(conexion, "CONFIG_ACTUALIZADA", request=request,
                    usuario_id=usuario["usuario_id"], entidad_tipo="configuracion",
                    detalle={"clave": clave})
    return fila


@router.get("/audit")
def auditoria(entidad_tipo: str | None = None, entidad_id: UUID | None = None,
              usuario_id: UUID | None = None, desde: datetime | None = None,
              hasta: datetime | None = None, page: int = Query(1, ge=1),
              limit: int = Query(50, ge=1, le=200),
              _u: dict = Depends(require_role("revisor", "admin")),
              conexion: Connection = Depends(connection)):
    filas = conexion.execute(SQL["auditoria_listar"], {
        "entidad_tipo": entidad_tipo, "entidad_id": entidad_id, "usuario_id": usuario_id,
        "desde": desde, "hasta": hasta, "limit": limit, "offset": (page - 1) * limit}).fetchall()
    total = filas[0]["total"] if filas else 0
    for fila in filas:
        fila.pop("total")
    return {"items": filas, "page": page, "limit": limit, "total": total}


@router.get("/reports/summary")
def informe(_u: dict = Depends(require_role("revisor", "admin")),
            conexion: Connection = Depends(connection)):
    return conexion.execute(SQL["informe_resumen"]).fetchone()
