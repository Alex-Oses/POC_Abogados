import io
import json
import zipfile
from typing import Literal
from urllib.parse import quote
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, Query, Request, UploadFile
from fastapi.responses import Response, StreamingResponse
from psycopg import Connection
from pydantic import BaseModel, Field

from app.api.deps import connection, require_role
from app.core.errors import AppError
from app.db.pool import tx
from app.db.queries import SQL
from app.services import anonymize, audit, cola, export, jg
from app.services import documents as service

router = APIRouter(tags=["documentos"])
T = require_role("transcriptor")
TR = require_role("transcriptor", "revisor")
R = require_role("revisor")
Modo = Literal["censurar", "borrar", "tachar", "etiqueta", "seudonimo", "iniciales"]


class IdIn(BaseModel):
    id: UUID


class ZipIn(BaseModel):
    ids: list[UUID] = Field(min_length=1, max_length=100)
    tipo: Literal["anon", "trans"] = "anon"


class PaginaIn(BaseModel):
    texto: str | None = Field(default=None, max_length=200_000)
    validada: bool | None = None
    html: str | None = Field(default=None, max_length=200_000)


class LocalizarIn(BaseModel):
    q: list[str] = Field(max_length=100)


class AnonimizarIn(BaseModel):
    regla_id: UUID | None = None
    modo: Modo = "censurar"  # por defecto de V15 (rgpd-considerations.md)


class AnotacionIn(BaseModel):
    accion_aplicada: Literal["censurar", "etiqueta", "iniciales", "pseudonimizado", "eliminado",
                             "mantenido", "tachado"] | None = None
    texto_sustitucion: str | None = Field(default=None, max_length=500)
    decision_revisor: Literal["confirmado", "modificado", "falso_positivo", "falso_negativo"]
    observaciones_revisor: str | None = Field(default=None, max_length=2000)


class AnotacionNuevaIn(BaseModel):
    bloque_id: UUID
    categoria_id: UUID
    inicio_offset: int = Field(ge=0)
    fin_offset: int = Field(gt=0)
    accion_aplicada: Literal["censurar", "etiqueta", "iniciales", "pseudonimizado", "eliminado",
                             "tachado"] | None = None
    texto_sustitucion: str | None = Field(default=None, max_length=500)


def _pdf(datos: bytes, nombre: str, inline: bool = False, cabeceras: dict | None = None):
    modo = "inline" if inline else "attachment"
    # ASCII de respaldo + filename* UTF-8: tildes, comillas o saltos de línea no rompen la cabecera.
    ascii_ = "".join(c if 32 <= ord(c) < 127 and c != '"' else "_" for c in nombre)
    return Response(datos, media_type="application/pdf", headers={
        "Content-Disposition": f"{modo}; filename=\"{ascii_}\"; filename*=UTF-8''{quote(nombre)}",
        **(cabeceras or {})})


# --- Subida y transformaciones --------------------------------------------------------------

@router.post("/transform/document", status_code=202)
async def subir(
    request: Request,
    file: UploadFile = File(...),
    modo: Literal["simple", "doble"] = Form("doble"),
    usuario: dict = Depends(T),
):
    """Sube y deja en la cola de OCR (0017). Con `Accept: application/x-ndjson` sigue el
    progreso leyendo la BD; cerrar el flujo no detiene el trabajo."""
    datos = await file.read()
    subido = service.registrar_subida(file.filename or "documento", datos, modo == "doble",
                                      usuario, request)
    cola.despertar.set()
    if "application/x-ndjson" in request.headers.get("accept", ""):
        return _ndjson(service.seguir_ocr(subido["id"], usuario))
    return subido


def _ndjson(eventos):
    lineas = (json.dumps(e, ensure_ascii=False, default=str) + "\n" for e in eventos)
    return StreamingResponse(lineas, media_type="application/x-ndjson")


@router.post("/transform/plain-text")
def plain_text(datos: IdIn, usuario: dict = Depends(TR), conexion: Connection = Depends(connection)):
    doc = service.obtener(conexion, datos.id, usuario)
    if not doc["v_id"]:
        raise AppError("SIN_TEXTO", "El documento no tiene versión", 422)
    version = doc["v_id"]
    if doc["v_tipo"] == "final_aprobado":
        version = doc["v_meta"]["version_revisada_id"]
    return {"result": "\n\n".join(anonymize.texto_plano(conexion, version, version))}


@router.post("/transform/build")
def build(datos: IdIn, usuario: dict = Depends(TR), conexion: Connection = Depends(connection)):
    doc = service.obtener(conexion, datos.id, usuario)
    return _pdf(export.vista_previa(conexion, doc), "vista_previa.pdf", inline=True)


# --- Documentos -----------------------------------------------------------------------------

@router.get("/documents")
def listar(
    estado: str | None = None,
    q: str | None = Query(default=None, max_length=200),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    usuario: dict = Depends(TR),
    conexion: Connection = Depends(connection),
):
    filas = conexion.execute(SQL["docs_listar"], {
        "estado": estado, "q": (q or "").strip() or None,
        "solo_de": None if service.es_revisor(usuario) else usuario["usuario_id"],
        "limit": limit, "offset": (page - 1) * limit}).fetchall()
    total = filas[0]["total"] if filas else 0
    for fila in filas:
        fila.pop("total")
    return {"items": filas, "page": page, "limit": limit, "total": total}


@router.get("/documents/{documento_id}")
def detalle(documento_id: UUID, usuario: dict = Depends(TR), conexion: Connection = Depends(connection)):
    return service.detalle(service.obtener(conexion, documento_id, usuario))


@router.get("/documents/{documento_id}/progress")
def progreso(documento_id: UUID, usuario: dict = Depends(TR),
             conexion: Connection = Depends(connection)):
    service.obtener(conexion, documento_id, usuario)
    return service.progreso(conexion, documento_id)


@router.get("/documents/{documento_id}/stream")
def seguir(documento_id: UUID, usuario: dict = Depends(TR),
           conexion: Connection = Depends(connection)):
    """NDJSON de progreso de un documento ya subido (p. ej. tras recargar la página)."""
    service.obtener(conexion, documento_id, usuario)
    return _ndjson(service.seguir_ocr(documento_id, usuario))


@router.post("/documents/{documento_id}/cancel")
def cancelar(documento_id: UUID, request: Request, usuario: dict = Depends(TR),
             conexion: Connection = Depends(connection)):
    return service.cancelar(conexion, service.obtener(conexion, documento_id, usuario),
                            usuario, request)


@router.post("/documents/{documento_id}/retry")
def reintentar(documento_id: UUID, request: Request, usuario: dict = Depends(TR),
               conexion: Connection = Depends(connection)):
    """Vuelve a poner en cola un OCR fallido o cancelado (0017)."""
    estado = service.reintentar(conexion, service.obtener(conexion, documento_id, usuario),
                                usuario, request)
    cola.despertar.set()
    return estado


@router.delete("/documents/{documento_id}", status_code=204)
def eliminar(documento_id: UUID, request: Request,
             usuario: dict = Depends(require_role("transcriptor", "admin")),
             conexion: Connection = Depends(connection)) -> None:
    doc = service.obtener(conexion, documento_id, usuario)
    if "admin" not in usuario["roles"] and doc["creado_por"] != usuario["usuario_id"]:
        raise AppError("FORBIDDEN", "Solo el dueño o un admin borra", 403)
    conexion.execute(SQL["doc_eliminar"], {"id": documento_id})
    audit.registrar(conexion, "DOCUMENTO_ELIMINADO", request=request,
                    usuario_id=usuario["usuario_id"], entidad_tipo="documento",
                    entidad_id=documento_id, detalle={"estado_anterior": doc["estado"]})


@router.get("/documents/{documento_id}/original")
def original(documento_id: UUID, request: Request, usuario: dict = Depends(TR),
             conexion: Connection = Depends(connection)):
    doc = service.obtener(conexion, documento_id, usuario)
    datos = service._original(doc)
    audit.registrar(conexion, "ORIGINAL_CONSULTADO", request=request,
                    usuario_id=usuario["usuario_id"], entidad_tipo="documento",
                    entidad_id=documento_id, detalle={})
    return Response(datos, media_type=doc["mime_type"],
                    headers={"Content-Disposition": "inline", "Cache-Control": "no-store"})


# --- Páginas --------------------------------------------------------------------------------

@router.get("/documents/{documento_id}/pages")
def paginas(documento_id: UUID, usuario: dict = Depends(TR), conexion: Connection = Depends(connection)):
    doc = service.obtener(conexion, documento_id, usuario)
    return {"items": service.paginas(conexion, doc)}


@router.patch("/documents/{documento_id}/pages/{numero}", status_code=204)
def editar_pagina(documento_id: UUID, numero: int, datos: PaginaIn, request: Request,
                  usuario: dict = Depends(TR), conexion: Connection = Depends(connection)) -> None:
    doc = service.obtener(conexion, documento_id, usuario)
    service.editar_pagina(conexion, doc, numero, datos.texto, datos.validada, usuario, request,
                          datos.html)


@router.post("/documents/{documento_id}/pages/{numero}/ocr")
async def releer_pagina(documento_id: UUID, numero: int, request: Request,
                        file: UploadFile | None = File(None),
                        modo: Literal["simple", "doble"] = Form("doble"),
                        usuario: dict = Depends(TR), conexion: Connection = Depends(connection)):
    fichero = await file.read() if file else None
    doc = service.obtener(conexion, documento_id, usuario)
    return service.releer_pagina(conexion, doc, numero, fichero or None, modo == "doble",
                                 usuario, request)


@router.get("/documents/{documento_id}/pages/{numero}/image")
def imagen_pagina(documento_id: UUID, numero: int, request: Request, usuario: dict = Depends(TR),
                  conexion: Connection = Depends(connection)):
    doc = service.obtener(conexion, documento_id, usuario)
    png = service.imagen_pagina(doc, numero)
    audit.registrar(conexion, "ORIGINAL_CONSULTADO", request=request,
                    usuario_id=usuario["usuario_id"], entidad_tipo="documento",
                    entidad_id=documento_id, detalle={"pagina": numero})
    return Response(png, media_type="image/png", headers={"Cache-Control": "private, no-store"})


@router.get("/documents/{documento_id}/pages/{numero}/locate")
def localizar(documento_id: UUID, numero: int, q: str = Query(..., max_length=200),
              usuario: dict = Depends(TR), conexion: Connection = Depends(connection)):
    """Caja (píxeles de la imagen a 150 dpi) de un texto en la página, o null."""
    doc = service.obtener(conexion, documento_id, usuario)
    return {"bbox": service.localizar(doc, numero, [q])[0]}


@router.post("/documents/{documento_id}/pages/{numero}/locate")
def localizar_varios(documento_id: UUID, numero: int, datos: LocalizarIn,
                     usuario: dict = Depends(TR), conexion: Connection = Depends(connection)):
    """Lote de `locate`: una caja (o null) por texto, en el mismo orden."""
    doc = service.obtener(conexion, documento_id, usuario)
    return {"bboxes": service.localizar(doc, numero, [q[:200] for q in datos.q])}


# --- Versiones y bloques --------------------------------------------------------------------

@router.get("/documents/{documento_id}/versions")
def versiones(documento_id: UUID, usuario: dict = Depends(R), conexion: Connection = Depends(connection)):
    service.obtener(conexion, documento_id, usuario)
    return {"items": conexion.execute(SQL["versiones_listar"],
                                      {"documento_id": documento_id}).fetchall()}


def _version(conexion, documento_id, numero, usuario):
    service.obtener(conexion, documento_id, usuario)
    fila = conexion.execute(SQL["version_por_numero"],
                            {"documento_id": documento_id, "numero": numero}).fetchone()
    if not fila:
        raise AppError("VERSION_NO_ENCONTRADA", "La versión no existe", 404)
    return fila


@router.get("/documents/{documento_id}/versions/{numero}")
def version(documento_id: UUID, numero: int, usuario: dict = Depends(R),
            conexion: Connection = Depends(connection)):
    return _version(conexion, documento_id, numero, usuario)


@router.get("/documents/{documento_id}/versions/{numero}/blocks")
def bloques(documento_id: UUID, numero: int, page: int = Query(1, ge=1),
            limit: int = Query(100, ge=1, le=500), pagina: int | None = None,
            usuario: dict = Depends(R), conexion: Connection = Depends(connection)):
    fila = _version(conexion, documento_id, numero, usuario)
    version_id = fila["metadatos_proceso"].get("version_revisada_id", fila["id"])
    filas = conexion.execute(SQL["bloques_version"], {
        "version_id": version_id, "pagina": pagina, "limit": limit,
        "offset": (page - 1) * limit}).fetchall()
    total = filas[0]["total"] if filas else 0
    items = [{
        "id": b["id"], "pagina_numero": b["pagina_numero"], "orden_lectura": b["orden_lectura"],
        "etiqueta": b["etiqueta"], "confianza": b["confianza"], "forma": b["forma"],
        "bbox": {"x": b["bbox_x"], "y": b["bbox_y"], "ancho": b["bbox_ancho"], "alto": b["bbox_alto"]},
        "puntos": b["puntos"], "pagina": {"ancho": b["pagina_ancho"], "alto": b["pagina_alto"]},
        "contenido": b["contenido"], "calidad_semaforo": b["calidad_semaforo"]} for b in filas]
    return {"items": items, "page": page, "limit": limit, "total": total}


# --- Anonimización y anotaciones ------------------------------------------------------------

@router.post("/documents/{documento_id}/anonymize", status_code=201)
def anonimizar(documento_id: UUID, datos: AnonimizarIn, request: Request,
               usuario: dict = Depends(TR), conexion: Connection = Depends(connection)):
    doc = service.obtener(conexion, documento_id, usuario)
    return anonymize.anonimizar(conexion, doc, datos.regla_id, datos.modo, usuario, request)


@router.get("/documents/{documento_id}/annotations")
def anotaciones(documento_id: UUID, version: UUID | None = None, categoria: UUID | None = None,
                pendientes: bool = False, usuario: dict = Depends(R),
                conexion: Connection = Depends(connection)):
    service.obtener(conexion, documento_id, usuario)
    return {"items": conexion.execute(SQL["anotaciones_listar"], {
        "documento_id": documento_id, "version_id": version, "categoria_id": categoria,
        "pendientes": pendientes}).fetchall()}


@router.post("/documents/{documento_id}/annotations", status_code=201)
def anotacion_nueva(documento_id: UUID, datos: AnotacionNuevaIn, request: Request,
                    usuario: dict = Depends(R), conexion: Connection = Depends(connection)):
    doc = service.obtener(conexion, documento_id, usuario)
    return anonymize.crear_manual(conexion, doc, datos.model_dump(), usuario, request)


@router.patch("/annotations/{anotacion_id}")
def decidir(anotacion_id: UUID, datos: AnotacionIn, request: Request, usuario: dict = Depends(R),
            conexion: Connection = Depends(connection)):
    return anonymize.decidir(conexion, anotacion_id, datos.model_dump(exclude_unset=True),
                             usuario, request)


# --- Justicia gratuita (fuera del contrato) -------------------------------------------------

@router.post("/documents/{documento_id}/justicia-gratuita")
def comprobar_jg(documento_id: UUID, request: Request, usuario: dict = Depends(TR),
                 conexion: Connection = Depends(connection)):
    return jg.comprobar(conexion, service.obtener(conexion, documento_id, usuario), usuario, request)


@router.post("/documents/{documento_id}/justicia-gratuita/send")
def enviar_jg(documento_id: UUID, request: Request, usuario: dict = Depends(TR),
              conexion: Connection = Depends(connection)):
    return jg.enviar(conexion, service.obtener(conexion, documento_id, usuario), usuario, request)


# --- Export ---------------------------------------------------------------------------------

@router.post("/documents/{documento_id}/export")
def exportar(documento_id: UUID, request: Request, usuario: dict = Depends(TR),
             conexion: Connection = Depends(connection)):
    doc = service.obtener(conexion, documento_id, usuario)
    if not service.es_revisor(usuario) and doc["creado_por"] != usuario["usuario_id"]:
        raise AppError("FORBIDDEN", "Solo el dueño o un revisor exporta", 403)
    pdf, huella, nombre = export.exportar(conexion, documento_id, usuario, request)
    return _pdf(pdf, nombre, cabeceras={"X-Document-Hash": huella})


@router.post("/documents/export/zip")
def exportar_zip(datos: ZipIn, request: Request, usuario: dict = Depends(TR)):
    """Varios PDF en un ZIP: `anon` solo de documentos aprobados o exportados; `trans` de los
    que tienen la transcripción terminada. Los que no cumplen se saltan y se cuentan en
    `X-Omitidos`. Cada documento se exporta y confirma en su propia transacción (A-16/A-18):
    el ZIP no deja bloqueado ni a medias el resto."""
    buffer, nombres, omitidos = io.BytesIO(), set(), 0
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for documento_id in dict.fromkeys(datos.ids):
            try:
                with tx() as conexion:
                    doc = service.obtener(conexion, documento_id, usuario)
                    if datos.tipo == "anon":
                        pdf, _, nombre = export.exportar(conexion, documento_id, usuario, request)
                    else:
                        pdf, nombre = export.transcrito(conexion, doc, usuario, request)
            except AppError:
                omitidos += 1
                continue
            base, i = nombre, 2
            while nombre in nombres:  # dos documentos con el mismo nombre no se pisan
                nombre, i = base.replace(".pdf", f" ({i}).pdf"), i + 1
            nombres.add(nombre)
            zf.writestr(nombre, pdf)
    if not nombres:
        raise AppError("SIN_DOCUMENTOS", "Ninguno de los documentos se puede exportar así", 409)
    return Response(buffer.getvalue(), media_type="application/zip", headers={
        "Content-Disposition": f'attachment; filename="documentos_{datos.tipo}.zip"',
        "X-Omitidos": str(omitidos)})


@router.post("/documents/{documento_id}/export/transcrito")
def exportar_transcrito(documento_id: UUID, request: Request, usuario: dict = Depends(TR),
                        conexion: Connection = Depends(connection)):
    """PDF de la transcripción antes de anonimizar: `<nombre>_trans.pdf`."""
    doc = service.obtener(conexion, documento_id, usuario)
    pdf, nombre = export.transcrito(conexion, doc, usuario, request)
    return _pdf(pdf, nombre)
