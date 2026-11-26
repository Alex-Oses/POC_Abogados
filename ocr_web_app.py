"""Mini aplicación web de OCR con PaddleOCR-VL 1.6 y Ollama.

Permite subir un PDF, procesando cada página individualmente a la API de Ollama
y obteniendo la transcripción texto con tiempos y rendimiento estimado.

Características:
- Procesa TODAS las páginas del PDF (sin límite fijo de 20)
- Transmite el progreso en NDJSON: una línea por página terminada
- Muestra la página y su texto en paralelo, con el texto editable
- Modo doble lectura: dos pasadas por página y lo que no coincide se marca
- Muestra estadísticas finales (tiempo total, promedio, rendimiento)
"""

import json
import base64
import difflib
import time
import os
import re
import sys
import glob
import uuid
from flask import Flask, render_template, request, jsonify, Response, stream_with_context, send_file

# Carpeta de este fichero: sirve en cualquier máquina
repo = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, repo)
MOCK = os.environ.get('OCR_MOCK') == '1'
MIN_CONTRAST = 80

app = Flask(__name__)

model = 'hf.co/PaddlePaddle/PaddleOCR-VL-1.6-GGUF:latest'
URL = 'http://localhost:11434'

# Directorio para imágenes temporales de páginas PDF
TEST_PDF_IMAGES = os.path.join(repo, 'test_pdf_images_web')
os.makedirs(TEST_PDF_IMAGES, exist_ok=True)
# Páginas de la subida actual: se muestran en el navegador mientras se transcriben
PAGES_DIR = os.path.join(TEST_PDF_IMAGES, 'pages')
os.makedirs(PAGES_DIR, exist_ok=True)


def ocr_single_img(img_path, temperature=0):
    """Una llamada OCR a la API de Ollama para una imagen."""
    if MOCK:
        # Texto falso para probar sin modelo; con temperatura cambia palabras
        time.sleep(0.5)
        text = ('Don Juan Pérez García, con DNI 12345678A y domicilio en Barcelona, '
                'solicita justicia gratuita. IBAN ES91 2100 0418 4502 0005 1332.')
        if temperature > 0:
            text = text.replace('domicilio', 'domicilo').replace('solicita', 'solicito')
        return 0.5, text
    try:
        with open(img_path, 'rb') as f:
            img_b64 = base64.b64encode(f.read()).decode()
        body = {
            'model': model,
            'prompt': 'OCR:',
            'images': [img_b64],
            'stream': False,
            'options': {'temperature': temperature, 'num_ctx': 4096, 'repeat_penalty': 1.05, 'num_predict': 1500}
        }
        start = time.time()
        import urllib.request
        req = urllib.request.Request(URL + '/api/generate', 
                                     json.dumps(body).encode(), 
                                     {'Content-Type': 'application/json'})
        with urllib.request.urlopen(req, timeout=300) as r:
            resp = json.loads(r.read())
        elapsed = time.time() - start
        text = resp.get('response', '').strip()
        return elapsed, text
    except Exception as e:
        return 0, f"Error: {str(e)}"


def find_rects(pdf_path, page_number, candidates_list):
    """Cajas normalizadas (0-1) de cada palabra en la capa de texto del PDF.

    Solo funciona con PDFs que tienen texto seleccionable; en un escaneo no
    hay capa de texto y devuelve None para todas.
    """
    try:
        import fitz
        doc = fitz.open(pdf_path)
        page = doc[page_number - 1]
        width, height = page.rect.width, page.rect.height
        out = []
        for candidates in candidates_list:
            rect = None
            for candidate in candidates:
                if not candidate:
                    continue
                hits = page.search_for(candidate)
                if hits:
                    rect = hits[0]
                    break
            if rect is None or not width or not height:
                out.append(None)
            else:
                out.append([round(rect.x0 / width, 4), round(rect.y0 / height, 4),
                            round(rect.x1 / width, 4), round(rect.y1 / height, 4)])
        doc.close()
        return out
    except Exception:
        return [None] * len(candidates_list)


def diff_segments(a, b):
    """Parte el primer texto en trozos y marca los que no coinciden con la segunda lectura."""
    ta = re.findall(r'\S+\s*', a)
    tb = re.findall(r'\S+\s*', b)
    # Se comparan las palabras sin el espacio que las sigue: un salto de línea
    # distinto no es una duda del OCR.
    ka = [t.strip() for t in ta]
    kb = [t.strip() for t in tb]
    merged = []
    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(a=ka, b=kb).get_opcodes():
        t = ''.join(ta[i1:i2])
        other = '' if tag == 'equal' else ' '.join(kb[j1:j2])
        diff = tag != 'equal'
        if merged and merged[-1]['diff'] == diff:
            merged[-1]['t'] += t
            if diff:
                merged[-1]['other'] = (merged[-1]['other'] + ' ' + other).strip()
        else:
            merged.append({'t': t, 'diff': diff, 'other': other})
    return [s for s in merged if s['t']]


def convert_pdf_to_images(pdf_path, upload_id, max_pages=500):
    """Convierte páginas PDF a imágenes usando PyMuPDF."""
    try:
        import fitz
        doc = fitz.open(pdf_path)
        num_pages = min(len(doc), max_pages)
        image_paths = []
        
        for page_num in range(num_pages):
            page = doc[page_num]
            pix = page.get_pixmap(dpi=150)
            img_name = f"{upload_id}_page_{page_num+1}.png"
            img_path = os.path.join(PAGES_DIR, img_name)
            pix.save(img_path)
            image_paths.append(img_path)
        
        doc.close()
        return image_paths, num_pages
    except ImportError:
        # Fallback: crear imagen sintética
        from PIL import Image, ImageDraw, ImageFont
        image_paths = []
        for page_num in range(max_pages):
            img = Image.new('RGB', (800, 1100), (255, 255, 255))
            draw = ImageDraw.Draw(img)
            try:
                font = ImageFont.truetype('arial.ttf', 24)
            except:
                font = ImageFont.load_default()
            draw.text((50, 50), f"Página {page_num+1}", fill=(0, 0, 0), font=font)
            draw.text((50, 100), "Contenido PDF simulado", fill=(0, 0, 0), font=font)
            img_name = f"{upload_id}_page_{page_num+1}.png"
            img_path = os.path.join(PAGES_DIR, img_name)
            img.save(img_path, quality=100)
            image_paths.append(img_path)
        return image_paths, max_pages


def contrast(img_path):
    """Contraste de la página: distancia entre la tinta (percentil 0,05 %) y el papel (99,5 %).

    Con 0,5 % una página de una sola línea da 0: la tinta no llega a ese porcentaje.
    """
    from PIL import Image
    hist = Image.open(img_path).convert('L').histogram()
    total = sum(hist)
    acc, lo, hi = 0, None, 255
    for level, n in enumerate(hist):
        acc += n
        if lo is None and acc >= total * 0.0005:
            lo = level
        if acc >= total * 0.995:
            hi = level
            break
    return int(hi - (lo or 0))


def process_page(img_path, pdf_path, page_no, mode):
    """Semáforo de calidad, OCR y (en modo doble) diferencias con sus cajas.

    pdf_path None: no hay capa de texto que buscar (página reescaneada).
    """
    c = contrast(img_path)
    quality = 'ok' if c >= MIN_CONTRAST else 'bad'
    t, text, diff = 0, '', None
    # Página mala: el modelo inventaría texto, así que no se lee
    if quality == 'ok':
        t, text = ocr_single_img(img_path)
        if mode == 'double':
            # Segunda lectura con otra temperatura: lo que no coincide es duda
            t2, text2 = ocr_single_img(img_path, temperature=0.3)
            t += t2
            diff = diff_segments(text, text2)
            candidates = [s['t'].split() + s['other'].split() for s in diff if s['diff']]
            rects = find_rects(pdf_path, page_no, candidates) if pdf_path else [None] * len(candidates)
            k = 0
            for s in diff:
                if s['diff']:
                    s['rect'] = rects[k]
                    k += 1
                else:
                    s['rect'] = None
    return {'type': 'page', 'page': page_no, 'time': round(t, 2), 'chars': len(text),
            'text': text, 'diff': diff, 'contrast': c, 'quality': quality}


@app.route('/')
def index():
    """Página principal con interfaz de subida de PDF."""
    return render_template('index.html')


@app.route('/ocr', methods=['POST'])
def ocr():
    """Procesa el PDF subido y transmite el progreso en NDJSON.

    Emite una línea JSON por evento: start (nº de páginas), page (una por
    página terminada), done (estadísticas finales) o error.
    """
    if 'pdf' not in request.files:
        return jsonify({'error': 'No se encontró archivo PDF'}), 400
    
    pdf_file = request.files['pdf']
    if pdf_file.filename == '':
        return jsonify({'error': 'No seleccionado archivo'}), 400
    
    if not pdf_file.filename.endswith('.pdf'):
        return jsonify({'error': 'Archivo debe ser PDF'}), 400
    
    # Las páginas y PDFs de la subida anterior ya no hacen falta
    for old in glob.glob(os.path.join(PAGES_DIR, '*.png')) + glob.glob(os.path.join(TEST_PDF_IMAGES, '*.pdf')):
        try:
            os.remove(old)
        except OSError:
            pass
    upload_id = uuid.uuid4().hex
    pdf_path = os.path.join(TEST_PDF_IMAGES, f'{upload_id}.pdf')
    pdf_file.save(pdf_path)
    mode = request.form.get('mode', 'single')

    def generate():
        try:
            image_paths, num_pages = convert_pdf_to_images(pdf_path, upload_id)
            yield json.dumps({'type': 'start', 'total_pages': num_pages, 'upload_id': upload_id, 'mode': mode}) + '\n'
            total_time = 0
            total_chars = 0
            for i, img_path in enumerate(image_paths):
                p = process_page(img_path, pdf_path, i + 1, mode)
                total_time += p['time']
                total_chars += p['chars']
                yield json.dumps(p) + '\n'
            avg_time = total_time / num_pages if num_pages > 0 else 0
            yield json.dumps({
                'type': 'done',
                'total_pages': num_pages,
                'total_time': round(total_time, 2),
                'avg_time_per_page': round(avg_time, 2),
                'pages_per_hour_estimate': round(3600 / avg_time, 1) if avg_time > 0 else 0,
                'total_chars': total_chars
            }) + '\n'
        except Exception as e:
            yield json.dumps({'type': 'error', 'error': str(e)}) + '\n'

    return Response(stream_with_context(generate()), mimetype='application/x-ndjson')


@app.route('/page/<upload_id>/<int:page>.png')
def page_image(upload_id, page):
    """Imagen de una página de la subida actual, para verla junto al texto."""
    if not re.fullmatch(r'[0-9a-f]{32}', upload_id):
        return '', 404
    path = os.path.join(PAGES_DIR, f'{upload_id}_page_{page}.png')
    if not os.path.exists(path):
        return '', 404
    return send_file(path, mimetype='image/png')


@app.route('/page/<upload_id>/<int:page>/ocr', methods=['POST'])
def page_ocr(upload_id, page):
    """Relee una página; si llega 'file' (PDF o imagen), sustituye antes su imagen."""
    if not re.fullmatch(r'[0-9a-f]{32}', upload_id):
        return '', 404
    img_path = os.path.join(PAGES_DIR, f'{upload_id}_page_{page}.png')
    if not os.path.exists(img_path):
        return '', 404
    pdf_path = os.path.join(TEST_PDF_IMAGES, f'{upload_id}.pdf')
    f = request.files.get('file')
    if f and f.filename:
        data = f.read()
        try:
            if f.filename.lower().endswith('.pdf'):
                import fitz
                doc = fitz.open(stream=data, filetype='pdf')
                doc[0].get_pixmap(dpi=150).save(img_path)
                doc.close()
            else:
                import io
                from PIL import Image
                Image.open(io.BytesIO(data)).convert('RGB').save(img_path, 'PNG')
        except Exception as e:
            return jsonify({'error': f'Archivo no válido: {e}'}), 400
        pdf_path = None  # la capa de texto del PDF original ya no corresponde
    return jsonify(process_page(img_path, pdf_path, page, request.form.get('mode', 'single')))


@app.route('/export', methods=['POST'])
def export():
    """PDF nuevo solo con el texto transcrito, una página por texto y sin metadatos."""
    import io
    import fitz
    data = request.get_json(silent=True) or {}
    pages = data.get('pages')
    if not isinstance(pages, list) or not all(isinstance(p, str) for p in pages):
        return jsonify({'error': 'pages debe ser una lista de textos'}), 400
    name = re.sub(r'[^\w.-]', '_', str(data.get('name') or 'documento'))[:80]
    name = re.sub(r'\.pdf$', '', name, flags=re.I).strip('._') or 'documento'
    doc = fitz.open()
    for text in pages or ['']:
        page = doc.new_page()
        # shortcut: el texto que no cabe en la página se corta; paginar si hace falta
        page.insert_textbox(page.rect + (50, 50, -50, -50), text, fontsize=11, fontname='helv')
    doc.set_metadata({})
    buf = io.BytesIO(doc.tobytes(garbage=3, deflate=True))
    doc.close()
    return send_file(buf, mimetype='application/pdf', as_attachment=True,
                     download_name=f'{name}_transcrito.pdf')


if __name__ == '__main__':
    print("=" * 60)
    print("Mini App de OCR PaddleOCR-VL 1.6 con Ollama")
    print("=" * 60)
    print(f"Modelo: {model}")
    print(f"URL Ollama: {URL}")
    print(f"Directorio temporal: {TEST_PDF_IMAGES}")
    print()
    print("Iniciando servidor web en http://127.0.0.1:5000")
    print("Subir un PDF al endpoint /ocr")
    print("La barra de progreso se actualizará cada 1 segundo")
    print("=" * 60)
    app.run(debug=True, host='127.0.0.1', port=5000)