"""Flujo completo con BD y OCR simulado: subida → páginas → JG → anonimizar → revisar → exportar.

Datos ficticios (AGENTS.md): el DNI 12345678Z tiene letra válida pero no es de nadie.
"""

import hashlib
import io
import json
import os
import zipfile
from uuid import uuid4

import psycopg
import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.core.security import hash_password
from app.main import app

pytestmark = pytest.mark.skipif(not os.getenv("DATABASE_TEST_URL"), reason="sin DATABASE_TEST_URL")
CLAVE = "una-clave-larga-123"
PAGINAS = [
    "DOCUMENTO NACIONAL DE IDENTIDAD\nDon Juan Pérez García\nDNI 12345678Z",
    "Volante de empadronamiento\nPadrón municipal de Reus\nConviven 3 personas en calle Mayor 5, Reus",
    "Nómina enero 2026\nRecibo de salarios de Juan Pérez García\nLíquido a percibir 1.200,00",
    "Declaración IRPF modelo 100\nBase imponible general 15.300,50",
    ("Juzgado de Primera Instancia 2 de Reus\nProcedimiento ordinario nº 123/2026\n"
    "Cédula de notificación a Juan Pérez García, domiciliado en calle Mayor 5, Reus"),
]


def _texto_pdf(datos: bytes) -> str:
    import pypdfium2 as pdfium

    doc = pdfium.PdfDocument(datos)
    partes = []
    try:
        for indice in range(len(doc)):
            textpage = doc[indice].get_textpage()
            partes.append(textpage.get_text_range())
            textpage.close()
    finally:
        doc.close()
    return "\n".join(partes)


def _pdf() -> bytes:
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas

    buffer = io.BytesIO()
    lienzo = canvas.Canvas(buffer, pagesize=A4)
    lienzo.setTitle(f"prueba-{uuid4().hex}")  # hash distinto en cada ejecución
    alto = A4[1]
    for texto in PAGINAS:
        y = alto - 72
        for linea in texto.split("\n"):
            lienzo.drawString(72, y, linea)
            y -= 16
        lienzo.showPage()
    # Página casi blanca: el semáforo la marca ilegible y no se transcribe.
    lienzo.setFillGray(0.93)
    lienzo.drawString(72, alto - 72, "Certificado de bienes")
    lienzo.drawString(72, alto - 88, "Registro de la propiedad")
    lienzo.showPage()
    lienzo.save()
    return buffer.getvalue()


@pytest.fixture()
def usuario():
    email = f"flujo-{uuid4().hex[:10]}@icat.local"
    with psycopg.connect(settings.database_url) as c:
        uid = c.execute("INSERT INTO usuarios (email, nombre, password_hash) VALUES (%s, 'Flujo', %s) "
                        "RETURNING id", (email, hash_password(CLAVE))).fetchone()[0]
        for rol in ("transcriptor", "revisor"):
            c.execute("INSERT INTO usuarios_roles VALUES (%s, %s)", (uid, rol))
    yield email


def test_flujo_completo(usuario):
    with TestClient(app) as cliente:
        token = cliente.post("/api/v1/user/login",
                             json={"email": usuario, "password": CLAVE}).json()["access_token"]
        h = {"Authorization": f"Bearer {token}"}

        # Subida con progreso NDJSON
        r = cliente.post("/api/v1/transform/document", headers={**h, "Accept": "application/x-ndjson"},
                         files={"file": ("expediente.pdf", _pdf(), "application/pdf")},
                         data={"modo": "doble"})
        eventos = [json.loads(linea) for linea in r.text.splitlines()]
        assert [e["type"] for e in eventos] == ["start"] + ["page"] * 6 + ["done"], eventos[-1]
        doc_id = eventos[-1]["id"]
        assert eventos[6]["estado"] == "ilegible" and eventos[6]["texto"] == ""

        paginas = cliente.get(f"/api/v1/documents/{doc_id}/pages", headers=h).json()["items"]
        assert [p["estado"] for p in paginas][-1] == "ilegible"
        assert cliente.get(f"/api/v1/documents/{doc_id}/pages/1/image").status_code == 200  # cookie

        # Edición y validación de página
        texto = paginas[0]["texto"] + "\nSexo: M"
        assert cliente.patch(f"/api/v1/documents/{doc_id}/pages/1", headers=h,
                             json={"texto": texto, "validada": True}).status_code == 204
        p1 = cliente.get(f"/api/v1/documents/{doc_id}/pages", headers=h).json()["items"][0]
        assert p1["texto"] == texto and p1["validada"] and p1["html"] is None

        # Texto con formato: se sanea, el texto plano se deriva y solo-texto quita el formato
        url = f"/api/v1/documents/{doc_id}/pages/2"
        assert cliente.patch(url, headers=h, json={
            "html": '<p><b>Volante</b><img src=x onerror="alert(1)"></p><div>Reus</div>'}).status_code == 204
        p2 = cliente.get(f"/api/v1/documents/{doc_id}/pages", headers=h).json()["items"][1]
        assert p2["html"] == "<p><b>Volante</b></p><div>Reus</div>" and p2["texto"] == "Volante\nReus"
        sin = cliente.post("/api/v1/transform/build",
                           headers=h, json={"id": doc_id})
        assert sin.status_code == 200 and sin.content.startswith(b"%PDF")
        assert cliente.patch(url, headers=h, json={"texto": PAGINAS[1]}).status_code == 204
        p2 = cliente.get(f"/api/v1/documents/{doc_id}/pages", headers=h).json()["items"][1]
        assert p2["html"] is None and p2["texto"] == PAGINAS[1]

        # Recuadros en lote (capa de texto del PDF)
        cajas = cliente.post(f"{url}/locate", headers=h, json={"q": ["Reus", "zzzz"]}).json()["bboxes"]
        assert cajas[0] and cajas[0]["ancho"] > 0 and cajas[1] is None

        # Justicia gratuita (orientativa)
        jg = cliente.post(f"/api/v1/documents/{doc_id}/justicia-gratuita", headers=h).json()
        estados = {d["tipo"]: d["estado"] for d in jg["documentos"]}
        assert estados["dni"] == "presente" and estados["irpf"] == "presente"
        assert estados["nomina"] == "incompleto" and estados["certificado_bienes"] == "ilegible"
        assert jg["datos"]["dni_valido"] is True and jg["datos"]["ingresos_anuales"] == 15300.5
        assert jg["datos"]["miembros_unidad_familiar"] == 3
        assert "123/2026" in jg["datos"]["procedimiento"]
        assert cliente.post(f"/api/v1/documents/{doc_id}/justicia-gratuita/send", headers=h).status_code == 200

        # Búsqueda de texto completo
        lista = cliente.get("/api/v1/documents", headers=h, params={"q": "empadronamiento"}).json()
        assert any(d["id"] == doc_id for d in lista["items"])
        assert next(d for d in lista["items"] if d["id"] == doc_id)["subido_por"] == "Flujo"
        assert cliente.get(f"/api/v1/documents/{doc_id}", headers=h).json()["subido_por"] == "Flujo"

        # PDF de la transcripción, antes de anonimizar
        tr = cliente.post(f"/api/v1/documents/{doc_id}/export/transcrito", headers=h)
        assert tr.status_code == 200 and tr.content.startswith(b"%PDF")
        assert "filename*=UTF-8''expediente_trans.pdf" in tr.headers["content-disposition"]
        assert "12345678Z" in _texto_pdf(tr.content)

        # Anonimización con Presidio
        an = cliente.post(f"/api/v1/documents/{doc_id}/anonymize", headers=h, json={"modo": "seudonimo"})
        assert an.status_code == 201, an.text
        assert an.json()["anotaciones"] > 0
        notas = cliente.get(f"/api/v1/documents/{doc_id}/annotations", headers=h).json()["items"]
        assert any(n["categoria"] == "DNI_NIE" and n["texto_original"] == "12345678Z" for n in notas)
        # Tras anonimizar sigue saliendo la transcripción original, no la anonimizada
        tr = cliente.post(f"/api/v1/documents/{doc_id}/export/transcrito", headers=h)
        assert "12345678Z" in _texto_pdf(tr.content)

        # Revisión
        rev = cliente.post(f"/api/v1/documents/{doc_id}/reviews", headers=h).json()
        tomada = cliente.post(f"/api/v1/reviews/{rev['id']}/claim", headers=h).json()
        assert tomada["estado"] == "en_proceso"
        pronto = cliente.patch(f"/api/v1/reviews/{rev['id']}", headers={**h, "If-Match": tomada["actualizado_en"]},
                               json={"estado": "aprobado"})
        assert pronto.status_code == 422  # A-09
        for n in notas:
            assert cliente.patch(f"/api/v1/annotations/{n['id']}", headers=h,
                                 json={"decision_revisor": "confirmado"}).status_code == 200
        cierre = cliente.patch(f"/api/v1/reviews/{rev['id']}", headers={**h, "If-Match": tomada["actualizado_en"]},
                               json={"estado": "aprobado"})
        assert cierre.status_code == 200, cierre.text
        assert cierre.json()["documento_estado"] == "aprobado"

        # Export idempotente con hash
        e1 = cliente.post(f"/api/v1/documents/{doc_id}/export", headers=h)
        assert e1.status_code == 200 and e1.headers["content-type"] == "application/pdf"
        assert hashlib.sha256(e1.content).hexdigest() == e1.headers["x-document-hash"]
        e2 = cliente.post(f"/api/v1/documents/{doc_id}/export", headers=h)
        assert e2.content == e1.content
        todo = _texto_pdf(e1.content)
        assert "12345678Z" not in todo and "Juan Pérez" not in todo

        # ZIP: el mismo PDF anonimizado; un id ajeno se salta y se cuenta
        z = cliente.post("/api/v1/documents/export/zip", headers=h,
                         json={"ids": [doc_id, str(uuid4())], "tipo": "anon"})
        assert z.status_code == 200 and z.headers["x-omitidos"] == "1"
        with zipfile.ZipFile(io.BytesIO(z.content)) as zf:
            assert zf.namelist() == ["expediente_anon.pdf"]
            assert zf.read("expediente_anon.pdf") == e1.content

        # Auditoría e informes
        aud = cliente.get("/api/v1/audit", headers=h, params={"entidad_id": doc_id}).json()["items"]
        eventos_aud = {a["evento"] for a in aud}
        assert {"DOCUMENTO_SUBIDO", "OCR_COMPLETADO", "PAGINA_EDITADA", "JG_ENVIADO",
                "ANONIMIZACION_IA", "PDF_EXPORTADO"} <= eventos_aud
        inf = cliente.get("/api/v1/reports/summary", headers=h).json()
        assert inf["paginas_mes"] >= 6 and inf["jg_enviados"] >= 1
