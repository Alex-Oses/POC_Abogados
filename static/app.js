// Frontend React (UMD + htm, sin build) servido por Flask.
// Todo el estado vive aquí: login falso → landing → subida → transcripción → revisión.
const { useState, useEffect, useRef } = React;
const html = htm.bind(React.createElement);

const MODES = {
    single: { label: 'Transcripción única', note: 'Editable · lectura única' },
    double: { label: 'Doble transcripción', note: 'Editable · doble lectura' },
};

function Header({ user, onHome, onLogout }) {
    return html`
    <header>
        <div className="logo" onClick=${onHome} style="cursor:pointer"><b>ICA<i>T</i></b><small>Il·lustre Col·legi de l'Advocacia de Tarragona</small></div>
        <span className="sp"></span>
        ${user && html`
        <div className="user">${user.email} <span className="avatar" aria-hidden="true">${(user.email[0] || 'D').toUpperCase()}</span>
            <button className="btn" onClick=${onLogout}>Salir</button>
        </div>`}
    </header>`;
}

function Login({ onLogin }) {
    const [email, setEmail] = useState('demo@icat.cat');
    const [pass, setPass] = useState('demo');
    return html`
    <main className="center">
        <div className="card login">
            <div className="logo"><b>ICA<i>T</i></b><small>Il·lustre Col·legi de l'Advocacia de Tarragona</small></div>
            <h1>Transcripción de documentos escaneados</h1>
            <form onSubmit=${e => { e.preventDefault(); onLogin({ email }); }}>
                <label className="fld">Correo<input type="email" value=${email} onInput=${e => setEmail(e.target.value)} required></label>
                <label className="fld">Contraseña<input type="password" value=${pass} onInput=${e => setPass(e.target.value)} required></label>
                <button className="btn pri wide" type="submit">Acceder con la cuenta del Col·legi</button>
            </form>
            <p className="sub">Office 365 · mismas credenciales que la extranet</p>
            <p className="banner ok">🔒 Todo se procesa en el servidor del Col·legi: ningún documento sale del ICAT.</p>
            <p className="doc-s">Demo: cualquier credencial vale.</p>
        </div>
    </main>`;
}

function Landing({ onStart }) {
    const feats = [
        ['📄', 'PDF a texto', 'Cada página se transcribe por separado y ves el original al lado.'],
        ['🔁', 'Doble lectura', 'Dos pasadas por página; lo que no coincide se marca en rojo.'],
        ['✍️', 'Revisión', 'Texto editable y páginas que se validan de una en una.'],
    ];
    return html`
    <main>
        <div className="card hero">
            <h1>Transcribe escaneos sin que salgan del Col·legi</h1>
            <p className="sub">Sube un PDF y PaddleOCR-VL lo pasa a texto página a página, con doble lectura opcional y revisión asistida.</p>
            <button className="btn pri" onClick=${onStart}>Empezar →</button>
        </div>
        <div className="feats">
            ${feats.map(([icon, title, text]) => html`
            <div className="card feat">
                <div className="big" aria-hidden="true">${icon}</div>
                <b>${title}</b>
                <p className="sub">${text}</p>
            </div>`)}
        </div>
    </main>`;
}

function TextPane({ pageNumber, page, edit, onEdit, onHover }) {
    const ref = useRef(null);
    const latest = useRef();
    latest.current = { page, edit, onEdit, onHover };

    // El contenido se pinta a mano (textContent) para no inyectar HTML del OCR.
    useEffect(() => {
        const el = ref.current;
        if (!el) return;
        const current = latest.current;
        el.replaceChildren();
        const page = current.page;
        if (!page || page.status !== 'done') {
            el.textContent = page && page.status === 'running'
                ? 'Esperando a que el modelo termine esta página…'
                : 'Todavía no transcrita.';
            return;
        }
        if (current.edit !== undefined) {
            el.textContent = current.edit;
            return;
        }
        if (!page.segs) {
            el.textContent = page.text || '(el modelo no ha detectado texto)';
            return;
        }
        for (const seg of page.segs) {
            if (!seg.diff) {
                el.appendChild(document.createTextNode(seg.t));
                continue;
            }
            const span = document.createElement('span');
            span.className = 'diff';
            span.textContent = seg.t;
            if (seg.other) span.title = '2ª lectura: ' + seg.other;
            span.addEventListener('mouseenter', () => latest.current.onHover(seg.rect || 'none'));
            span.addEventListener('mouseleave', () => latest.current.onHover(null));
            el.appendChild(span);
        }
    }, [pageNumber, page && page.status, page && page.segs]);

    return html`<div className="ocr-text" ref=${ref} contentEditable=${page && page.status === 'done' ? 'true' : 'false'} spellCheck="false"
        onInput=${e => latest.current.onEdit(e.currentTarget.innerText)}></div>`;
}

function Workspace() {
    const [mode, setMode] = useState('single');
    const [job, setJob] = useState(null);
    const [selected, setSelected] = useState(1);
    const [hover, setHover] = useState(null);
    const [edits, setEdits] = useState({});
    const [error, setError] = useState('');
    const [stats, setStats] = useState(null);
    const [finished, setFinished] = useState(false);

    const reset = () => {
        setJob(null); setSelected(1); setHover(null); setEdits({}); setError(''); setStats(null); setFinished(false);
    };

    const start = (file) => {
        if (!file) return;
        if (!file.name.toLowerCase().endsWith('.pdf')) {
            setError('Selecciona un archivo PDF.'); return;
        }
        if (file.size > 50 * 1024 * 1024) {
            setError('El archivo es muy grande (máximo 50 MB).'); return;
        }
        reset();
        setJob({ name: file.name, uploadId: null, total: 0, pages: {} });

        const formData = new FormData();
        formData.append('pdf', file);
        formData.append('mode', mode);

        // La respuesta es NDJSON: una línea por evento (start, page, done, error).
        fetch('/ocr', { method: 'POST', body: formData })
            .then(async response => {
                if (!response.ok) {
                    const err = await response.json().catch(() => ({}));
                    throw new Error(err.error || 'HTTP ' + response.status);
                }
                const reader = response.body.getReader();
                const decoder = new TextDecoder();
                let buffer = '';
                while (true) {
                    const { done, value } = await reader.read();
                    if (done) break;
                    buffer += decoder.decode(value, { stream: true });
                    let nl;
                    while ((nl = buffer.indexOf('\n')) >= 0) {
                        const line = buffer.slice(0, nl).trim();
                        buffer = buffer.slice(nl + 1);
                        if (line) handleEvent(JSON.parse(line));
                    }
                }
            })
            .catch(e => setError('Error: ' + e.message));
    };

    const handleEvent = (ev) => {
        if (ev.type === 'start') {
            const pages = {};
            for (let n = 1; n <= ev.total_pages; n++) {
                pages[n] = { status: n === 1 ? 'running' : 'pending', reviewed: false };
            }
            setJob(prev => ({ ...prev, uploadId: ev.upload_id, total: ev.total_pages, pages }));
            setSelected(1);
        } else if (ev.type === 'page') {
            setJob(prev => {
                if (!prev) return prev;
                const pages = {
                    ...prev.pages,
                    [ev.page]: { ...prev.pages[ev.page], status: 'done', text: ev.text, segs: ev.diff, time: ev.time, chars: ev.chars },
                };
                if (ev.page < prev.total) pages[ev.page + 1] = { ...pages[ev.page + 1], status: 'running' };
                return { ...prev, pages };
            });
        } else if (ev.type === 'done') {
            setStats(ev);
            setFinished(true);
        } else if (ev.type === 'error') {
            setError(ev.error);
        }
    };

    const pages = job ? job.pages : {};
    const page = pages[selected];
    const total = job ? job.total : 0;
    const reviewedCount = Object.values(pages).filter(p => p.reviewed).length;

    const review = (n) => {
        setJob(prev => {
            if (!prev) return prev;
            const pages = { ...prev.pages, [n]: { ...prev.pages[n], reviewed: true } };
            return { ...prev, pages };
        });
        const order = [];
        for (let p = n + 1; p <= total; p++) order.push(p);
        for (let p = 1; p < n; p++) order.push(p);
        const next = order.find(p => pages[p] && !pages[p].reviewed);
        if (next) setSelected(next);
    };

    const allReviewed = total > 0 && reviewedCount === total;

    const dropProps = {
        onClick: () => document.getElementById('pdfFile').click(),
        onDragEnter: e => { e.preventDefault(); e.currentTarget.classList.add('over'); },
        onDragOver: e => { e.preventDefault(); e.currentTarget.classList.add('over'); },
        onDragLeave: e => e.currentTarget.classList.remove('over'),
        onDrop: e => {
            e.preventDefault(); e.currentTarget.classList.remove('over');
            if (e.dataTransfer.files.length) start(e.dataTransfer.files[0]);
        },
    };

    return html`
    <main>
        <h1>${job ? 'Transcribiendo · ' + (job.name || '') : 'Transcripción de documentos escaneados'}</h1>
        <p className="sub">${job
            ? `${total} página(s) · ${MODES[mode].note}`
            : 'Sube un PDF y el modelo local lo transcribe página a página. Nada sale del servidor del Col·legi.'}</p>

        ${error && html`<div className="banner bad">${error}</div>`}

        ${!job && html`
        <div className="modes" role="radiogroup" aria-label="Modo de transcripción">
            ${Object.entries(MODES).map(([value, m]) => html`
            <label className="mode ${mode === value ? 'on' : ''}">
                <input type="radio" name="mode" value=${value} checked=${mode === value} onChange=${() => setMode(value)}>
                ${m.label}${value === 'double' ? ' · lo que no coincide se marca en rojo' : ''}
            </label>`)}
        </div>
        <button className="drop" type="button" ...${dropProps}>
            <b>Arrastra aquí tu PDF</b><br>o haz clic para seleccionarlo · máximo 50 MB
        </button>
        <input type="file" id="pdfFile" accept=".pdf" hidden onChange=${e => start(e.target.files[0])}>`}

        ${job && total > 0 && html`
        <div className="rev">
            <div className="card thumbs" aria-label="Páginas">
                ${Array.from({ length: total }, (_, k) => k + 1).map(n => {
                    const p = pages[n] || {};
                    const cls = ['thumb', n === selected ? 'on' : '', p.reviewed ? 'ok' : '', p.status === 'running' ? 'run' : ''].join(' ');
                    return html`
                    <button type="button" className="${cls}" onClick=${() => setSelected(n)}>
                        <span className="dot"></span>
                        <span>Página ${n}${p.reviewed ? ' ✓' : ''}</span>
                    </button>`;
                })}
            </div>
            <div className="scan">
                <div className="paper ${hover === 'none' ? 'outline' : ''}">
                    <img src=${`/page/${job.uploadId}/${selected}.png`} alt=${`Página ${selected} del PDF`}>
                    ${Array.isArray(hover) && html`<span className="hlbox" style=${{
                        left: (hover[0] * 100) + '%', top: (hover[1] * 100) + '%',
                        width: ((hover[2] - hover[0]) * 100) + '%', height: ((hover[3] - hover[1]) * 100) + '%',
                    }}></span>`}
                </div>
            </div>
            <div className="card text-pane">
                <div className="tool">
                    <strong>Página ${selected}</strong>
                    <span className="chip ${page && page.status === 'done' ? (page.segs && page.segs.some(s => s.diff) ? 'bad' : 'ok') : ''}">
                        ${!page || page.status !== 'done'
                            ? (page && page.status === 'running' ? 'transcribiendo…' : 'en cola')
                            : edits[selected] !== undefined
                                ? `${page.time} s · editado`
                                : page.segs && page.segs.some(s => s.diff)
                                    ? `${page.time} s · ${page.segs.filter(s => s.diff).length} diferencia(s)`
                                    : `${page.time} s · ${page.chars} caracteres`}
                    </span>
                    <span className="sp"></span>
                    <span className="doc-s">${MODES[mode].note} · ${reviewedCount}/${total} revisadas</span>
                </div>
                <${TextPane}
                    pageNumber=${selected}
                    page=${page}
                    edit=${edits[selected]}
                    onEdit=${text => setEdits(prev => ({ ...prev, [selected]: text }))}
                    onHover=${setHover} />
                <div className="tool foot">
                    ${hover === 'none' && html`<span className="doc-s">Esta página no tiene capa de texto: no se puede localizar la palabra en la imagen.</span>`}
                    <span className="sp"></span>
                    <button className="btn pri" disabled=${!page || page.status !== 'done' || page.reviewed}
                        onClick=${() => review(selected)}>✓ Marcar como revisada</button>
                </div>
            </div>
        </div>`}

        ${finished && html`
        <div className="kpis">
            <div className="card kpi"><b>${stats.total_pages}</b><span>páginas</span></div>
            <div className="card kpi"><b>${stats.total_time} s</b><span>tiempo total</span></div>
            <div className="card kpi"><b>${stats.avg_time_per_page} s</b><span>media por página</span></div>
            <div className="card kpi"><b>${stats.pages_per_hour_estimate}</b><span>páginas / hora</span></div>
            <div className="card kpi"><b>${stats.total_chars}</b><span>caracteres</span></div>
        </div>`}

        ${allReviewed && html`
        <div className="banner ok row">✓ Todas las páginas revisadas
            <span className="sp"></span>
            <button className="btn pri" onClick=${reset}>Nueva transcripción</button>
        </div>`}
    </main>`;
}

function App() {
    const [user, setUser] = useState(null);
    const [screen, setScreen] = useState('login');

    return html`
    <${Header} user=${user} onHome=${() => user && setScreen('landing')} onLogout=${() => { setUser(null); setScreen('login'); }} />
    ${screen === 'login' && html`<${Login} onLogin=${u => { setUser(u); setScreen('landing'); }} />`}
    ${screen === 'landing' && html`<${Landing} onStart=${() => setScreen('app')} />`}
    ${screen === 'app' && html`<${Workspace} />`}`;
}

ReactDOM.createRoot(document.getElementById('root')).render(html`<${App} />`);
