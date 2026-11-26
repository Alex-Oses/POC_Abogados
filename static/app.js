// Frontend React 18 (UMD + htm, sin build) servido por Flask. Aspecto y rutas de maqueta/index.html.
// Estado global mutable `S` (como la maqueta) + `up()` para repintar. Datos reales: /ocr, /page, /export.
const { useState, useEffect, useRef } = React;
const html = htm.bind(React.createElement);
const Frag = React.Fragment;
const L = window.L;
let lang = 'ca';
const t = k => (L[lang][k] ?? L.ca[k] ?? k);
const range = n => Array.from({ length: n }, (_, k) => k + 1);

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
    user: null, docs: [], curDoc: null, cur: 1, mode: 'single', q: '', audit: [],
    hl: null, pop: null, modal: null, toast: '', guideOpen: false,
    sent: false, exported: false, anMode: 'censurar', anonPage: 1, detOpen: false, original: false, anHl: null,
    cats: { nom: 1, dni: 1, adreca: 1, contacte: 1, iban: 1, matricula: 0, menor: 1, salut: 1, magistrat: 1, juridica: 0 },
    on: new Set(), off: new Set(),
};
let rerender = () => {};
const up = () => rerender();
const go = h => { location.hash = h; };
function log(e) { S.audit.unshift(`${new Date().toLocaleTimeString('ca-ES')}  ${S.user ? S.user.name : '—'}  ${e}`); }
let toastTimer = null;
function toast(m) { S.toast = m; up(); clearTimeout(toastTimer); toastTimer = setTimeout(() => { S.toast = ''; up(); }, 2600); }

// ---------- modelo de página ----------
const newPage = n => ({ n, status: 'q', fixes: {}, ver: 0 });
function setPageData(p, ev) {
    Object.assign(p, {
        status: 'done', text: ev.text || '', diff: ev.diff || null, time: ev.time, chars: ev.chars,
        contrast: ev.contrast, quality: ev.quality || 'ok', fixes: {}, edit: undefined,
        validated: false, esc: false, _segs: null, img: Date.now(),
    });
    p.ver++;
}
function splitInvalid(text, rect, out) {
    let last = 0, m;
    RE_ID.lastIndex = 0;
    while ((m = RE_ID.exec(text))) {
        const iban = m[0].startsWith('ES'), alt = iban ? ibanFix(m[0]) : dniFix(m[0]);
        if (alt === null) continue;
        if (m.index > last) out.push({ t: text.slice(last, m.index) });
        out.push({ t: m[0], kind: 'invalid', sub: iban ? 'iban' : 'dni', alt, rect });
        last = m.index + m[0].length;
    }
    if (last < text.length) out.push({ t: text.slice(last) });
}
// Segmentos de la página: texto plano + avisos (doubt = doble lectura, invalid = DNI/IBAN).
function pageSegs(p) {
    if (p._segs) return p._segs;
    const out = [];
    if (p.diff) p.diff.forEach(s => s.diff ? out.push({ t: s.t, kind: 'doubt', alt: s.other ?? '', rect: s.rect }) : splitInvalid(s.t, s.rect, out));
    else splitInvalid(p.text || '', null, out);
    out.forEach((s, i) => { if (s.kind) s.id = 'w' + i; });
    return (p._segs = out);
}
const warns = p => (p && p.status === 'done' && p.quality !== 'bad' ? pageSegs(p).filter(s => s.kind) : []);
const pending = p => warns(p).filter(s => !(s.id in p.fixes));
function pstate(p) {
    if (!p || p.status !== 'done') return 'n';
    if (p.validated) return 'v';
    if (p.esc) return 'esc';
    if (p.quality === 'bad') return 'bad';
    return pending(p).length ? 'w' : 'ok';
}
const finalText = p => p.edit ?? pageSegs(p).map(s => (s.id in p.fixes ? p.fixes[s.id] : s.t)).join('');
const docPages = d => range(d.total).map(n => d.pages[n]).filter(Boolean);
const docAllDone = d => d.total > 0 && docPages(d).every(p => ['v', 'esc'].includes(pstate(p)));
function nextAttention(d, from) {
    for (let k = 1; k <= d.total; k++) {
        const m = ((from - 1 + k) % d.total) + 1;
        if (!['v', 'esc'].includes(pstate(d.pages[m]))) return m;
    }
    return null;
}

// ---------- llamadas al backend ----------
function startUpload(file) {
    if (!file) return;
    if (!/\.pdf$/i.test(file.name)) return toast(t('err_pdf'));
    if (file.size > 50 * 1024 * 1024) return toast(t('err_size'));
    const doc = {
        name: file.name, mode: S.mode, uploadId: null, total: 0, pages: {}, stats: null, error: '', done: false,
        at: new Date().toLocaleTimeString('ca-ES', { hour: '2-digit', minute: '2-digit' }),
    };
    S.docs.unshift(doc); S.curDoc = doc; S.cur = 1;
    log(`Pujat ${file.name} (${S.mode})`);
    go('#processant'); up();
    const fd = new FormData();
    fd.append('pdf', file); fd.append('mode', S.mode);
    // Respuesta NDJSON: una línea por evento (start, page, done, error).
    fetch('/ocr', { method: 'POST', body: fd })
        .then(async r => {
            if (!r.ok) { const j = await r.json().catch(() => ({})); throw new Error(j.error || 'HTTP ' + r.status); }
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
            doc.done = true; up();
        })
        .catch(e => { doc.error = e.message; doc.done = true; up(); });
}
function onEvent(doc, ev) {
    if (ev.type === 'start') {
        doc.uploadId = ev.upload_id; doc.total = ev.total_pages;
        range(doc.total).forEach(n => { doc.pages[n] = newPage(n); });
        if (doc.pages[1]) doc.pages[1].status = 'run';
    } else if (ev.type === 'page') {
        const p = doc.pages[ev.page] || (doc.pages[ev.page] = newPage(ev.page));
        setPageData(p, ev);
        const nx = doc.pages[ev.page + 1];
        if (nx && nx.status === 'q') nx.status = 'run';
    } else if (ev.type === 'done') {
        doc.stats = ev; doc.done = true;
        log(`OCR completat ${doc.name} (${doc.total} pàg.)`);
    } else if (ev.type === 'error') {
        doc.error = ev.error; doc.done = true;
    }
    up();
}
async function reOcr(d, n, file) {
    const p = d.pages[n], fd = new FormData();
    fd.append('mode', d.mode);
    if (file) fd.append('file', file);
    p.status = 'run'; S.hl = null; up();
    try {
        const r = await fetch(`/page/${d.uploadId}/${n}/ocr`, { method: 'POST', body: fd });
        const j = await r.json().catch(() => ({}));
        if (!r.ok || j.error) throw new Error(j.error || 'HTTP ' + r.status);
        setPageData(p, j);
        log(file ? `Pàg. ${n} reescanejada (fitxer pujat) ${d.name}` : `Pàg. ${n} transcrita de nou ${d.name}`);
        toast('✓ ' + (file ? t('esc_ok') : t('retranscriure')));
    } catch (e) {
        p.status = 'done';
        toast('Error: ' + e.message);
    }
    up();
}
async function exportPdf(d) {
    try {
        const pages = range(d.total).map(n => { const p = d.pages[n]; return p && p.status === 'done' && p.quality !== 'bad' ? finalText(p) : ''; });
        const r = await fetch('/export', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ name: d.name, pages }) });
        if (!r.ok) { const j = await r.json().catch(() => ({})); throw new Error(j.error || 'HTTP ' + r.status); }
        const a = document.createElement('a');
        a.href = URL.createObjectURL(await r.blob());
        a.download = d.name.replace(/\.pdf$/i, '') + '_transcrit.pdf';
        a.click();
        setTimeout(() => URL.revokeObjectURL(a.href), 2000);
        log(`Exportat ${d.name} (${d.total} pàg.)`);
        toast('⤓ ' + a.download);
    } catch (e) { toast('Error: ' + e.message); }
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
    const segs = pageSegs(p);
    let changed = false;
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
function onTextInput(p, el) {
    p.edit = el.innerText;
    for (const s of pending(p)) if (!el.querySelector(`[data-wid="${s.id}"]`)) p.fixes[s.id] = '';
    if (!p.editLogged) { p.editLogged = true; log(`Correcció manual pàg. ${p.n}`); }
    up();
}
function openWarn(el, p) {
    const r = el.getBoundingClientRect();
    S.pop = { type: 'warn', p, id: el.dataset.wid, left: r.left + scrollX, top: r.bottom + scrollY + 8 };
    up();
}
function applyFix(p, id, val, manual) {
    const s = pageSegs(p).find(x => x.id === id), tx = document.getElementById('txt');
    const el = tx && tx.querySelector(`[data-wid="${id}"]`);
    p.fixes[id] = val;
    if (el) {
        el.textContent = val; el.className = 'fixed';
        ['contenteditable', 'tabindex', 'role', 'aria-label'].forEach(a => el.removeAttribute(a));
    }
    if (tx) p.edit = tx.innerText;
    log(manual ? `Edició manual «${s.t}» (pàg. ${p.n})` : `Corregit «${s.t}» → «${val}» (pàg. ${p.n})`);
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
function hoverWarn(target, p) {
    const w = target.closest && target.closest('[data-wid]');
    const s = w && pageSegs(p).find(x => x.id === w.dataset.wid);
    setHl(s ? s.rect || 'none' : null);
}

function TextPane({ p }) {
    const ref = useRef(null);
    useEffect(() => { buildText(ref.current, p); }, []); // el padre usa key = doc+pàgina+versió
    return html`<div className="text" id="txt" ref=${ref} contentEditable="true" spellCheck=${false}
        onInput=${() => onTextInput(p, ref.current)}
        onClick=${e => { const w = e.target.closest('[data-wid]'); if (w && !(w.dataset.wid in p.fixes)) openWarn(w, p); }}
        onKeyDown=${e => { const w = e.target.dataset && e.target.dataset.wid; if (w && (e.key === 'Enter' || e.key === ' ') && !(w in p.fixes)) { e.preventDefault(); openWarn(e.target, p); } }}
        onMouseOver=${e => hoverWarn(e.target, p)} onMouseLeave=${() => setHl(null)}
        onFocus=${e => hoverWarn(e.target, p)}></div>`;
}

// ---------- piezas comunes ----------
function Lang({ style }) {
    const set = l => { lang = l; document.documentElement.lang = l; up(); };
    return html`<div className="lang" role="group" aria-label="Idioma" style=${style}>
        ${['ca', 'es'].map(l => html`<button key=${l} type="button" className=${lang === l ? 'on' : ''} aria-pressed=${lang === l} onClick=${() => set(l)}>${l.toUpperCase()}</button>`)}
    </div>`;
}
const Logo = () => html`<div className="logo"><b>ICA<i>T</i></b><small>Il·lustre Col·legi de l'Advocacia de Tarragona</small></div>`;
function logout() { log('Tancament de sessió'); S.user = null; S.curDoc = null; go('#login'); up(); }
function Shell({ active, demo, children }) {
    return html`<${Frag}>
    <header>
        <a href="#landing" className="logo-a" aria-label=${t('inici')}><${Logo} /></a>
        <nav aria-label="Principal">${[['safata', '#safata'], ['jg', '#jg'], ['arxiu', '#arxiu'], ['informes', '#informes']].map(([k, h]) =>
            html`<a key=${k} href=${h} className=${active === k ? 'on' : ''} aria-current=${active === k ? 'page' : undefined}>${t(k)}</a>`)}</nav>
        <${Lang} />
        <div className="user">${t('rol')} <span className="avatar" title=${S.user.email} aria-hidden="true">${S.user.ini}</span>
            <button type="button" className="btn" onClick=${logout}>${t('sortir')}</button></div>
    </header>
    <main>${children}${demo && html`<p className="ficticio">${t('ficticia')}</p>`}</main>
    <//>`;
}
const NoDoc = () => html`<${Shell} active="safata"><div className="card" style=${{ padding: '28px', textAlign: 'center' }}>
    <p>${t('no_doc')}</p><a className="btn pri" href="#safata">‹ ${t('safata')}</a></div><//>`;
const chip = (cls, txt) => html`<span className=${'chip ' + cls}>${txt}</span>`;
function StatsKpis({ s }) {
    if (!s) return null;
    const k = [[s.total_pages, 'st_total'], [s.total_time + ' s', 'st_time'], [s.avg_time_per_page + ' s', 'st_avg'], [s.pages_per_hour_estimate, 'st_ph'], [s.total_chars, 'st_chars']];
    return html`<div className="kpis k5">${k.map(([v, l]) => html`<div key=${l} className="card kpi"><b>${v}</b><span>${t(l)}</span></div>`)}</div>`;
}

// ---------- login y landing ----------
function Login() {
    const [email, setEmail] = useState('demo@icat.cat');
    const [pass, setPass] = useState('demo');
    const submit = e => {
        e.preventDefault();
        const name = email.split('@')[0];
        S.user = { email, name, ini: name.slice(0, 2).toUpperCase() };
        log('Inici de sessió');
        go('#landing'); up();
    };
    return html`<div className="card login">
        <${Logo} />
        <h1 style=${{ margin: '28px 0 22px' }}>${t('login_t')}</h1>
        <form onSubmit=${submit}>
            <label className="fld">${t('correu')}<input type="email" value=${email} onChange=${e => setEmail(e.target.value)} required autoComplete="username" /></label>
            <label className="fld">${t('contrasenya')}<input type="password" value=${pass} onChange=${e => setPass(e.target.value)} required autoComplete="current-password" /></label>
            <button className="btn pri wide" type="submit">${t('login_b')}</button>
        </form>
        <p className="sub" style=${{ marginTop: '10px' }}>${t('login_n')}</p>
        <p className="banner ok" style=${{ marginTop: '22px' }}>🔒 ${t('local')}</p>
        <p className="doc-s">${t('demo_cred')}</p>
        <${Lang} style=${{ display: 'inline-flex', marginTop: '12px' }} />
    </div>`;
}
function Landing() {
    const feats = [['📄', 'f1t', 'f1d'], ['🔁', 'f2t', 'f2d'], ['✍️', 'f3t', 'f3d']];
    return html`<${Shell}>
        <div className="card hero">
            <h1>${t('land_t')}</h1>
            <p className="sub">${t('land_s')}</p>
            <a className="btn pri" href="#safata">${t('comencar')} →</a>
        </div>
        <div className="feats">${feats.map(([i, a, b]) => html`<div key=${a} className="card feat"><div className="big" aria-hidden="true">${i}</div><b>${t(a)}</b><p className="sub">${t(b)}</p></div>`)}</div>
    <//>`;
}

// ---------- safata / arxiu ----------
const FAKE = () => [
    { id: 'JG-2026-1184', t: 'Sol·licitud justícia gratuïta', s: 'Expedient complet: DNI, nòmines, IRPF', tipo: t('jg'), p: 23, st: S.sent ? t('enviat') : t('transcrit'), q: S.sent ? ['ok', '✓ ' + t('validat')] : ['w', '! 4 ' + t('revisar')], r: '10:31', go: '#jg' },
    { id: 'Queixa 2026/311', t: 'Escrit de la persona usuària', s: 'Escanejat per fax', tipo: 'Deontologia', p: 3, st: t('transcrit'), q: ['bad', '✕ ' + t('tornar')], r: '09:15' },
    { id: 'Sentència 70/2020', t: 'Resolució per publicar', s: 'Formació i jurisprudència', tipo: 'Arxiu', p: 4, st: S.exported ? t('exportat') : t('anonimitzar'), q: ['ok', '✓ ' + t('fiable')], r: '09:05', go: '#anonimitzar', arx: S.exported },
    { id: 'Dictamen honoraris 2026/057', t: 'Minuta', s: "Taula d'honoraris i taxació", tipo: 'Honoraris', p: 6, st: t('transcrivint') + ' 4/6', q: ['ok', '✓ ' + t('fiable')], r: '09:58', prog: 66 },
    { id: 'Fòrum Jurídic núm. 12 (1998)', t: 'Hemeroteca', s: "Digitalització de l'hemeroteca", tipo: 'Arxiu', p: 64, st: t('transcrit'), q: ['ok', '✓ ' + t('fiable')], r: 'Ahir', arx: true },
];
function realRow(d) {
    const pg = docPages(d), done = pg.filter(p => p.status === 'done').length, sts = pg.map(pstate);
    const allV = docAllDone(d), nW = pg.reduce((a, p) => a + pending(p).length, 0), nBad = sts.filter(s => s === 'bad').length;
    const st = !d.done ? `${t('transcrivint')} ${done}/${d.total || '…'}` : d.error ? 'Error' : allV ? t('validat') : t('transcrit');
    const q = d.error ? ['bad', '✕ Error'] : nBad ? ['bad', `✕ ${nBad} ${t('tornar')}`] : nW ? ['w', `! ${nW} ${t('revisar')}`] : allV ? ['ok', '✓ ' + t('validat')] : ['ok', '✓ ' + t('fiable')];
    return {
        id: d.name, t: t(d.mode === 'double' ? 'm_double' : 'm_single'), s: d.error || `${t('local')}`, tipo: 'PDF', p: d.total || '…', st, q, r: d.at,
        prog: d.total ? Math.round((done / d.total) * 100) : 0, arx: allV, real: true,
        full: pg.filter(p => p.status === 'done').map(finalText).join(' '),
        open: () => { S.curDoc = d; S.cur = (d.done && nextAttention(d, d.total)) || 1; S.hl = null; go(d.done && !d.error ? '#revisio' : '#processant'); },
    };
}
function Rows({ rows, head }) {
    return html`<div className="card"><table>
        ${head && html`<thead><tr><th></th><th>${t('th_doc')}</th><th>${t('th_tipus')}</th><th>${t('th_pag')}</th><th>${t('th_estat')}</th><th>${t('th_q')}</th><th>${t('th_reb')}</th></tr></thead>`}
        <tbody>${rows.map((d, i) => {
            const open = d.open || (d.go && (() => go(d.go)));
            return html`<tr key=${d.id + i} className=${open ? 'click' : ''} tabIndex=${open ? 0 : undefined}
                onClick=${open || undefined} onKeyDown=${e => { if (open && e.key === 'Enter') open(); }}>
                <td style=${{ width: '44px' }}><div className="tile" style=${{ minHeight: 0, padding: '4px', width: '30px' }}><div className="pg" style=${{ margin: 0, height: '28px', width: '20px' }}></div></div></td>
                <td><div className="doc-t">${d.id} · ${d.t}</div><div className="doc-s">${d.s}</div></td><td>${d.tipo}</td><td>${d.p}</td>
                <td><div className="bar"><i style=${{ width: (d.prog ?? 100) + '%' }}></i></div><span className="doc-s">${d.st}</span></td>
                <td>${chip(d.q[0], d.q[1])}</td><td>${d.r}</td></tr>`;
        })}</tbody></table></div>`;
}
const matchQ = d => { const q = S.q.trim().toLowerCase(); return !q || (d.id + d.t + d.s + (d.full || '')).toLowerCase().includes(q); };
function Search() {
    return html`<input className="search" value=${S.q} placeholder=${t('cerca')} aria-label=${t('cerca')} onChange=${e => { S.q = e.target.value; up(); }} />`;
}
function Safata() {
    const pick = () => document.getElementById('pdfFile').click();
    const realPages = S.docs.flatMap(docPages);
    const nDone = realPages.filter(p => p.status === 'done').length;
    const nW = realPages.filter(p => pstate(p) === 'w').length, nBad = realPages.filter(p => pstate(p) === 'bad').length;
    const drag = {
        onDragEnter: e => { e.preventDefault(); e.currentTarget.classList.add('over'); },
        onDragOver: e => { e.preventDefault(); e.currentTarget.classList.add('over'); },
        onDragLeave: e => e.currentTarget.classList.remove('over'),
        onDrop: e => { e.preventDefault(); e.currentTarget.classList.remove('over'); startUpload(e.dataTransfer.files[0]); },
    };
    const rows = [...S.docs.map(realRow), ...FAKE()].filter(matchQ);
    return html`<${Shell} active="safata" demo=${true}>
        <h1>${t('safata_t')}</h1><p className="sub">${t('safata_s')} ${t('local')}</p>
        <div className="kpis">
            <div className="card kpi"><b>${37 + S.docs.length}</b><span>${t('k1')}</span></div>
            <div className="card kpi"><b>${389 + nDone}</b><span>${t('k2')}</span></div>
            <div className="card kpi"><b style=${{ color: 'var(--w)' }}>${13 + nW}</b><span>${t('k3')}</span></div>
            <div className="card kpi"><b style=${{ color: 'var(--p)' }}>${2 + nBad}</b><span>${t('k4')}</span></div>
        </div>
        <div className="mselect" role="radiogroup" aria-label=${t('mode_l')}>
            ${['single', 'double'].map(m => html`<label key=${m} className=${'mopt' + (S.mode === m ? ' on' : '')}>
                <input type="radio" name="mode" value=${m} checked=${S.mode === m} onChange=${() => { S.mode = m; up(); }} />
                ${t('m_' + m)}${m === 'double' ? ' · ' + t('m_double_n') : ''}</label>`)}
        </div>
        <button type="button" className="drop" onClick=${pick} ...${drag}><b>${t('drop')}</b> ${t('drop2')} · ${t('max50')}</button>
        <input type="file" id="pdfFile" accept=".pdf,application/pdf" hidden onChange=${e => { startUpload(e.target.files[0]); e.target.value = ''; }} />
        <div className="row" style=${{ marginBottom: '12px' }}><${Search} /><button type="button" className="btn pri" onClick=${pick}>＋ ${t('nou')}</button></div>
        <${Rows} rows=${rows} head=${true} />
    <//>`;
}
function Arxiu() {
    const rows = [...S.docs.map(realRow), ...FAKE()].filter(d => d.arx).filter(matchQ);
    return html`<${Shell} active="arxiu" demo=${true}>
        <h1>${t('arxiu_t')}</h1><p className="sub">${t('arxiu_s')}</p>
        <div style=${{ marginBottom: '12px' }}><${Search} /></div>
        <${Rows} rows=${rows} />
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
        <h1 aria-live="polite">${d.done ? `${t('proc_fi')} · ${d.name}` : `${t('proc_t')} ${done}/${d.total || '…'} · ${d.name}`}</h1>
        <p className="sub">${t(d.mode === 'double' ? 'm_double' : 'm_single')} · ${t('proc_s2')}</p>
        ${d.error && html`<div className="banner bad">Error: ${d.error}</div>`}
        <div className="card"><div className="tiles">
            ${d.total === 0 && !d.done && html`<div className="tile run"><div className="pg"></div><span className="spin" aria-hidden="true"></span> …</div>`}
            ${range(d.total).map(n => { const p = d.pages[n]; return html`<div key=${n} className=${'tile' + (p && p.status === 'run' ? ' run' : '')}><div className="pg"></div>${t('pag')} ${n}<br />${tileBody(p)}</div>`; })}
        </div></div>
        ${d.done && html`<div className="card" style=${{ marginTop: '16px', padding: '16px 18px' }}>
            <div className="row wrap">
                ${chip('ok', `✓ ${ok} ${t('sum_ok')}`)}
                ${w.length > 0 && chip('w', `! ${w.length} ${t('sum_w')} (${t('pag')} ${w.join(', ')})`)}
                ${bad.length > 0 && chip('bad', `✕ ${bad.length} ${t('sum_bad2')} (${t('pag')} ${bad.join(', ')})`)}
                <span className="sp"></span>
                <a className="btn" href="#safata">${t('tornar_safata')}</a>
                ${d.total > 0 && html`<a className="btn pri" href="#revisio" onClick=${() => { S.cur = nextAttention(d, d.total) || 1; }}>${t('obrir')} →</a>`}
            </div>
            <${StatsKpis} s=${d.stats} />
        </div>`}
    <//>`;
}

// ---------- revisió ----------
function setCur(n) { S.cur = n; S.hl = null; S.pop = null; up(); }
function Revisio() {
    const d = S.curDoc;
    if (!d || !d.total) return html`<${NoDoc} />`;
    const n = Math.min(S.cur, d.total), p = d.pages[n] || newPage(n), st = pstate(p), pend = pending(p);
    const totalW = docPages(d).reduce((a, x) => a + pending(x).length, 0), allDone = docAllDone(d);
    const hl = S.hl, done = p.status === 'done';
    const box = Array.isArray(hl) && {
        left: hl[0] * 100 + '%', top: hl[1] * 100 + '%', width: (hl[2] - hl[0]) * 100 + '%', height: (hl[3] - hl[1]) * 100 + '%',
    };
    const validate = () => {
        p.validated = true;
        log(`Validada pàg. ${n} ${d.name}`);
        toast('✓ ' + t('validat'));
        setCur(nextAttention(d, n) || n);
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
            <button type="button" className="btn" disabled=${!done || !d.uploadId} onClick=${() => reOcr(d, n)}>↻ ${t('retranscriure')}</button>
            <button type="button" className="btn" onClick=${() => exportPdf(d)}>⤓ ${t('exportar_pdf')}</button>
            ${st === 'bad'
                ? html`<button type="button" className="btn pri" onClick=${() => { S.modal = { type: 'esc', d, n }; up(); }}>${t('marcar_esc')}</button>`
                : html`<button type="button" className="btn pri" disabled=${!done || pend.length > 0 || st === 'v' || st === 'esc'} title=${pend.length ? t('resol') : undefined} onClick=${validate}>✓ ${st === 'v' ? t('validat') : t('validar')}</button>`}
        </div>
        ${allDone && html`<div className="banner ok row">✓ ${t('doc_ok')}<span className="sp"></span>
            <a className="btn" href="#safata">${t('nova')}</a><a className="btn pri" href="#jg">${t('comprovar')} →</a></div>`}
        <div className="rev">
            <div className="card thumbs" role="list" aria-label=${t('th_pag')}>
                ${range(d.total).map(k => { const s = pstate(d.pages[k]); return html`<button key=${k} type="button" data-p=${k} className=${'thumb' + (k === n ? ' on' : '')} aria-current=${k === n ? 'page' : undefined}
                    onClick=${() => setCur(k)} onKeyDown=${e => thumbKey(e, k)}><span className=${'dot ' + dot(s)}></span>${t('pag')} ${k}${s === 'v' ? ' ✓' : ''}</button>`; })}
            </div>
            <div className="scan card">
                ${d.uploadId && html`<div className=${'pimg' + (hl === 'none' ? ' outline' : '') + (st === 'bad' ? ' ilegible' : '')}>
                    <img src=${`/page/${d.uploadId}/${n}.png?v=${p.img || 0}`} alt=${`${t('pag')} ${n}`} />
                    ${box && html`<span className="hlbox" style=${box}></span>`}
                </div>`}
            </div>
            <div className="card rtxt">
                <div className="tool"><b style=${{ color: 'var(--t)' }}>Text</b> · ${t('desat')} <span className="sp"></span>${t('seg')}</div>
                ${!done ? html`<div style=${{ padding: '20px' }} className="doc-s">${p.status === 'run' ? html`<span className="spin" aria-hidden="true"></span> ${t('pend_pag')}` : t('en_cua')}</div>`
                : st === 'bad' || (p.quality === 'bad' && p.esc) ? html`<div style=${{ padding: '20px' }}><div className="banner bad"><b>✕ ${t('il_t')}</b> (${t('contrast').toLowerCase()} ${p.contrast} < 80)<br />${t('il_s2')}</div>
                    ${p.esc && html`<div className="banner w">${t('marcar_esc')} ✓</div>`}</div>`
                : html`<${TextPane} key=${d.at + d.name + n + '-' + p.ver} p=${p} />`}
                ${hl === 'none' && html`<div className="tool foot doc-s">${t('no_capa')}</div>`}
            </div>
        </div>
        <div className="legend"><span><span className="doubt">94</span> ${t('lg_w')}</span><span><span className="invalid">8192…</span> ${t('lg_bad')}</span>
            <span className="sp"></span><span>${done ? `${t('qual')}: ${p.quality === 'bad' ? '✕' : '✓'} ${t('contrast').toLowerCase()} ${p.contrast ?? '—'}` : ''}</span></div>
    <//>`;
}

// ---------- justícia gratuïta ----------
function JG() {
    const ck = [['ok', 'DNI / NIE dels 3 membres', '3 documents · lletres de control correctes', t('complet')],
        ['ok', "Certificat d'empadronament", 'Inclou els 3 membres · Ajuntament de Tarragona', t('complet')],
        ['w', 'Darreres 12 nòmines', 'Trobades 10 de 12 · falten agost i setembre de 2026', t('incomplet')],
        ['ok', "Declaració d'IRPF 2025", 'Base imposable general: 18.742,30 €', t('complet')],
        ['bad', "Certificat de béns de l'Ajuntament", 'Pàg. 22 il·legible · cal tornar-la a escanejar', t('falta')],
        ['ok', 'Notificació del jutjat', 'Procediment verbal 1547/2026 · Jutjat de 1a Instància núm. 4', t('complet')]];
    const col = c => (c === 'ok' ? 'var(--ok)' : c === 'w' ? 'var(--w)' : 'var(--p)');
    return html`<${Shell} active="jg" demo=${true}>
        <h1>JG-2026-1184 · ${t('jg_t')}</h1><p className="sub">${t('jg_s')}</p>
        ${S.sent && html`<div className="banner ok row">✓ ${t('env_ok')}<span className="sp"></span><a className="btn pri" href="#anonimitzar">${t('seg_anon')} →</a></div>`}
        <div className="grid2">
            <div className="card"><div className="box-h">${t('aportada')}</div>${ck.map(([c, a, b, s]) => html`<div key=${a} className="check">
                <span className="ic" style=${{ color: col(c) }}>${c === 'ok' ? '✓' : c === 'w' ? '!' : '✕'}</span><div className="sp"><div>${a}</div><div className="doc-s">${b}</div></div>${chip(c, s)}</div>`)}</div>
            <div className="card"><div className="box-h">${t('dades')}</div>
                <div className="kv"><span>${t('sol')}</span><b>Lucía Martínez Peña</b><span>DNI</span><b>47851236N <span style=${{ color: 'var(--ok)' }}>✓</span></b>
                    <span>${t('ingressos')}</span><b>18.742,30 € (IRPF 2025)</b><span>${t('membres')}</span><b>3</b><span>${t('proc')}</span><b>Verbal 1547/2026</b><span>${t('domicili')}</span><b>C/ Major 112, 43003 Tarragona</b></div>
                <div style=${{ padding: '0 18px' }}><div className="banner w"><b>${t('orient')}</b> ${t('orient2')}</div></div>
                <div className="row" style=${{ padding: '6px 18px 18px' }}>
                    <button type="button" className="btn" onClick=${() => { S.modal = { type: 'dem' }; up(); }}>${t('demanar')}</button>
                    <button type="button" className="btn pri" disabled=${S.sent} onClick=${() => { S.sent = true; log('JG-2026-1184 enviat a tramitació'); toast('✓ ' + t('env_ok')); }}>${t('enviar_tram')}</button>
                </div>
            </div>
        </div>
    <//>`;
}

// ---------- anonimitzar ----------
const SENTP = [
    [['h', 'TRIBUNAL SUPERIOR DE JUSTICIA, SALA DE LO CONTENCIOSO-ADMINISTRATIVO'], ['p', 'SENTENCIA N.º 70/2020'],
        ['p', 'Procedimiento ordinario 1014/2019. Magistrado-Juez: Ilmo. Sr. D. ', ['Fernando Ruiz Calvo', 'magistrat'], '.'],
        ['p', 'ANTECEDENTES DE HECHO. PRIMERO.- Por la representación procesal de D. ', ['Raúl Gómez Cañizares', 'nom'], ', con DNI ', ['22633920B', 'dni'], ' y domicilio en ', ['calle Mayor, n.º 112, 43003 Tarragona', 'adreca'], ', se presentó demanda en reclamación de 606.336,74 €, más los intereses legales.'],
        ['p', 'La actora aporta correo ', ['raul.gomez@ejemplo.com', 'contacte'], ' y teléfono ', ['612 345 678', 'contacte'], ', y solicita el pago en la cuenta ', ['ES91 2100 0418 4502 0005 1332', 'iban'], '.'],
        ['p', 'SEGUNDO.- El vehículo matrícula ', ['4821 KLM', 'matricula'], ' fue retirado por la grúa municipal. El menor ', ['Pablo Gómez Ruiz', 'menor'], ', hijo de ', ['Raúl Gómez Cañizares', 'nom'], ', sufrió ', ['una fractura de muñeca', 'salut'], '.'],
        ['p', 'TERCERO.- ', ['Raúl Gómez Cañizares', 'nom'], ' reiteró su petición mediante escrito de 3 de marzo de 2020.'],
        ['p', 'FALLO: Que debo ESTIMAR y ESTIMO la demanda, condenando a ', ['Construcciones Levante, S.L.', 'juridica'], ' al pago de las costas.']],
    [['p', 'CUARTO.- La demandante, D.ª ', ['Lucía Martínez Peña', 'nom'], ', con DNI ', ['43123456Z', 'dni'], ' y domicilio en ', ['calle Sant Antoni, n.º 8, 43003 Tarragona', 'adreca'], ', interpuso reclamación previa el 12 de mayo de 2019.'],
        ['p', 'La parte demandada sostiene que el pago se hizo en la cuenta ', ['ES91 2100 0418 4502 0005 1332', 'iban'], '.'],
        ['p', 'QUINTO.- Practicada la prueba, queda acreditado que el vehículo matrícula ', ['4821 KLM', 'matricula'], ' fue trasladado al depósito municipal.']],
    [['p', 'SEXTO.- Consta en autos el informe de la empresa ', ['Construcciones Levante, S.L.', 'juridica'], ', firmado por D. ', ['Raúl Gómez Cañizares', 'nom'], '.'],
        ['p', 'SÉPTIMO.- Para aclarar los hechos se contactó con la actora en el teléfono ', ['612 345 678', 'contacte'], ' y por correo ', ['raul.gomez@ejemplo.com', 'contacte'], '.']],
    [['p', 'OCTAVO.- La cuantía del procedimiento asciende a 606.336,74 € y no se aprecian dudas sobre la legitimación de D. ', ['Raúl Gómez Cañizares', 'nom'], '.'],
        ['p', 'NOVENO.- Notifíquese esta resolución a las partes, con la advertencia de que cabe recurso de apelación.'],
        ['p', 'Así lo pronuncia, manda y firma D. ', ['Fernando Ruiz Calvo', 'magistrat'], ', Magistrado-Juez.']],
];
const ENTS = [];
// Cada entidad pasa a ser su id dentro de ANP.
const ANP = SENTP.map((pg, pi) => pg.map(([k, ...xs]) => [k, xs.map(x => (Array.isArray(x) ? ENTS.push({ v: x[0], c: x[1], id: ENTS.length, p: pi + 1 }) - 1 : x))]));
const CATS = ['nom', 'dni', 'adreca', 'contacte', 'iban', 'matricula', 'menor', 'salut', 'magistrat', 'juridica'];
const TAG = { nom: 'PERSONA', dni: 'DNI', adreca: 'ADREÇA', contacte: 'CONTACTE', iban: 'IBAN', matricula: 'MATRÍCULA', menor: 'MENOR', salut: 'DADA DE SALUT', magistrat: 'MAGISTRAT', juridica: 'EMPRESA' };
const PEOPLE = ['nom', 'magistrat', 'menor'];
const isOn = e => S.on.has(e.id) || (S.cats[e.c] && !S.off.has(e.id));
const uniq = a => a.filter((v, k) => a.indexOf(v) === k);
function label(e) {
    const people = PEOPLE.includes(e.c), n = uniq(ENTS.filter(x => x.c === e.c).map(x => x.v)).indexOf(e.v);
    if (S.anMode === 'pseudonim' && (people || e.c === 'juridica'))
        return (e.c === 'juridica' ? 'Empresa ' : 'Persona ') + String.fromCharCode(65 + uniq(ENTS.filter(x => PEOPLE.includes(x.c) || x.c === e.c).map(x => x.v)).indexOf(e.v));
    if (S.anMode === 'inicials' && people) return e.v.split(' ').map(w => w[0] + '.').join(' ');
    return `[${TAG[e.c]}${people ? ' ' + (n + 1) : ''}]`;
}
function entTip(el, e) {
    const r = el.getBoundingClientRect();
    S.pop = { type: 'ent', e, left: r.left + scrollX, top: r.bottom + scrollY + 8 }; up();
}
function toggleEnt(e, all) {
    const ids = all ? ENTS.filter(x => x.v === e.v).map(x => x.id) : [e.id], on = !isOn(e);
    ids.forEach(id => { if (on) { S.on.add(id); S.off.delete(id); } else { S.off.add(id); S.on.delete(id); } });
    up();
}
function Ent({ e }) {
    const tagged = ['etiqueta', 'pseudonim', 'inicials'].includes(S.anMode);
    const cls = S.original ? 'orig' : !isOn(e) ? 'off' : tagged ? 'm-tag' : 'm-' + S.anMode;
    const hlt = S.anHl && (S.anHl.c === e.c || S.anHl.e === e.id);
    const tip = ev => { if (!S.original) entTip(ev.currentTarget, e); };
    const untip = () => { if (S.pop && S.pop.type === 'ent') { S.pop = null; up(); } };
    return html`<button type="button" className=${'ent ' + cls + (hlt ? ' hlt' : '')} data-e=${e.id}
        aria-label=${!S.original && isOn(e) ? t('c_' + e.c) : undefined}
        onClick=${ev => toggleEnt(e, ev.shiftKey)} onMouseEnter=${tip} onMouseLeave=${untip} onFocus=${tip} onBlur=${untip}>${!S.original && isOn(e) && tagged ? label(e) : e.v}</button>`;
}
function hoverListEnt(e) {
    S.anHl = { e: e.id };
    if (e.p !== S.anonPage) S.anonPage = e.p;
    up();
    setTimeout(() => { const b = document.querySelector(`.ent[data-e="${e.id}"]`); if (b) b.scrollIntoView({ block: 'nearest', behavior: 'smooth' }); });
}
function Anonimitzar() {
    const count = c => ENTS.filter(e => e.c === c).length, onN = ENTS.filter(isOn).length;
    const page = (d) => { S.anonPage = Math.min(ANP.length, Math.max(1, S.anonPage + d)); up(); };
    return html`<${Shell} active="arxiu" demo=${true}>
        <div className="card row wrap" style=${{ padding: '10px 14px', marginBottom: '12px' }}>
            <a href="#safata" className="btn">‹ ${t('safata')}</a><b>${t('an_t')} · Sentència 70/2020</b><span>(${t('pag')} ${S.anonPage} ${t('de')} ${ANP.length})</span>
            <button type="button" className="btn" aria-label="‹" disabled=${S.anonPage === 1} onClick=${() => page(-1)}>‹</button>
            <button type="button" className="btn" aria-label="›" disabled=${S.anonPage === ANP.length} onClick=${() => page(1)}>›</button>
            <span className="sp"></span>
            <button type="button" className="btn" onClick=${() => { S.original = !S.original; if (S.original) log('Consulta vista original Sentència 70/2020'); up(); }}>${S.original ? t('vista_an') : t('vista')}</button>
            <button type="button" className="btn pri" onClick=${() => { S.modal = { type: 'expan' }; up(); }}>⤓ ${t('exp_an')}</button>
        </div>
        <div className="anon">
            <div className="card doc">${ANP[S.anonPage - 1].map(([k, xs], i) => React.createElement(k === 'h' ? 'h4' : 'p', { key: i },
                xs.map((x, j) => (typeof x === 'number' ? html`<${Ent} key=${j} e=${ENTS[x]} />` : x))))}</div>
            <aside className="card side"><h3>${t('an_panel')}</h3><div className="doc-s">${ENTS.length} ${t('detect')} · ${onN} ${t('anonim')}</div>
                <h5>${t('com')}</h5>
                <div className="modes">${['censurar', 'esborrar', 'tatxar', 'etiqueta', 'pseudonim', 'inicials'].map(m => html`<button key=${m} type="button" className=${S.anMode === m ? 'on' : ''} aria-pressed=${S.anMode === m} onClick=${() => { S.anMode = m; up(); }}>${t('m_' + m)}</button>`)}</div>
                ${S.anMode === 'tatxar' && html`<div className="banner w" style=${{ marginTop: '8px' }}>${t('tatxar_av')}</div>`}
                <h5>${t('que')}</h5>
                ${CATS.map(c => html`<label key=${c} className="cat" onMouseEnter=${() => { S.anHl = { c }; up(); }} onMouseLeave=${() => { S.anHl = null; up(); }}>
                    <input type="checkbox" checked=${!!S.cats[c]} disabled=${c === 'menor' || c === 'salut'}
                        onFocus=${() => { S.anHl = { c }; up(); }} onBlur=${() => { S.anHl = null; up(); }}
                        onChange=${e => { S.cats[c] = e.target.checked ? 1 : 0; S.on.clear(); S.off.clear(); up(); }} />${t('c_' + c)}<em>${count(c)}</em></label>`)}
                <details open=${S.detOpen} onToggle=${e => { S.detOpen = e.currentTarget.open; }}><summary>${t('veure')} (${onN})</summary>
                    <ul>${ENTS.filter(isOn).map(e => html`<li key=${e.id} onMouseEnter=${() => hoverListEnt(e)} onMouseLeave=${() => { S.anHl = null; up(); }}>
                        <span>■ ${e.v.length > 24 ? e.v.slice(0, 24) + '…' : e.v}</span><span className="doc-s">${TAG[e.c]}</span></li>`)}</ul>
                </details>
            </aside>
        </div>
    <//>`;
}
function AuditCard({ style }) {
    return html`<div className="card" style=${style}><div className="box-h">${t('registre')}</div>
        <div className="audit">${S.audit.length ? S.audit.map((a, i) => html`<div key=${i}>${a}</div>`) : t('cap')}</div></div>`;
}
function Exportat() {
    return html`<${Shell} active="arxiu" demo=${true}>
        <div className="card" style=${{ padding: '28px', maxWidth: '720px', margin: '0 auto' }}>
            <div className="banner ok"><b>✓ ${t('exp_t')}</b> · Sentència_70-2020_anonimitzada.pdf · ${t('exp_s')}</div>
            <ul style=${{ lineHeight: 2 }}>${['g1', 'g2', 'g3', 'g4'].map(g => html`<li key=${g}>${t(g)}</li>`)}</ul>
            <div className="row"><button type="button" className="btn pri" onClick=${() => toast('⤓ Sentència_70-2020_anonimitzada.pdf')}>⤓ ${t('descarregar')}</button><a className="btn" href="#safata">${t('tornar_safata')}</a></div>
        </div>
        <${AuditCard} style=${{ maxWidth: '720px', margin: '16px auto 0' }} />
    <//>`;
}
function Informes() {
    const pg = S.docs.flatMap(docPages).filter(p => p.status === 'done');
    const avg = pg.length ? (pg.reduce((a, p) => a + (p.time || 0), 0) / pg.length).toFixed(2) : '—';
    return html`<${Shell} active="informes" demo=${true}>
        <h1>${t('inf_t')}</h1><p className="sub">${t('inf_s')}</p>
        <div className="kpis"><div className="card kpi"><b>8.214</b><span>${t('i1')}</span></div><div className="card kpi"><b>38 s</b><span>${t('i2')}</span></div>
            <div className="card kpi"><b>2,1 %</b><span>${t('i3')}</span></div><div className="card kpi"><b>${146 + (S.sent ? 1 : 0)}</b><span>${t('i4')}</span></div></div>
        <h5 className="box-h" style=${{ padding: '8px 0' }}>${t('sessio')}</h5>
        <div className="kpis">
            <div className="card kpi"><b>${S.docs.length}</b><span>${t('s_docs')}</span></div>
            <div className="card kpi"><b>${pg.length}</b><span>${t('s_pag')}</span></div>
            <div className="card kpi"><b>${pg.filter(p => p.validated).length}</b><span>${t('s_val')}</span></div>
            <div className="card kpi"><b>${avg}</b><span>${t('s_avg')}</span></div>
        </div>
        <${AuditCard} />
    <//>`;
}

// ---------- popover, modales, guía ----------
function Pop() {
    const P = S.pop, ref = useRef(null);
    useEffect(() => { if (P.type === 'warn') { const b = ref.current && ref.current.querySelector('button'); if (b) b.focus(); } }, [P]);
    const style = { left: Math.max(8, Math.min(P.left, innerWidth - 320)) + 'px', top: P.top + 'px' };
    if (P.type === 'ent') {
        const e = P.e, n = ENTS.filter(x => x.v === e.v).length;
        return html`<div className="pop" role="tooltip" style=${style}><b>${t('c_' + e.c)}</b>«${e.v}» · ${t('apareix')} ${n} ${n > 1 ? t('vegades') : 'vegada'}
            <div className="doc-s">${isOn(e) ? t('tip_on') : t('tip_off')}</div><div className="doc-s">🔒 ${t('registrada')}</div></div>`;
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
    useEffect(() => { const f = ref.current && ref.current.querySelector('input,textarea,button'); if (f) f.focus(); }, []);
    const close = () => { S.modal = null; up(); };
    let body;
    if (M.type === 'esc') {
        const { d, n } = M, p = d.pages[n];
        body = html`<h2>${t('esc_t')}</h2><p>${t('esc_s')} (${t('pag')} ${n}).</p>
            <input type="file" accept=".pdf,image/*" style=${{ width: '100%' }} onChange=${e => setFile(e.target.files[0] || null)} />
            <div className="row" style=${{ marginTop: '16px' }}><span className="sp"></span><button type="button" className="btn" onClick=${close}>${t('cancel')}</button>
                <button type="button" className="btn" onClick=${() => { p.esc = true; log(`Pàg. ${n} marcada per tornar a escanejar ${d.name}`); S.modal = null; S.cur = nextAttention(d, n) || n; up(); }}>${t('marcar_esc')}</button>
                <button type="button" className="btn pri" disabled=${!file} onClick=${() => { S.modal = null; reOcr(d, n, file); }}>${t('pujar_pag')}</button></div>`;
    } else if (M.type === 'dem') {
        body = html`<h2>${t('msg_t')}</h2><textarea style=${{ width: '100%', height: '190px', font: '14px/1.5 Roboto', border: '1px solid var(--line)', borderRadius: '6px', padding: '10px' }} defaultValue=${t('msg')}></textarea>
            <div className="row" style=${{ marginTop: '14px' }}><span className="sp"></span><button type="button" className="btn" onClick=${close}>${t('cancel')}</button>
                <button type="button" className="btn pri" onClick=${() => { close(); log('Requeriment enviat a la sol·licitant (UNITRAM)'); toast('✓ ' + t('req_ok')); }}>${t('enviar')}</button></div>`;
    } else {
        body = html`<h2>${t('conf_t')}</h2><p>${t('conf_1')}</p>
            <label className="cat"><input type="checkbox" checked=${ok} onChange=${e => setOk(e.target.checked)} /> ${t('conf_c')}</label>
            <div className="row" style=${{ marginTop: '16px' }}><span className="sp"></span><button type="button" className="btn" onClick=${close}>${t('cancel')}</button>
                <button type="button" className="btn pri" disabled=${!ok} onClick=${() => { S.modal = null; S.exported = true; log(`Exportat Sentència 70/2020 anonimitzada (mode: ${S.anMode}, ${ENTS.filter(isOn).length} dades)`); go('#exportat'); }}>${t('exportar')}</button></div>`;
    }
    return html`<div className="modal-bg"><div className="modal" role="dialog" aria-modal="true" ref=${ref}>${body}</div></div>`;
}
const STEPS = [['login', 'Login'], ['landing', 'Inici'], ['safata', 'Safata → Nou document'], ['processant', 'OCR + semàfor'], ['revisio', 'Revisió i avisos'], ['jg', 'Justícia gratuïta'], ['anonimitzar', 'Anonimització'], ['exportat', 'Exportació'], ['arxiu', 'Arxiu'], ['informes', 'Informes']];
function Guide({ r }) {
    return html`<div className="guide">
        ${S.guideOpen && html`<ol>${STEPS.map(([k, l]) => html`<li key=${k} className=${k === r ? 'on' : ''}><a href=${'#' + k}>${l}</a></li>`)}</ol>`}
        <button type="button" className="btn" aria-expanded=${S.guideOpen} onClick=${() => { S.guideOpen = !S.guideOpen; up(); }}>${S.guideOpen ? '✕' : '☰ ' + t('guia')}</button>
    </div>`;
}

// ---------- router ----------
const VIEWS = { login: Login, landing: Landing, safata: Safata, processant: Processant, revisio: Revisio, jg: JG, anonimitzar: Anonimitzar, exportat: Exportat, arxiu: Arxiu, informes: Informes };
function onKey(ev) {
    if (ev.key === 'Escape' && (S.pop || S.modal)) { S.pop = null; S.modal = null; up(); return; }
    if (ev.ctrlKey && ev.key === 'ArrowRight' && location.hash === '#revisio' && S.curDoc) {
        ev.preventDefault();
        const w = document.querySelector('#txt .doubt, #txt .invalid'), p = S.curDoc.pages[S.cur];
        if (w) { w.focus(); openWarn(w, p); } else { const n = nextAttention(S.curDoc, S.cur); if (n) setCur(n); }
    }
}
function onDocClick(ev) {
    if (S.pop && !ev.target.closest('.pop,[data-wid],.ent')) { S.pop = null; up(); }
}
function App() {
    const [, setTick] = useState(0);
    rerender = () => setTick(x => x + 1);
    useEffect(() => {
        const onHash = () => { S.pop = null; S.modal = null; S.hl = null; S.anHl = null; scrollTo(0, 0); up(); };
        addEventListener('hashchange', onHash);
        document.addEventListener('keydown', onKey);
        document.addEventListener('click', onDocClick);
        return () => { removeEventListener('hashchange', onHash); document.removeEventListener('keydown', onKey); document.removeEventListener('click', onDocClick); };
    }, []);
    let r = location.hash.slice(1) || 'login';
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
