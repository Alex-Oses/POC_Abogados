"""Qué decisiones y preguntas esperan a una persona. Solo lee la bóveda.

Uso: python scripts/decisiones.py [@persona]
"""

import re
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.stdout.reconfigure(encoding="utf-8")


def persona_por_defecto():
    """Quién ejecuta el script: la firma de git del repo."""
    try:
        nombre = subprocess.run(
            ["git", "config", "user.name"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        nombre = ""
    return nombre.lstrip("@")


PERSONA = (sys.argv[1] if len(sys.argv) > 1 else persona_por_defecto()).lstrip("@")


def lee(ruta):
    """Texto con saltos de línea normalizados: el repo mezcla LF y CRLF."""
    return ruta.read_text(encoding="utf-8").replace("\r\n", "\n")


def campo(texto, nombre):
    m = re.search(rf"\*\*{nombre}\*\*:\s*(.+)|^\s*-\s*\*\*{nombre}\*\*:?\s*(.+)$", texto, re.M)
    if not m:
        return ""
    return (m.group(1) or m.group(2) or "").strip()


def decisiones():
    for fichero in sorted((RAIZ / "vault/Decisiones").glob("*.md")):
        texto = lee(fichero)
        if not campo(texto, "Estado").lower().startswith("propuesta"):
            continue
        titulo = re.sub(r"\s*[—·]\s*", " · ", texto.splitlines()[0].lstrip("# ").strip())
        votos = campo(texto, "Votos")
        falta = ""
        if "falta" in votos.lower():
            pendientes = re.findall(r"@(\w+)", votos.split("Faltan", 1)[-1])
            if PERSONA not in pendientes:
                continue  # ya votaste o no te toca
            falta = "voto de " + ", ".join("@" + p for p in pendientes)
        else:
            falta = "tu OK (sin votos registrados)"
        yield titulo, falta, f"[[{fichero.stem}]]"


def lineas(seccion, empieza_por=None, contiene=None):
    texto = lee(RAIZ / "vault/Tablero.md")
    bloque = re.search(rf"^## {seccion}\n(.*?)(?=\n## |\Z)", texto, re.S | re.M)
    for linea in (bloque.group(1).splitlines() if bloque else []):
        linea = linea.strip()
        if empieza_por and not linea.startswith(empieza_por):
            continue
        if contiene and contiene not in linea:
            continue
        yield linea


def main():
    if not PERSONA:
        print("Falta la persona: configura `git config user.name` o pasa un nombre.")
        return
    pendientes = list(decisiones())
    filas = [(titulo, f"**{falta}**", donde) for titulo, falta, donde in pendientes]

    for linea in lineas("Preguntas abiertas", empieza_por=f"- @{PERSONA}:"):
        pregunta = re.sub(rf"^- @{PERSONA}:\s*", "", linea).split("· @")[0].strip()
        filas.append((f"Pregunta: {pregunta}", "**tu respuesta**", "[[Tablero]] § Preguntas abiertas"))

    ya_en_tabla = {donde for _, _, donde in pendientes}
    for linea in lineas("Pendiente", empieza_por="- [ ]", contiene=f"@{PERSONA}"):
        if any(enlace in linea for enlace in ya_en_tabla):
            continue  # ya sale arriba como decisión
        tarea = re.sub(r"^- \[ \]\s*", "", linea)
        tarea = re.sub(rf"\s*·\s*@\w+(\s+@\w+)*\s*$", "", tarea)
        filas.append((tarea, "**tu decisión**", "[[Tablero]] § Pendiente"))

    if not filas:
        print(f"Nada pendiente de @{PERSONA}.")
        return

    print("| Qué | Qué falta de ti | Dónde |")
    print("|---|---|---|")
    for titulo, falta, donde in filas:
        print(f"| {titulo} | {falta} | {donde} |")


if __name__ == "__main__":
    main()
