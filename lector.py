"""
Lector de notas: convierte el link de Google Noticias en la URL real del
medio (Google lo codifica; se decodifica con su propio endpoint) y extrae el
comienzo del texto de la nota (primeros parrafos) para que la IA tenga
CONTENIDO y no solo el titulo.

Honesto: no todos los medios lo permiten (paywall, bloqueo de robots). Si
falla, la nota queda solo con su titular. Cache en disco para no repetir.
"""
import os
import re
import json
import time
import html as _html
import requests
from html.parser import HTMLParser

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE_FILE = os.path.join(HERE, "cache_notas.json")
UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
      "Accept-Language": "es-CL,es;q=0.9"}
TTL = 2 * 24 * 3600
MAX_CHARS = 700


def _cache():
    try:
        return json.load(open(CACHE_FILE))
    except Exception:
        return {}


def _save(c):
    try:
        # poda entradas viejas
        ahora = time.time()
        c = {k: v for k, v in c.items() if ahora - v.get("ts", 0) < TTL}
        json.dump(c, open(CACHE_FILE, "w"))
    except Exception:
        pass


def url_real(link):
    """Decodifica un link news.google.com/rss/articles/... -> URL del medio.
    Devuelve None si no se puede."""
    if "news.google.com" not in link:
        return link
    try:
        aid = link.split("/articles/")[1].split("?")[0]
        h = requests.get(link, headers={"User-Agent": "Mozilla/5.0"}, timeout=20).text
        sg = re.search(r'data-n-a-sg="([^"]+)"', h)
        ts = re.search(r'data-n-a-ts="([^"]+)"', h)
        if not (sg and ts):
            return None
        payload = ('[[["Fbv4je","[\\"garturlreq\\",[[\\"es-419\\",\\"CL\\",[\\"FINANCE_TOP_INDICES\\",\\"WEB_TEST_1_0_0\\"],'
                   'null,null,1,1,\\"CL:es-419\\",null,180,null,null,null,null,null,0,null,null,[1608992183,723341000]],'
                   '\\"es-419\\",\\"CL\\",1,[2,3,4,8],1,0,\\"655000234\\",0,0,null,0],\\"' + aid + '\\",' + ts.group(1) +
                   ',\\"' + sg.group(1) + '\\"]",null,"generic"]]]')
        r = requests.post("https://news.google.com/_/DotsSplashUi/data/batchexecute",
                          data={"f.req": payload},
                          headers={"User-Agent": "Mozilla/5.0",
                                   "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8"}, timeout=20)
        if "garturlres" not in r.text:
            return None
        m = re.search(r'"(https?://[^"\\]+)', r.text.split("garturlres")[1])
        return m.group(1).rstrip("\\") if m else None
    except Exception:
        return None


class _P(HTMLParser):
    """Junta el texto de los <p> (ignora scripts, menus, etc.)."""
    SKIP = ("script", "style", "nav", "header", "footer", "aside", "form", "noscript", "figure", "button")

    def __init__(self):
        super().__init__()
        self.parrafos, self._buf, self._en_p, self._skip = [], [], False, 0

    def handle_starttag(self, tag, attrs):
        if tag in self.SKIP:
            self._skip += 1
        elif tag == "p" and not self._skip:
            self._en_p, self._buf = True, []

    def handle_endtag(self, tag):
        if tag in self.SKIP:
            self._skip = max(0, self._skip - 1)
        elif tag == "p" and self._en_p:
            t = re.sub(r"\s+", " ", "".join(self._buf)).strip()
            if len(t) >= 60:
                self.parrafos.append(t)
            self._en_p = False

    def handle_data(self, d):
        if self._en_p and not self._skip:
            self._buf.append(d)


_GENERICO = ("no pudimos encontrar", "portal financiero", "consulta las últimas noticias", "noticias de última hora",
             "manténgase al día", "página no encontrada", "page not found", "404")
_BASURA = ("cookies", "suscríbete", "suscribete", "regístrate", "registrate", "inicia sesión", "newsletter",
           "todos los derechos", "publicidad", "comparte", "síguenos", "lee también", "te puede interesar")


def _json_ld_body(h):
    """articleBody o description del JSON-LD (lo mas limpio cuando existe)."""
    best = ""
    for x in re.findall(r'<script[^>]+application/ld\+json[^>]*>(.*?)</script>', h, re.S):
        try:
            j = json.loads(x.strip())
        except Exception:
            continue
        objs = j if isinstance(j, list) else [j]
        for o in objs:
            if not isinstance(o, dict):
                continue
            for o2 in ([o] + (o.get("@graph") or [])):
                if isinstance(o2, dict):
                    body = o2.get("articleBody") or ""
                    if isinstance(body, str) and len(body) > len(best):
                        best = body
    return re.sub(r"\s+", " ", best).strip()


def _meta_desc(h):
    for pat in (r'<meta[^>]+property="og:description"[^>]+content="([^"]*)"',
                r'<meta[^>]+content="([^"]*)"[^>]+property="og:description"',
                r'<meta[^>]+name="description"[^>]+content="([^"]*)"',
                r'<meta[^>]+content="([^"]*)"[^>]+name="description"'):
        m = re.search(pat, h, re.I)
        if m and len(m.group(1)) > 40:
            return _html.unescape(m.group(1)).strip()
    return ""


def _es_generico(s):
    low = s.lower()
    return any(g in low for g in _GENERICO)


def _recortar(s, max_chars):
    s = s.strip()
    if len(s) <= max_chars:
        return s
    return s[:max_chars].rsplit(" ", 1)[0] + "…"


def texto_nota(url, max_chars=MAX_CHARS):
    """Comienzo de la nota (texto plano) o '' si no se pudo. Orden: cuerpo en
    JSON-LD (limpio) -> parrafos <p> -> descripcion meta (1-2 frases)."""
    try:
        r = requests.get(url, headers=UA, timeout=20)
        if r.status_code != 200 or "text/html" not in r.headers.get("content-type", ""):
            return ""
        h = r.text
        if r.url.rstrip("/").endswith(("404", "404.html")):
            return ""
        body = _json_ld_body(h)
        if len(body) >= 200:
            return _recortar(_html.unescape(body), max_chars)
        p = _P()
        p.feed(h)
        out, n = [], 0
        for t in p.parrafos:
            low = t.lower()
            if any(b in low for b in _BASURA):
                continue
            out.append(_html.unescape(t))
            n += len(t)
            if n >= max_chars:
                break
        s = " ".join(out)
        if len(s) >= 200:
            return _recortar(s, max_chars)
        desc = _meta_desc(h)
        if desc and len(desc) > len(s) and not _es_generico(desc):
            return _recortar(desc, max_chars)
        return _recortar(s, max_chars) if (s and not _es_generico(s)) else ""
    except Exception:
        return ""


def enriquecer(items, max_notas=12, tiempo_max=90):
    """Agrega 'url' y 'resumen' a los items (in place). Se detiene al llegar a
    max_notas o tiempo_max segundos. Devuelve cuantas notas trajeron texto."""
    cache = _cache()
    t0, hechas, con_texto = time.time(), 0, 0
    for it in items:
        if hechas >= max_notas or time.time() - t0 > tiempo_max:
            break
        link = it.get("link") or ""
        if not link:
            continue
        c = cache.get(link)
        if c and time.time() - c.get("ts", 0) < TTL:
            it["url"], it["resumen"] = c.get("url"), c.get("resumen", "")
        else:
            url = url_real(link)
            resumen = texto_nota(url) if url else ""
            it["url"], it["resumen"] = url, resumen
            cache[link] = {"url": url, "resumen": resumen, "ts": time.time()}
        hechas += 1
        if it.get("resumen"):
            con_texto += 1
    _save(cache)
    return con_texto
