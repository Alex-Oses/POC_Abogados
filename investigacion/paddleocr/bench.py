"""Mini benchmark de PaddleOCR-VL vía Ollama: s/página secuencial y en paralelo.

Uso: python bench.py pagina1.png pagina2.jpg ... [--model TAG] [--paralelo 4]
Imprime una fila Markdown para pegar en vault/Proyecto/Rendimiento OCR.md.
Requiere Ollama arrancado con OLLAMA_NUM_PARALLEL >= --paralelo.
"""
import argparse, base64, json, os, platform, subprocess, time, urllib.request
from concurrent.futures import ThreadPoolExecutor

URL = os.environ.get("OLLAMA_HOST", "http://localhost:11434").rstrip("/")


def api(path, body=None):
    req = urllib.request.Request(URL + path, json.dumps(body).encode() if body else None,
                                 {"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=600) as r:
        return json.load(r)


def ocr(model, img):
    # Misma configuración que la recomendada en Rendimiento OCR.md
    r = api("/api/generate", {"model": model, "prompt": "OCR:", "images": [img], "stream": False,
                              "options": {"temperature": 0, "num_ctx": 4096,
                                          "repeat_penalty": 1.05, "num_predict": 1500}})
    assert r["response"].strip(), "respuesta vacía del modelo"


def gpu():
    try:
        return subprocess.run(["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader"],
                              capture_output=True, text=True, check=True).stdout.strip().replace("\n", " + ")
    except (OSError, subprocess.CalledProcessError):
        return "sin GPU NVIDIA"


def main():
    p = argparse.ArgumentParser()
    p.add_argument("paginas", nargs="+")
    p.add_argument("--model")
    p.add_argument("--paralelo", type=int, default=4)
    a = p.parse_args()
    model = a.model or next(m["name"] for m in api("/api/tags")["models"] if "paddle" in m["name"].lower())
    imgs = [base64.b64encode(open(f, "rb").read()).decode() for f in a.paginas]

    ocr(model, imgs[0])  # calentamiento: carga el modelo en memoria
    t = time.perf_counter()
    for i in imgs:
        ocr(model, i)
    seq = (time.perf_counter() - t) / len(imgs)

    t = time.perf_counter()
    with ThreadPoolExecutor(a.paralelo) as ex:
        list(ex.map(lambda i: ocr(model, i), imgs))
    par = (time.perf_counter() - t) / len(imgs)

    print(f"Modelo {model} · {len(imgs)} páginas\n")
    print(f"| Equipo | CPU | GPU | s/pág (1 a la vez) | s/pág ({a.paralelo} en paralelo) | pág/hora |")
    print("|---|---|---|---|---|---|")
    print(f"| {platform.node()} | {platform.processor() or platform.machine()} | {gpu()} "
          f"| {seq:.1f} | {par:.1f} | {3600 / par:,.0f} |")


if __name__ == "__main__":
    main()
