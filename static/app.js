// Frontend React 18 (UMD + htm, sin build) servido por FastAPI. Aspecto y rutas de maqueta/index.html.
// Estado global mutable `S` (como la maqueta) + `up()` para repintar. Todos los datos salen de /api/v1.
const { useState, useEffect, useRef } = React;
const html = htm.bind(React.createElement);
const Frag = React.Fragment;
const L = window.L;
let lang = 'ca';
const t = k => (L[lang][k] ?? L.ca[k] ?? k);
const range = n => Array.from({ length: n }, (_, k) => k + 1);
const API = '/api/v1';

// ---------- validadores (DNI/NIE e IBAN ES) ----------
const DNI_L = 'TRWAGMYFPDXBNJZSQVHLCKE';
// Devuelve la versión corregida si la letra no cuadra, o null si es válido.
function dniFix(s) {
    const num = s.slice(0, -1).replace(/^[XYZ]/, c => 'XYZ'.indexOf(c));
    const want = DNI_L[Number(num) % 23];
    return want === s.slice(-1) ? null : s.slice(0, -1) + want;
}
const mod97 = digits => { let r = 0; for (const ch of digits) r = (r * 10 + Number(ch)) % 97; return r; };
function ibanFix(raw) {
    const s = raw.replace(/\s/g, ''), bban = s.slice(4);
    if (mod97(bban + '1428' + s.slice(2, 4)) === 1) return null; // ES = 14 28
    const ck = String(98 - mod97(bban + '142800')).padStart(2, '0');
    return ('ES' + ck + bban).replace(/(.{4})/g, '$1 ').trim();
}
const RE_ID = /\b(?:\d{8}|[XYZ]\d{7})[A-Z]\b|\bES\d{2}(?: ?\d{4}){5}\b/g;

// ---------- estado ----------
const S = {
    user: null, booting: true, docs: [], curDoc: null, cur: 1, mode: 'double', rej: [], q: '', f: { estado: '', per: '', modo: '' }, sel: new Set(),
    hl: null, pop: null, modal: null, toast: '', guideOpen: false,
    jg: null, jgId: '', an: null, anMode: 'esborrar', anonPage: 1, detOpen: false, original: false, anHl: null,
    exp: null, audit: [], summary: null, arxiu: [],
};
let rerender = () => {};
const up = () => rerender();
const go = h => { location.hash = h; };
let toastTimer = null;
function toast(m) { S.toast = m; up(); clearTimeout(toastTimer); toastTimer = setTimeout(() => { S.toast = ''; up(); }, 2600); }
const remember = id => { try { sessionStorage.setItem('icat_doc', id); } catch (e) { /* sin storage */ } };

// ---------- API ----------
// Cookie HttpOnly `icat_token` (misma origen): no hace falta guardar el token en JS.
async function api(path, opts = {}) {
    const r = await fetch(API + path, { credentials: 'same-origin', ...opts });
    if (r.status === 401 && !path.startsWith('/user/login')) { S.user = null; go('#login'); up(); throw new Error(t('sessio_cad')); }
    if (!r.ok) {
        const j = await r.json().catch(() => ({}));
        const e = new Error((j.error && j.error.message) || (typeof j.detail === 'string' ? j.detail : 'HTTP ' + r.status));
        e.code = j.error && j.error.code; e.status = r.status;
        throw e;
    }
    return r;
}
const getJ = async p => (await api(p)).json();
const sendJ = async (p, method, body, headers = {}) => {
    const r = await api(p, { method, headers: { 'Content-Type': 'application/json', ...headers }, body: body === undefined ? undefined : JSON.stringify(body) });
    return r.status === 204 ? null : r.json();
};
const fail = e => toast('Error: ' + e.message);
function download(blob, name) {
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob); a.download = name; a.click();
    setTimeout(() => URL.revokeObjectURL(a.href), 2000);
}
const hhmm = iso => (iso ? new Date(iso).toLocaleString(lang === 'ca' ? 'ca-ES' : 'es-ES', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' }) : '');

// ---------- modelo de página ----------
const newPage = n => ({ n, status: 'q', fixes: {}, ver: 0 });
// `ev` es un evento `page` del stream o una fila de GET /pages: mismos campos.
function setPageData(p, ev) {
    const txt = ev.texto || '';
    let diff = ev.diferencias || null;
    // Si el texto se editó después del OCR, las diferencias guardadas ya no casan: se descartan.
    if (diff && diff.map(s => s.t).join('') !== txt) diff = null;
    if (diff) {
        const boxes = (ev.avisos || []).filter(a => a.tipo === 'doble_lectura');
        let k = 0;
        diff = diff.map(s => (s.diff ? { ...s, bbox: (boxes[k++] || {}).bbox || null } : s));
    }
    Object.assign(p, {
        status: 'done', text: txt, diff, time: ev.tiempo, contrast: ev.contraste_bruto ?? ev.contraste,
        quality: ev.estado === 'ilegible' ? 'bad' : 'ok', fixes: {}, edit: undefined,
        validated: !!ev.validada, esc: false, _segs: null, _loc: null, img: Date.now(), html: ev.html || null, fmt: !!ev.html,
    });
    p.ver++;
}
function splitInvalid(text, bbox, out) {
    let last = 0, m;
    RE_ID.lastIndex = 0;
    while ((m = RE_ID.exec(text))) {
        const iban = m[0].startsWith('ES'), alt = iban ? ibanFix(m[0]) : dniFix(m[0]);
        if (alt === null) continue;
        if (m.index > last) out.push({ t: text.slice(last, m.index) });
        out.push({ t: m[0], kind: 'invalid', sub: iban ? 'iban' : 'dni', alt, bbox });
        last = m.index + m[0].length;
    }
    if (last < text.length) out.push({ t: text.slice(last) });
}
// Segmentos de la página: texto plano + avisos (doubt = doble lectura, invalid = DNI/IBAN).
function pageSegs(p) {
    if (p._segs) return p._segs;
    const out = [];
    if (p.diff) p.diff.forEach(s => (s.diff ? out.push({ t: s.t, kind: 'doubt', alt: s.other ?? '', bbox: s.bbox }) : splitInvalid(s.t, null, out)));
    else splitInvalid(p.text || '', null, out);
    out.forEach((s, i) => { if (s.kind) s.id = 'w' + i; });
    return (p._segs = out);
}
const warns = p => (p && p.status === 'done' && p.quality !== 'bad' && !p.validated ? pageSegs(p).filter(s => s.kind) : []);
const pending = p => warns(p).filter(s => !(s.id in p.fixes));
function pstate(p) {
    if (!p || p.status !== 'done') return 'n';
    if (p.validated) return 'v';
    if (p.esc) return 'esc';
    if (p.quality === 'bad') return 'bad';
    return pending(p).length ? 'w' : 'ok';
}
const finalText = p => p.edit ?? pageSegs(p).map(s => (s.id in p.fixes ? p.fixes[s.id] : s.t)).join('');
// Cuerpo del PATCH: si la página tiene formato se manda el HTML (el backend saca el texto); si no, el texto (borra el HTML).
const pageBody = p => (p.fmt && p.html ? { html: p.html } : { texto: finalText(p) });
const docPages = d => range(d.total).map(n => d.pages[n]).filter(Boolean);
const docAllDone = d => d.total > 0 && docPages(d).every(p => ['v', 'esc'].includes(pstate(p)));
// Con la cola de OCR, las páginas ya guardadas se editan aunque el resto siga en proceso.
const RUNNING = ['pendiente', 'ocr_procesando'];
const editable = d => d && (d.estado === 'ocr_completado' || RUNNING.includes(d.estado));
function nextAttention(d, from) {
    for (let k = 1; k <= d.total; k++) {
        const m = ((from - 1 + k) % d.total) + 1;
        if (!['v', 'esc'].includes(pstate(d.pages[m]))) return m;
    }
    return null;
}

// ---------- sesión ----------
async function boot() {
    try {
        S.user = await getJ('/user/me');
        let id = null;
        try { id = sessionStorage.getItem('icat_doc'); } catch (e) { /* sin storage */ }
        if (id) await loadDoc(id).catch(() => null);
    } catch (e) { S.user = null; }
    S.booting = false;
    if (!S.user) go('#login');
    up();
}
async function logout() {
    try { await api('/user/logout', { method: 'POST' }); } catch (e) { /* ya caducada */ }
    S.user = null; S.curDoc = null; S.an = null; S.jg = null; S.exp = null;
    try { sessionStorage.removeItem('icat_doc'); } catch (e) { /* sin storage */ }
    go('#login'); up();
}

// ---------- documentos ----------
async function loadDoc(id) {
    const [det, pg] = await Promise.all([getJ(`/documents/${id}`), getJ(`/documents/${id}/pages`)]);
    const meta = (det.version_actual && det.version_actual.metadatos_proceso) || {};
    if (RUNNING.includes(det.estado) && !det.num_paginas) det.num_paginas = (await getJ(`/documents/${id}/progress`).catch(() => ({}))).total_pages;
    const d = {
        id, name: det.nombre_original, estado: det.estado, mode: meta.modo === 'simple' ? 'single' : 'double',
        total: Math.max(pg.items.length, det.num_paginas || 0), pages: {}, done: true, error: '', jg: det.justicia_gratuita,
    };
    pg.items.forEach(r => { const p = newPage(r.numero); setPageData(p, r); d.pages[r.numero] = p; });
    range(d.total).forEach(n => { d.pages[n] = d.pages[n] || newPage(n); });
    S.curDoc = d; remember(id);
    if (RUNNING.includes(d.estado)) followDoc(d);
    return d;
}
async function openDoc(row) {
    try {
        const d = await loadDoc(row.id);
        S.cur = nextAttention(d, d.total) || 1; S.hl = null;
        go(['ocr_completado'].includes(d.estado) ? '#revisio' : ['en_revision', 'aprobado'].includes(d.estado) ? '#anonimitzar' : d.estado === 'exportado' ? '#exportat' : '#revisio');
    } catch (e) { fail(e); }
}
async function loadList() {
    try {
        const q = S.q.trim();
        const j = await getJ('/documents?limit=100' + (q ? '&q=' + encodeURIComponent(q) : ''));
        // pendiente puede ser «en cola» o «falló»: el error solo viene en /progress
        await Promise.all(j.items.filter(d => RUNNING.includes(d.estado)).map(d => getJ(`/documents/${d.id}/progress`).then(g => {
            d._err = g.error; d.pages_done = g.pages_done; d.queue_position = g.queue_position; d.num_paginas = d.num_paginas || g.total_pages;
        }, () => null)));
        S.docs = j.items; up();
    } catch (e) { fail(e); }
}
async function loadArxiu() {
    try {
        const q = S.q.trim();
        const j = await getJ('/documents?estado=exportado&limit=100' + (q ? '&q=' + encodeURIComponent(q) : ''));
        S.arxiu = j.items; up();
    } catch (e) { fail(e); }
}

// Lee una respuesta NDJSON (start, page, done, error) y aplica cada evento al documento.
async function readNd(r, doc) {
    const reader = r.body.getReader(), dec = new TextDecoder();
    let buf = '';
    for (;;) {
        const { done, value } = await reader.read();
        if (done) break;
        buf += dec.decode(value, { stream: true });
        let nl;
        while ((nl = buf.indexOf('\n')) >= 0) {
            const line = buf.slice(0, nl).trim();
            buf = buf.slice(nl + 1);
            if (line) onEvent(doc, JSON.parse(line));
        }
    }
    if (buf.trim()) onEvent(doc, JSON.parse(buf));
}
// Reintento del OCR de un documento fallido o cancelado: vuelve a la cola y se sigue su progreso.
async function retryDoc(d) {
    try {
        await sendJ(`/documents/${d.id}/retry`, 'POST');
        d.error = ''; d._err = ''; d.done = false; d._follow = false;
        toast(t('q_retry_ok'));
        if (d.total) { docPages(d).forEach(p => { p.status = 'q'; }); followDoc(d); }
        up(); loadList();
    } catch (e) { fail(e); }
}
// Reanuda el progreso de un documento en cola o en proceso (tras recargar o al abrirlo desde la safata).
function followDoc(d) {
    if (d._follow) return;
    d._follow = true; d.done = false;
    api(`/documents/${d.id}/stream`, { headers: { Accept: 'application/x-ndjson' } })
        .then(r => readNd(r, d))
        .catch(e => { d.error = e.message; })
        .then(() => { d.done = true; d._follow = false; up(); });
}
// Varios ficheros: se encolan sin stream (202) y se sigue el progreso desde la safata.
async function queueUploads(files) {
    for (const file of files) {
        // Los rechazados quedan en un aviso fijo: un toast se pisaría con el siguiente fichero.
        if (!/\.(pdf|png|jpe?g)$/i.test(file.name)) { S.rej.push(file.name + ': ' + t('err_pdf')); continue; }
        if (file.size > 20 * 1024 * 1024) { S.rej.push(file.name + ': ' + t('err_size')); continue; }
        const fd = new FormData();
        fd.append('file', file); fd.append('modo', S.mode === 'double' ? 'doble' : 'simple');
        try { await api('/transform/document', { method: 'POST', body: fd }); toast('✓ ' + file.name + ' · ' + t('q_added')); } catch (e) { S.rej.push(file.name + ': ' + (e.code === 'DOCUMENTO_DUPLICADO' ? t('dup') : e.message)); up(); }
    }
    loadList();
}
function startUpload(file) {
    if (!file) return;
    if (!/\.(pdf|png|jpe?g)$/i.test(file.name)) return toast(t('err_pdf'));
    if (file.size > 20 * 1024 * 1024) return toast(t('err_size'));
    const doc = { id: null, name: file.name, mode: S.mode, estado: 'ocr_procesando', total: 0, pages: {}, stats: null, error: '', done: false };
    S.curDoc = doc; S.cur = 1;
    go('#processant'); up();
    const fd = new FormData();
    fd.append('file', file); fd.append('modo', S.mode === 'double' ? 'doble' : 'simple');
    // Respuesta NDJSON: una línea por evento (start, page, done, error).
    api('/transform/document', { method: 'POST', body: fd, headers: { Accept: 'application/x-ndjson' } })
        .then(async r => { await readNd(r, doc); doc.done = true; up(); })
        .catch(e => { doc.error = e.code === 'DOCUMENTO_DUPLICADO' ? t('dup') : e.message; doc.done = true; up(); });
}
function onEvent(doc, ev) {
    if (ev.type === 'start') {
        doc.id = ev.id; doc.total = ev.total_pages; doc.queue = ev.queue_position; remember(ev.id);
        range(doc.total).forEach(n => { doc.pages[n] = doc.pages[n] || newPage(n); });
        const first = docPages(doc).find(p => p.status !== 'done');
        if (first && !ev.queue_position) first.status = 'run';
    } else if (ev.type === 'queue') {
        doc.queue = ev.queue_position;
        const first = docPages(doc).find(p => p.status !== 'done');
        if (first && !ev.queue_position && first.status === 'q') first.status = 'run';
    } else if (ev.type === 'page') {
        const p = doc.pages[ev.numero] || (doc.pages[ev.numero] = newPage(ev.numero));
        doc.queue = 0;
        if (p.status !== 'done') setPageData(p, ev); // /stream repite las ya guardadas: no pisar lo que se está editando
        const nx = doc.pages[ev.numero + 1];
        if (nx && nx.status === 'q') nx.status = 'run';
    } else if (ev.type === 'done') {
        doc.stats = ev; doc.done = true; doc.estado = ev.estado || 'ocr_completado';
    } else if (ev.type === 'error') {
        if (ev.id) doc.id = ev.id; // para poder reintentar sin volver a subir
        doc.error = ev.code === 'CANCELADO' ? t('q_cancelat') : ev.message; doc.done = true;
        docPages(doc).forEach(p => { if (p.status === 'run') p.status = 'q'; });
    }
    up();
}
async function reOcr(d, n, file) {
    const p = d.pages[n], fd = new FormData();
    fd.append('modo', d.mode === 'double' ? 'doble' : 'simple');
    if (file) fd.append('file', file);
    p.status = 'run'; S.hl = null; up();
    try {
        setPageData(p, await (await api(`/documents/${d.id}/pages/${n}/ocr`, { method: 'POST', body: fd })).json());
        toast('✓ ' + (file ? t('esc_ok') : t('retranscriure')));
    } catch (e) { p.status = 'done'; fail(e); }
    up();
}
// Guardado de la transcripción: PATCH con retardo para no enviar cada tecla.
const saveTimers = {};
function saveText(d, p) {
    if (!editable(d)) return;
    clearTimeout(saveTimers[p.n]);
    saveTimers[p.n] = setTimeout(() => {
        sendJ(`/documents/${d.id}/pages/${p.n}`, 'PATCH', pageBody(p)).catch(fail);
    }, 800);
}
// PDF de la transcripción antes de anonimizar: <nombre>_trans.pdf
async function exportTranscrit(id, name) {
    try {
        const r = await api(`/documents/${id}/export/transcrito`, { method: 'POST' });
        download(await r.blob(), (name || 'document').replace(/\.[^.]+$/, '') + '_trans.pdf');
    } catch (e) { fail(e); }
}
async function exportDoc(id, name) {
    try {
        const r = await api(`/documents/${id}/export`, { method: 'POST' });
        const blob = await r.blob();
        const fname = (name || 'document').replace(/\.[^.]+$/, '') + '_anon.pdf';
        S.exp = { id, name: fname, hash: r.headers.get('X-Document-Hash'), blob };
        S.audit = (await getJ(`/audit?entidad_id=${id}&limit=100`)).items;
        go('#exportat'); up();
    } catch (e) { fail(e); }
}

// ---------- revisión: avisos en el texto ----------
function warnNode(s, p) {
    const el = document.createElement('span');
    el.dataset.wid = s.id;
    if (s.id in p.fixes) { el.className = 'fixed'; el.textContent = p.fixes[s.id]; return el; }
    el.className = s.kind;
    el.textContent = s.t;
    el.tabIndex = 0;
    el.contentEditable = 'false';
    el.setAttribute('role', 'button');
    el.setAttribute('aria-label', s.kind === 'doubt' ? t('dues') : s.sub === 'dni' ? t('dni_bad') : t('iban_bad'));
    return el;
}
// Pinta el texto con nodos DOM (nunca HTML del OCR). Si hay edición, se reubican los avisos pendientes en ella.
function buildText(el, p) {
    el.replaceChildren();
    if (p.html) { el.append(cleanFrag(p.html)); markWarns(el, p); return; }
    const segs = pageSegs(p);
    let changed = false;
    if (!p.text && p.edit === undefined) { el.append(t('buit')); return; }
    if (p.edit === undefined) {
        segs.forEach(s => el.append(s.kind ? warnNode(s, p) : s.t));
    } else {
        let pos = 0;
        for (const s of segs.filter(x => x.kind && !(x.id in p.fixes))) {
            const i = p.edit.indexOf(s.t, pos);
            if (i < 0) { p.fixes[s.id] = ''; changed = true; continue; } // el usuario lo cambió a mano
            el.append(p.edit.slice(pos, i), warnNode(s, p));
            pos = i + s.t.length;
        }
        el.append(p.edit.slice(pos));
    }
    if (changed) setTimeout(up);
}
function onTextInput(d, p, el, ev) {
    if (ev && /^format/.test(ev.inputType || '')) p.fmt = true; // Ctrl+B/I/U nativos
    p.edit = el.innerText;
    if (p.fmt) p.html = toHtml(el);
    for (const s of pending(p)) if (!el.querySelector(`[data-wid="${s.id}"]`)) p.fixes[s.id] = '';
    saveText(d, p);
    up();
}
function openWarn(el, p) {
    const r = el.getBoundingClientRect();
    S.pop = { type: 'warn', p, id: el.dataset.wid, left: r.left + scrollX, top: r.bottom + scrollY + 8 };
    up();
}
function applyFix(p, id, val, manual) {
    const tx = document.getElementById('txt');
    const el = tx && tx.querySelector(`[data-wid="${id}"]`);
    p.fixes[id] = val;
    if (el) {
        el.textContent = val; el.className = 'fixed';
        ['contenteditable', 'tabindex', 'role', 'aria-label'].forEach(a => el.removeAttribute(a));
    }
    if (tx) { p.edit = tx.innerText; if (p.fmt) p.html = toHtml(tx); }
    saveText(S.curDoc, p);
    S.pop = null; up();
    if (manual && el) {
        tx.focus();
        const r = document.createRange(); r.selectNodeContents(el);
        const sel = getSelection(); sel.removeAllRanges(); sel.addRange(r);
    }
}
function setHl(v) {
    if (JSON.stringify(v) === JSON.stringify(S.hl)) return;
    S.hl = v; up();
}
function hoverWarn(target, p, d) {
    const w = target.closest && target.closest('[data-wid]');
    const s = w && pageSegs(p).find(x => x.id === w.dataset.wid);
    if (!s) return setHl(null);
    hoverSeg(s, p, d);
}
function hoverSeg(s, p, d) {
    if (s.bbox || s.bbox === false) return setHl(s.bbox || 'none');
    S.hlWant = s.id;
    setHl('wait'); // contorno que late mientras llega la caja
    if (p._locBusy) return; // la llamada en lote ya la traerá
    // Sin caja (el lote falló o no se pidió): se pide sola al backend.
    getJ(`/documents/${d.id}/pages/${p.n}/locate?q=${encodeURIComponent(s.t.trim())}`)
        .then(r => { s.bbox = r.bbox || false; if (S.hlWant === s.id) setHl(s.bbox || 'none'); })
        .catch(() => { s.bbox = false; if (S.hlWant === s.id) setHl('none'); });
}
// Al mostrar una página se piden de una vez las cajas de todos sus avisos que aún no la tienen.
function prefetchBoxes(d, p) {
    if (!d || !d.id || !p || p.status !== 'done' || p._loc) return;
    const miss = warns(p).filter(s => !s.bbox && s.bbox !== false && s.t.trim());
    if (!miss.length) return;
    p._locBusy = true;
    p._loc = sendJ(`/documents/${d.id}/pages/${p.n}/locate`, 'POST', { q: miss.map(s => s.t.trim()) })
        .then(r => miss.forEach((s, i) => { s.bbox = (r.bboxes || [])[i] || false; }), () => null)
        .then(() => { p._locBusy = false; const s = miss.find(x => x.id === S.hlWant); if (s) hoverSeg(s, p, d); });
}

// ---------- mini Word: formato del texto ----------
const FONTS = ['Georgia', 'Times New Roman', 'Arial', 'Verdana', 'Courier New', 'Roboto'];
const SIZES = [10, 11, 12, 14, 16, 18, 20, 24, 28, 32];
const COLORS = ['#1F2328', '#B2051B', '#1A5FB4', '#26A269', '#C64600', '#613583'];
const MARKS = ['#FFF3A3', '#C6F6C6', '#CDE4FF', '#FFD6E0'];
const TAGS = new Set(['P', 'DIV', 'BR', 'B', 'STRONG', 'I', 'EM', 'U', 'S', 'MARK', 'SPAN', 'FONT']);
const font1 = v => (v || '').split(',')[0].replace(/["']/g, '').trim();
// Copia solo los estilos permitidos (misma lista que el backend).
function cleanStyle(src, dst) {
    if (FONTS.includes(font1(src.fontFamily))) dst.fontFamily = font1(src.fontFamily);
    const m = /^(\d+(?:\.\d+)?)(px|pt)$/.exec(src.fontSize || '');
    if (m && +m[1] >= 8 && +m[1] <= 48) dst.fontSize = src.fontSize;
    ['color', 'backgroundColor', 'fontWeight', 'fontStyle'].forEach(k => { if (src[k]) dst[k] = src[k]; });
    // execCommand escribe text-decoration-line; el backend solo admite text-decoration
    const td = src.textDecoration || src.textDecorationLine;
    if (td && td !== 'none') dst.textDecoration = td;
}
// Reconstruye el árbol con nodos nuevos: etiquetas fuera de la lista se desenvuelven; de los atributos solo queda style filtrado.
function cleanNode(n, out) {
    for (const c of n.childNodes) {
        if (c.nodeType === 3) { out.append(c.data); continue; }
        if (c.nodeType !== 1 || ['SCRIPT', 'STYLE', 'TEMPLATE', 'TITLE'].includes(c.tagName)) continue;
        if (!TAGS.has(c.tagName)) { cleanNode(c, out); continue; }
        const e = document.createElement(c.tagName === 'FONT' ? 'span' : c.tagName.toLowerCase());
        cleanStyle(c.style, e.style);
        if (c.tagName === 'FONT') {
            if (FONTS.includes(font1(c.getAttribute('face')))) e.style.fontFamily = font1(c.getAttribute('face'));
            if (c.getAttribute('color')) e.style.color = c.getAttribute('color');
        }
        cleanNode(c, e);
        out.append(e);
    }
    return out;
}
const cleanFrag = str => cleanNode(new DOMParser().parseFromString(str, 'text/html').body, document.createDocumentFragment());
// HTML a guardar: sin las marcas de aviso (son solo UI) y saneado.
function toHtml(el) {
    const c = el.cloneNode(true);
    c.querySelectorAll('[data-wid]').forEach(w => w.replaceWith(...w.childNodes));
    const box = document.createElement('div');
    cleanNode(c, box);
    return box.innerHTML;
}
// En páginas con formato, los avisos pendientes se vuelven a marcar buscando su texto en los nodos de texto.
// shortcut: un aviso partido entre dos estilos no se encuentra y se da por resuelto, como al editar a mano.
function markWarns(el, p) {
    const w = document.createTreeWalker(el, NodeFilter.SHOW_TEXT);
    let node = w.nextNode(), changed = false;
    for (const s of pageSegs(p).filter(x => x.kind && !(x.id in p.fixes) && x.t)) {
        let i = -1;
        while (node && (i = node.data.indexOf(s.t)) < 0) node = w.nextNode();
        if (!node) { p.fixes[s.id] = ''; changed = true; continue; }
        const hit = node.splitText(i), after = hit.splitText(s.t.length);
        hit.replaceWith(warnNode(s, p));
        node = after; w.currentNode = after;
    }
    if (changed) setTimeout(up);
}
let fmtRange = null; // última selección dentro del texto: los controles de la barra la roban al recibir foco
function fmtCmd(d, p, fn) {
    const el = document.getElementById('txt');
    if (!el) return;
    el.focus();
    if (fmtRange) { const sel = getSelection(); sel.removeAllRanges(); sel.addRange(fmtRange); }
    document.execCommand('styleWithCSS', false, true);
    fn(el);
    p.fmt = true;
    onTextInput(d, p, el);
}
const exec = (c, v) => () => document.execCommand(c, false, v);
// execCommand fontSize solo admite 1-7: se aplica 7 y se cambia por la medida real.
const setSize = v => el => {
    document.execCommand('fontSize', false, '7');
    el.querySelectorAll('font[size="7"],[style*="xxx-large"]').forEach(f => { f.removeAttribute('size'); f.style.fontSize = v + 'px'; });
};
function FmtBar({ d, p, ed }) {
    const [st, setSt] = useState({});
    useEffect(() => {
        const on = () => {
            const sel = getSelection(), el = document.getElementById('txt');
            if (!sel.rangeCount || !el || !el.contains(sel.anchorNode)) return;
            fmtRange = sel.getRangeAt(0).cloneRange();
            const a = sel.anchorNode.nodeType === 1 ? sel.anchorNode : sel.anchorNode.parentElement;
            const q = c => { try { return document.queryCommandState(c); } catch (e) { return false; } };
            setSt({ b: q('bold'), i: q('italic'), u: q('underline'), s: q('strikeThrough'),
                font: font1(document.queryCommandValue('fontName')), size: Math.round(parseFloat(getComputedStyle(a).fontSize)) });
        };
        document.addEventListener('selectionchange', on);
        return () => { document.removeEventListener('selectionchange', on); fmtRange = null; };
    }, []);
    const run = fn => fmtCmd(d, p, fn);
    const keep = e => e.preventDefault(); // que el botón no quite la selección del texto
    const btn = (k, label, fn, pressed, style) => html`<button key=${label} type="button" disabled=${!ed} aria-label=${t(label)} title=${t(label)}
        aria-pressed=${pressed} style=${style} onMouseDown=${keep} onClick=${() => run(fn)}>${k}</button>`;
    const sw = (c, label, cmd) => html`<button key=${cmd + c} type="button" className="sw" disabled=${!ed} aria-label=${label + ' ' + c} title=${label + ' ' + c}
        style=${{ background: c }} onMouseDown=${keep} onClick=${() => run(exec(cmd, c))}></button>`;
    return html`<div className="fmt" role="toolbar" aria-label=${t('f_bar')}>
        <select aria-label=${t('f_font')} title=${t('f_font')} disabled=${!ed} value=${FONTS.includes(st.font) ? st.font : ''}
            onChange=${e => e.target.value && run(exec('fontName', e.target.value))}>
            <option value="">${t('f_font')}</option>
            ${FONTS.map(f => html`<option key=${f} value=${f} style=${{ fontFamily: f }}>${f}</option>`)}
        </select>
        <select aria-label=${t('f_size')} title=${t('f_size')} disabled=${!ed} value=${SIZES.includes(st.size) ? String(st.size) : ''}
            onChange=${e => e.target.value && run(setSize(e.target.value))}>
            <option value="">${t('f_size')}</option>
            ${SIZES.map(z => html`<option key=${z} value=${String(z)}>${z}</option>`)}
        </select>
        <span className="sep" aria-hidden="true"></span>
        ${btn('B', 'f_bold', exec('bold'), !!st.b, { fontWeight: 700 })}
        ${btn('I', 'f_italic', exec('italic'), !!st.i, { fontStyle: 'italic' })}
        ${btn('U', 'f_under', exec('underline'), !!st.u, { textDecoration: 'underline' })}
        ${btn('S', 'f_strike', exec('strikeThrough'), !!st.s, { textDecoration: 'line-through' })}
        <span className="sep" aria-hidden="true"></span>
        <span className="doc-s" aria-hidden="true">A</span>
        ${COLORS.map(c => sw(c, t('f_color'), 'foreColor'))}
        <input type="color" aria-label=${t('f_color') + ' · ' + t('f_custom')} title=${t('f_custom')} disabled=${!ed}
            onChange=${e => run(exec('foreColor', e.target.value))} />
        <span className="sep" aria-hidden="true"></span>
        <span className="doc-s" aria-hidden="true">${t('f_mark')}</span>
        ${MARKS.map(c => sw(c, t('f_mark'), 'hiliteColor'))}
        <button type="button" className="sw" disabled=${!ed} aria-label=${t('f_none')} title=${t('f_none')} onMouseDown=${keep}
            onClick=${() => run(exec('hiliteColor', 'transparent'))}>⌀</button>
        <span className="sep" aria-hidden="true"></span>
        ${btn('↶', 'f_undo', exec('undo'))}
        ${btn('↷', 'f_redo', exec('redo'))}
        ${btn('⨯', 'f_clear', exec('removeFormat'))}
    </div>`;
}

function TextPane({ d, p }) {
    const ref = useRef(null);
    const ed = editable(d);
    useEffect(() => { buildText(ref.current, p); }, []); // el padre usa key = doc+pàgina+versió
    return html`<div className="text" id="txt" ref=${ref} contentEditable=${ed ? 'true' : 'false'} spellCheck=${false}
        onInput=${e => onTextInput(d, p, ref.current, e.nativeEvent)}
        onClick=${e => { const w = e.target.closest('[data-wid]'); if (ed && w && !(w.dataset.wid in p.fixes)) openWarn(w, p); }}
        onKeyDown=${e => { const w = e.target.dataset && e.target.dataset.wid; if (ed && w && (e.key === 'Enter' || e.key === ' ') && !(w in p.fixes)) { e.preventDefault(); openWarn(e.target, p); } }}
        onMouseOver=${e => hoverWarn(e.target, p, d)} onMouseLeave=${() => { S.hlWant = null; setHl(null); }}
        onFocus=${e => hoverWarn(e.target, p, d)}></div>`;
}

// ---------- piezas comunes ----------
function Lang({ style }) {
    const set = l => { lang = l; document.documentElement.lang = l; up(); };
    return html`<div className="lang" role="group" aria-label="Idioma" style=${style}>
        ${['ca', 'es'].map(l => html`<button key=${l} type="button" className=${lang === l ? 'on' : ''} aria-pressed=${lang === l} onClick=${() => set(l)}>${l.toUpperCase()}</button>`)}
    </div>`;
}
const Logo = () => html`<div className="logo"><b>ICA<i>T</i></b><small>Il·lustre Col·legi de l'Advocacia de Tarragona</small></div>`;
const ROLS = { transcriptor: 'r_trans', revisor: 'r_rev', admin: 'r_admin' };
function Shell({ active, children }) {
    const u = S.user, full = `${u.nombre} ${u.apellidos}`.trim();
    const ini = full.split(/\s+/).map(w => w[0]).join('').slice(0, 2).toUpperCase();
    return html`<${Frag}>
    <header>
        <a href="#safata" className="logo-a" aria-label=${t('inici')}><${Logo} /></a>
        <nav aria-label="Principal">${[['safata', '#safata'], ['jg', '#jg'], ['arxiu', '#arxiu'], ['informes', '#informes']].map(([k, h]) =>
            html`<a key=${k} href=${h} className=${active === k ? 'on' : ''} aria-current=${active === k ? 'page' : undefined}>${t(k)}</a>`)}</nav>
        <${Lang} />
        <div className="user"><span><b>${full}</b><br />${u.roles.map(r => t(ROLS[r] || r)).join(' · ')}</span>
            <span className="avatar" title=${u.email} aria-hidden="true">${ini}</span>
            <button type="button" className="btn" onClick=${logout}>${t('sortir')}</button></div>
    </header>
    <main key=${active + location.hash.split('/')[0]}>${children}</main>
    <//>`;
}
const NoDoc = () => html`<${Shell} active="safata"><div className="card" style=${{ padding: '28px', textAlign: 'center' }}>
    <p>${t('no_doc')}</p><a className="btn pri" href="#safata">‹ ${t('safata')}</a></div><//>`;
const Empty = ({ msg }) => html`<div className="card" style=${{ padding: '28px', textAlign: 'center' }}><p className="doc-s">${msg}</p></div>`;
const chip = (cls, txt) => html`<span className=${'chip ' + cls}>${txt}</span>`;
function StatsKpis({ d }) {
    const s = d.stats;
    if (!s) return null;
    const n = d.total || 1;
    const k = [[d.total, 'st_total'], [s.total_time + ' s', 'st_time'], [(s.total_time / n).toFixed(2) + ' s', 'st_avg'],
        [s.total_time ? Math.round((3600 * d.total) / s.total_time) : '—', 'st_ph'], [s.total_chars, 'st_chars']];
    return html`<div className="kpis k5">${k.map(([v, l]) => html`<div key=${l} className="card kpi"><b>${v}</b><span>${t(l)}</span></div>`)}</div>`;
}
// Fragmento de ts_headline: solo se interpretan <b>…</b>; el resto se pinta como texto.
function Snippet({ s }) {
    if (!s) return null;
    return html`<div className="doc-s">…${s.split(/(<b>.*?<\/b>)/g).map((x, i) => (x.startsWith('<b>') ? html`<mark key=${i}>${x.slice(3, -4)}</mark>` : x))}…</div>`;
}

// ---------- login ----------
function Login() {
    const [email, setEmail] = useState('');
    const [pass, setPass] = useState('');
    const [err, setErr] = useState('');
    const [busy, setBusy] = useState(false);
    const submit = async e => {
        e.preventDefault(); setErr(''); setBusy(true);
        try {
            await sendJ('/user/login', 'POST', { email, password: pass });
            S.user = await getJ('/user/me');
            go('#safata'); up();
        } catch (x) { setErr(x.status === 401 ? t('login_err') : x.message); setBusy(false); }
    };
    return html`<div className="card login">
        <${Logo} />
        <h1 style=${{ margin: '28px 0 22px' }}>${t('login_t')}</h1>
        <form onSubmit=${submit}>
            <label className="fld">${t('correu')}<input type="email" value=${email} onChange=${e => setEmail(e.target.value)} required autoComplete="username" /></label>
            <label className="fld">${t('contrasenya')}<input type="password" value=${pass} onChange=${e => setPass(e.target.value)} required autoComplete="current-password" /></label>
            ${err && html`<div className="banner bad" role="alert">${err}</div>`}
            <button className="btn pri wide" type="submit" disabled=${busy}>${t('login_b')}</button>
        </form>
        <p className="banner ok" style=${{ marginTop: '22px' }}>🔒 ${t('local')}</p>
        <${Lang} style=${{ display: 'inline-flex', marginTop: '12px' }} />
    </div>`;
}
// ---------- safata / arxiu ----------
const EST = { pendiente: ['n', 'e_pend'], ocr_procesando: ['n', 'transcrivint'], ocr_completado: ['ok', 'transcrit'], anonimizando: ['n', 'e_anon'],
    en_revision: ['w', 'anonimitzar'], eliminado: ['n', 'e_elim'], aprobado: ['ok', 'e_aprov'], rechazado: ['bad', 'e_rebut'], exportado: ['ok', 'exportat'] };
function rowOf(d) {
    const [cls, k] = EST[d.estado] || ['n', d.estado];
    const st = d._err === 'CANCELADO' ? ['n', t('q_cancelat')] : d._err ? ['bad', '✕ ' + t('q_error')] : d.estado === 'pendiente' ? ['n', t('q_cua') + (d.queue_position ? ` (${t('q_pos')} ${d.queue_position})` : '')]
        : d.estado === 'ocr_procesando' ? ['n', `${t('transcrivint')} ${d.pages_done || 0}/${d.num_paginas || '…'}`] : [cls, t(k)];
    const q = d.paginas_ilegibles > 0 ? ['bad', `✕ ${d.paginas_ilegibles} ${t('tornar')}`]
        : d.paginas_revisar > 0 ? ['w', `! ${d.paginas_revisar} ${t('revisar')}`] : ['ok', '✓ ' + t('fiable')];
    return { id: d.id, title: d.nombre_original, frag: d.fragmento, p: d.num_paginas ?? '…', st, q, r: hhmm(d.creado_en), raw: d,
        open: d.estado === 'anonimizando' || d._err ? null : () => openDoc(d) };
}
// Filtros en el cliente sobre la lista ya cargada (≤100): estado, quién lo subió y modo de transcripción.
const filtra = list => list.filter(d => (!S.f.estado || d.estado === S.f.estado) && (!S.f.per || d.subido_por === S.f.per)
    && (!S.f.modo || d.modo_ocr === S.f.modo));
function Filters({ list, estados }) {
    const set = (k, v) => { S.f = { ...S.f, [k]: v }; S.sel = new Set(); up(); };
    const pers = [...new Set(list.map(d => d.subido_por).filter(Boolean))].sort();
    const sel = (k, label, opts) => html`<select className="search fsel" aria-label=${label} value=${S.f[k]} onChange=${e => set(k, e.target.value)}>
        <option value="">${label}: ${t('tots')}</option>${opts.map(([v, l]) => html`<option key=${v} value=${v}>${l}</option>`)}</select>`;
    return html`<div className="row wrap" style=${{ marginBottom: '12px' }}>
        ${estados && sel('estado', t('th_estat'), Object.keys(EST).filter(e => list.some(d => d.estado === e)).map(e => [e, t(EST[e][1])]))}
        ${sel('per', t('pujat_per'), pers.map(p => [p, p]))}
        ${sel('modo', t('mode_l'), [['doble', t('m_double')], ['simple', t('m_single')]])}
        ${(S.f.estado || S.f.per || S.f.modo) && html`<button type="button" className="btn" onClick=${() => { S.f = { estado: '', per: '', modo: '' }; S.sel = new Set(); up(); }}>✕ ${t('netejar')}</button>`}
    </div>`;
}
async function downloadZip(tipo) {
    try {
        const r = await api('/documents/export/zip', { method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ ids: [...S.sel], tipo }) });
        download(await r.blob(), `documentos_${tipo}.zip`);
        const om = Number(r.headers.get('X-Omitidos') || 0);
        toast(om ? `✓ ZIP · ${om} ${t('zip_omesos')}` : '✓ ZIP');
    } catch (e) { fail(e); }
}
function ZipBar({ rows, anon }) {
    const all = rows.length > 0 && rows.every(d => S.sel.has(d.id));
    return html`<div className="row wrap" style=${{ marginBottom: '8px' }}>
        <label className="cat"><input type="checkbox" checked=${all} onChange=${() => { S.sel = all ? new Set() : new Set(rows.map(d => d.id)); up(); }} /> ${t('sel_tots')} (${S.sel.size})</label>
        <span className="sp"></span>
        <button type="button" className="btn" disabled=${!S.sel.size} onClick=${() => downloadZip('trans')}>⬇ ZIP ${t('exp_transcrit')}</button>
        ${anon && html`<button type="button" className="btn pri" disabled=${!S.sel.size} onClick=${() => downloadZip('anon')}>⬇ ZIP ${t('zip_anon')}</button>`}
    </div>`;
}
const toggleSel = id => { const s = new Set(S.sel); s.has(id) ? s.delete(id) : s.add(id); S.sel = s; up(); };
function Rows({ rows, head }) {
    return html`<div className="card"><table>
        ${head && html`<thead><tr><th></th><th></th><th>${t('th_doc')}</th><th>${t('th_pag')}</th><th>${t('th_estat')}</th><th>${t('th_q')}</th><th>${t('th_reb')}</th></tr></thead>`}
        <tbody>${rows.map(d => html`<tr key=${d.id} className=${d.open ? 'click' : ''} tabIndex=${d.open ? 0 : undefined}
                onClick=${d.open || undefined} onKeyDown=${e => { if (d.open && e.key === 'Enter') d.open(); }}>
                <td style=${{ width: '44px' }} onClick=${e => e.stopPropagation()}><input type="checkbox" className="rsel" aria-label=${d.title}
                    checked=${S.sel.has(d.id)} onChange=${() => toggleSel(d.id)} /></td>
                <td style=${{ width: '44px' }}><div className="tile" style=${{ minHeight: 0, padding: '4px', width: '30px' }}><div className="pg" style=${{ margin: 0, height: '28px', width: '20px' }}></div></div></td>
                <td><div className="doc-t">${d.title}</div><div className="mob">${chip(d.st[0], d.st[1])}</div>${d.raw.subido_por && html`<div className="doc-s">${t('pujat_per')} ${d.raw.subido_por}</div>`}
                    ${d.raw.modo_ocr && html`<div className="doc-s">${d.raw.modo_ocr === 'doble' ? '⧉ ' + t('m_double') : '▢ ' + t('m_single')}</div>`}<${Snippet} s=${d.frag} />
                    ${!RUNNING.includes(d.raw.estado) && !d.raw._err && html`<button type="button" className="btn" style=${{ marginTop: '4px' }}
                        onClick=${e => { e.stopPropagation(); exportTranscrit(d.id, d.title); }}>⬇ ${t('exp_transcrit')}</button>`}</td><td>${d.p}</td>
                <td>${chip(d.st[0], d.st[1])}<${QueueInfo} d=${d.raw} /></td><td>${RUNNING.includes(d.raw.estado) ? '' : chip(d.q[0], d.q[1])}</td><td>${d.r}</td></tr>`)}</tbody></table></div>`;
}
// Progreso, cancelar y reintentar de los documentos de la cola (dentro de una fila clicable: no propagar el clic).
// Textos de error del backend que tienen traducción; el resto se muestra tal cual.
const errText = e => (e === 'CANCELADO' ? t('q_cancelat') : /^Transcripción interrumpida/.test(e) ? t('q_interr') : e);
function QueueInfo({ d }) {
    if (!d || !RUNNING.includes(d.estado)) return null;
    const stop = e => e.stopPropagation();
    const cancel = async e => { stop(e); try { await sendJ(`/documents/${d.id}/cancel`, 'POST'); toast(t('q_cancelat')); } catch (x) { fail(x); } loadList(); };
    if (d._err) return html`<div className="doc-s">${errText(d._err)} <button type="button" className="btn" onClick=${e => { stop(e); retryDoc(d); }}>↻ ${t('q_retry')}</button></div>`;
    return html`<div className="row" style=${{ gap: '6px', marginTop: '4px' }}>
        ${d.estado === 'ocr_procesando' && html`<progress max=${d.num_paginas || 1} value=${d.pages_done || 0} aria-label=${t('transcrivint')}></progress>`}
        ${d.estado === 'pendiente' && html`<button type="button" className="btn" onClick=${cancel}>${t('cancel')}</button>`}
    </div>`;
}
let searchTimer = null;
function Search({ reload }) {
    return html`<input className="search" value=${S.q} placeholder=${t('cerca')} aria-label=${t('cerca')}
        onChange=${e => { S.q = e.target.value; up(); clearTimeout(searchTimer); searchTimer = setTimeout(reload, 350); }} />`;
}
function Safata() {
    useEffect(() => {
        loadList();
        // refresco mientras haya documentos en cola o transcribiéndose
        const iv = setInterval(() => { if (S.docs.some(d => RUNNING.includes(d.estado) && !d._err)) loadList(); }, 3000);
        return () => clearInterval(iv);
    }, []);
    const pick = () => document.getElementById('pdfFile').click();
    const upload = fl => { const files = [...fl]; if (files.length > 1) queueUploads(files); else startUpload(files[0]); };
    const today = new Date().toDateString(), sum = k => S.docs.reduce((a, d) => a + (Number(d[k]) || 0), 0);
    const drag = {
        onDragEnter: e => { e.preventDefault(); e.currentTarget.classList.add('over'); },
        onDragOver: e => { e.preventDefault(); e.currentTarget.classList.add('over'); },
        onDragLeave: e => e.currentTarget.classList.remove('over'),
        onDrop: e => { e.preventDefault(); e.currentTarget.classList.remove('over'); upload(e.dataTransfer.files); },
    };
    return html`<${Shell} active="safata">
        <h1>${t('safata_t')}</h1><p className="sub">${t('safata_s')} ${t('local')}</p>
        <div className="kpis">
            <div className="card kpi"><b>${S.docs.filter(d => new Date(d.creado_en).toDateString() === today).length}</b><span>${t('k1')}</span></div>
            <div className="card kpi"><b>${sum('num_paginas')}</b><span>${t('k2')}</span></div>
            <div className="card kpi"><b style=${{ color: 'var(--w)' }}>${sum('paginas_revisar')}</b><span>${t('k3')}</span></div>
            <div className="card kpi"><b style=${{ color: 'var(--p)' }}>${sum('paginas_ilegibles')}</b><span>${t('k4')}</span></div>
        </div>
        <div className="mselect" role="radiogroup" aria-label=${t('mode_l')}>
            ${['single', 'double'].map(m => html`<label key=${m} className=${'mopt' + (S.mode === m ? ' on' : '')}>
                <input type="radio" name="mode" value=${m} checked=${S.mode === m} onChange=${() => { S.mode = m; up(); }} />
                ${t('m_' + m)}${m === 'double' ? ' · ' + t('m_double_n') : ''}</label>`)}
        </div>
        <button type="button" className="drop" onClick=${pick} ...${drag}><b>${t('drop')}</b> ${t('drop2')} · ${t('max50')}</button>
        <input type="file" id="pdfFile" accept=".pdf,application/pdf,image/png,image/jpeg" multiple hidden onChange=${e => { upload(e.target.files); e.target.value = ''; }} />
        <div className="row" style=${{ marginBottom: '12px' }}><${Search} reload=${loadList} /><button type="button" className="btn pri" onClick=${pick}>＋ ${t('nou')}</button></div>
        ${S.rej.length > 0 && html`<div className="banner bad row" role="alert"><div className="sp">${S.rej.map((m, i) => html`<div key=${i}>✕ ${m}</div>`)}</div>
            <button type="button" className="btn" onClick=${() => { S.rej = []; up(); }}>${t('tancar')}</button></div>`}
        <${Filters} list=${S.docs} estados=${true} />
        ${(() => { const rows = filtra(S.docs); return rows.length ? html`<${ZipBar} rows=${rows} anon=${true} /><${Rows} rows=${rows.map(rowOf)} head=${true} />`
            : html`<${Empty} msg=${S.q || S.f.estado || S.f.per || S.f.modo ? t('sense_res') : t('buida')} />`; })()}
    <//>`;
}
function Arxiu() {
    useEffect(() => { loadArxiu(); }, []);
    return html`<${Shell} active="arxiu">
        <h1>${t('arxiu_t')}</h1><p className="sub">${t('arxiu_s')}</p>
        <div style=${{ marginBottom: '12px' }}><${Search} reload=${loadArxiu} /></div>
        <${Filters} list=${S.arxiu} />
        ${(() => { const rows = filtra(S.arxiu); return rows.length ? html`<${ZipBar} rows=${rows} anon=${true} /><${Rows} rows=${rows.map(d => ({ ...rowOf(d), r: hhmm(d.exportado_en), open: () => exportDoc(d.id, d.nombre_original) }))} head=${true} />`
            : html`<${Empty} msg=${S.q || S.f.per || S.f.modo ? t('sense_res') : t('arxiu_buit')} />`; })()}
    <//>`;
}

// ---------- processant ----------
function tileBody(p) {
    if (!p || p.status === 'q') return t('cua');
    if (p.status === 'run') return html`<span><span className="spin" aria-hidden="true"></span> ${t('ocr')}…</span>`;
    const s = pstate(p);
    return s === 'bad' ? chip('bad', '✕ ' + t('tornar')) : s === 'w' ? chip('w', '! ' + t('revisar_n')) : s === 'v' ? chip('ok', '✓ ' + t('validat')) : chip('ok', '✓ ' + t('fiable'));
}
function Processant() {
    const d = S.curDoc;
    if (!d) return html`<${NoDoc} />`;
    const pg = docPages(d), done = pg.filter(p => p.status === 'done').length;
    const sts = pg.map(p => [p.n, pstate(p)]);
    const ok = sts.filter(([, s]) => ['ok', 'v'].includes(s)).length, w = sts.filter(([, s]) => s === 'w').map(([n]) => n), bad = sts.filter(([, s]) => s === 'bad').map(([n]) => n);
    return html`<${Shell} active="safata">
        <h1 aria-live="polite">${d.error && !d.total ? d.name : d.done ? `${t('proc_fi')} · ${d.name}` : `${t('proc_t')} ${done}/${d.total || '…'} · ${d.name}`}</h1>
        <p className="sub">${t(d.mode === 'double' ? 'm_double' : 'm_single')} · ${t('proc_s2')}</p>
        ${d.error && html`<div className="banner bad row"><div className="sp">Error: ${d.error}</div>
            ${d.id && html`<button type="button" className="btn" onClick=${() => retryDoc(d)}>↻ ${t('q_retry')}</button>`}</div>`}
        ${!(d.error && !d.total) && html`<div className="card"><div className="tiles">
            ${d.total === 0 && !d.done && html`<div className="tile run"><div className="pg"></div><span className="spin" aria-hidden="true"></span> …</div>`}
            ${range(d.total).map(n => { const p = d.pages[n]; return html`<div key=${n} className=${'tile' + (p && p.status === 'run' ? ' run' : '')}><div className="pg"></div>${t('pag')} ${n}<br />${tileBody(p)}</div>`; })}
        </div></div>`}
        ${d.error && !d.total && html`<a className="btn" href="#safata">${t('tornar_safata')}</a>`}
        ${d.done && !(d.error && !d.total) && html`<div className="card" style=${{ marginTop: '16px', padding: '16px 18px' }}>
            <div className="row wrap">
                ${chip('ok', `✓ ${ok} ${t('sum_ok')}`)}
                ${w.length > 0 && chip('w', `! ${w.length} ${t('sum_w')} (${t('pag')} ${w.join(', ')})`)}
                ${bad.length > 0 && chip('bad', `✕ ${bad.length} ${t('sum_bad2')} (${t('pag')} ${bad.join(', ')})`)}
                <span className="sp"></span>
                <a className="btn" href="#safata">${t('tornar_safata')}</a>
                ${d.total > 0 && !d.error && html`<a className="btn pri" href="#revisio" onClick=${() => { S.cur = nextAttention(d, d.total) || 1; }}>${t('obrir')} →</a>`}
            </div>
            <${StatsKpis} d=${d} />
        </div>`}
    <//>`;
}

// ---------- revisió ----------
function setCur(n) { S.cur = n; S.hl = null; S.pop = null; up(); }
function Revisio() {
    const d = S.curDoc;
    const [nat, setNat] = useState(null); // tamaño real del PNG: las cajas vienen en píxeles
    // La miniatura actual siempre a la vista (con 20+ páginas la columna no cabe entera).
    useEffect(() => { const el = document.querySelector('.thumbs .thumb.on'); if (el) el.scrollIntoView({ block: 'nearest' }); }, [S.cur, S.curDoc && S.curDoc.id]);
    useEffect(() => { const d = S.curDoc; if (d && d.id && d.pages) [S.cur, S.cur + 1].forEach(k => prefetchBoxes(d, d.pages[k])); });
    if (!d || !d.total || !d.id) return html`<${NoDoc} />`;
    const n = Math.min(S.cur, d.total), p = d.pages[n] || newPage(n), st = pstate(p), pend = pending(p);
    const totalW = docPages(d).reduce((a, x) => a + pending(x).length, 0), allDone = docAllDone(d);
    const hl = S.hl, done = p.status === 'done', ed = editable(d);
    const box = hl && hl.ancho && nat && {
        left: (hl.x / nat[0]) * 100 + '%', top: (hl.y / nat[1]) * 100 + '%', width: (hl.ancho / nat[0]) * 100 + '%', height: (hl.alto / nat[1]) * 100 + '%',
    };
    const validate = async () => {
        clearTimeout(saveTimers[n]);
        try {
            await sendJ(`/documents/${d.id}/pages/${n}`, 'PATCH', { ...pageBody(p), validada: true });
            p.validated = true;
            toast('✓ ' + t('validat'));
            setCur(nextAttention(d, n) || n);
        } catch (e) { fail(e); }
    };
    const thumbKey = (e, k) => {
        if (e.key !== 'ArrowDown' && e.key !== 'ArrowUp') return;
        e.preventDefault();
        const m = k + (e.key === 'ArrowDown' ? 1 : -1);
        if (m >= 1 && m <= d.total) { setCur(m); setTimeout(() => { const b = document.querySelector(`[data-p="${m}"]`); if (b) b.focus(); }); }
    };
    const dot = s => (s === 'esc' ? 'bad' : s);
    return html`<${Shell} active="safata">
        <div className="card row wrap" style=${{ padding: '10px 14px', marginBottom: '12px' }}>
            <a href="#safata" className="btn">‹ ${t('safata')}</a><b>${d.name}</b><span>(${t('pag')} ${n} ${t('de')} ${d.total})</span>
            ${totalW > 0 && chip('w', `! ${t('revisar_n')}: ${totalW} ${t('avisos')}`)}
            <span className="sp"></span>
            <button type="button" className="btn" disabled=${!done || !ed} onClick=${() => reOcr(d, n)}>↻ ${t('retranscriure')}</button>
            ${!ed && html`<a className="btn" href="#anonimitzar">${t('an_t')} →</a>`}
            ${st === 'bad'
                ? html`<button type="button" className="btn pri" disabled=${!ed} onClick=${() => { S.modal = { type: 'esc', d, n }; up(); }}>${t('marcar_esc')}</button>`
                : html`<button type="button" className="btn pri" disabled=${!ed || !done || pend.length > 0 || st === 'v' || st === 'esc'} title=${pend.length ? t('resol') : undefined} onClick=${validate}>✓ ${st === 'v' ? t('validat') : t('validar')}</button>`}
        </div>
        ${!ed && html`<div className="banner w">${t('no_edit')}</div>`}
        ${allDone && html`<div className="banner ok row">✓ ${t('doc_ok')}<span className="sp"></span>
            <a className="btn" href="#safata">${t('nova')}</a><a className="btn" href="#jg" onClick=${() => { S.jgId = d.id; S.jg = null; }}>${t('comprovar')} →</a>
            <a className="btn pri" href="#anonimitzar">${t('an_t')} →</a></div>`}
        <div className="rev">
            <div className="card thumbs" role="list" aria-label=${t('th_pag')}>
                <div className="thumbs-h">${d.total} ${t('pag')} · ${docPages(d).filter(x => x.status === 'done').length} ${t('th_fetes')}</div>
                ${range(d.total).map(k => { const s = pstate(d.pages[k]); return html`<button key=${k} type="button" data-p=${k} className=${'thumb' + (k === n ? ' on' : '')} aria-current=${k === n ? 'page' : undefined}
                    onClick=${() => setCur(k)} onKeyDown=${e => thumbKey(e, k)}><span className=${'dot ' + dot(s)}></span>${t('pag')} ${k}${s === 'v' ? ' ✓' : ''}</button>`; })}
            </div>
            <div className="scan card">
                <div className=${'pimg' + (hl === 'none' ? ' outline' : hl === 'wait' ? ' wait' : '') + (st === 'bad' ? ' ilegible' : '')}>
                    ${done && html`<img src=${`${API}/documents/${d.id}/pages/${n}/image?v=${p.img || 0}`} alt=${`${t('pag')} ${n}`}
                        onLoad=${e => setNat([e.currentTarget.naturalWidth, e.currentTarget.naturalHeight])} />`}
                    ${box && html`<span className="hlbox" style=${box}></span>`}
                </div>
            </div>
            <div className="card rtxt">
                <div className="tool"><b style=${{ color: 'var(--t)' }}>Text</b> · ${ed ? t('desat') : t('nomes_lect')}
                    ${done && p.quality !== 'bad' && html`<span className=${'chip ' + (p.diff ? (p.diff.some(x => x.diff) ? 'bad' : 'ok') : 'n')}>${p.diff ? `${t('dues_l')} · ${p.diff.filter(x => x.diff).length} ${t('difs')}` : t('una_l')}</span>`}
                    <span className="sp"></span>${done ? `${t('contrast')} ${p.contrast ?? '—'}` : ''} · ${t('seg')}</div>
                ${!done ? html`<div style=${{ padding: '20px' }} className="doc-s">${p.status === 'run' ? html`<span className="spin" aria-hidden="true"></span> ${t('pend_pag')}` : t('en_cua')}</div>`
                : st === 'bad' || (p.quality === 'bad' && p.esc) ? html`<div style=${{ padding: '20px' }}><div className="banner bad"><b>✕ ${t('il_t')}</b> (${t('contrast').toLowerCase()} ${p.contrast + ' < 80'})<br />${t('il_s2')}</div>
                    ${p.esc && html`<div className="banner w">${t('marcar_esc')} ✓</div>`}</div>`
                : html`<${Frag}><${FmtBar} d=${d} p=${p} ed=${ed} /><${TextPane} key=${d.id + n + '-' + p.ver} d=${d} p=${p} /><//>`}
                ${hl === 'none' && html`<div className="tool foot doc-s">${t('no_capa')}</div>`}
            </div>
        </div>
    <//>`;
}

// ---------- justícia gratuïta ----------
async function runJg(id) {
    S.jgId = id; S.jg = { loading: true }; S.jgPage = 1; up();
    try {
        const [res, det] = await Promise.all([sendJ(`/documents/${id}/justicia-gratuita`, 'POST'), getJ(`/documents/${id}`)]);
        S.jg = { ...res, id, name: det.nombre_original, sent: (det.justicia_gratuita || {}).enviado_en || null };
    } catch (e) { S.jg = null; fail(e); }
    up();
}
async function sendJg() {
    try {
        const r = await sendJ(`/documents/${S.jg.id}/justicia-gratuita/send`, 'POST');
        S.jg.sent = r.enviado_en; toast('✓ ' + t('env_ok')); up();
    } catch (e) { fail(e); }
}
function JG() {
    useEffect(() => { if (!S.docs.length) loadList(); if (S.jgId && (!S.jg || S.jg.id !== S.jgId)) runJg(S.jgId); }, []);
    const j = S.jg, ready = j && !j.loading;
    const opts = S.docs.filter(d => d.num_paginas);
    const col = c => (c === 'ok' ? 'var(--ok)' : c === 'w' ? 'var(--w)' : 'var(--p)');
    const cls = e => (e === 'presente' ? 'ok' : e === 'incompleto' ? 'w' : 'bad');
    const lbl = e => t(e === 'presente' ? 'complet' : e === 'incompleto' ? 'incomplet' : e === 'ilegible' ? 'il_t' : 'falta');
    const det = x => [x.paginas.length ? `${t('pag')} ${x.paginas.join(', ')}` : '', x.detalle || '', x.meses && x.meses.length ? x.meses.join(', ') : '',
        x.paginas_ilegibles.length ? `${t('pag')} ${x.paginas_ilegibles.join(', ')}: ${t('il_t').toLowerCase()}` : ''].filter(Boolean).join(' · ');
    const da = ready && j.datos;
    const eur = v => (v == null ? '—' : v.toLocaleString(lang === 'ca' ? 'ca-ES' : 'es-ES', { minimumFractionDigits: 2 }) + ' €');
    return html`<${Shell} active="jg">
        <h1>${ready ? j.name + ' · ' : ''}${t('jg_t')}</h1><p className="sub">${t('jg_s2')}</p>
        <div className="row" style=${{ marginBottom: '12px' }}>
            <select className="search" aria-label=${t('tria_doc')} value=${S.jgId} onChange=${e => { if (e.target.value) runJg(e.target.value); }}>
                <option value="">${t('tria_doc')}</option>
                ${opts.map(d => html`<option key=${d.id} value=${d.id}>${d.nombre_original} (${d.num_paginas} ${t('pag')})</option>`)}
            </select>
        </div>
        ${!j && (opts.length ? html`<div className="feats">${opts.map(d => html`<button type="button" key=${d.id} className="card feat jgdoc" onClick=${() => runJg(d.id)}>
                <div className="doc-t">${d.nombre_original}</div>
                <div className="doc-s">${d.num_paginas} ${t('pag')}${d.subido_por ? ' · ' + d.subido_por : ''} · ${hhmm(d.creado_en)}</div>
                <div style=${{ marginTop: '8px' }}>${chip(...(EST[d.estado] ? [EST[d.estado][0], t(EST[d.estado][1])] : ['n', d.estado]))}</div></button>`)}</div>`
            : html`<${Empty} msg=${t('buida')} />`)}
        ${j && j.loading && html`<div className="card" style=${{ padding: '20px' }}><span className="spin" aria-hidden="true"></span> ${t('comprovant')}</div>`}
        ${ready && html`<${Frag}>
        ${j.sent && html`<div className="banner ok row">✓ ${t('env_ok')} (${hhmm(j.sent)})<span className="sp"></span><a className="btn pri" href="#anonimitzar" onClick=${() => { S.an = null; }}>${t('an_t')} →</a></div>`}
        <div className="grid2">
            <div className="card"><div className="box-h">${t('aportada')}</div>${j.documentos.map(x => { const c = cls(x.estado); return html`<div key=${x.tipo} className=${'check' + (x.paginas.length ? ' click' : '')} onClick=${x.paginas.length ? () => { S.jgPage = x.paginas[0]; up(); } : undefined}>
                <span className="ic" style=${{ color: col(c) }}>${c === 'ok' ? '✓' : c === 'w' ? '!' : '✕'}</span><div className="sp"><div>${jgName(x)}${x.requerido ? '' : ' · ' + t('opcional')}</div><div className="doc-s">${det(x)}</div></div>${chip(c, lbl(x.estado))}</div>`; })}
                ${j.paginas_sin_clasificar.length > 0 && html`<div className="check doc-s">${t('sense_classif')}: ${t('pag')} ${j.paginas_sin_clasificar.join(', ')}</div>`}
            </div>
            <div className="card"><div className="box-h">${t('dades')}</div>
                <div className="kv"><span>${t('sol')}</span><b>${da.solicitante || '—'}</b>
                    <span>DNI</span><b>${da.dni || '—'} ${da.dni && html`<span style=${{ color: da.dni_valido ? 'var(--ok)' : 'var(--p)' }}>${da.dni_valido ? '✓' : '✕'}</span>`}</b>
                    <span>${t('ingressos')}</span><b>${eur(da.ingresos_anuales)}</b><span>${t('membres')}</span><b>${da.miembros_unidad_familiar ?? '—'}</b>
                    <span>${t('proc')}</span><b>${da.procedimiento || '—'}</b><span>${t('domicili')}</span><b>${da.domicilio || '—'}</b></div>
                <div style=${{ padding: '0 18px' }}><div className="banner w"><b>${t('orient')}</b> ${t('orient2')}</div>
                    ${j.completo ? html`<div className="banner ok">✓ ${t('jg_complet')}</div>` : html`<div className="banner bad">${t('jg_falta')}</div>`}</div>
                <div className="row" style=${{ padding: '6px 18px 18px' }}>
                    <button type="button" className="btn" disabled=${!j.requerimiento} onClick=${() => { S.modal = { type: 'dem', text: j.requerimiento }; up(); }}>${t('demanar')}</button>
                    <button type="button" className="btn pri" disabled=${!!j.sent} onClick=${() => { if (j.completo) sendJg(); else { S.modal = { type: 'jgsend' }; up(); } }}>${t('enviar_tram')}</button>
                </div>
            </div>
        </div>
        <${JgPreview} j=${j} /><//>`}
    <//>`;
}
// Vista previa: miniaturas de todas las páginas con su tipo detectado; clic en una o en un documento la amplía.
const jgName = x => (t('jgt_' + x.tipo) === 'jgt_' + x.tipo ? x.nombre : t('jgt_' + x.tipo));
function JgPreview({ j }) {
    const tipoDe = {};
    j.documentos.forEach(x => [...x.paginas, ...x.paginas_ilegibles].forEach(p => { tipoDe[p] = jgName(x); }));
    const total = Math.max(0, ...Object.keys(tipoDe).map(Number), ...j.paginas_sin_clasificar,
        (S.docs.find(d => d.id === j.id) || {}).num_paginas || 0);
    const cur = S.jgPage && S.jgPage <= total ? S.jgPage : 1;
    const src = n => `${API}/documents/${j.id}/pages/${n}/image`;
    return html`<div className="card" style=${{ marginTop: '16px' }}><div className="box-h row">${t('jg_prev')}<span className="sp"></span>
            <button type="button" className="btn" onClick=${async () => { try { await loadDoc(j.id); S.cur = cur; S.hl = null; go('#revisio'); } catch (e) { fail(e); } }}>${t('jg_obrir')} →</button></div>
        <div className="jgprev">
            <div className="jgthumbs">${Array.from({ length: total }, (_, i) => i + 1).map(n => html`<button type="button" key=${n}
                className=${'thumb' + (n === cur ? ' on' : '')} onClick=${() => { S.jgPage = n; up(); }}>
                <img src=${src(n)} alt="" loading="lazy" /><span><b>${t('pag')} ${n}</b><br />${tipoDe[n] || t('sense_classif')}</span></button>`)}</div>
            <div className="scan"><div className="pimg"><img key=${cur} src=${src(cur)} alt=${`${t('pag')} ${cur}`} /></div></div>
        </div></div>`;
}

// ---------- anonimitzar ----------
// Modo de la maqueta → modo del endpoint y accion_aplicada (V15).
const MODES = { censurar: ['censurar', 'censurar'], esborrar: ['borrar', 'eliminado'], tatxar: ['tachar', 'tachado'],
    etiqueta: ['etiqueta', 'etiqueta'], pseudonim: ['seudonimo', 'pseudonimizado'], inicials: ['iniciales', 'iniciales'] };
const modeOf = accion => Object.keys(MODES).find(k => MODES[k][1] === accion) || 'esborrar';
const isOn = a => a.decision_revisor !== 'falso_positivo' && a.accion_aplicada !== 'mantenido';
// Igual que anonymize.sustitucion del backend, pero con la tabla de seudónimos de todo el documento.
function pseudo(list) {
    const tab = {}, out = {};
    list.forEach(a => {
        const key = a.categoria + '|' + a.texto_original.toLowerCase().split(/\s+/).join(' ');
        if (!(key in tab)) {
            const n = Object.keys(tab).filter(k => k.startsWith(a.categoria + '|')).length;
            tab[key] = a.categoria === 'NOMBRE_PERSONA' ? `Persona ${String.fromCharCode(65 + (n % 26))}${n < 26 ? '' : Math.floor(n / 26)}` : `[${a.categoria} ${n + 1}]`;
        }
        out[a.id] = tab[key];
    });
    return out;
}
// Flujo del backend: anonimizar (ocr_completado) → abrir revisión → tomarla → decidir anotaciones.
async function loadAn(id) {
    S.an = { loading: true, id }; up();
    try {
        let det = await getJ(`/documents/${id}`);
        if (det.estado === 'ocr_completado') {
            await sendJ(`/documents/${id}/anonymize`, 'POST', { modo: MODES[S.anMode][0] });
            det = await getJ(`/documents/${id}`);
        }
        if (!['en_revision', 'aprobado', 'exportado'].includes(det.estado)) throw new Error(t('an_no') + ' (' + det.estado + ')');
        let rev = null;
        if (det.estado === 'en_revision') {
            const all = (await getJ('/reviews?limit=100')).items.filter(r => r.documento_id === id);
            rev = all.find(r => r.estado === 'en_proceso') || all.find(r => r.estado === 'en_cola');
            if (!rev) rev = await sendJ(`/documents/${id}/reviews`, 'POST');
            if (rev.estado === 'en_cola') rev = await sendJ(`/reviews/${rev.id}/claim`, 'POST');
        }
        const [an, pg, cats] = await Promise.all([getJ(`/documents/${id}/annotations`), getJ(`/documents/${id}/pages`), getJ('/categories?activa=true')]);
        const texts = {};
        pg.items.forEach(p => { texts[p.numero] = p.texto || ''; });
        const anns = an.items;
        if (anns.length) S.anMode = modeOf((anns.find(isOn) || anns[0]).accion_aplicada);
        S.an = { id, name: det.nombre_original, estado: det.estado, rev, anns, texts, total: pg.items.length, cats: cats.items };
        S.anonPage = Math.min(S.anonPage, S.an.total) || 1;
        S.curDoc = S.curDoc && S.curDoc.id === id ? S.curDoc : null; remember(id);
    } catch (e) { S.an = { error: e.message, id }; }
    up();
}
const anEditable = () => S.an && S.an.estado === 'en_revision' && S.an.rev;
// Aplica la decisión a varias anotaciones (PATCH /annotations/{id}) y guarda lo que devuelve el backend.
async function decide(list, on, mode = S.anMode) {
    if (!anEditable()) return toast(t('an_ro'));
    const ps = mode === 'pseudonim' ? pseudo(S.an.anns) : {};
    try {
        // De 4 en 4: todas a la vez agotan el pool de BD (10 conexiones) y salen 503.
        for (let i = 0; i < list.length; i += 4) {
            await Promise.all(list.slice(i, i + 4).map(async a => {
                const body = on ? { decision_revisor: 'confirmado', accion_aplicada: MODES[mode][1] } : { decision_revisor: 'falso_positivo' };
                if (on && ps[a.id]) body.texto_sustitucion = ps[a.id];
                Object.assign(a, await sendJ(`/annotations/${a.id}`, 'PATCH', body));
            }));
        }
    } catch (e) { fail(e); }
    up();
}
const toggleEnt = (a, all) => decide(all ? S.an.anns.filter(x => x.texto_original === a.texto_original) : [a], !isOn(a));
async function setMode(m) {
    if (!anEditable()) return toast(t('an_ro'));
    S.anMode = m; up();
    await decide(S.an.anns.filter(isOn), true, m);
}
async function confirmExport() {
    const A = S.an;
    try {
        if (A.estado === 'en_revision') {
            const open = A.anns.filter(a => !a.decision_revisor);
            if (open.length) await decide(open, true);
            const rev = (await getJ('/reviews?limit=100')).items.find(r => r.id === A.rev.id);
            await sendJ(`/reviews/${A.rev.id}`, 'PATCH', { estado: 'aprobado' }, { 'If-Match': rev.actualizado_en });
        }
        S.an = null;
        await exportDoc(A.id, A.name);
    } catch (e) { fail(e); }
}
function entTip(el, a) {
    const r = el.getBoundingClientRect();
    S.pop = { type: 'ent', a, left: r.left + scrollX, top: r.bottom + scrollY + 8 }; up();
}
function Ent({ a }) {
    const tagged = ['etiqueta', 'pseudonim', 'inicials'].includes(S.anMode);
    const on = isOn(a), cls = S.original ? 'orig' : !on ? 'off' : tagged ? 'm-tag' : 'm-' + S.anMode;
    const hlt = S.anHl && (S.anHl.c === a.categoria || S.anHl.e === a.id);
    const tip = ev => { if (!S.original) entTip(ev.currentTarget, a); };
    const untip = () => { if (S.pop && S.pop.type === 'ent') { S.pop = null; up(); } };
    return html`<button type="button" className=${'ent ' + cls + (hlt ? ' hlt' : '')} data-e=${a.id}
        aria-label=${!S.original && on ? a.categoria : undefined}
        onClick=${ev => toggleEnt(a, ev.shiftKey)} onMouseEnter=${tip} onMouseLeave=${untip} onFocus=${tip} onBlur=${untip}>${!S.original && on && tagged ? a.texto_sustitucion : a.texto_original}</button>`;
}
// Texto de la página partido por las anotaciones (offsets sobre el texto del bloque). Nunca HTML.
function pageParts(n) {
    const txt = S.an.texts[n] || '', out = [];
    let pos = 0;
    S.an.anns.filter(a => a.pagina_numero === n).sort((x, y) => x.inicio_offset - y.inicio_offset).forEach(a => {
        if (a.inicio_offset < pos) return;
        if (a.inicio_offset > pos) out.push(txt.slice(pos, a.inicio_offset));
        out.push(html`<${Ent} key=${a.id} a=${a} />`);
        pos = a.fin_offset;
    });
    out.push(txt.slice(pos));
    return out;
}
function hoverListEnt(a) {
    S.anHl = { e: a.id };
    if (a.pagina_numero !== S.anonPage) S.anonPage = a.pagina_numero;
    up();
    setTimeout(() => { const b = document.querySelector(`.ent[data-e="${a.id}"]`); if (b) b.scrollIntoView({ block: 'nearest', behavior: 'smooth' }); });
}
function Anonimitzar() {
    useEffect(() => {
        const id = (S.curDoc && S.curDoc.id) || (S.an && S.an.id) || S.jgId;
        if (id && (!S.an || S.an.id !== id || S.an.error)) loadAn(id);
    }, []);
    const A = S.an;
    if (!A) return html`<${NoDoc} />`;
    if (A.loading) return html`<${Shell} active="safata"><div className="card" style=${{ padding: '20px' }}><span className="spin" aria-hidden="true"></span> ${t('an_carrega')}</div><//>`;
    if (A.error) return html`<${Shell} active="safata"><div className="banner bad">Error: ${A.error}</div><a className="btn" href="#safata">‹ ${t('safata')}</a><//>`;
    const onN = A.anns.filter(isOn).length, ed = anEditable();
    const byCat = {};
    A.anns.forEach(a => { (byCat[a.categoria] = byCat[a.categoria] || []).push(a); });
    const catName = c => (A.cats.find(x => x.codigo === c) || {}).nombre || c;
    const page = dd => { S.anonPage = Math.min(A.total, Math.max(1, S.anonPage + dd)); up(); };
    return html`<${Shell} active="safata">
        <div className="card row wrap" style=${{ padding: '10px 14px', marginBottom: '12px' }}>
            <a href="#safata" className="btn">‹ ${t('safata')}</a><b>${t('an_t')} · ${A.name}</b><span>(${t('pag')} ${S.anonPage} ${t('de')} ${A.total})</span>
            <button type="button" className="btn" aria-label="‹" disabled=${S.anonPage === 1} onClick=${() => page(-1)}>‹</button>
            <button type="button" className="btn" aria-label="›" disabled=${S.anonPage === A.total} onClick=${() => page(1)}>›</button>
            <span className="sp"></span>
            <button type="button" className="btn" onClick=${() => { S.original = !S.original; up(); }}>${S.original ? t('vista_an') : t('vista')}</button>
            <button type="button" className="btn pri" onClick=${() => { S.modal = { type: 'expan' }; up(); }}>⤓ ${t('exp_an')}</button>
        </div>
        ${!ed && html`<div className="banner w">${t('an_ro')}</div>`}
        <div className="anon">
            <div className="card doc" style=${{ whiteSpace: 'pre-wrap' }}>${A.texts[S.anonPage] ? pageParts(S.anonPage) : html`<span className="doc-s">${t('buit')}</span>`}</div>
            <aside className="card side"><h3>${t('an_panel')}</h3><div className="doc-s">${A.anns.length} ${t('detect')} · ${onN} ${t('anonim')}${A.anns.some(a => !a.decision_revisor) ? ` (${A.anns.filter(a => !a.decision_revisor).length} ${t('sense_dec')})` : ''}</div>
                <h5>${t('com')}</h5>
                <div className="modes">${Object.keys(MODES).map(m => html`<button key=${m} type="button" className=${S.anMode === m ? 'on' : ''} aria-pressed=${S.anMode === m} disabled=${!ed} onClick=${() => setMode(m)}>${t('m_' + m)}</button>`)}</div>
                ${S.anMode === 'tatxar' && html`<div className="banner w" style=${{ marginTop: '8px' }}>${t('tatxar_av')}</div>`}
                <h5>${t('que')}</h5>
                ${!A.anns.length && html`<div className="doc-s">${t('cap_dada')}</div>`}
                ${Object.keys(byCat).map(c => { const all = byCat[c], chk = all.some(isOn); return html`<label key=${c} className="cat" onMouseEnter=${() => { S.anHl = { c }; up(); }} onMouseLeave=${() => { S.anHl = null; up(); }}>
                    <input type="checkbox" checked=${chk} disabled=${!ed}
                        onFocus=${() => { S.anHl = { c }; up(); }} onBlur=${() => { S.anHl = null; up(); }}
                        onChange=${e => decide(all, e.target.checked)} />${catName(c)}<em>${all.length}</em></label>`; })}
                <details open=${S.detOpen} onToggle=${e => { S.detOpen = e.currentTarget.open; }}><summary>${t('veure')} (${onN})</summary>
                    <ul>${A.anns.filter(isOn).map(a => html`<li key=${a.id} onMouseEnter=${() => hoverListEnt(a)} onMouseLeave=${() => { S.anHl = null; up(); }}>
                        <span>■ ${a.texto_original.length > 24 ? a.texto_original.slice(0, 24) + '…' : a.texto_original}</span><span className="doc-s">${a.categoria}</span></li>`)}</ul>
                </details>
            </aside>
        </div>
    <//>`;
}
// Código de evento → texto: con traducción si existe; si no, el código en minúsculas y sin guiones bajos.
const evName = ev => (t('ev_' + ev) === 'ev_' + ev ? ev.toLowerCase().replace(/_/g, ' ') : t('ev_' + ev));
function AuditCard({ style }) {
    return html`<div className="card" style=${style}><div className="box-h">${t('registre')}</div>
        <div className="audit">${S.audit.length ? S.audit.map(a => html`<div key=${a.id}>${hhmm(a.creado_en)}  ${evName(a.evento)} ${a.detalle && a.detalle.pagina ? t('pag') + ' ' + a.detalle.pagina : ''}</div>`) : t('cap')}</div></div>`;
}
function Exportat() {
    const E = S.exp;
    useEffect(() => { if (!E && S.curDoc && S.curDoc.estado === 'exportado') exportDoc(S.curDoc.id, S.curDoc.name); }, []);
    if (!E) return html`<${NoDoc} />`;
    return html`<${Shell} active="arxiu">
        <div className="card" style=${{ padding: '28px', maxWidth: '720px', margin: '0 auto' }}>
            <div className="banner ok"><b>✓ ${t('exp_t')}</b> · ${E.name} · ${t('exp_s')}</div>
            <p className="doc-s" style=${{ wordBreak: 'break-all' }}>SHA-256: <code>${E.hash}</code></p>
            <ul style=${{ lineHeight: 2 }}>${['g1', 'g2', 'g3', ...(S.anMode === 'pseudonim' ? ['g4'] : [])].map(g => html`<li key=${g}>${t(g)}</li>`)}</ul>
            <div className="row"><button type="button" className="btn pri" onClick=${() => { download(E.blob, E.name); toast('⤓ ' + E.name); }}>⤓ ${t('descarregar')}</button><a className="btn" href="#safata">${t('tornar_safata')}</a></div>
        </div>
        <${AuditCard} style=${{ maxWidth: '720px', margin: '16px auto 0' }} />
    <//>`;
}
function Informes() {
    useEffect(() => {
        Promise.all([getJ('/reports/summary'), getJ('/audit?limit=50')])
            .then(([s, a]) => { S.summary = s; S.audit = a.items; up(); }).catch(fail);
    }, []);
    const s = S.summary;
    return html`<${Shell} active="informes">
        <h1>${t('inf_t')}</h1><p className="sub">${t('inf_s2')}</p>
        ${!s ? html`<div className="card" style=${{ padding: '20px' }}><span className="spin" aria-hidden="true"></span></div>` : html`<${Frag}>
        <div className="kpis"><div className="card kpi"><b>${s.paginas_mes}</b><span>${t('i1')}</span></div>
            <div className="card kpi"><b>${s.tiempo_medio_revision_seg == null ? '—' : s.tiempo_medio_revision_seg + ' s'}</b><span>${t('i2b')}</span></div>
            <div className="card kpi"><b>${s.paginas_reescaneadas}</b><span>${t('i3b')}</span></div><div className="card kpi"><b>${s.jg_enviados}</b><span>${t('i4')}</span></div></div>
        <div className="kpis">
            <div className="card kpi"><b>${s.documentos_mes}</b><span>${t('s_docs')}</span></div>
            <div className="card kpi"><b>${s.exportados_mes}</b><span>${t('exp_mes')}</span></div>
        </div>
        <div className="card row wrap" style=${{ padding: '12px 18px', marginBottom: '16px' }}>${Object.entries(s.documentos_por_estado || {}).map(([k, v]) => html`<span key=${k}>${chip((EST[k] || ['n'])[0], `${t((EST[k] || [0, k])[1])}: ${v}`)}</span>`)}</div>
        <//>`}
        <${AuditCard} />
    <//>`;
}

// ---------- popover, modales, guía ----------
function Pop() {
    const P = S.pop, ref = useRef(null);
    useEffect(() => { if (P.type === 'warn') { const b = ref.current && ref.current.querySelector('button'); if (b) b.focus(); } }, [P]);
    const style = { left: Math.max(8, Math.min(P.left, innerWidth - 320)) + 'px', top: P.top + 'px' };
    if (P.type === 'ent') {
        const a = P.a, n = S.an ? S.an.anns.filter(x => x.texto_original === a.texto_original).length : 1;
        return html`<div className="pop" role="tooltip" style=${style}><b>${a.categoria}</b>«${a.texto_original}» · ${t('apareix')} ${n} ${n > 1 ? t('vegades') : t('vegada')}
            <div className="doc-s">${isOn(a) ? t('tip_on') : t('tip_off')}</div><div className="doc-s">🔒 ${t('registrada')}</div></div>`;
    }
    const s = pageSegs(P.p).find(x => x.id === P.id);
    if (!s) return null;
    const fix = (v, manual) => applyFix(P.p, s.id, v, manual);
    return html`<div className="pop" role="dialog" aria-label=${s.kind === 'doubt' ? t('dues') : t(s.sub + '_bad')} style=${style} ref=${ref}>
        ${s.kind === 'doubt'
            ? html`<b>${t('dues')}</b>${t('l1')}: «${s.t}» · ${t('l2')}: «${s.alt}»<br />${t('comprova')}
                <div className="row wrap"><button type="button" className="btn pri" onClick=${() => fix(s.alt)}>${t('usar')} «${s.alt}»</button><button type="button" className="btn" onClick=${() => fix(s.t)}>${t('mantenir')} «${s.t}»</button></div>`
            : html`<b>${t(s.sub + '_bad')}</b>${t(s.sub + '_sug2')}
                <div className="row wrap"><button type="button" className="btn pri" onClick=${() => fix(s.alt)}>${t('corregir')} ${s.alt}</button><button type="button" className="btn" onClick=${() => fix(s.t, true)}>${t('editar')}</button></div>`}
    </div>`;
}
function Modal() {
    const M = S.modal, ref = useRef(null);
    const [file, setFile] = useState(null);
    const [ok, setOk] = useState(false);
    const [txt, setTxt] = useState(M.text || '');
    useEffect(() => { const f = ref.current && ref.current.querySelector('input,textarea,button'); if (f) f.focus(); }, []);
    const close = () => { S.modal = null; up(); };
    let body;
    if (M.type === 'esc') {
        const { d, n } = M, p = d.pages[n];
        body = html`<h2>${t('esc_t')}</h2><p>${t('esc_s')} (${t('pag')} ${n}).</p>
            <input type="file" accept=".pdf,image/*" style=${{ width: '100%' }} onChange=${e => setFile(e.target.files[0] || null)} />
            <div className="row" style=${{ marginTop: '16px' }}><span className="sp"></span><button type="button" className="btn" onClick=${close}>${t('cancel')}</button>
                <button type="button" className="btn" onClick=${() => { p.esc = true; S.modal = null; S.cur = nextAttention(d, n) || n; up(); }}>${t('marcar_esc')}</button>
                <button type="button" className="btn pri" disabled=${!file} onClick=${() => { S.modal = null; reOcr(d, n, file); }}>${t('pujar_pag')}</button></div>`;
    } else if (M.type === 'jgsend') {
        body = html`<h2>${t('enviar_tram')}</h2><p className="banner bad">${t('jg_falta')}</p><p>${t('jg_env_inc')}</p>
            <div className="row" style=${{ marginTop: '16px' }}><span className="sp"></span><button type="button" className="btn" onClick=${close}>${t('cancel')}</button>
                <button type="button" className="btn pri" onClick=${() => { close(); sendJg(); }}>${t('enviar_tram')}</button></div>`;
    } else if (M.type === 'dem') {
        body = html`<h2>${t('msg_t')}</h2><textarea aria-label=${t('msg_t')} style=${{ width: '100%', height: '190px', font: '14px/1.5 Roboto', border: '1px solid var(--line)', borderRadius: '6px', padding: '10px' }} value=${txt} onChange=${e => setTxt(e.target.value)}></textarea>
            <div className="row" style=${{ marginTop: '14px' }}><span className="sp"></span><button type="button" className="btn" onClick=${close}>${t('cancel')}</button>
                <button type="button" className="btn pri" onClick=${() => { close(); navigator.clipboard.writeText(txt).then(() => toast('✓ ' + t('req_copiat')), () => toast(t('req_nocopia'))); }}>${t('copiar')}</button></div>`;
    } else {
        const pend = S.an ? S.an.anns.filter(a => !a.decision_revisor).length : 0;
        body = html`<h2>${t('conf_t')}</h2><p>${t('conf_1')}</p>
            ${pend > 0 && html`<p className="banner w">${pend} ${t('pend_conf')}</p>`}
            <label className="cat"><input type="checkbox" checked=${ok} onChange=${e => setOk(e.target.checked)} /> ${t('conf_c')}</label>
            <div className="row" style=${{ marginTop: '16px' }}><span className="sp"></span><button type="button" className="btn" onClick=${close}>${t('cancel')}</button>
                <button type="button" className="btn pri" disabled=${!ok} onClick=${() => { S.modal = null; up(); confirmExport(); }}>${t('exportar')}</button></div>`;
    }
    return html`<div className="modal-bg"><div className="modal" role="dialog" aria-modal="true" ref=${ref}>${body}</div></div>`;
}
const STEPS = [['login', 'Login'], ['safata', 'Safata → Nou document'], ['processant', 'OCR + semàfor'], ['revisio', 'Revisió i avisos'], ['jg', 'Justícia gratuïta'], ['anonimitzar', 'Anonimització'], ['exportat', 'Exportació'], ['arxiu', 'Arxiu'], ['informes', 'Informes']];
function Guide({ r }) {
    return html`<div className="guide">
        ${S.guideOpen && html`<ol>${STEPS.map(([k, l]) => html`<li key=${k} className=${k === r ? 'on' : ''}><a href=${'#' + k}>${l}</a></li>`)}</ol>`}
        <button type="button" className="btn" aria-expanded=${S.guideOpen} onClick=${() => { S.guideOpen = !S.guideOpen; up(); }}>${S.guideOpen ? '✕' : '☰ ' + t('guia')}</button>
    </div>`;
}

// ---------- router ----------
const VIEWS = { login: Login, safata: Safata, processant: Processant, revisio: Revisio, jg: JG, anonimitzar: Anonimitzar, exportat: Exportat, arxiu: Arxiu, informes: Informes };
function onKey(ev) {
    if (ev.key === 'Escape' && (S.pop || S.modal)) { S.pop = null; S.modal = null; up(); return; }
    if (ev.ctrlKey && ev.key === 'ArrowRight' && location.hash === '#revisio' && S.curDoc) {
        ev.preventDefault();
        const w = document.querySelector('#txt .doubt, #txt .invalid'), p = S.curDoc.pages[S.cur];
        if (w && editable(S.curDoc)) { w.focus(); openWarn(w, p); } else { const n = nextAttention(S.curDoc, S.cur); if (n) setCur(n); }
    }
}
function onDocClick(ev) {
    if (S.pop && !ev.target.closest('.pop,[data-wid],.ent')) { S.pop = null; up(); }
}
function App() {
    const [, setTick] = useState(0);
    rerender = () => setTick(x => x + 1);
    useEffect(() => {
        const onHash = () => { S.pop = null; S.modal = null; S.hl = null; S.anHl = null;
            S.sel = new Set(); S.f = { estado: '', per: '', modo: '' }; scrollTo(0, 0); up(); };
        addEventListener('hashchange', onHash);
        document.addEventListener('keydown', onKey);
        document.addEventListener('click', onDocClick);
        boot();
        return () => { removeEventListener('hashchange', onHash); document.removeEventListener('keydown', onKey); document.removeEventListener('click', onDocClick); };
    }, []);
    if (S.booting) return html`<div className="card login"><${Logo} /><p><span className="spin" aria-hidden="true"></span></p></div>`;
    let r = location.hash.slice(1) || (S.user ? 'safata' : 'login');
    if (r === 'landing') { history.replaceState(null, '', '#safata'); r = 'safata'; } // ruta antigua: la safata es ahora la portada
    if (!VIEWS[r] || !S.user) r = 'login';
    document.documentElement.lang = lang;
    return html`<${Frag}>
        <${VIEWS[r]} key=${r} />
        <${Guide} r=${r} />
        ${S.pop && html`<${Pop} />`}
        ${S.modal && html`<${Modal} key=${S.modal.type} />`}
        ${S.toast && html`<div className="toast" role="status">${S.toast}</div>`}
    <//>`;
}

ReactDOM.createRoot(document.getElementById('root')).render(html`<${App} />`);
