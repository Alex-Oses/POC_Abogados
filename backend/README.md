# Backend

Python 3.12+ y FastAPI. Estructura de la decisión [[0014-stack-backend-c-sharp-java-python]] y del documento [[Estructura del backend (Python)]].

## Arrancar

```powershell
cd backend
python -m venv .venv
.venv\Scripts\python -m pip install -e ".[dev]"
Copy-Item .env.example .env   # ajusta DATABASE_URL y el admin de desarrollo
.venv\Scripts\uvicorn app.main:app --reload
```

La base de datos la manda Flyway (`docs/architecture/migrations/`). Este backend no crea ni migra el esquema.

`GET /health` responde `503` mientras no haya base de datos; el resto de rutas también, salvo las que rechazan antes por falta de token (`401`).

## Qué está implementado

- Fundación: configuración, errores con la forma del contrato, logs JSON con `request_id`, pool de `psycopg`, transacción por petición.
- Identidad local de desarrollo: `POST /user/login`, `POST /user/logout`, `GET /user/me`, `POST /user/password/change`.
- Administración: `GET /admin/users`, `PATCH /admin/users/{id}`, `DELETE /admin/users/{id}/sessions`.
- Auditoría encadenada por hash en la misma transacción que la acción.
- Semilla del admin de desarrollo por variables de entorno (U-21), nunca por endpoint. Lleva **los tres roles** (transcriptor, revisor y admin) y el arranque lo deja activo, para probar todo el flujo sin SSO.
- Documentos y OCR (`POST /transform/document`, `POST /transform/plain-text`, `POST /transform/build`, `GET/DELETE /documents`, `/pages`, `/original`, `/versions`, `/blocks`).
- Anonimización (`POST /documents/{id}/anonymize`, `GET /documents/{id}/annotations`, `PATCH /annotations/{id}`).
- Revisión y aprobación (`GET /reviews`, `POST /documents/{id}/reviews`, `claim`, `assign`, `PATCH /reviews/{id}`, `reopen`, `sign-off`).
- Exportación PDF determinista sin píxeles del original (`POST /documents/{id}/export`).
- Reglas, categorías, auditoría y configuración (`GET/POST/PATCH /rules`, `/categories`, `GET /audit`, `GET/PUT /config/{clave}`).
- SSO en pausa: no hay rutas `auth/sso/*`; se retomará cuando el ICAT registre la aplicación OIDC.

Queda pendiente de integración externa: conectar `app/integrations/etl.py` al servicio real de PaddleOCR-VL / Presidio y añadir `reportlab` si se requiere layout avanzado.

## Pruebas

```powershell
.venv\Scripts\python -m pytest
```

Las pruebas de base de datos se saltan salvo que exista `DATABASE_TEST_URL` apuntando a un PostgreSQL con `V1`..`V15`:

```powershell
$env:DATABASE_TEST_URL="postgresql://postgres:postgres@localhost:5432/icat_test"
.venv\Scripts\python -m pytest
```
