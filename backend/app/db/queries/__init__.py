from pathlib import Path


def _cargar() -> dict[str, str]:
    """Cada .sql agrupa consultas separadas por `-- name: nombre`."""
    consultas: dict[str, str] = {}
    for ruta in Path(__file__).parent.glob("*.sql"):
        nombre = None
        lineas: list[str] = []
        for linea in ruta.read_text(encoding="utf-8").splitlines():
            if linea.startswith("-- name:"):
                if nombre:
                    consultas[nombre] = "\n".join(lineas).strip()
                nombre = linea.split(":", 1)[1].strip()
                lineas = []
            elif nombre:
                lineas.append(linea)
        if nombre:
            consultas[nombre] = "\n".join(lineas).strip()
    return consultas


SQL = _cargar()
