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

src, dst = Path(sys.argv[1]).resolve(), Path(sys.argv[2]).resolve()
body = markdown.markdown(src.read_text(encoding="utf-8"), extensions=["tables", "fenced_code"])
html = f'<!doctype html><html lang="es"><head><meta charset="utf-8"><base href="{src.parent.as_uri()}/"><style>{CSS}</style></head><body>{body}</body></html>'
tmp = src.parent / f".{src.stem}.tmp.html"
tmp.write_text(html, encoding="utf-8")
try:
    with sync_playwright() as p:
        b = p.chromium.launch(channel="msedge", headless=True)
        pg = b.new_page(); pg.goto(tmp.as_uri()); pg.wait_for_load_state("networkidle")
        pg.pdf(path=str(dst), format="A4", print_background=True, display_header_footer=True,
               header_template="<span></span>",
               footer_template='<div style="font:8px Arial;color:#5E5E5E;width:100%;padding:0 18mm;display:flex;justify-content:space-between">'
                               f'<span>{src.stem} · POC ICAT</span><span><span class="pageNumber"></span> / <span class="totalPages"></span></span></div>')
        b.close()
finally:
    tmp.unlink(missing_ok=True)
print(dst)
