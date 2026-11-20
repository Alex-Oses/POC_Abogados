# Estructura del backend

- **Para**: entrega del 27/11/2026 (ver [[Equipo]])
- **Estado**: **borrador** · 20/11/2026 · se edita en este mismo fichero
- **Autor**: @ia-opencode-ruben
- **Qué es**: dónde vive cada cosa en el backend y qué imports se prevén. El *por qué* del stack está en [[Enfoque tecnico]]; el contrato, en [`docs/api/endpoints.md`](../../docs/api/endpoints.md).

## 1. Regla de frontera

El backend **no hace OCR, ni anonimiza, ni compone el PDF** ([[Enfoque tecnico]] §2). Por eso no hay `modules/OCR` ni `modules/Anonimize`: hay un cliente HTTP en `integrations/etl.py`. Si algún día el OCR entra en el backend, entra en `jobs/`, no en un módulo nuevo.

## 2. Árbol

```
backend/
  pyproject.toml
  .env.example
  app/
    main.py                   # crea FastAPI, monta routers, middleware y handlers
    core/
      config.py               # pydantic-settings: BD, rutas del ETL, límites
      errors.py               # AppError + código HTTP + payload de error
      security.py             # token opaco, hash, fechas de sesión
      logging.py              # logs sin payloads: ni un nombre ni un DNI
    db/
      pool.py                 # ConnectionPool de psycopg + tx()
      tables.py               # Table(...) de lo que se consulta con Core
      queries/                # .sql con nombre: vistas, informes, colas
        __init__.py
        documents.sql
        review.sql
        reports.sql
    middleware/
      auth.py                 # lee el token, no decide permisos
      audit.py                # request_id + una línea de log por petición
      limit_rate.py           # techo por IP y ventana; en memoria
      handler_error.py        # registra los exception handlers (no es middleware)
    api/
      deps.py                 # transacción, usuario actual, require_role()
      v1/
        auth.py  users.py  documents.py  review.py
        anonymize.py  export.py  rules.py  admin.py
    services/                 # lógica + transacción, uno por dominio
      auth.py  users.py  documents.py  review.py
      anonymize.py  export.py  rules.py  admin.py
    schemas/                  # Pydantic: entrada y salida, nada más
      common.py  auth.py  users.py  documents.py  review.py  export.py
    integrations/
      etl.py                  # cliente del ETL/Ollama (OCR, Presidio)
      storage.py              # originales y PDF en disco, con ruta y hash
    jobs/
      ocr.py                  # Cuando I5 se cierre: OCR por página en segundo plano
      pdf.py
  tests/
    conftest.py               # PostgreSQL real + un usuario por rol
    test_documents.py  test_review.py  test_export.py
```

Reglas de forma:

- **Síncrono**: los handlers son `def`, no `async def`. FastAPI los corre en un pool de hilos y las tres piezas caras (psycopg, Presidio, reportlab) son bloqueantes. Se pasa a `async` el día que el OCR sea por página y exista `jobs/`.
- **Una petición, una transacción**: la abre `api/deps.py` y la cierra el handler. Los servicios reciben la conexión, no la crean.
- **`services/` separado** de `api/`: el router valida y delega; el servicio hace la consulta y decide.
- **`middleware/auth.py` solo identifica** (deja el token en `request.state`). Quién puede qué se decide en `deps.require_role()`, porque necesita el rol por ruta y distinguir 403 de 404. Un middleware que autorice acaba con una lista de rutas exentas que nadie mantiene.
- **`middleware/handler_error.py` no es middleware**: expone una función `install(app)` que registra `app.add_exception_handler`.
- **`db/tables.py` es deuda consciente**: Flyway manda, así que si cambia una columna hay que tocar el `Table` a mano. Por eso solo entran ahí las tablas que se consultan con Core ([[0013-consultas-sql-o-sqlalchemy-core]]).

## 3. Imports previstos

Solo lo que se usará de verdad; nada de «por si acaso».

### `app/main.py`

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI

from app.api.v1 import admin, anonymize, auth, documents, export, review, rules, users
from app.core.config import settings
from app.core.logging import setup_logging
from app.db.pool import pool
from app.middleware import audit, auth as auth_middleware, limit_rate
from app.middleware.handler_error import install as install_error_handlers
```

### `app/core/config.py`

```python
from functools import lru_cache
from pydantic import AnyHttpUrl, PostgresDsn
from pydantic_settings import BaseSettings, SettingsConfigDict
```

### `app/core/errors.py`

```python
from dataclasses import dataclass, field
from typing import Any
```

### `app/core/security.py`

```python
import hashlib
import secrets
from datetime import datetime, timedelta, timezone
```

### `app/core/logging.py`

```python
import json
import logging
import sys
import uuid
from contextvars import ContextVar
```

### `app/db/pool.py`

```python
from contextlib import contextmanager
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

from app.core.config import settings
```

### `app/db/tables.py`

```python
from sqlalchemy import Column, MetaData, Table
from sqlalchemy.dialects.postgresql import JSONB, UUID
```

### `app/db/queries/__init__.py`

```python
from pathlib import Path

SQL = {p.stem: p.read_text(encoding="utf-8") for p in Path(__file__).parent.glob("*.sql")}
```

### `app/middleware/auth.py`

```python
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
```

### `app/middleware/audit.py`

```python
from time import perf_counter
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from app.core.logging import log, request_id
```

### `app/middleware/limit_rate.py`

```python
from collections import defaultdict, deque
from time import monotonic
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
```

### `app/middleware/handler_error.py`

```python
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from psycopg import errors as pg_errors

from app.core.errors import AppError
from app.core.logging import log
```

### `app/api/deps.py`

```python
from fastapi import Depends, Request

from app.core.errors import AppError
from app.db.pool import tx
from app.services import auth as auth_service
```

### `app/api/v1/documents.py`

```python
from uuid import UUID
from fastapi import APIRouter, Depends, Query, UploadFile, status

from app.api.deps import current_user, require_role, connection
from app.schemas.documents import DocumentList, DocumentOut
from app.services import documents as service
```

### `app/services/documents.py`

```python
from datetime import datetime, timezone
from uuid import UUID

from psycopg import Connection
from sqlalchemy import select

from app.core.errors import AppError
from app.db import tables
from app.db.queries import SQL
```

### `app/schemas/documents.py`

```python
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field
```

### `app/integrations/etl.py`

```python
import httpx

from app.core.config import settings
```

### `app/integrations/storage.py`

```python
import hashlib
from pathlib import Path
from uuid import UUID

from app.core.config import settings
```

### `app/jobs/ocr.py`

```python
from uuid import UUID

from app.db.pool import tx
from app.integrations.etl import ocr_page
```

### `tests/conftest.py`

```python
import pytest
from fastapi.testclient import TestClient
from psycopg import connect

from app.core.config import settings
from app.main import app
```

### `pyproject.toml`

```toml
dependencies = [
  "fastapi", "uvicorn[standard]", "pydantic", "pydantic-settings",
  "psycopg[binary,pool]", "sqlalchemy", "httpx",
]
[dependency-groups]
dev = ["pytest", "ruff"]
```

## 4. Lo que no hay

| Carpeta o capa | Por qué no |
|---|---|
| `controllers/` | Los routers son los controladores y ya viven en `api/v1/` |
| `data/` | Se llama `db/`, que es lo que es |
| `repositories/` | Con una sola BD y ~20 consultas solo traduce nombres |
| `validators/` | Pydantic valida en la frontera; lo que necesita BD es una regla de `services/` |
| `properties/` | Vocabulario de C#; en Python no existe |
| `dto/` | Se llama `schemas/` (Pydantic) |
| `modules/OCR`, `modules/Anonimize` | ETL, no backend |
| `cache/` o TTL | La verdad está en la BD; se añade si se mide que hace falta |
| Un fichero por endpoint (40 carpetas) | Se parte por dominio, y solo `documents` tiene volumen para subcarpetas |

## 5. Pendiente

- [[0013-consultas-sql-o-sqlalchemy-core]]: si es SQL directo, desaparecen `sqlalchemy` y `db/tables.py`.
- `middleware/limit_rate.py` es por proceso: con más de un worker de Uvicorn, cada uno lleva su cuenta. Con un worker sobra.
- Los *jobs* de `jobs/` dependen de que se cierre el OCR por página ([[Tablero]]).
