from app.services.presidio import CATEGORIAS_ANONIMIZACION, detectar_entidades_presidio


def test_categorias_iniciales_presidio() -> None:
    assert set(CATEGORIAS_ANONIMIZACION.keys()) == {
        "PERSON",
        "DNI_NIE",
        "EMAIL_ADDRESS",
        "PHONE_NUMBER",
        "LOCATION",
        "IBAN_CODE",
    }


def test_detectar_entidades_presidio_basico() -> None:
    texto = (
        "Contacto: 12345678Z, correo prueba@icat.cat, "
        "teléfono 612345678, IBAN ES9121000418450200051332."
    )
    entidades = detectar_entidades_presidio(texto)
    tipos = {e["tipo"] for e in entidades}
    assert {"DNI_NIE", "EMAIL_ADDRESS", "PHONE_NUMBER", "IBAN_CODE"}.issubset(tipos)
