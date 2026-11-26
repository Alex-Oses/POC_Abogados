"""Comprueba que una base de datos (la de Marina u otra) sirve para el backend antes de arrancar.

Uso:  backend/.venv/bin/python scripts/comprobar_bd.py "postgresql://usuario:clave@host:5432/icat"
      (sin argumento usa DATABASE_URL del entorno o de backend/.env)

Solo lee: no crea ni migra nada (el esquema lo manda Flyway, docs/architecture/README.md).
Sale con código 1 si falta algo imprescindible.
"""

import os
import re
import sys
from pathlib import Path

import psycopg

TABLAS = ["usuarios", "usuarios_roles", "sesiones_usuario", "documentos", "versiones_documento",
          "bloques_layout", "paginas_documento", "anotaciones_entidad", "categorias_sensibles",
          "reglas_anonimizacion", "regla_categorias", "revisiones", "auditoria", "configuracion_sistema"]
# Columnas que el backend usa y que llegaron en V14/V15: si faltan, el esquema es anterior.
COLUMNAS = {"usuarios": ["nombre", "apellidos", "estado", "password_hash"],
            "documentos": ["metadatos_extras", "clave_cifrado", "num_paginas", "exportado_en"],
            "versiones_documento": ["es_actual", "metadatos_proceso", "ruta_pdf"],
            "paginas_documento": ["numero", "estado"]}


def url() -> str:
    if len(sys.argv) > 1:
        return sys.argv[1]
    if os.getenv("DATABASE_URL"):
        return os.environ["DATABASE_URL"]
    env = Path(__file__).resolve().parents[1] / "backend" / ".env"
    m = re.search(r"^DATABASE_URL=(.+)$", env.read_text(encoding="utf-8"), re.MULTILINE) if env.exists() else None
    if not m:
        sys.exit("ERROR: falta la URL de la base de datos")
    return m.group(1).strip()


def main() -> int:
    errores = 0
    try:
        conexion = psycopg.connect(url(), connect_timeout=10)
    except Exception as error:  # noqa: BLE001 - se informa y se sale
        print(f"ERROR: no conecta: {str(error).splitlines()[0]}")
        return 1
    with conexion:
        print("OK   conecta:", conexion.execute("SELECT version()").fetchone()[0].split(",")[0])
        existentes = {f[0] for f in conexion.execute(
            "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'")}
        for tabla in TABLAS:
            if tabla not in existentes:
                print(f"FALTA tabla {tabla}")
                errores += 1
        for tabla, columnas in COLUMNAS.items():
            hay = {f[0] for f in conexion.execute(
                "SELECT column_name FROM information_schema.columns WHERE table_name = %s", (tabla,))}
            for c in columnas:
                if tabla in existentes and c not in hay:
                    print(f"FALTA columna {tabla}.{c}")
                    errores += 1
        if "configuracion_sistema" in existentes:
            fila = conexion.execute(
                "SELECT valor FROM configuracion_sistema WHERE clave = 'version_esquema_bd'").fetchone()
            print("INFO versión de esquema:", fila[0] if fila else "sin dato")
        triggers = conexion.execute(
            "SELECT count(*) FROM information_schema.triggers WHERE trigger_schema = 'public'").fetchone()[0]
        print(f"INFO triggers.sql: {'aplicado' if triggers else 'no aplicado'} ({triggers} triggers)")
        if "categorias_sensibles" in existentes:
            n = conexion.execute("SELECT count(*) FROM categorias_sensibles").fetchone()[0]
            print(f"{'OK  ' if n else 'FALTA'} categorías sensibles: {n} (V11)")
            errores += 0 if n else 1
        # Permisos: el backend escribe en documentos y auditoría.
        for tabla in ("documentos", "auditoria", "usuarios"):
            if tabla in existentes and not conexion.execute(
                    "SELECT has_table_privilege(current_user, %s, 'INSERT')", (tabla,)).fetchone()[0]:
                print(f"FALTA permiso INSERT en {tabla}")
                errores += 1
    print("LISTA para el backend" if not errores else f"NO LISTA: {errores} problema(s)")
    return 1 if errores else 0


if __name__ == "__main__":
    sys.exit(main())
