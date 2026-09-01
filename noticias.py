"""
Titulares por seccion desde Google Noticias (RSS gratis, sin API key).

Google Noticias agrega TODOS los medios (DF, El Mercurio, La Tercera,
Bloomberg Linea, Reuters en español, EFE, CNN...). Se buscan varios temas
por seccion (config.NOTICIAS), se puntua cada titular por palabras clave y
se DEDUPLICA por "historia" (la misma noticia sale en 20 medios con
titulos distintos; se muestra una vez). Logica heredada de dolar-bot.

HONESTO: son titulares publicos, no analisis propio ni prediccion.
"""
import re
import html
import unicodedata
import datetime as dt
import requests
import feedparser
import config as C

UA = {"User-Agent": "Mozilla/5.0"}


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


def _score(titulo):
    t = titulo.lower()
    s = sum(p for kw, p in C.KW.items() if kw in t)
    if any(x in t for x in C.EXCLUIR) and "chile" not in t:
        s -= 8
    return s


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


def buscar_seccion(consultas, top):
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
            f = firma(titulo)
            if len(f) < 3:
                continue
            cands.append({"titulo": titulo, "fuente": fuente, "link": e.get("link", ""),
                          "score": _score(full), "firma": f, "fecha": _fecha(e)})
    cands.sort(key=lambda x: (-x["score"], -(x["fecha"].timestamp() if x["fecha"] else 0)))
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
        items = buscar_seccion(consultas, top)
        out[sec] = items
        for it in items:
            it2 = dict(it)
            it2["seccion"] = sec
            todas.append(it2)
    # "lo mas relevante": mayor puntaje global, una historia por tema
    todas.sort(key=lambda x: -x["score"])
    vistas, rel = [], []
    for it in todas:
        if _misma(it["firma"], vistas):
            continue
        vistas.append(it["firma"])
        rel.append(it)
    out["relevante"] = rel[:6]
    return out
