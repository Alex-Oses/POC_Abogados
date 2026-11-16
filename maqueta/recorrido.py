"""Recorre la maqueta como un usuario, guarda capturas y falla si hay errores de JS."""
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright

url = Path(sys.argv[1]).resolve().as_uri()
out = Path(sys.argv[2]); out.mkdir(exist_ok=True)
errors = []

with sync_playwright() as p:
    b = p.chromium.launch(channel="msedge", headless=True)
    pg = b.new_page(viewport={"width": 1440, "height": 1000})
    pg.on("pageerror", lambda e: errors.append(str(e)))
    shot = lambda n: pg.screenshot(path=str(out / f"{n}.png"))

    pg.goto(url); shot("01-login")
    pg.click("text=Accedir amb el compte del Col·legi"); shot("02-safata")
    pg.click("#nou"); pg.wait_for_timeout(700); shot("03-processant")
    pg.wait_for_selector("text=Obrir revisió", timeout=15000); shot("04-processat")
    pg.click("text=Obrir revisió")
    assert pg.is_disabled("#val"), "validar debería estar bloqueado con avisos"
    for k in ("num", "dni"):
        pg.hover(f"[data-w={k}]")
        assert pg.is_visible(f"[data-wi={k}].on"), f"la imagen debería marcar «{k}»"
    shot("05a-revisio-marca-imatge")
    pg.click("[data-w=num]"); shot("05-revisio-dues-lectures")
    pg.click("#pop .btn.pri")
    pg.click("[data-w=dni]"); pg.click("#pop .btn.pri")
    pg.click("[data-w=iban]"); pg.click("#pop .btn.pri")
    assert pg.is_enabled("#val"); pg.click("#val")
    pg.click("[data-w=liq]"); pg.click("#pop .btn.pri"); pg.click("#val")
    assert "22" in pg.inner_text(".card.row"), "debería saltar a la pág. 22"
    shot("06-revisio-ilegible"); pg.click("#esc")
    pg.wait_for_selector("text=Comprovar documentació"); shot("07-revisio-acabada")
    pg.click("text=Comprovar documentació"); shot("08-jg")
    pg.click("#dem"); shot("09-jg-requeriment"); pg.click("#ms")
    pg.click("#env"); pg.click("text=Següent: anonimitzar una resolució"); shot("10-anonimitzar-censura")
    pg.hover(".ent >> nth=1"); shot("11-anonimitzar-fitxa")
    pg.click("[data-m=etiqueta]"); shot("12-anonimitzar-etiqueta")
    pg.click("[data-m=pseudonim]"); shot("13-anonimitzar-pseudonim")
    pg.click("[data-c=matricula]"); pg.click(".ent >> nth=1", modifiers=["Shift"])
    pg.click("#expan"); assert pg.is_disabled("#ex"); pg.check("#cf"); shot("14-confirmar")
    pg.click("#ex"); pg.wait_for_selector("text=Registre d'auditoria"); shot("15-exportat")
    pg.click("[data-lang=es]"); shot("16-exportat-es")
    pg.goto(url + "#arxiu"); pg.fill("#q", "sentència"); shot("17-arxiu-cerca")
    b.close()

print("errores JS:", errors or "ninguno")
sys.exit(1 if errors else 0)
