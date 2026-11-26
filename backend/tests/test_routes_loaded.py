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
        "/api/v1/documents/{documento_id}/versions/{numero}",
        "/api/v1/documents/{documento_id}/versions/{numero}/blocks",
        "/api/v1/documents/{documento_id}/anonymize",
        "/api/v1/documents/{documento_id}/annotations",
        "/api/v1/annotations/{anotacion_id}",
        "/api/v1/reviews",
        "/api/v1/documents/{documento_id}/reviews",
        "/api/v1/reviews/{revision_id}/claim",
        "/api/v1/reviews/{revision_id}",
        "/api/v1/documents/{documento_id}/reopen",
        "/api/v1/documents/{documento_id}/export",
        "/api/v1/rules",
        "/api/v1/categories",
        "/api/v1/audit",
    }
    assert esperadas.issubset(rutas)

