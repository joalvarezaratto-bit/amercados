"""
Titulares por seccion desde Google Noticias (RSS gratis, sin API key).

Google Noticias agrega TODOS los medios (DF, El Mercurio, La Tercera,
Bloomberg Linea, Reuters en español, EFE, CNN...). Se buscan varios temas
por seccion (config.NOTICIAS), se puntua cada titular por palabras clave y
se DEDUPLICA por "historia" (la misma noticia sale en 20 medios con
titulos distintos; se muestra una vez). Logica heredada de dolar-bot.

HONESTO: son titulares publicos, no analisis propio ni prediccion.
"""
import os
import re
import json
import html
import unicodedata
import datetime as dt
import requests
import feedparser
import config as C

UA = {"User-Agent": "Mozilla/5.0"}
HERE = os.path.dirname(os.path.abspath(__file__))
VISTAS_FILE = os.path.join(HERE, "noticias_vistas.json")   # historias ya enviadas (se versiona)


def _url(q, region):
    q = requests.utils.quote(q)
    if region == "cl":
        return f"https://news.google.com/rss/search?q={q}&hl=es-419&gl=CL&ceid=CL:es-419"
    return f"https://news.google.com/rss/search?q={q}&hl=es-419&gl=US&ceid=US:es-419"


_STOP = set((
    "de la el en y a los las un una por con para que se su del al lo es mas "
    "ante sobre hoy tras entre como o u ni le ya son fue ser este esta esto "
    "estos estas segun hasta desde muy no si cual sus e mientras pese aun "
    "aunque hay ha han sin dia dias tan solo esa ese uno dos the of and to in"
).split())


def _sin_tildes(s):
    return "".join(c for c in unicodedata.normalize("NFD", s)
                   if unicodedata.category(c) != "Mn")


def _stem(w):
    return w[:-1] if len(w) > 4 and w.endswith("s") else w


def firma(titulo):
    t = _sin_tildes(titulo.lower())
    palabras = re.findall(r"[a-z0-9%]+", t)
    return frozenset(_stem(w) for w in palabras if len(w) >= 3 and w not in _STOP)


def _misma(f, previas):
    for p in previas:
        comun = len(f & p)
        if comun >= 3 and comun / max(1, min(len(f), len(p))) >= 0.5:
            return True
    return False


# Medios chilenos (si la fuente es uno de estos, la nota es de Chile aunque el
# titulo no diga "Chile"). Se compara en minusculas y sin tildes.
MEDIOS_CL = ("diario financiero", "df.cl", "la tercera", "emol", "el mercurio", "biobio", "bio bio",
             "cooperativa", "cnn chile", "t13", "24horas", "24 horas", "la segunda", "el mostrador",
             "ex-ante", "pauta", "diarioestrategia", "estrategia", "publimetro", "adn radio",
             "radio duna", "infinita", "ciper", "el dinamo", "el dínamo", "america economia",
             "américa economía", "la nacion chile", "chilevision", "chv", "mega", "meganoticias",
             "portal innova", "xtb", "minería chilena", "mineria chilena", "redimin", "mch",
             "g5noticias", "fintualist", "el desconcierto", "the clinic", "radio agricultura",
             "diario concepcion", "el sur", "soychile", "reporte minero", "bnamericas", "df sud",
             "la hora", "lun", "las ultimas noticias", "elmostrador", "latercera", "mascontainer",
             "portal portuario", "portalportuario", "econsult", "banco central")
# Señales de que la nota es de OTRO pais (se descarta en la seccion Chile
# salvo que el titulo mencione Chile).
OTRO_PAIS = ("colombia", "minhacienda", "el emisor", "banrep", "petro", "de la espriella", "bogotá",
             "bogota", "méxico", "mexico", "banxico", "sheinbaum", "argentin", "milei", "perú", "peru",
             "bcrp", "ecuador", "uruguay", "paraguay", "bolivia", "venezuela", "maduro", "españa",
             "brasil", "lula", "portafolio", "semana", "infobae", "ámbito", "ambito", "clarín",
             "clarin", "el país", "el pais", "expansión", "expansion", "el economista", "gestión",
             "gestion", "la república", "la republica", "el universal", "el financiero", "forbes méxico",
             "forbes mexico", "eju.tv", "el tiempo")
CHILE_KW = ("chile", "chilen", "santiago", "banco central de chile", "hacienda", "kast", "codelco",
            "ipsa", "imacec", "ine ", "tpm", "cochilco", "sonami", "sofofa", "cámara de diputados",
            "senado", "la moneda", "peso chileno", "uf ", "afp", "isapre", "enap", "sqm", "latam",
            "falabella", "cencosud", "copec", "entel", "bci", "banco de chile", "santander chile",
            "colbún", "colbun", "enel chile", "ccu", "andina", "cmpc", "mall plaza", "parque arauco",
            "vapores", "antofagasta", "escondida", "collahuasi", "los pelambres", "quebrada blanca")


def _es_chile(titulo, fuente):
    """True si la nota es de Chile: fuente chilena, o el titulo menciona Chile.
    Descarta notas de otros paises (Colombia/Mexico/Argentina...) que se
    cuelan por hablar de 'Hacienda', 'Presupuesto', 'Banco Central'."""
    t = _sin_tildes((titulo + " ").lower())
    f = _sin_tildes((fuente or "").lower())
    if any(k in t for k in CHILE_KW):
        return True
    if any(m in f for m in MEDIOS_CL):
        return not any(o in t for o in OTRO_PAIS[:40])   # medio chileno hablando de otro pais
    if any(o in t for o in OTRO_PAIS) or any(o in f for o in OTRO_PAIS):
        return False
    return False   # sin señal de Chile -> fuera (mejor callar que confundir)


_MACRO_CL = ("ipc", "tpm", "banco central", "imacec", "desempleo", "reunión de política", "tasa de política")


def _score(titulo, sec=None):
    t = titulo.lower()
    s = sum(p for kw, p in C.KW.items() if kw in t)
    if any(x in t for x in C.EXCLUIR) and "chile" not in t:
        s -= 8
    if sec == "chile" and any(k in t for k in _MACRO_CL):
        s += 3   # el dato macro chileno del dia debe subir a "lo mas relevante"
    return s


_COLA = re.compile(r"\s*[:|\-–—]\s*(?:dow jones|s&p|nasdaq|wall street|futuros|acciones|bolsa|mercados)(?:[ ,|/&-]*(?:dow jones|s&p ?500|s&p|nasdaq|wall street|futuros|acciones|bolsa|mercados|hoy))*\s*$", re.I)
_SUFIJOS = re.compile(r"\s*[|\-–—]\s*(?:investing\.com[^|]*|yahoo[^|]*|bloomberg línea|infobae|el economista|expansión)\s*$", re.I)


def limpiar_titulo(t):
    """Quita colas SEO ('…: Dow Jones, S&P, Nasdaq, Wall Street, Futuros') y
    nombres de medio pegados al final del titular."""
    t = html.unescape(t).strip()
    for _ in range(2):
        t = _COLA.sub("", t)
        t = _SUFIJOS.sub("", t)
    t = re.sub(r"\s+", " ", t).strip(" :;-–—|")
    return t


def _fuente(entry, titulo):
    try:
        src = entry.source.get("title", "")
    except Exception:
        src = ""
    if not src and " - " in titulo:
        src = titulo.rsplit(" - ", 1)[-1]
    return src.strip()


def _fecha(entry):
    try:
        p = entry.published_parsed
        return dt.datetime(*p[:6], tzinfo=dt.timezone.utc)
    except Exception:
        return None


def buscar_seccion(consultas, top, solo_chile=False, sec=None):
    cands = []
    for region, q in consultas:
        try:
            d = feedparser.parse(requests.get(_url(q, region), headers=UA, timeout=15).content)
        except Exception:
            continue
        for e in d.entries[:25]:
            full = html.unescape(e.get("title", ""))
            fuente = _fuente(e, full)
            titulo = full.rsplit(" - ", 1)[0] if " - " in full else full
            titulo = titulo.strip()
            if len(titulo) < 20:
                continue
            if solo_chile and not _es_chile(titulo, fuente):
                continue
            titulo = limpiar_titulo(titulo)
            f = firma(titulo)
            if len(f) < 3:
                continue
            cands.append({"titulo": titulo, "fuente": fuente, "link": e.get("link", ""),
                          "score": _score(full), "firma": f, "fecha": _fecha(e)})
    # relevancia + RECENCIA: una noticia de hace 1 h vale mas que la misma de anoche.
    # bonus: +4 si tiene menos de 2 h, +3 hasta 4 h, +2 hasta 8 h, +1 hasta 14 h.
    ahora = dt.datetime.now(dt.timezone.utc)
    for c in cands:
        horas = ((ahora - c["fecha"]).total_seconds() / 3600) if c["fecha"] else 24
        c["horas"] = horas
        c["base"] = c["score"]   # relevancia sin el bonus de recencia
        c["score"] += 4 if horas <= 2 else (3 if horas <= 4 else (2 if horas <= 8 else (1 if horas <= 14 else 0)))
    cands.sort(key=lambda x: (-x["score"], x.get("horas", 99)))
    vistas, unicos = [], []
    for c in cands:
        if _misma(c["firma"], vistas):
            continue
        vistas.append(c["firma"])
        unicos.append(c)
    return unicos[:top]


def recolectar(top=None):
    """{seccion: [titulares]} + 'relevante' = lo mas fuerte de todo el dia."""
    top = top or C.NOTICIAS_TOP_POR_SECCION
    out = {}
    todas = []
    for sec, consultas in C.NOTICIAS.items():
        items = buscar_seccion(consultas, top, solo_chile=(sec == "chile"), sec=sec)
        out[sec] = items
        for it in items:
            it2 = dict(it)
            it2["seccion"] = sec
            todas.append(it2)
    # "lo mas relevante": mayor puntaje, una historia por tema, maximo 2 por
    # seccion y SIEMPRE al menos una de Chile (si hay alguna con puntaje >= 4)
    todas.sort(key=lambda x: -x["score"])
    vistas, rel, por_sec = [], [], {}
    for it in todas:
        if _misma(it["firma"], vistas) or por_sec.get(it["seccion"], 0) >= 2:
            continue
        vistas.append(it["firma"]); por_sec[it["seccion"]] = por_sec.get(it["seccion"], 0) + 1
        rel.append(it)
        if len(rel) >= 6:
            break
    if not any(it["seccion"] == "chile" for it in rel[:4]):
        cl = next((it for it in todas if it["seccion"] == "chile" and it["score"] >= 4 and not _misma(it["firma"], [r["firma"] for r in rel[:3]])), None)
        if cl:
            rel = rel[:3] + [cl] + [r for r in rel[3:] if r is not cl]
    out["relevante"] = rel[:6]
    # ULTIMA HORA: lo mas reciente con relevancia minima (distinto de "lo mas relevante")
    recientes = [it for it in todas if it.get("fecha") and it.get("horas", 99) <= 6 and it.get("base", 0) >= 5]
    recientes.sort(key=lambda x: x["horas"])
    vistas, uh = [], []
    for it in recientes:
        if _misma(it["firma"], vistas):
            continue
        vistas.append(it["firma"])
        uh.append(it)
    out["ultima_hora"] = uh[:6]
    return out


def dato_publicado(N, clave):
    """Busca en los titulares chilenos de hoy la cifra de un dato macro ya publicado.
    clave: 'ipc' -> ('IPC', '0,6%', titular) ; 'tpm' -> ('TPM', '4,50%', titular). None si no hay."""
    pats = {
        "ipc": (r"\bIPC\b.*?([+-]?\d{1,2},\d{1,2})\s*%", "IPC de Chile (INE)"),
        "tpm": (r"(?:TPM|tasa de política|Banco Central).*?(?:mantiene|mantuvo|sube|subió|baja|bajó|recorta|recortó|eleva|elevó).*?(\d{1,2},\d{1,2})\s*%", "TPM del Banco Central"),
    }
    if clave not in pats:
        return None
    pat, nombre = pats[clave]
    mensual, anual, fuente_m, titulo_m = None, None, "", ""
    for it in (N.get("chile") or []) + (N.get("tasas") or []) + (N.get("cambio") or []):
        if it.get("horas") is not None and it["horas"] > 30:
            continue
        for m in re.finditer(pat, it["titulo"], re.I):
            v = float(m.group(1).replace(",", "."))
            low = it["titulo"].lower()
            if clave == "ipc":
                # mensual: cifra chica (< 2%) o rotulada "mensual"; anual: "anual"/"12 meses" o cifra grande
                if ("anual" in low or "12 meses" in low or "interanual" in low or v >= 2.0) and anual is None:
                    anual = m.group(1)
                elif v < 2.0 and mensual is None:
                    mensual, fuente_m, titulo_m = m.group(1), it.get("fuente", ""), it["titulo"]
            else:
                return (nombre, m.group(1) + "%", it["titulo"], it.get("fuente", ""))
    if clave == "ipc" and (mensual or anual):
        valor = (f"{mensual}% mensual" if mensual else "") + (" · " if mensual and anual else "") + (f"{anual}% anual" if anual else "")
        return (nombre, valor, titulo_m or "", fuente_m or "prensa")
    return None


def hace(it):
    """'hace 40 min' / 'hace 3 h' a partir de la fecha de publicacion."""
    h = it.get("horas")
    if h is None:
        return ""
    m = int(round(h * 60))
    return f"hace {m} min" if m < 60 else f"hace {int(round(h))} h"


# ---------------------------------------------------------------- vistas
def cargar_vistas():
    """Firmas de las historias ya enviadas (informe o flash)."""
    try:
        return [frozenset(x) for x in json.load(open(VISTAS_FILE))]
    except Exception:
        return []


def marcar_vistas(items):
    """Recuerda las historias mostradas para que el próximo flash traiga solo
    lo NUEVO. Guarda las últimas ~400."""
    vistas = cargar_vistas()
    for it in items:
        f = it.get("firma") or firma(it["titulo"])
        if not _misma(f, vistas):
            vistas.append(f)
    try:
        json.dump([sorted(f) for f in vistas[-400:]], open(VISTAS_FILE, "w"))
    except Exception:
        pass


def nuevas(N, top=4):
    """Titulares NO enviados antes, los más relevantes primero (una historia
    por tema)."""
    vistas = cargar_vistas()
    out = []
    for it in N.get("relevante", []) + [x for s, its in N.items() if s != "relevante" for x in its]:
        if _misma(it["firma"], vistas) or _misma(it["firma"], [o["firma"] for o in out]):
            continue
        out.append(it)
    out.sort(key=lambda x: -x["score"])
    return out[:top]
