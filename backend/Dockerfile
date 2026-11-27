# Imagen del backend (sirve también el frontend: templates/ + static/, ver app/main.py).
# El contexto de build es la raíz del repo, no backend/:
#   docker build -f backend/Dockerfile -t icat-backend .
#   docker run -p 8000:8000 --env-file backend/.env -v icat_storage:/app/storage icat-backend
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# libgomp1: lo carga onnxruntime, que llega con rapidocr (situar palabras en escaneos).
RUN apt-get update \
    && apt-get install -y --no-install-recommends libgomp1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY backend/pyproject.toml /app/backend/
COPY backend/app /app/backend/app
RUN pip install /app/backend

# Sin el modelo de spaCy, Presidio cae al fallback por regex y no detecta personas ni lugares.
RUN python -m spacy download es_core_news_md

# RAIZ en main.py es parents[2] de backend/app/main.py, o sea /app.
COPY templates /app/templates
COPY static /app/static

RUN useradd -m -u 10001 icat && mkdir -p /app/storage && chown icat /app/storage
USER icat
WORKDIR /app/backend

EXPOSE 8000
# /health responde 503 mientras no haya BD: el contenedor queda unhealthy, no se reinicia solo.
HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=3 \
    CMD python -c "import sys, urllib.request; sys.exit(urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=4).status != 200)"

# Un worker: la cola de OCR (0017) y el techo de intentos de login son por proceso.
# La BD, OLLAMA_URL y STORAGE_KEY se pasan por entorno; el original cifrado vive en /app/storage.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
