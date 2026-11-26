from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.api.v1 import auth, users
from app.core.logging import log, setup_logging
from app.db.pool import pool, tx
from app.middleware import audit
from app.middleware import auth as auth_middleware
from app.middleware.handler_error import install as install_error_handlers
from app.services.users import sembrar_admin


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    app.state.bd_disponible = False
    try:
        pool.open(wait=True, timeout=5)
        app.state.bd_disponible = True
    except Exception as error:  # noqa: BLE001 - el servicio arranca degradado y /health lo dice
        log.error("bd_no_disponible", extra={"detalle": str(error).splitlines()[0]})

    if app.state.bd_disponible:
        try:
            with tx() as conexion:
                sembrar_admin(conexion)
        except Exception:  # noqa: BLE001 - sin semilla se sigue; el fallo queda en el log
            log.exception("semilla_admin_fallida")

    yield
    pool.close()


app = FastAPI(title="ICAT · API", version="0.1.0", lifespan=lifespan)
app.add_middleware(auth_middleware.IdentificarToken)
app.add_middleware(audit.RegistroPeticiones)
install_error_handlers(app)

app.include_router(auth.router, prefix="/api/v1")
app.include_router(users.router, prefix="/api/v1")


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
