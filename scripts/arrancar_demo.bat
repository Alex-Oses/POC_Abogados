@echo off
rem Desarrollo local en Windows con un clic: PostgreSQL (Docker), Ollama + modelo, backend FastAPI y navegador.
rem Uso: doble clic. Para probar sin modelo de OCR: arrancar_demo.bat mock
chcp 65001 >nul
setlocal
cd /d "%~dp0.."
set ROOT=%CD%
set MODEL=hf.co/PaddlePaddle/PaddleOCR-VL-1.6-GGUF:latest
set PORT=8000

where python >nul 2>&1 || (echo Falta Python 3.12: https://www.python.org/downloads/ & pause & exit /b 1)
where docker >nul 2>&1 || (echo Falta Docker Desktop: https://www.docker.com/products/docker-desktop/ & pause & exit /b 1)

rem 1. Docker Desktop en marcha
docker info >nul 2>&1
if errorlevel 1 (
    echo Arrancando Docker Desktop...
    if exist "%ProgramFiles%\Docker\Docker\Docker Desktop.exe" start "" "%ProgramFiles%\Docker\Docker\Docker Desktop.exe"
    for /l %%i in (1,1,60) do (
        docker info >nul 2>&1 && goto docker_ok
        timeout /t 3 >nul
    )
    echo Docker no responde. Abre Docker Desktop y vuelve a intentarlo. & pause & exit /b 1
)
:docker_ok

rem 2. Base de datos y espera a que acepte conexiones
docker compose up -d db || (echo No se pudo arrancar la base de datos & pause & exit /b 1)
echo Esperando a PostgreSQL...
for /l %%i in (1,1,60) do (
    docker compose exec -T db pg_isready -U postgres -d icat >nul 2>&1 && goto db_ok
    timeout /t 2 >nul
)
echo PostgreSQL no responde. & pause & exit /b 1
:db_ok

rem 3. OCR: modelo en Ollama local, o simulado con "mock"
if /i "%1"=="mock" (
    set OCR_MOCK=1
    echo Modo prueba: OCR simulado, sin Ollama.
) else (
    set OCR_MOCK=0
    where ollama >nul 2>&1 || (echo Falta Ollama: https://ollama.com/download & pause & exit /b 1)
    curl -s http://localhost:11434/api/tags >nul 2>&1 || (start "Ollama" /min ollama serve & timeout /t 3 >nul)
    ollama list | findstr /i "PaddleOCR-VL-1.6" >nul || ollama pull %MODEL%
)

rem 4. Entorno de Python del backend (solo la primera vez)
cd /d "%ROOT%\backend"
if not exist ".venv\Scripts\python.exe" (
    echo Creando el entorno de Python, tarda unos minutos la primera vez...
    python -m venv .venv || (pause & exit /b 1)
    .venv\Scripts\python -m pip install --quiet --upgrade pip
    .venv\Scripts\python -m pip install -e ".[dev]" || (pause & exit /b 1)
)
.venv\Scripts\python -c "import es_core_news_md" >nul 2>&1 || .venv\Scripts\python -m spacy download es_core_news_md

rem 5. backend\.env con secretos aleatorios (nunca se sube al repo)
if not exist ".env" (
    echo Creando backend\.env con claves nuevas...
    .venv\Scripts\python -c "import re,secrets;from cryptography.fernet import Fernet;s=open('.env.example',encoding='utf-8').read();s=re.sub(r'(?m)^ADMIN_PASSWORD=.*$','ADMIN_PASSWORD='+secrets.token_urlsafe(12),s);s=re.sub(r'(?m)^STORAGE_KEY=.*$','STORAGE_KEY='+Fernet.generate_key().decode(),s);open('.env','w',encoding='utf-8').write(s)" || (pause & exit /b 1)
)

echo.
echo ==================================================
echo  App: http://127.0.0.1:%PORT%/
for /f "tokens=1,* delims==" %%a in ('findstr /b "ADMIN_EMAIL= ADMIN_PASSWORD=" .env') do echo  %%a: %%b
echo  OCR_MOCK=%OCR_MOCK%
echo ==================================================
echo.

rem 6. Navegador y servidor (OCR_MOCK del entorno manda sobre el de .env)
start "" cmd /c "timeout /t 4 >nul & start http://127.0.0.1:%PORT%/"
.venv\Scripts\python -m uvicorn app.main:app --host 127.0.0.1 --port %PORT%
pause
