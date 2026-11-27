"""OCR: la llamada a Ollama prueba las bases del host cuando la configurada no tiene red.

En Docker rootless `host.docker.internal` no resuelve; el OCR debe caer a 10.0.2.2 y recordar
la base que responde. Se prueba sin modelo: `urlopen` es falso.
"""

import io
import json
import urllib.error
import urllib.request

import pytest

from app.core.config import settings
from app.services import ocr


def _responde(texto: str) -> io.BytesIO:
    return io.BytesIO(json.dumps({"response": texto}).encode())


@pytest.fixture(autouse=True)
def _limpio(monkeypatch):
    monkeypatch.setattr(settings, "ocr_mock", False)
    monkeypatch.setattr(ocr, "_ACTIVA", None)


def test_cae_a_la_base_del_host_si_la_configurada_no_resuelve(monkeypatch):
    monkeypatch.setattr(settings, "ollama_url", "http://no-resuelve:11434")
    vistas = []

    def urlopen(peticion, timeout=None):
        vistas.append(peticion.full_url)
        if "no-resuelve" in peticion.full_url:
            raise urllib.error.URLError("Name or service not known")
        return _responde("hola")

    monkeypatch.setattr(urllib.request, "urlopen", urlopen)
    _, texto = ocr.leer(b"png")

    assert texto == "hola"
    assert vistas[0].startswith("http://no-resuelve:11434")
    assert vistas[1] == "http://host.docker.internal:11434/api/generate"
    assert ocr._ACTIVA == "http://host.docker.internal:11434"


def test_recuerda_la_base_que_respondio(monkeypatch):
    monkeypatch.setattr(settings, "ollama_url", "http://no-resuelve:11434")
    vistas = []

    def urlopen(peticion, timeout=None):
        vistas.append(peticion.full_url)
        if "no-resuelve" in peticion.full_url:
            raise urllib.error.URLError("Connection refused")
        return _responde("hola")

    monkeypatch.setattr(urllib.request, "urlopen", urlopen)
    ocr.leer(b"png")
    vistas.clear()
    ocr.leer(b"png")

    assert len(vistas) == 1  # la primera base probada ya es la buena: no vuelve a fallar
    assert vistas[0].startswith("http://host.docker.internal")


def test_un_404_no_prueba_otras_bases(monkeypatch):
    monkeypatch.setattr(settings, "ollama_url", "http://ollama:11434")
    vistas = []

    def urlopen(peticion, timeout=None):
        vistas.append(peticion.full_url)
        raise urllib.error.HTTPError(peticion.full_url, 404, "Not Found", {}, None)

    monkeypatch.setattr(urllib.request, "urlopen", urlopen)
    with pytest.raises(urllib.error.HTTPError):
        ocr.leer(b"png")

    assert vistas == ["http://ollama:11434/api/generate"]  # el modelo falta: no es la red


def test_url_configurada_con_barra_final(monkeypatch):
    monkeypatch.setattr(settings, "ollama_url", "http://ollama:11434/")
    vistas = []

    def urlopen(peticion, timeout=None):
        vistas.append(peticion.full_url)
        return _responde("ok")

    monkeypatch.setattr(urllib.request, "urlopen", urlopen)
    assert ocr.leer(b"png")[1] == "ok"
    assert vistas == ["http://ollama:11434/api/generate"]
