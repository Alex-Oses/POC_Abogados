"""Marcado del PDF final (sin BD): un solape no puede dejar texto original a la vista (A-09)."""

from app.services.export import marcar


def _anotacion(inicio, fin, accion="censurar", decision="confirmado", sust=None):
    return {"inicio_offset": inicio, "fin_offset": fin, "accion_aplicada": accion,
            "decision_revisor": decision, "texto_sustitucion": sust}


def test_sin_solape_marca_cada_tramo():
    marcado, tachado = marcar("Juan 12345678Z fin", [_anotacion(5, 14)])
    assert "12345678Z" not in marcado and not tachado
    assert "Juan" in marcado and "fin" in marcado


def test_solape_no_deja_texto_a_la_vista():
    contenido = "DNI 12345678Z de Juan"
    marcado, _ = marcar(contenido, [_anotacion(4, 13), _anotacion(9, 16)])
    # El segundo tramo se recorta al resto, no se descarta: toda la unión queda tapada.
    assert "12345678Z" not in marcado and " de " not in marcado
    assert "Juan" in marcado


def test_mantenido_no_tapa_la_siguiente():
    marcado, _ = marcar("Juan 12345678Z fin", [_anotacion(0, 4, "mantenido"), _anotacion(5, 14)])
    assert "Juan" in marcado and "12345678Z" not in marcado


def test_tachar_marca_el_aviso():
    marcado, tachado = marcar("Juan 12345678Z", [_anotacion(5, 14, "tachado")])
    assert tachado and "12345678Z" in marcado  # tachar conserva el texto: solo es para revisar
