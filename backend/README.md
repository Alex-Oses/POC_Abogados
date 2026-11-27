# Backend

Python 3.12+ y FastAPI. Estructura de la decisión [[0014-stack-backend-c-sharp-java-python]] y del documento [[Estructura del backend (Python)]].

## Arrancar

```powershell
docker compose up -d db        # desde la raíz: PostgreSQL 16 con V1..V15 + views.sql (y la base icat_test)
#   Si el 5432 ya está ocupado (pasa en el servidor):
#   DB_PUERTO=5433 docker compose up -d db
#   y DATABASE_URL=postgresql://postgres:postgres@127.0.0.1:5433/icat
cd backend
python -m venv .venv
.venv\Scripts\python -m pip install -e ".[dev]"
.venv\Scripts\python -m spacy download es_core_news_md
Copy-Item .env.example .env   # rellena ADMIN_PASSWORD y STORAGE_KEY (ver comentario en el fichero)
.venv\Scripts\uvicorn app.main:app --reload   # API en /api/v1 y la app en http://127.0.0.1:8000/
```

`OCR_MOCK=1` prueba sin modelo (lee la capa de texto del PDF). Sin él hace falta Ollama con `hf.co/PaddlePaddle/PaddleOCR-VL-1.6-GGUF:latest`.

La base de datos la manda Flyway (`docs/architecture/migrations/`). Este backend no crea ni migra el esquema; `backend/db/init.sh` solo la monta para desarrollo. `triggers.sql` **no** se aplica: falla en PostgreSQL 16 (`sha256(text)`) y el backend ya mantiene `es_actual`, la numeración de versiones, el estado y la auditoría.

`GET /health` responde `503` mientras no haya base de datos; el resto de rutas también, salvo las que rechazan antes por falta de token (`401`).

## Todo en Docker (sin sudo)

Si no quieres depender del Python de la máquina (versión, venv, modelo de spaCy):

```bash
bash scripts/arrancar_docker.sh                 # desde la raíz: crea backend/.env si falta, construye y arranca BD + app
bash scripts/arrancar_docker.sh --sin-build     # siguiente vez, sin reconstruir
docker compose up -d --build                    # lo mismo a mano: sin banderas
docker compose down                             # parar (-v borra también la base de datos)
```

`backend/.env` se lee solo: el servicio `app` lo declara con `env_file` y `required: false`, así que `docker compose up -d` no necesita banderas y `docker compose up -d db` sigue funcionando aunque ese fichero no exista. Lo que no puede venir de ahí son `DATABASE_URL`, `OLLAMA_URL` y `STORAGE_DIR`, que el compose fija al valor de dentro del contenedor (y pisan lo que diga el fichero).

- La imagen `backend/Dockerfile` trae Python 3.12, Presidio, spaCy con `es_core_news_md`, RapidOCR y `pypdfium2`: el Python del host no se usa.
- Dentro del contenedor se fuerzan `DATABASE_URL` (`db:5432`), `OLLAMA_URL` (`host.docker.internal:11434`) y `STORAGE_DIR` (`/app/storage`, donde monta el volumen).
- Para otro Ollama: `OLLAMA_URL_DOCKER=http://mi-ollama:11434 bash scripts/arrancar_docker.sh`.
- Con Docker **rootless** (el de la VM) `host.docker.internal` no resuelve y el OCR acaba en «✕ Error d'OCR». Pon la IP privada de la máquina en el `.env` de la raíz: `OLLAMA_URL_DOCKER=http://10.0.0.4:11434` (compruébala antes con `curl http://10.0.0.4:11434/api/tags`).
- Un documento que falla no se pierde: en la bandeja sale **↻ Reintentar**, que lo devuelve a la cola conservando las páginas ya leídas. Volver a subir el mismo fichero hace lo mismo en vez de contestar «ya está».
- Si el 8000 está ocupado (por ejemplo, el servicio `icat-app` que deja `instalar_servidor.sh`): `APP_PUERTO=8010 bash scripts/arrancar_docker.sh`. El 5432, con `DB_PUERTO=5433`.
- No pide sudo: solo que el motor de Docker esté arrancado y que tu usuario pueda usarlo.

### Parar y liberar los puertos

```bash
docker compose down --remove-orphans   # para y borra app y BD: con ellos se van los puertos publicados
docker ps -a                           # no debe quedar ningún contenedor de icat
```

`down` es lo normal y no necesita sudo: al borrar los contenedores, Docker suelta el 8000/8010 y el 5432/5433. Si después de eso un puerto sigue ocupado (pasa con Docker rootless, cuyo gestor de puertos se queda colgado), mira quién lo tiene antes de tocar nada:

```bash
ss -ltn | grep -E ':(8000|8001|5432|5433)'          # qué está escuchando
docker ps -a --format '{{.Names}}\t{{.Ports}}'      # qué contenedor lo publica
docker rm -f <contenedor>                           # si es uno suelto de un `docker run` (down no lo quita)
systemctl --user restart docker                     # rootless: reinicia el motor y suelta los puertos huérfanos
```

### Puertos en el servidor compartido

En `genai-openllm-vm` el 5432 lo tiene otro PostgreSQL, el 8000 el servicio `icat-app` de systemd y el 8001 otro servicio. Sin tocar nada de los demás, la BD se publica en 5433 y la app en 8010:

```bash
cd ~/POC_Abogados
printf 'DB_PUERTO=5433\nAPP_PUERTO=8010\n' > .env   # .env de la raíz: lo lee docker compose
docker compose up -d
curl -s http://127.0.0.1:8010/health
```

Dentro de la red no cambia nada (`db:5432`, y el contenedor escuchando en su 8000): esos números son solo el puerto publicado en `127.0.0.1`. Quién ocupa qué y cómo comprobarlo, en [docs/GUIA_SERVIDOR.md](../docs/GUIA_SERVIDOR.md) §3 bis.

## Servidor (acceso desde fuera de la red)

Guía completa paso a paso: [docs/GUIA_SERVIDOR.md](../docs/GUIA_SERVIDOR.md).

En un Ubuntu 24.04 limpio, desde la carpeta donde vaya la app:

```bash
curl -fsSLO https://raw.githubusercontent.com/Alex-Oses/POC_Abogados/feat/backend-documentos/scripts/instalar_servidor.sh
DOMINIO=icat-poc.westeurope.cloudapp.azure.com DATABASE_URL=postgresql://usuario:clave@host-de-marina:5432/icat bash instalar_servidor.sh
```

- `DATABASE_URL` (opcional): la BD de Marina. Sin ella monta PostgreSQL 16 en Docker con V1..V15 + vistas. Antes de arrancar pasa `scripts/comprobar_bd.py` (tablas, columnas, versión y permisos).
- `DOMINIO` (recomendado): certificado real de Let's Encrypt. En Azure, la IP pública da un nombre gratis (Configuración > etiqueta DNS). Sin dominio usa un certificado propio y el navegador avisa.
- Abrir 80 y 443 en el grupo de seguridad de red (NSG) de Azure.
- Sin IA externa: OCR (Ollama, solo en 127.0.0.1), Presidio, spaCy y RapidOCR corren en el servidor. Las fuentes también se sirven desde él. Internet solo hace falta al instalar.
- Deja `arrancar.sh`, `parar.sh`, `actualizar.sh` y `logs.sh`. La app arranca sola al encender (systemd).
- **Si algo falla:** la instalación queda en `logs/instalacion-FECHA.log` y arrancar/parar/actualizar en `logs/manejo.log`. `bash diagnostico.sh` junta en `logs/diagnostico-FECHA.txt` sistema, servicios, salud, BD, Ollama, puertos y los últimos logs de la app y de Caddy, con claves y contraseñas tapadas. Ese es el fichero que hay que enviar. La contraseña del admin queda en `admin_password.txt`, nunca en los logs.
- Documentos de prueba ficticios: `backend/.venv/bin/python scripts/generar_pruebas.py` → `pruebas/`.

## Qué está implementado

- Fundación: configuración, errores con la forma del contrato, logs JSON con `request_id`, pool de `psycopg`, transacción por petición.
- Identidad local de desarrollo: `POST /user/login`, `POST /user/logout`, `GET /user/me`, `POST /user/password/change`.
- Administración: `GET /admin/users`, `PATCH /admin/users/{id}`, `DELETE /admin/users/{id}/sessions`.
- Auditoría encadenada por hash en la misma transacción que la acción.
- Semilla del admin de desarrollo por variables de entorno (U-21), nunca por endpoint. Lleva **los tres roles** (transcriptor, revisor y admin) y el arranque lo deja activo, para probar todo el flujo sin SSO.
- SSO en pausa: no hay rutas `auth/sso/*`; se retomará cuando el ICAT registre la aplicación OIDC.

- Documentos y OCR: original cifrado (Fernet), semáforo de contraste, doble lectura (A-24), progreso NDJSON, imagen de página, edición/validación y reescaneo de página.
- Anonimización con Presidio (`es_core_news_md`, configuración «mejorada» de `docs/presidio.md`) y seis formas.
- Revisión (cola, toma, cierre con `If-Match`, reapertura) y export PDF con ReportLab (0007), idempotente con hash.
- Justicia gratuita orientativa, búsqueda de texto completo, auditoría e informe mensual.
- Sirve el frontend (`templates/index.html` + `static/`) en `/`. Estado por ruta: `docs/api/endpoints.md` §11.

No están: SSO, `assign`, `sign-off` (A-15 en pausa), alta/edición de reglas y categorías, y `/config`.

## Pruebas

```powershell
.venv\Scripts\python -m pytest
```

Las pruebas de base de datos se saltan salvo que exista `DATABASE_TEST_URL` apuntando a un PostgreSQL con `V1`..`V15`:

```powershell
$env:DATABASE_TEST_URL="postgresql://postgres:postgres@127.0.0.1:5432/icat_test"
.venv\Scripts\python -m pytest
```
