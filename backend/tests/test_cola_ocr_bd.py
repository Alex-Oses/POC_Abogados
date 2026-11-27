"""Cola de OCR (0017): orden, páginas disponibles durante el proceso, edición y reanudación."""

import json
import os
import time
from uuid import uuid4

import psycopg
import pymupdf
import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.core.security import hash_password
from app.main import app
from app.services import cola, documents

pytestmark = pytest.mark.skipif(not os.getenv("DATABASE_TEST_URL"), reason="sin DATABASE_TEST_URL")
CLAVE = "una-clave-larga-123"


def _pdf(paginas: int) -> bytes:
    doc = pymupdf.open()
    for i in range(paginas):
        doc.new_page().insert_text((72, 72), f"Página {i + 1} de prueba ficticia", fontsize=12)
    datos = doc.tobytes()
    doc.close()
    return datos + f"%{uuid4().hex}".encode()


@pytest.fixture()
def cliente(monkeypatch):
    monkeypatch.setattr(settings, "ocr_mock_delay", 0.4)
    monkeypatch.setattr(settings, "ocr_sondeo_seg", 0.1)
    email = f"cola-{uuid4().hex[:10]}@icat.local"
    with psycopg.connect(settings.database_url) as c:
        uid = c.execute("INSERT INTO usuarios (email, nombre, password_hash) VALUES (%s, 'Cola', %s) "
                        "RETURNING id", (email, hash_password(CLAVE))).fetchone()[0]
        c.execute("INSERT INTO usuarios_roles VALUES (%s, 'transcriptor')", (uid,))
    with TestClient(app) as c:
        token = c.post("/api/v1/user/login", json={"email": email, "password": CLAVE}).json()["access_token"]
        c.headers["Authorization"] = f"Bearer {token}"
        yield c


def _subir(cliente, paginas: int) -> str:
    r = cliente.post("/api/v1/transform/document", data={"modo": "simple"},
                     files={"file": ("x.pdf", _pdf(paginas), "application/pdf")})
    assert r.status_code == 202, r.text
    assert r.json()["num_paginas"] == paginas and r.json()["estado"] == "pendiente"
    return r.json()["id"]


def _esperar(cliente, doc_id, condicion, segundos=30) -> dict:
    fin = time.time() + segundos
    while time.time() < fin:
        prog = cliente.get(f"/api/v1/documents/{doc_id}/progress").json()
        if condicion(prog):
            return prog
        time.sleep(0.05)
    raise AssertionError(prog)


def test_cola_por_pagina(cliente):
    a = _subir(cliente, 3)
    b = _subir(cliente, 1)
    # Página 1 de A lista mientras A sigue y B espera detrás.
    prog = _esperar(cliente, a, lambda p: p["pages_done"] >= 1 and p["estado"] == "ocr_procesando")
    assert prog["total_pages"] == 3 and prog["current_page"] == prog["pages_done"] + 1
    pb = cliente.get(f"/api/v1/documents/{b}/progress").json()
    assert pb["estado"] == "pendiente" and pb["queue_position"] >= 1 and pb["pages_done"] == 0
    listado = {d["id"]: d for d in cliente.get("/api/v1/documents").json()["items"]}
    assert listado[b]["queue_position"] == pb["queue_position"] and listado[a]["pages_done"] >= 1

    items = cliente.get(f"/api/v1/documents/{a}/pages").json()["items"]
    assert items[0]["numero"] == 1 and "Página 1" in items[0]["texto"]
    assert cliente.get(f"/api/v1/documents/{a}/pages/1/image").status_code == 200
    assert cliente.patch(f"/api/v1/documents/{a}/pages/1",
                         json={"texto": "Editada", "validada": True}).status_code == 204
    assert cliente.patch(f"/api/v1/documents/{a}/pages/3", json={"texto": "x"}).status_code == 409

    _esperar(cliente, a, lambda p: p["estado"] == "ocr_completado")
    _esperar(cliente, b, lambda p: p["estado"] == "ocr_completado")
    items = cliente.get(f"/api/v1/documents/{a}/pages").json()["items"]
    assert [p["numero"] for p in items] == [1, 2, 3]
    assert items[0]["texto"] == "Editada" and items[0]["validada"]  # el worker no la pisó


def test_ndjson_desde_bd(cliente):
    r = cliente.post("/api/v1/transform/document", headers={"Accept": "application/x-ndjson"},
                     data={"modo": "simple"}, files={"file": ("x.pdf", _pdf(2), "application/pdf")})


    tipos = [json.loads(linea)["type"] for linea in r.text.splitlines()]
    assert tipos == ["start", "page", "page", "done"]


def test_reanuda_tras_reinicio(cliente):
    doc_id = _subir(cliente, 4)
    _esperar(cliente, doc_id, lambda p: p["pages_done"] >= 1 and p["estado"] == "ocr_procesando")
    cola.detener()  # simula apagado a mitad
    prog = cliente.get(f"/api/v1/documents/{doc_id}/progress").json()
    assert prog["estado"] == "ocr_procesando" and 1 <= prog["pages_done"] < 4
    cola.arrancar()  # al arrancar vuelve a la cola y sigue desde la última guardada
    _esperar(cliente, doc_id, lambda p: p["estado"] == "ocr_completado")
    items = cliente.get(f"/api/v1/documents/{doc_id}/pages").json()["items"]
    assert [p["numero"] for p in items] == [1, 2, 3, 4]


def test_cancelar(cliente):
    a = _subir(cliente, 3)
    b = _subir(cliente, 2)
    r = cliente.post(f"/api/v1/documents/{b}/cancel")
    assert r.status_code == 200 and r.json()["error"] == "CANCELADO"
    assert cliente.post(f"/api/v1/documents/{b}/cancel").status_code == 409
    _esperar(cliente, a, lambda p: p["estado"] == "ocr_completado")
    pb = cliente.get(f"/api/v1/documents/{b}/progress").json()
    assert pb["estado"] == "pendiente" and pb["pages_done"] == 0 and pb["queue_position"] is None


def test_reintentar_tras_fallo(cliente, monkeypatch):
    real = documents.ocr.procesar_pagina

    def falla(*args, **kwargs):
        raise RuntimeError("modelo caído")

    monkeypatch.setattr(documents.ocr, "procesar_pagina", falla)
    doc_id = _subir(cliente, 1)
    error = _esperar(cliente, doc_id, lambda p: p["error"] == "OCR_FALLIDO")
    assert error["queue_position"] is None  # fuera de la cola hasta que se reintente
    assert cliente.post(f"/api/v1/documents/{doc_id}/cancel").status_code == 409
    monkeypatch.setattr(documents.ocr, "procesar_pagina", real)
    r = cliente.post(f"/api/v1/documents/{doc_id}/retry")
    assert r.status_code == 200 and r.json()["error"] is None and r.json()["queue_position"] >= 1
    _esperar(cliente, doc_id, lambda p: p["estado"] == "ocr_completado")


def test_borrar_durante_ocr_no_resucita(cliente):
    doc_id = _subir(cliente, 4)
    _esperar(cliente, doc_id, lambda p: p["pages_done"] >= 1 and p["estado"] == "ocr_procesando")
    assert cliente.delete(f"/api/v1/documents/{doc_id}").status_code == 204
    time.sleep(1.2)  # deja terminar la página en curso
    assert cliente.get(f"/api/v1/documents/{doc_id}/progress").status_code == 404
    ids = {d["id"] for d in cliente.get("/api/v1/documents").json()["items"]}
    assert doc_id not in ids


def test_editar_formato_no_pone_el_semaforo_en_verde(cliente):
    doc_id = _subir(cliente, 1)
    _esperar(cliente, doc_id, lambda p: p["estado"] == "ocr_completado")
    with psycopg.connect(settings.database_url) as c:
        c.execute("UPDATE bloques_layout b SET calidad_semaforo = 'amarillo' "
                  "FROM versiones_documento v WHERE v.id = b.version_id "
                  "AND v.documento_id = %s AND v.es_actual", (doc_id,))

    def semaforo():
        with psycopg.connect(settings.database_url) as c:
            return c.execute("SELECT b.calidad_semaforo FROM bloques_layout b "
                             "JOIN versiones_documento v ON v.id = b.version_id "
                             "WHERE v.documento_id = %s AND v.es_actual AND b.pagina_numero = 1",
                             (doc_id,)).fetchone()[0]

    assert cliente.patch(f"/api/v1/documents/{doc_id}/pages/1",
                         json={"texto": "Otra lectura"}).status_code == 204
    assert semaforo() == "amarillo"
    assert cliente.patch(f"/api/v1/documents/{doc_id}/pages/1",
                         json={"validada": True}).status_code == 204
    assert semaforo() == "verde"
