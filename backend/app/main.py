from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.api.v1 import auth, catalog, documents, reviews, users
from app.core.logging import log, setup_logging
from app.db import pool as bd
from app.db.pool import tx
from app.middleware import audit
from app.middleware import auth as auth_middleware
from app.middleware.handler_error import install as install_error_handlers
from app.services import cola, sharepoint
from app.services.users import sembrar_admin


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    app.state.bd_disponible = False
    try:
        bd.abrir()
        app.state.bd_disponible = True
    except Exception as error:  # noqa: BLE001 - el servicio arranca degradado y /health lo dice
        log.error("bd_no_disponible", extra={"detalle": str(error).splitlines()[0]})

    if app.state.bd_disponible:
        try:
            with tx() as conexion:
                sembrar_admin(conexion)
        except Exception:  # noqa: BLE001 - sin semilla se sigue; el fallo queda en el log
            log.exception("semilla_admin_fallida")

        try:
            cola.arrancar()  # 0017: OCR en segundo plano; reanuda lo que quedó a medias
        except Exception:  # noqa: BLE001 - sin cola la API sigue; el fallo queda en el log
            log.exception("cola_ocr_no_arranca")
        sharepoint.arrancar()  # solo si SHAREPOINT_* está configurado

    yield
    sharepoint.detener()
    cola.detener()
    bd.cerrar()


app = FastAPI(title="ICAT · API", version="0.1.0", lifespan=lifespan)
app.add_middleware(auth_middleware.IdentificarToken)
app.add_middleware(audit.RegistroPeticiones)
install_error_handlers(app)

app.include_router(auth.router, prefix="/api/v1")
app.include_router(users.router, prefix="/api/v1")
app.include_router(documents.router, prefix="/api/v1")
app.include_router(reviews.router, prefix="/api/v1")
app.include_router(catalog.router, prefix="/api/v1")

# Frontend en el mismo proceso: `/` sirve templates/index.html y `/static` sus ficheros.
RAIZ = Path(__file__).resolve().parents[2]
if (RAIZ / "static").is_dir():
    app.mount("/static", StaticFiles(directory=RAIZ / "static"), name="static")


@app.get("/", include_in_schema=False)
def inicio():
    return FileResponse(RAIZ / "templates" / "index.html")


@app.get("/health", tags=["operación"])
def health(request: Request):
    if not getattr(request.app.state, "bd_disponible", False):
        return JSONResponse(status_code=503, content={"estado": "degradado", "bd": False})
    try:
        with tx() as conexion:
            conexion.execute("SELECT 1")
    except Exception:  # noqa: BLE001 - cualquier fallo de BD es "degradado" en /health
        return JSONResponse(status_code=503, content={"estado": "degradado", "bd": False})
    return {"estado": "ok", "bd": True}
