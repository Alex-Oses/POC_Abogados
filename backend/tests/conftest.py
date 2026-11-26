import os

# Debe fijarse antes de importar `app`: la configuración se lee al importar.
if os.getenv("DATABASE_TEST_URL"):
    os.environ["DATABASE_URL"] = os.environ["DATABASE_TEST_URL"]
# Las pruebas nunca llaman al modelo: el OCR simulado lee la capa de texto del PDF.
os.environ["OCR_MOCK"] = "1"
