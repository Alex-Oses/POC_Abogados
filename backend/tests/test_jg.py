"""Extracción de datos de justicia gratuita en castellano y catalán (datos ficticios)."""

from app.services.jg import extraer


def test_nombre_e_ingresos_en_catalan_sin_irpf():
    datos = extraer({1: "Nom: Joan Prova Ficticia\nDNI 12345678Z", 2: "Ingressos: 9000 EUR"}, {})
    assert datos["solicitante"] == "Joan Prova Ficticia"
    assert datos["ingresos_anuales"] == 9000.0


def test_irpf_manda_sobre_la_linea_de_ingresos():
    textos = {1: "Ingresos: 1.000,00", 2: "Modelo 100\nBase imponible general 15.300,50"}
    assert extraer(textos, {2: "irpf"})["ingresos_anuales"] == 15300.5
