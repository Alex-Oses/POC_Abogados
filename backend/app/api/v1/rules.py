from uuid import UUID

from fastapi import APIRouter, Depends, Query
from psycopg import Connection

from app.api.deps import connection, require_role
from app.schemas.common import PaginatedOut
from app.schemas.rules import (
    CategoryIn,
    CategoryOut,
    CategoryPatchIn,
    RuleIn,
    RuleOut,
    RulePatchIn,
)
from app.services import rules as rules_service

router = APIRouter(tags=["reglas y categorías"])


@router.get("/rules", response_model=PaginatedOut[RuleOut])
def list_rules(
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    usuario: dict = Depends(require_role("admin")),
    conexion: Connection = Depends(connection),
):
    return rules_service.listar_reglas(conexion, page, limit)


@router.post("/rules", response_model=RuleOut, status_code=201)
def create_rule(
    body: RuleIn,
    usuario: dict = Depends(require_role("admin")),
    conexion: Connection = Depends(connection),
):
    return rules_service.crear_regla(conexion, usuario, body.model_dump(exclude={"categoria_ids"}))


@router.patch("/rules/{regla_id}", response_model=RuleOut)
def patch_rule(
    regla_id: UUID,
    body: RulePatchIn,
    usuario: dict = Depends(require_role("admin")),
    conexion: Connection = Depends(connection),
):
    return rules_service.actualizar_regla(
        conexion, usuario, regla_id, body.model_dump(exclude={"categoria_ids"})
    )


@router.get("/categories", response_model=PaginatedOut[CategoryOut])
def list_categories(
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    usuario: dict = Depends(require_role("admin")),
    conexion: Connection = Depends(connection),
):
    return rules_service.listar_categorias(conexion, page, limit)


@router.post("/categories", response_model=CategoryOut, status_code=201)
def create_category(
    body: CategoryIn,
    usuario: dict = Depends(require_role("admin")),
    conexion: Connection = Depends(connection),
):
    return rules_service.crear_categoria(conexion, usuario, body.model_dump())


@router.patch("/categories/{categoria_id}", response_model=CategoryOut)
def patch_category(
    categoria_id: UUID,
    body: CategoryPatchIn,
    usuario: dict = Depends(require_role("admin")),
    conexion: Connection = Depends(connection),
):
    return rules_service.actualizar_categoria(conexion, usuario, categoria_id, body.model_dump())
