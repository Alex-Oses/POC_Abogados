"""Rendimiento de Presidio en local sobre documentos jurídicos ficticios (castellano y catalán).

Genera un corpus sintético con los datos personales marcados de antemano, ejecuta Presidio con
distintos modelos de spaCy y configuraciones, y mide acierto, falsos positivos, velocidad y memoria.

Uso:
  pip install presidio-analyzer presidio-anonymizer psutil
  python -m spacy download es_core_news_sm es_core_news_md es_core_news_lg ca_core_news_md
  python investigacion/presidio/benchmark.py            # todas las combinaciones -> resultados/
  python investigacion/presidio/benchmark.py --uno es es_core_news_md ajustada 0   # una combinación (JSON)
"""
import json, random, re, statistics, subprocess, sys, time
from pathlib import Path

N_DOCS = 150
SEED = 7
LETRAS = "TRWAGMYFPDXBNJZSQVHLCKE"

# ---------------------------------------------------------------- corpus
NOMBRES = {"es": (["José Antonio", "María", "Lucía", "Raúl", "Ana", "Javier", "Carmen", "Francisco", "Laura", "David", "Marta", "Sergio", "Elena", "Pablo", "Rosa"],
                  ["García", "Martínez", "López", "Sánchez", "Pérez", "Gómez", "Ruiz", "Núñez", "Fernández", "Romero", "Navarro", "Torres", "Domínguez", "Vázquez", "Cañizares"]),
           "ca": (["Jordi", "Montserrat", "Pere", "Núria", "Joan", "Mireia", "Oriol", "Laia", "Marc", "Roser", "Xavier", "Anna", "Josep", "Mercè", "Pau"],
                  ["Puig", "Serra", "Vila", "Ferrer", "Soler", "Pujol", "Casals", "Font", "Roca", "Bosch", "Vidal", "Riera", "Mas", "Camps", "Sala"])}
CIUDADES = [("43003", "Tarragona"), ("43201", "Reus"), ("43800", "Valls"), ("43700", "El Vendrell"), ("43500", "Tortosa")]
VIAS = {"es": ["calle Mayor", "avenida de Roma", "calle de la Unión", "plaza de la Fuente", "paseo de las Palmeras", "calle Real"],
        "ca": ["carrer Major", "carrer de la Unió", "plaça de la Font", "rambla Nova", "passeig de les Palmeres", "carrer Reial"]}
EMPRESAS = ["Construcciones Levante", "Serveis Logístics Tarragona", "Inversiones Costa Daurada", "Transports Camp", "Gestoria Mediterrània"]
CONSONANTES = "BCDFGHJKLMNPRSTVWXYZ"


# Corpus de validación: otra semilla y formatos que las reglas de «mejorada» no vieron al ajustarse.
VAL = False
NOMBRES_VAL = {"es": (["Inmaculada", "Gonzalo", "Begoña", "Iñaki", "Rocío", "Álvaro"], ["Iglesias", "Ortega", "Castillo", "Garrido", "de la Fuente", "Medina"]),
               "ca": (["Arnau", "Queralt", "Ferran", "Gemma", "Biel", "Txell"], ["Grau", "Tort", "Batlle", "Coll", "Pons", "de Vilanova"])}
VIAS_VAL = {"es": ["Avda. Catalunya", "Pza. de la Font", "Ctra. de Valls"], "ca": ["Av. Catalunya", "Pl. de la Font", "Ctra. de Valls"]}


def dni(r, fmt=0):
    n = r.randrange(10**7, 10**8); l = LETRAS[n % 23]
    if VAL and r.random() < .3:
        return f"{n} {l}"
    return [f"{n}{l}", f"{n}-{l}", f"{n:,}".replace(",", ".") + f"-{l}"][fmt]


def nie(r):
    p = r.choice("XYZ"); n = r.randrange(10**6, 10**7)
    return f"{p}{n:07d}{LETRAS[int(str('XYZ'.index(p)) + f'{n:07d}') % 23]}"


def iban(r):
    bban = "".join(str(r.randrange(10)) for _ in range(20))
    cc = 98 - int(bban + "142800") % 97
    s = f"ES{cc:02d}{bban}"
    return s if r.random() < .3 else " ".join(s[i:i + 4] for i in range(0, 24, 4))


def persona(r, lang):
    n, a = NOMBRES_VAL[lang] if VAL and r.random() < .5 else NOMBRES[lang]
    s = f"{r.choice(n)} {r.choice(a)} {'i ' if lang == 'ca' and r.random() < .5 else ''}{r.choice(a)}"
    return s.upper() if r.random() < .25 else s  # en escritos judiciales es habitual el nombre en mayúsculas


def direccion(r, lang):
    cp, ciudad = r.choice(CIUDADES)
    via, n = r.choice(VIAS[lang]), r.randrange(1, 200)
    num = "núm." if lang == "ca" else "n.º"
    corta = ("C/ " if lang == "es" else "c. ") + via.split(" ", 1)[1].split(" ")[-1]
    if VAL and r.random() < .4:
        v = r.choice(VIAS_VAL[lang])
        return r.choice([f"{v} {n}, {ciudad}", f"{v}, {n}, {'bajos' if lang == 'es' else 'baixos'}"])
    return r.choice([f"{via}, {num} {n}, {cp} {ciudad}", f"{corta} {n}, {r.randrange(1, 6)}.º {r.randrange(1, 4)}.ª, {ciudad}",
                     f"{via}, {n}", f"{via} {num} {n} de {ciudad}"])


def telefono(r):
    a, b, c = r.choice("679") + str(r.randrange(10, 99)), r.randrange(100, 999), r.randrange(100, 999)
    if VAL and r.random() < .4:
        return r.choice([f"{a}.{str(b)[:2]}.{str(b)[2]}{str(c)[0]}.{str(c)[1:]}", f"(+34) {a}{b}{c}"])
    return r.choice([f"{a} {b} {c}", f"{a}{b}{c}", f"+34 {a} {str(b)[:2]} {str(b)[2]}{str(c)[0]} {str(c)[1:]}"])


RELLENO = {"es": [
    "Conforme a lo dispuesto en el artículo 394 de la Ley de Enjuiciamiento Civil, las costas se imponen a la parte cuyas pretensiones hayan sido totalmente rechazadas.",
    "El Juzgado de Primera Instancia n.º 4 de Reus dictó auto de admisión a trámite, dando traslado a la Seguridad Social y a la Agencia Tributaria.",
    "Se han observado las prescripciones legales, salvo el plazo para dictar sentencia por la acumulación de asuntos que pesa sobre este órgano judicial.",
    "La Ley 29/1994, de 24 de noviembre, de Arrendamientos Urbanos, resulta de aplicación al contrato objeto de este procedimiento.",
    "Contra esta resolución cabe recurso de apelación ante la Audiencia Provincial de Tarragona en el plazo de veinte días.",
    "El Colegio de la Abogacía de Tarragona emitió informe sobre los honorarios reclamados, que obra unido a las actuaciones."],
  "ca": [
    "D'acord amb l'article 394 de la Llei d'enjudiciament civil, les costes s'imposen a la part que hagi vist rebutjades totes les seves pretensions.",
    "El Jutjat de Primera Instància núm. 4 de Reus va admetre la demanda a tràmit i en va donar trasllat a la Seguretat Social i a l'Agència Tributària.",
    "S'han observat les prescripcions legals, llevat del termini per dictar sentència per l'acumulació d'assumptes d'aquest òrgan judicial.",
    "La Llei 29/1994, de 24 de novembre, d'arrendaments urbans, és aplicable al contracte objecte d'aquest procediment.",
    "Contra aquesta resolució es pot interposar recurs d'apel·lació davant l'Audiència Provincial de Tarragona en el termini de vint dies.",
    "El Col·legi de l'Advocacia de Tarragona va emetre un informe sobre els honoraris reclamats, que consta a les actuacions."]}


def plantilla(r, lang):
    """Devuelve una lista de trozos: texto o (valor, categoría). EMPRESA es un negativo: no debe anonimizarse."""
    p1, p2, p3, mag = (persona(r, lang) for _ in range(4))
    correo = re.sub(r"[^a-z.]", "", p1.lower().replace(" ", ".").translate(str.maketrans("áéíóúàèòïüñç", "aeiouaeoiunc")))[:30] + "@ejemplo.com"
    tel = telefono(r)
    cat = f"{r.randrange(10**6, 10**7)}{r.choice('ABCDEF')}{r.choice('FGH')}{r.randrange(1000, 9999)}N{r.randrange(1000, 9999)}{r.choice('XYZ')}{r.choice('XYZ')}"
    mat = f"{r.randrange(1000, 9999)}{r.choice(' -')}{''.join(r.choice(CONSONANTES) for _ in range(3))}"
    rell = lambda: "\n\n" + " ".join(r.sample(RELLENO[lang], 3)) + "\n\n"
    fmt = r.choice([0, 0, 1, 2])
    emp = r.choice(EMPRESAS) + ", S.L."
    if lang == "es":
        return [
            "TRIBUNAL SUPERIOR DE JUSTICIA. SENTENCIA N.º ", str(r.randrange(10, 999)), "/2026\n\nProcedimiento ordinario ",
            str(r.randrange(100, 2000)), "/2025. Magistrado-Juez: Ilmo. Sr. D. ", (mag, "PERSON"), ".\n\n",
            "ANTECEDENTES DE HECHO. PRIMERO.- Por la representación procesal de D. ", (p1, "PERSON"), ", con DNI ", (dni(r, fmt), "DNI"),
            " y domicilio en ", (direccion(r, lang), "DIRECCION"), ", se presentó demanda contra ", (emp, "EMPRESA"),
            " en reclamación de ", f"{r.randrange(1000, 900000):,}".replace(",", "."), ",00 €.", rell(),
            "SEGUNDO.- Testigo: ", (p2, "PERSON"), ", con NIE ", (nie(r), "NIE"), ". La actora aporta correo ", (correo, "EMAIL"),
            " y teléfono ", (tel, "TELEFONO"), ", y solicita el pago en la cuenta ", (iban(r), "IBAN"), ".\n\n",
            "TERCERO.- El vehículo matrícula ", (mat, "MATRICULA"), " fue retirado. Referencia catastral del local: ", (cat, "CATASTRAL"),
            ". Comparece asimismo ", (p3, "PERSON"), ", en calidad de perito.", rell(),
            "FALLO: Que debo ESTIMAR y ESTIMO la demanda, condenando a ", (emp, "EMPRESA"), " al pago de las costas. DNI y NIE verificados.",
        ]
    return [
        "JUTJAT DE PRIMERA INSTÀNCIA. SENTÈNCIA NÚM. ", str(r.randrange(10, 999)), "/2026\n\nProcediment ordinari ",
        str(r.randrange(100, 2000)), "/2025. Magistrat: Il·lm. Sr. ", (mag, "PERSON"), ".\n\n",
        "ANTECEDENTS DE FET. PRIMER.- La representació processal de ", (p1, "PERSON"), ", amb DNI ", (dni(r, fmt), "DNI"),
        " i domicili a ", (direccion(r, lang), "DIRECCION"), ", va presentar demanda contra ", (emp, "EMPRESA"),
        " en reclamació de ", f"{r.randrange(1000, 900000):,}".replace(",", "."), ",00 €.", rell(),
        "SEGON.- Testimoni: ", (p2, "PERSON"), ", amb NIE ", (nie(r), "NIE"), ". L'actora aporta el correu ", (correo, "EMAIL"),
        " i el telèfon ", (tel, "TELEFONO"), ", i sol·licita el pagament al compte ", (iban(r), "IBAN"), ".\n\n",
        "TERCER.- El vehicle amb matrícula ", (mat, "MATRICULA"), " va ser retirat. Referència cadastral del local: ", (cat, "CATASTRAL"),
        ". Compareix també ", (p3, "PERSON"), ", en qualitat de pèrit.", rell(),
        "DECISIÓ: Estimo la demanda i condemno ", (emp, "EMPRESA"), " al pagament de les costes. DNI i NIE verificats.",
    ]


def corpus(lang, validacion=False):
    global VAL
    VAL = validacion
    r = random.Random(f"{SEED + (100 if validacion else 0)}-{lang}")
    docs = []
    for _ in range(N_DOCS):
        text, gold = "", []
        for part in plantilla(r, lang):
            if isinstance(part, tuple):
                gold.append((len(text), len(text) + len(part[0]), part[1])); text += part[0]
            else:
                text += part
        docs.append((text, gold))
    VAL = False
    return docs


CONFUSION = {"S": "5", "5": "S", "O": "0", "0": "O", "l": "1", "1": "l", "B": "8", "8": "B", "e": "c", "c": "e", "a": "o", "o": "a", "i": "í", "n": "m", "m": "n", "u": "v"}


def ruido(text, tasa, r):
    """Errores de OCR por sustitución (misma longitud, así las posiciones del corpus siguen valiendo)."""
    return "".join(CONFUSION.get(c, c) if c in CONFUSION and r.random() < tasa else c for c in text)


# ---------------------------------------------------------------- presidio
def motor(lang, modelo, config):
    from presidio_analyzer import AnalyzerEngine, Pattern, PatternRecognizer, RecognizerRegistry
    from presidio_analyzer.nlp_engine import NlpEngineProvider
    from presidio_analyzer.predefined_recognizers import (EmailRecognizer, EsNieRecognizer, EsNifRecognizer, IbanRecognizer,
                                                          PhoneRecognizer, SpacyRecognizer)
    nlp = NlpEngineProvider(nlp_configuration={"nlp_engine_name": "spacy", "models": [{"lang_code": lang, "model_name": modelo}]}).create_engine()
    reg = RecognizerRegistry(supported_languages=[lang])
    for rec in (EsNifRecognizer(supported_language=lang), EsNieRecognizer(supported_language=lang), IbanRecognizer(supported_language=lang),
                EmailRecognizer(supported_language=lang), PhoneRecognizer(supported_language=lang, supported_regions=("ES",)),
                SpacyRecognizer(supported_language=lang, supported_entities=["PERSON", "LOCATION"])):
        reg.add_recognizer(rec)
    if config == "mejorada":
        pat = lambda ent, rx, score=0.85: reg.add_recognizer(PatternRecognizer(supported_entity=ent, supported_language=lang, patterns=[Pattern(ent, rx, score)]))
        pat("ES_REF_CATASTRAL", r"\b\d{7}[A-Z]{2}\d{4}[A-Z]\d{4}[A-Z]{2}\b")
        pat("MATRICULA", rf"\b\d{{4}}[\s-]?[{CONSONANTES}]{{3}}\b")
        pat("PHONE_NUMBER", r"(?:\+34\s?)?\b[6789]\d{2}(?:\s?\d{2}){3}\b|\b[6789]\d{2}\s?\d{3}\s?\d{3}\b", 0.6)
        pat("ES_NIF", r"\b\d{1,2}\.\d{3}\.\d{3}-?[A-Z]\b", 0.7)
        pat("DIRECCION", r"(?i)\b(?:calle|c/|c\.|avenida|avda\.|plaza|paseo|carrer|pla[çc]a|rambla|passeig)\s[^,\n]{2,40}"
                         r"(?:,?\s*(?:n\.?º|núm\.?)?\s*\d+(?![.\d]))?(?:,\s*\d\.º\s*\d\.ª)?(?:,\s*\d{5})?(?:,?\s*(?:de\s)?[A-ZÀ-Ú][\wÀ-ÿ'·]*(?:\s[A-ZÀ-Ú][\wÀ-ÿ'·]*)?)?")
    if config == "ajustada":
        pat = lambda ent, rx, score=0.85: reg.add_recognizer(PatternRecognizer(supported_entity=ent, supported_language=lang, patterns=[Pattern(ent, rx, score)]))
        pat("ES_REF_CATASTRAL", r"\b\d{7}[A-Z]{2}\d{4}[A-Z]\d{4}[A-Z]{2}\b")
        pat("MATRICULA", rf"\b\d{{4}}\s?[{CONSONANTES}]{{3}}\b")
        pat("PHONE_NUMBER", r"\b[6789]\d{2}\s?\d{3}\s?\d{3}\b", 0.6)
        pat("DIRECCION", r"(?i)\b(?:calle|c/|avenida|avda\.|plaza|paseo|carrer|pla[çc]a|rambla|passeig)\s[^,\n]{2,40}"
                         r"(?:,\s*(?:n\.?º|núm\.?)\s*\d+)?(?:,\s*\d{5}\s+[A-ZÀ-Ú][\wÀ-ÿ'·]*(?:\s[A-ZÀ-Ú][\wÀ-ÿ'·]*)?)?")
    return AnalyzerEngine(registry=reg, nlp_engine=nlp, supported_languages=[lang])


# Palabras que el modelo confunde con nombres o lugares en textos jurídicos.
IGNORAR = ["DNI", "NIE", "FALLO", "DECISIÓ", "Testigo", "Testimoni", "ANTECEDENTES", "ANTECEDENTS", "HECHO", "FET", "SENTENCIA", "SENTÈNCIA",
           "TRIBUNAL", "JUSTICIA", "JUTJAT", "Magistrado-Juez", "Magistrat", "Ilmo", "Il·lm", "ESTIMAR", "ESTIMO"]
# «mejorada»: un LOCATION que es un municipio o una institución no es un dato personal (las direcciones van por patrón).
# shortcut: lista corta de municipios; en producción, el nomenclátor completo de Catalunya.
MUNICIPIOS = {"Tarragona", "Reus", "Valls", "El Vendrell", "Tortosa", "Girona", "Barcelona", "Lleida", "Madrid"}
INSTITUCION_RX = re.compile(r"(?:La\s)?(?:Ley|Llei|Audiencia|Audiència|Juzgado|Jutjat|Colegio|Col·legi|Tribunal|Agencia|Agència|Seguridad|Seguretat|Arrendamientos|Arrendaments)\b")
EMPRESA_RX = re.compile(r"[A-ZÀ-Ú][\wÀ-ÿ·]+(?:\s[A-ZÀ-Ú][\wÀ-ÿ·]+)*,\s*S\.[LA]\.")


MAYUS_RX = re.compile(r"\b[A-ZÀ-Ú·]{2,}(?:\s+[A-ZÀ-Ú·]+)+\b")


def analizar(eng, text, lang, config):
    # «mejorada»: el modelo apenas reconoce nombres en MAYÚSCULAS; los lee en Tipo Título (misma longitud, mismas posiciones).
    leido = MAYUS_RX.sub(lambda m: m.group().title(), text) if config == "mejorada" else text
    res = sorted(eng.analyze(text=leido, language=lang, allow_list=IGNORAR if config != "base" else None), key=lambda x: x.start)
    if config == "mejorada":  # «Jordi Puig i Serra»: el modelo corta el nombre en la «i»; se unen los dos trozos
        unidos = []
        for x in res:
            p = unidos[-1] if unidos else None
            if p and p.entity_type == x.entity_type == "PERSON" and text[p.end:x.start].lower() in (" i ", " y "):
                p.end = x.end
            else:
                unidos.append(x)
        res = [x for x in unidos if not (x.entity_type == "LOCATION" and (text[x.start:x.end] in MUNICIPIOS or INSTITUCION_RX.match(text, x.start)))]
    spans = [(x.start, x.end) for x in res]
    if config != "base":  # el CENDOJ no anonimiza personas jurídicas
        emp = [(m.start(), m.end()) for m in EMPRESA_RX.finditer(text)]
        spans = [s for s in spans if not any(s[0] < e and b < s[1] for b, e in emp)]
    return spans


# ---------------------------------------------------------------- métricas
def evaluar(docs, preds):
    por_cat, fp, emp_tapada, total_pred = {}, 0, 0, 0
    for (text, gold), spans in zip(docs, preds):
        total_pred += len(spans)
        for b, e, c in gold:
            cub = set()
            for s, f in spans:
                cub |= set(range(max(b, s), min(e, f)))
            d = por_cat.setdefault(c, {"n": 0, "toca": 0, "completo": 0})
            d["n"] += 1; d["toca"] += bool(cub); d["completo"] += len(cub) == e - b
        positivos = [(b, e) for b, e, c in gold if c != "EMPRESA"]
        for s, f in spans:
            if not any(s < e and b < f for b, e in positivos):
                fp += 1
                emp_tapada += any(s < e and b < f for b, e, c in gold if c == "EMPRESA")
    pos = {c: d for c, d in por_cat.items() if c != "EMPRESA"}
    n = sum(d["n"] for d in pos.values())
    return {"recall_completo": sum(d["completo"] for d in pos.values()) / n, "recall_toca": sum(d["toca"] for d in pos.values()) / n,
            "precision": (total_pred - fp) / total_pred if total_pred else 0, "fp_por_doc": fp / len(docs),
            "empresas_tapadas": por_cat.get("EMPRESA", {}).get("toca", 0) / max(1, por_cat.get("EMPRESA", {}).get("n", 1)),
            "por_categoria": {c: {"recall_completo": d["completo"] / d["n"], "recall_toca": d["toca"] / d["n"], "n": d["n"]} for c, d in pos.items()}}


def una(lang, modelo, config, tasa, validacion=False):
    import psutil
    proc = psutil.Process()
    t0 = time.perf_counter(); eng = motor(lang, modelo, config); carga = time.perf_counter() - t0
    docs = corpus(lang, validacion)
    r = random.Random(SEED)
    textos = [ruido(t, tasa, r) if tasa else t for t, _ in docs]
    analizar(eng, textos[0], lang, config)  # calentamiento
    tiempos, preds = [], []
    for t in textos:
        a = time.perf_counter(); preds.append(analizar(eng, t, lang, config)); tiempos.append(time.perf_counter() - a)
    # El ruido sustituye caracteres sin cambiar la longitud, así que las posiciones del corpus siguen valiendo.
    m = evaluar([(t, g) for t, (_, g) in zip(textos, docs)], preds)
    tiempos.sort()
    m.update(lang=lang, modelo=modelo, config=config, ruido=tasa, validacion=validacion, docs=len(docs), chars_por_doc=round(statistics.mean(len(t) for t in textos)),
             carga_s=round(carga, 2), ms_mediana=round(statistics.median(tiempos) * 1000, 1), ms_p95=round(tiempos[int(.95 * len(tiempos))] * 1000, 1),
             paginas_hora=round(3600 / statistics.mean(tiempos)), ram_mb=round(proc.memory_info().rss / 2**20))
    return m


# (lang, modelo, config, ruido, validación) — la validación usa otra semilla y formatos no vistos al ajustar.
COMBOS = ([("es", m, c, 0.0, False) for m in ("es_core_news_sm", "es_core_news_md", "es_core_news_lg") for c in ("base", "ajustada", "mejorada")]
          + [("es", "es_core_news_md", "mejorada", t, False) for t in (0.01, 0.04)]
          + [("ca", "ca_core_news_md", c, 0.0, False) for c in ("base", "ajustada", "mejorada")]
          + [("es", "es_core_news_md", "mejorada", 0.0, True), ("ca", "ca_core_news_md", "mejorada", 0.0, True)])

if __name__ == "__main__":
    if sys.argv[1:2] == ["--uno"]:
        print(json.dumps(una(sys.argv[2], sys.argv[3], sys.argv[4], float(sys.argv[5]), sys.argv[6:7] == ["True"])))
        sys.exit()
    # Auto-comprobación del generador: identificadores válidos.
    r = random.Random(1)
    d = dni(r); assert LETRAS[int(d[:-1]) % 23] == d[-1]
    i = iban(r).replace(" ", ""); assert int(i[4:] + "1428" + i[2:4]) % 97 == 1
    out = Path(__file__).parent / "resultados"; out.mkdir(exist_ok=True)
    res = []
    for combo in COMBOS:
        print("·", *combo, flush=True)
        p = subprocess.run([sys.executable, "-I", __file__, "--uno", *map(str, combo)], capture_output=True, text=True, encoding="utf-8")
        if p.returncode:
            print(p.stderr[-2000:]); sys.exit(1)
        res.append(json.loads(p.stdout.strip().splitlines()[-1]))
    (out / "resultados.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    print("\nidioma modelo config ruido corpus | cubierto toca precisión FP/doc empresas | ms/pág pág/h carga RAM")
    for m in res:
        print(f"{m['lang']} {m['modelo']} {m['config']} {m['ruido']:.0%} {'valid' if m['validacion'] else 'ajuste'} "
              f"| {m['recall_completo']:.1%} {m['recall_toca']:.1%} {m['precision']:.1%} "
              f"{m['fp_por_doc']:.2f} {m['empresas_tapadas']:.0%} | {m['ms_mediana']} {m['paginas_hora']} {m['carga_s']}s {m['ram_mb']}MB")
