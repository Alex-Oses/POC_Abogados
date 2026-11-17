"""Convierte un .md de docs/ en PDF con el estilo del proyecto.

Uso: pip install markdown playwright
     python docs/pdf.py docs/maqueta.md salida.pdf
"""
import sys
from pathlib import Path
import markdown
from playwright.sync_api import sync_playwright

CSS = """
@page { size: A4; margin: 22mm 18mm 20mm; }
body { font: 10.5pt/1.55 Roboto, 'Segoe UI', Arial, sans-serif; color: #212121; }
h1 { font-weight: 400; font-size: 26pt; color: #B2051B; margin: 0 0 6pt; }
h2 { font-weight: 400; font-size: 17pt; margin: 22pt 0 8pt; padding-top: 6pt; border-top: 2px solid #B2051B; page-break-after: avoid; }
h3 { font-size: 12pt; color: #B2051B; margin: 16pt 0 6pt; page-break-after: avoid; }
table { border-collapse: collapse; width: 100%; margin: 8pt 0 12pt; font-size: 9.5pt; page-break-inside: avoid; }
th { background: #212121; color: #fff; text-align: left; font-weight: 500; padding: 5pt 7pt; }
td { border-bottom: 1px solid #E2DFDA; padding: 5pt 7pt; vertical-align: top; }
code { font: 9pt Consolas, monospace; background: #F6F5F3; padding: 1pt 3pt; border-radius: 2pt; }
pre { background: #F6F5F3; padding: 8pt 10pt; border-radius: 4pt; page-break-inside: avoid; }
pre code { background: none; padding: 0; }
img { max-width: 100%; border: 1px solid #E2DFDA; border-radius: 3pt; margin: 6pt 0; page-break-inside: avoid; }
blockquote { margin: 8pt 0; padding: 6pt 12pt; background: #FFF4D6; border-left: 3px solid #8A5A00; }
li { margin: 2pt 0; }
"""

# --informe: formato de informe para revisión (portada, índice, franja lateral, contraportada). Sin marcas de empresa.
INFORME = """
@import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;600;700&display=swap');
@page { size: A4; margin: 24mm 22mm 24mm 20mm; }
body { font: 10pt/1.6 Poppins, 'Segoe UI', sans-serif; color: #232A49; }
.portada, .contra { overflow: hidden;
  background: linear-gradient(160deg, #2b2f3f, #0f1220); color: #fff; position: relative; }

.portada .t { font-weight: 300; font-size: 44pt; line-height: 1.1; color: #F2F23A; margin-top: 105mm; }
.portada .s { font-weight: 700; font-size: 20pt; margin: 14pt 0 30pt; max-width: 110mm; }
.portada .m { color: #F2F23A; font-size: 15pt; line-height: 2; }
.cuadros i { position: absolute; background: #F2F23A; opacity: .85; }
.grad { position: absolute; left: 0; right: 0; bottom: 0; height: 4mm; background: linear-gradient(90deg, #232A49, #E5197F); }
.indice { page-break-after: always; }
.indice ol { padding-left: 16pt; font-weight: 600; } .indice li { padding: 3pt 0; border-bottom: 1px dotted #232A49; }
h1.ind { color: #E5197F; font-weight: 700; font-size: 24pt; border: 0; }
h1 { display: none; }
h2 { font-weight: 300; font-size: 22pt; margin: 22pt 0 10pt; page-break-after: avoid; counter-increment: s; }
h2::before { content: counter(s) "  "; }
h3 { font-weight: 700; font-size: 11pt; color: #fff; background: #232A49; padding: 6pt 9pt; margin: 18pt 0 8pt; page-break-after: avoid; }
h3 { color: #F2F23A; } h3 code { background: none; color: inherit; font: inherit; }
table { border-collapse: collapse; width: 100%; margin: 8pt 0 14pt; font-size: 9pt; page-break-inside: avoid; }
th { background: #232A49; color: #F2F23A; text-align: left; font-weight: 700; padding: 5pt 8pt; }
td { padding: 7pt 8pt; vertical-align: top; } td + td { font-weight: 600; }
ul { list-style: none; padding-left: 14pt; } ul li::before { content: "▪"; color: #E5197F; margin-left: -12pt; margin-right: 6pt; }
blockquote { background: #232A49; color: #fff; font-weight: 600; margin: 10pt 0; padding: 10pt 14pt; }
code { font: 8.5pt Consolas, monospace; background: #F1F2F6; padding: 1pt 3pt; }
pre { background: #F1F2F6; padding: 8pt 10pt; page-break-inside: avoid; } pre code { background: none; }
img { max-width: 100%; margin: 6pt 0; page-break-inside: avoid; }
a { color: #232A49; }
"""

informe = "--informe" in sys.argv
args = [a for a in sys.argv[1:] if a != "--informe"]
src, dst = Path(args[0]).resolve(), Path(args[1]).resolve()
texto = src.read_text(encoding="utf-8")
body = markdown.markdown(texto, extensions=["tables", "fenced_code"])
if informe:
    import datetime, re
    titulo = re.search(r"^# (.+)$", texto, re.M).group(1)
    t, _, s = titulo.partition(" · ")
    fecha = datetime.date.today().strftime("%d/%m/%Y")
    cuadros = '<div class="cuadros"><i style="right:30mm;top:22mm;width:20mm;height:20mm"></i><i style="right:12mm;top:22mm;width:18mm;height:38mm;opacity:.6"></i><i style="right:50mm;top:58mm;width:18mm;height:18mm"></i></div>'
    # shortcut: índice sin números de página (Chromium no los da al generar), si hace falta, pasar a WeasyPrint.
    indice = "".join(f"<li>{h}</li>" for h in re.findall(r"^## (?:\d+\.\s*)?(.+)$", texto, re.M))
    body = re.sub(r"<h2>\d+\.\s*", "<h2>", body)
    portada = (f'<div class="portada">{cuadros}<div class="t">{t}</div><div class="s">{s or "Documento técnico"}</div>'
               f'<div class="m">Documento para revisión<br>{fecha}</div><div class="grad"></div></div>')
    body = f'<div class="indice"><h1 class="ind" style="display:block">Índice</h1><ol>{indice}</ol></div>{body}'
    CSS = INFORME
pie = ('<div style="font:8px Arial;color:#5E5E5E;width:100%;padding:0 18mm;display:flex;justify-content:space-between">'
       + (f'<span>{fecha} | Ref. POC ICAT<br>Clasificación: documento interno</span>' if informe else f'<span>{src.stem} · POC ICAT</span>')
       + '<span><span class="pageNumber"></span> / <span class="totalPages"></span></span></div>')


def render(pg, contenido, path, css_extra="", pie=None):
    html = f'<!doctype html><html lang="es"><head><meta charset="utf-8"><base href="{src.parent.as_uri()}/"><style>{CSS}{css_extra}</style></head><body>{contenido}</body></html>'
    tmp = src.parent / f".{src.stem}.tmp.html"
    tmp.write_text(html, encoding="utf-8")
    try:
        pg.goto(tmp.as_uri()); pg.wait_for_load_state("networkidle")
        pg.pdf(path=str(path), format="A4", print_background=True, prefer_css_page_size=True, display_header_footer=bool(pie),
               header_template="<span></span>", footer_template=pie or "<span></span>")
    finally:
        tmp.unlink(missing_ok=True)


with sync_playwright() as p:
    b = p.chromium.launch(channel="msedge", headless=True)
    pg = b.new_page()
    if not informe:
        render(pg, body, dst, pie=pie)
    else:
        # Portada y contraportada a sangre y sin pie: se generan aparte y se unen.
        import pypdfium2
        sangre = "@page { margin: 0 } body { margin: 0 } .portada, .contra { height: 296.5mm; box-sizing: border-box; padding: 20mm 22mm 0 24mm }"
        partes = [dst.with_suffix(f".{n}.pdf") for n in ("a", "b", "c")]
        render(pg, portada, partes[0], sangre)
        render(pg, body, partes[1], pie=pie)
        render(pg, '<div class="contra"><div class="grad"></div></div>', partes[2], sangre)
        doc = pypdfium2.PdfDocument.new()
        for parte in partes:
            fuente = pypdfium2.PdfDocument(str(parte)); doc.import_pages(fuente); fuente.close()
        doc.save(str(dst)); doc.close()
        for parte in partes:
            parte.unlink()
    b.close()
print(dst)
