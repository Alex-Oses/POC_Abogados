"""Entrada por SharePoint: cada PDF que se deja en `<SHAREPOINT_CARPETA>/<Nombre Persona>/` se sube
solo a la app y entra en la cola de OCR, con «subido por» = nombre de la carpeta.

Sondea Microsoft Graph cada `SHAREPOINT_SONDEO_SEG` con una app de Entra ID (client credentials,
permiso de aplicación `Sites.Selected` o `Files.ReadWrite.All`). Tras subirlo mueve el fichero a
`<persona>/Procesados` (o `Rechazados` si la app no lo acepta), así nunca se sube dos veces.
Si la carpeta coincide con el nombre de un usuario activo, el documento es suyo; si no, queda
a nombre del admin y lo ven revisores y admin.
"""

import json
import threading
import time
import urllib.parse
import urllib.request

from app.core.config import settings
from app.core.errors import AppError
from app.core.logging import log
from app.db.pool import tx
from app.db.queries import SQL
from app.services import cola, documents

GRAPH = "https://graph.microsoft.com/v1.0"
PROCESADOS, RECHAZADOS = "Procesados", "Rechazados"
_parar = threading.Event()


class Graph:
    """Lo mínimo de Graph que hace falta. Se sustituye por un falso en las pruebas."""

    def __init__(self):
        self._token, self._caduca = "", 0.0

    def _cabecera(self) -> dict:
        if time.time() > self._caduca - 60:
            datos = urllib.parse.urlencode({
                "client_id": settings.sharepoint_client_id,
                "client_secret": settings.sharepoint_client_secret,
                "grant_type": "client_credentials",
                "scope": "https://graph.microsoft.com/.default"}).encode()
            url = f"https://login.microsoftonline.com/{settings.sharepoint_tenant_id}/oauth2/v2.0/token"
            with urllib.request.urlopen(url, datos, timeout=30) as r:
                token = json.load(r)
            self._token, self._caduca = token["access_token"], time.time() + token["expires_in"]
        return {"Authorization": f"Bearer {self._token}", "Content-Type": "application/json"}

    def _pedir(self, metodo: str, ruta: str, cuerpo: dict | None = None) -> dict:
        peticion = urllib.request.Request(
            f"{GRAPH}/drives/{settings.sharepoint_drive_id}{ruta}", method=metodo,
            headers=self._cabecera(), data=json.dumps(cuerpo).encode() if cuerpo else None)
        with urllib.request.urlopen(peticion, timeout=60) as r:
            return json.load(r) if r.status != 204 else {}

    def hijos(self, item_id: str | None) -> list[dict]:
        ruta = (f"/items/{item_id}/children" if item_id else
                f"/root:/{urllib.parse.quote(settings.sharepoint_carpeta)}:/children")
        salida, url = [], ruta + "?$top=200"
        while url:
            pagina = self._pedir("GET", url)
            salida += pagina.get("value", [])
            siguiente = pagina.get("@odata.nextLink")
            url = siguiente.split(f"/drives/{settings.sharepoint_drive_id}", 1)[1] if siguiente else None
        return salida

    def descargar(self, item: dict) -> bytes:
        with urllib.request.urlopen(item["@microsoft.graph.downloadUrl"], timeout=120) as r:
            return r.read()

    def subcarpeta(self, padre_id: str, nombre: str) -> str:
        for h in self.hijos(padre_id):
            if h["name"] == nombre and "folder" in h:
                return h["id"]
        return self._pedir("POST", f"/items/{padre_id}/children", {
            "name": nombre, "folder": {}, "@microsoft.graph.conflictBehavior": "fail"})["id"]

    def mover(self, item_id: str, carpeta_id: str) -> None:
        self._pedir("PATCH", f"/items/{item_id}?@microsoft.graph.conflictBehavior=rename",
                    {"parentReference": {"id": carpeta_id}})


def _usuario_de(nombre: str) -> dict | None:
    with tx() as conexion:
        fila = conexion.execute(SQL["usuario_por_nombre"], {"nombre": nombre}).fetchone()
        if not fila and settings.admin_email:
            admin = conexion.execute(SQL["usuario_por_email"], {"email": settings.admin_email}).fetchone()
            fila = admin and {"usuario_id": admin["id"], "nombre": admin["nombre"],
                              "apellidos": admin["apellidos"]}
    return fila


def sondear(graph, usuario_de=_usuario_de, subir=documents.registrar_subida) -> int:
    """Una pasada: sube los PDF nuevos de cada carpeta de persona. Devuelve cuántos subió."""
    subidos = 0
    for carpeta in graph.hijos(None):
        if "folder" not in carpeta:
            continue
        persona = carpeta["name"].strip()
        pdfs = [h for h in graph.hijos(carpeta["id"])
                if "file" in h and h["name"].lower().endswith(".pdf")]
        if not pdfs:
            continue
        usuario = usuario_de(persona)
        if not usuario:
            log.error("sharepoint_sin_usuario", extra={"detalle": persona})
            continue
        for item in pdfs:
            destino = PROCESADOS
            try:
                subir(item["name"], graph.descargar(item), True, usuario, None,
                      subido_por=persona, origen="sharepoint")
                subidos += 1
            except AppError as error:
                # Duplicado: ya está en la app, se archiva igual. Formato o tamaño: a Rechazados.
                destino = PROCESADOS if error.code == "DOCUMENTO_DUPLICADO" else RECHAZADOS
                log.info("sharepoint_rechazado", extra={"detalle": f"{item['name']}: {error.code}"})
            graph.mover(item["id"], graph.subcarpeta(carpeta["id"], destino))
    if subidos:
        cola.despertar.set()
    return subidos


def _bucle(parar: threading.Event) -> None:
    graph = Graph()
    while not parar.is_set():
        try:
            sondear(graph)
        except Exception:  # noqa: BLE001 - red o Graph caídos: el fichero sigue allí y se reintenta
            log.exception("sharepoint_sondeo_fallido")
        parar.wait(settings.sharepoint_sondeo_seg)


def configurado() -> bool:
    return all((settings.sharepoint_tenant_id, settings.sharepoint_client_id,
                settings.sharepoint_client_secret, settings.sharepoint_drive_id))


def arrancar() -> None:
    global _parar
    if configurado():
        _parar = threading.Event()  # nuevo en cada arranque: uno parado antes no lo frena
        threading.Thread(target=_bucle, args=(_parar,), name="sharepoint", daemon=True).start()
        log.info("sharepoint_activo", extra={"detalle": settings.sharepoint_carpeta})


def detener() -> None:
    _parar.set()
