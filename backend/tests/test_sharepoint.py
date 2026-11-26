"""Ruteo de la entrada por SharePoint con un Graph falso: sin red ni BD."""

from app.core.errors import AppError
from app.services import sharepoint


class GraphFalso:
    def __init__(self, arbol):
        self.arbol = arbol  # {id_carpeta: [items]}; None = carpeta raíz
        self.movidos = []

    def hijos(self, item_id):
        return self.arbol.get(item_id, [])

    def descargar(self, item):
        return item["datos"]

    def subcarpeta(self, padre_id, nombre):
        return f"{padre_id}/{nombre}"

    def mover(self, item_id, carpeta_id):
        self.movidos.append((item_id, carpeta_id))


def test_sube_con_nombre_de_carpeta_y_archiva():
    graph = GraphFalso({
        None: [{"id": "c1", "name": "Ana López ", "folder": {}}, {"id": "x", "name": "suelto.pdf", "file": {}}],
        "c1": [{"id": "f1", "name": "a.pdf", "file": {}, "datos": b"ok"},
               {"id": "f2", "name": "dup.PDF", "file": {}, "datos": b"dup"},
               {"id": "f3", "name": "roto.pdf", "file": {}, "datos": b"mal"},
               {"id": "f4", "name": "nota.txt", "file": {}, "datos": b"-"},
               {"id": "p", "name": "Procesados", "folder": {}}],
    })
    llamadas = []

    def subir(nombre, datos, doble, usuario, request, subido_por, origen):
        llamadas.append((nombre, usuario["usuario_id"], subido_por, origen))
        if datos == b"dup":
            raise AppError("DOCUMENTO_DUPLICADO", "", 409)
        if datos == b"mal":
            raise AppError("FORMATO_NO_SOPORTADO", "", 415)
        return {"id": "d"}

    n = sharepoint.sondear(graph, usuario_de=lambda nombre: {"usuario_id": "u-" + nombre}, subir=subir)

    assert n == 1
    assert [c[0] for c in llamadas] == ["a.pdf", "dup.PDF", "roto.pdf"]  # .txt y la raíz no
    assert all(c[1:] == ("u-Ana López", "Ana López", "sharepoint") for c in llamadas)
    assert graph.movidos == [("f1", "c1/Procesados"), ("f2", "c1/Procesados"), ("f3", "c1/Rechazados")]


def test_sin_usuario_no_toca_los_ficheros():
    graph = GraphFalso({None: [{"id": "c1", "name": "Nadie", "folder": {}}],
                        "c1": [{"id": "f1", "name": "a.pdf", "file": {}, "datos": b"ok"}]})
    assert sharepoint.sondear(graph, usuario_de=lambda n: None, subir=None) == 0
    assert graph.movidos == []
