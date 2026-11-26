@echo off
rem Arranca la demo de OCR con un clic: Ollama + modelo, la app Flask (frontend y OCR) y el navegador.
rem Uso: doble clic. Para probar sin modelo: arrancar_demo.bat mock
chcp 65001 >nul
cd /d "%~dp0.."
set MODEL=hf.co/PaddlePaddle/PaddleOCR-VL-1.6-GGUF:latest

where python >nul 2>&1 || (echo Falta Python 3.12: https://www.python.org/downloads/ & pause & exit /b 1)
python -m pip install --quiet flask pymupdf pillow

if /i "%1"=="mock" (
    set OCR_MOCK=1
    echo Modo prueba: OCR simulado, sin Ollama.
) else (
    where ollama >nul 2>&1 || (echo Falta Ollama: https://ollama.com/download & pause & exit /b 1)
    rem Si Ollama no responde, se arranca en segundo plano
    curl -s http://localhost:11434/api/tags >nul 2>&1 || (start "Ollama" /min ollama serve & timeout /t 3 >nul)
    ollama list | findstr /i "PaddleOCR-VL-1.6" >nul || ollama pull %MODEL%
)

start "" http://127.0.0.1:5000
python ocr_web_app.py
pause
