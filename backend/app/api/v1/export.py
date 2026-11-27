"""PDF final (0007, A-16 a A-18): vista previa, export individual, transcripción y ZIP."""

import io
import zipfile
from typing import Literal
from urllib.parse import quote
from uuid import UUID

from fastapi import APIRouter, Depends, Request
from fastapi.responses import Response
from psycopg import Connection
from pydantic import BaseModel, Field

from app.api.deps import connection, require_role
from app.api.v1.documents import IdIn
from app.core.errors import AppError
from app.db.pool import tx
from app.services import documents as service
from app.services import export

router = APIRouter(tags=["documentos"])
TR = require_role("transcriptor", "revisor")


class ZipIn(BaseModel):
    ids: list[UUID] = Field(min_length=1, max_length=100)
    tipo: Literal["anon", "trans"] = "anon"


def _pdf(datos: bytes, nombre: str, inline: bool = False, cabeceras: dict | None = None):
    modo = "inline" if inline else "attachment"
    # ASCII de respaldo + filename* UTF-8: tildes, comillas o saltos de línea no rompen la cabecera.
    ascii_ = "".join(c if 32 <= ord(c) < 127 and c != '"' else "_" for c in nombre)
    return Response(datos, media_type="application/pdf", headers={
        "Content-Disposition": f"{modo}; filename=\"{ascii_}\"; filename*=UTF-8''{quote(nombre)}",
        **(cabeceras or {})})


@router.post("/transform/build")
def build(datos: IdIn, usuario: dict = Depends(TR), conexion: Connection = Depends(connection)):
    doc = service.obtener(conexion, datos.id, usuario)
    return _pdf(export.vista_previa(conexion, doc), "vista_previa.pdf", inline=True)


@router.post("/documents/{documento_id}/export")
def exportar(documento_id: UUID, request: Request, usuario: dict = Depends(TR),
             conexion: Connection = Depends(connection)):
    doc = service.obtener(conexion, documento_id, usuario)
    if not service.es_revisor(usuario) and doc["creado_por"] != usuario["usuario_id"]:
        raise AppError("FORBIDDEN", "Solo el dueño o un revisor exporta", 403)
    pdf, huella, nombre = export.exportar(conexion, documento_id, usuario, request)
    return _pdf(pdf, nombre, cabeceras={"X-Document-Hash": huella})


@router.post("/documents/{documento_id}/export/transcrito")
def exportar_transcrito(documento_id: UUID, request: Request, usuario: dict = Depends(TR),
                        conexion: Connection = Depends(connection)):
    """PDF de la transcripción antes de anonimizar: `<nombre>_trans.pdf`."""
    doc = service.obtener(conexion, documento_id, usuario)
    pdf, nombre = export.transcrito(conexion, doc, usuario, request)
    return _pdf(pdf, nombre)


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
