from app.integrations.pdf import aplicar_sustituciones_bloque, generar_pdf_bytes
from app.main import app


def test_rutas_v1_registradas():
    rutas = set(app.openapi()["paths"].keys())
    esperadas = {
        "/health",
        "/api/v1/user/login",
        "/api/v1/admin/users",
        "/api/v1/transform/document",
        "/api/v1/transform/plain-text",
        "/api/v1/transform/build",
        "/api/v1/documents",
        "/api/v1/documents/{documento_id}",
        "/api/v1/documents/{documento_id}/pages",
        "/api/v1/documents/{documento_id}/original",
        "/api/v1/documents/{documento_id}/versions",
        "/api/v1/documents/{documento_id}/versions/{numero_version}",
        "/api/v1/documents/{documento_id}/versions/{numero_version}/blocks",
        "/api/v1/documents/{documento_id}/anonymize",
        "/api/v1/documents/{documento_id}/annotations",
        "/api/v1/annotations/{anotacion_id}",
        "/api/v1/reviews",
        "/api/v1/documents/{documento_id}/reviews",
        "/api/v1/reviews/{revision_id}/claim",
        "/api/v1/reviews/{revision_id}/assign",
        "/api/v1/reviews/{revision_id}",
        "/api/v1/documents/{documento_id}/reopen",
        "/api/v1/documents/{documento_id}/sign-off",
        "/api/v1/documents/{documento_id}/export",
        "/api/v1/rules",
        "/api/v1/rules/{regla_id}",
        "/api/v1/categories",
        "/api/v1/categories/{categoria_id}",
        "/api/v1/audit",
        "/api/v1/config",
        "/api/v1/config/{clave}",
    }
    assert esperadas.issubset(rutas)


def test_sustituciones_bloque_y_pdf():
    texto = "Juan Pérez con DNI 12345678A"
    anotaciones = [
        {"inicio": 0, "fin": 10, "estado": "aceptada", "texto_sustitucion": "[NOMBRE]"},
        {"inicio": 19, "fin": 28, "estado": "falso_negativo", "texto_sustitucion": "[DNI]"},
    ]
    resultado = aplicar_sustituciones_bloque(texto, anotaciones)
    assert resultado == "[NOMBRE] con DNI [DNI]"
    pdf = generar_pdf_bytes([{"texto_final": resultado}], modo="layout")
    assert pdf.startswith(b"%PDF-")
