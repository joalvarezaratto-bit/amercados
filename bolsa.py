"""
Bolsa de Santiago con datos reales: las ~30 acciones grandes del IPSA desde
Yahoo Finance (sufijo .SN, gratis, al dia aunque el indice ^IPSA este
congelado). Calcula alzas/bajas, sectores y un IPSA ESTIMADO.

IPSA estimado: variacion diaria = suma ponderada (pesos aprox. de config) de
las variaciones de las acciones. Nivel = ultimo cierre EXACTO conocido por
prensa (state.json) arrastrado con las variaciones ponderadas de los dias
siguientes. Se rotula "estimado": no es el dato oficial de la Bolsa.
"""
import os
import json
import time
import datetime as dt
import config as C
import datos as DS

HERE = os.path.dirname(os.path.abspath(__file__))
VOL_FILE = os.path.join(HERE, "volumen_hist.json")   # historial de montos por sesion (se versiona)


import requests

UA = {"User-Agent": "Mozilla/5.0"}
CACHE_FILE = os.path.join(HERE, "cache_bolsa.json")
TTL = 600


def _quote_1d(tk):
    """Consulta INTRADIA (range=1d): el unico modo en que Yahoo entrega un
    'cierre anterior' correcto para las acciones .SN (su historial diario
    repite precios viejos y da variaciones falsas)."""
    for host in ("query1", "query2"):
        try:
            r = requests.get(f"https://{host}.finance.yahoo.com/v8/finance/chart/{tk}",
                             params={"interval": "5m", "range": "1d"}, headers=UA, timeout=20)
            res = r.json()["chart"]["result"][0]
            m = res["meta"]
            price = m.get("regularMarketPrice")
            prev = m.get("chartPreviousClose") or m.get("previousClose")
            if price is None or not prev:
                return None
            closes = [c for c in (res["indicators"]["quote"][0].get("close") or []) if c]
            ts = res.get("timestamp") or []
            return {"price": price, "prev": prev, "chg": (price - prev) / prev * 100,
                    "vol": m.get("regularMarketVolume"), "market_time": m.get("regularMarketTime"),
                    "intra": closes, "sesion_ts": ts[0] if ts else m.get("regularMarketTime"), "ts": time.time()}
        except Exception:
            continue
    return None


def recolectar():
    """Trae las acciones (con cache de 10 min). Lista de dicts."""
    try:
        cache = json.load(open(CACHE_FILE))
    except Exception:
        cache = {}
    out = []
    for tk, nombre, sector, peso in C.IPSA_ACCIONES:
        d = cache.get(tk)
        if not d or time.time() - d.get("ts", 0) > TTL:
            d = _quote_1d(tk) or d
            if d:
                cache[tk] = d
            time.sleep(0.15)   # no golpear a Yahoo
        if not d:
            continue
        edad = DS.edad_horas(d.get("market_time"))
        out.append({"ticker": tk, "nombre": nombre, "sector": sector, "peso": peso,
                    "price": d["price"], "prev": d["prev"], "chg": d["chg"], "vol": d.get("vol"),
                    "intra": d.get("intra") or [], "market_time": d.get("market_time"),
                    "sesion_ts": d.get("sesion_ts"), "viejo": bool(edad and edad > 36)})
    try:
        json.dump(cache, open(CACHE_FILE, "w"))
    except Exception:
        pass
    return out


def _fecha_local(ts, tz):
    return dt.datetime.fromtimestamp(ts, tz).date()


def analizar(acciones, tz, cierre_prensa=None):
    """Resumen: alzas, bajas, sectores, IPSA estimado."""
    if not acciones:
        return None
    vivas = [a for a in acciones if not a["viejo"]]
    base = vivas or acciones
    peso_total = sum(a["peso"] for a in base) or 1
    var_idx = sum(a["chg"] * a["peso"] for a in base) / peso_total
    alzas = sorted([a for a in base if a["chg"] > 0], key=lambda a: -a["chg"])
    bajas = sorted([a for a in base if a["chg"] < 0], key=lambda a: a["chg"])
    # sectores: variacion ponderada por peso
    sect = {}
    for a in base:
        s = sect.setdefault(a["sector"], {"peso": 0.0, "suma": 0.0, "n": 0})
        s["peso"] += a["peso"]; s["suma"] += a["chg"] * a["peso"]; s["n"] += 1
    sectores = sorted([(k, v["suma"] / v["peso"], v["n"], v["peso"]) for k, v in sect.items() if v["peso"] > 0],
                      key=lambda x: -x[1])
    # contribucion al indice (puntos porcentuales) por accion
    for a in base:
        a["contrib"] = a["chg"] * a["peso"] / peso_total
    # ---- montos transados (volumen x precio, en pesos) ----
    for a in base:
        a["monto"] = (a.get("vol") or 0) * a["price"]
    monto_total = sum(a["monto"] for a in base)
    mas_transadas = sorted(base, key=lambda a: -a["monto"])[:6]
    hist = _cargar_hist()
    prom20 = None
    if hist:
        vals = [v["total"] for f, v in sorted(hist.items())[-20:] if v.get("total")]
        if len(vals) >= 3:
            prom20 = sum(vals) / len(vals)
    hora = max((a["market_time"] or 0) for a in base)
    sesion = _fecha_local(max((a.get("sesion_ts") or a["market_time"] or 0) for a in base), tz) if hora else None
    # ---- IPSA estimado: nivel = cierre EXACTO de prensa de la sesion anterior
    #      arrastrado con la variacion ponderada de hoy (solo si calzan las fechas)
    nivel, nivel_base, nivel_fecha = None, None, None
    if cierre_prensa and cierre_prensa.get("price") and cierre_prensa.get("fecha") and sesion:
        try:
            f0 = dt.date.fromisoformat(cierre_prensa["fecha"])
            prev_habil = sesion - dt.timedelta(days=1)
            while prev_habil.weekday() >= 5 or prev_habil.strftime("%m-%d") in C.FERIADOS_CL or prev_habil.strftime("%Y-%m-%d") in C.FERIADOS_CL:
                prev_habil -= dt.timedelta(days=1)
            if f0 == prev_habil:
                nivel = cierre_prensa["price"] * (1 + var_idx / 100)
                nivel_base, nivel_fecha = cierre_prensa["price"], f0
            elif f0 == sesion:
                nivel, nivel_base, nivel_fecha = cierre_prensa["price"], cierre_prensa["price"], f0
        except Exception:
            nivel = None
    return {"var": var_idx, "n": len(base), "n_alzas": len(alzas), "n_bajas": len(bajas),
            "alzas": alzas[:5], "bajas": bajas[:5], "sectores": sectores, "acciones": sorted(base, key=lambda a: -a["chg"]),
            "nivel": nivel, "nivel_fecha": nivel_fecha, "nivel_base": nivel_base,
            "market_time": hora, "sesion": sesion,
            "monto_total": monto_total, "mas_transadas": mas_transadas, "monto_prom20": prom20,
            "monto_vs_prom": ((monto_total / prom20 - 1) * 100) if prom20 else None, "n_hist": len(hist)}


# Nombre con el que la prensa suele llamar a cada empresa (para buscar "por que").
PRENSA_ALIAS = {
    "SQM": "SQM", "Banco de Chile": "Banco de Chile", "Santander Chile": "Banco Santander Chile",
    "Falabella": "Falabella", "Copec": "Empresas Copec", "LATAM Airlines": "LATAM Airlines",
    "Cencosud": "Cencosud", "BCI": "Banco BCI", "Enel Américas": "Enel Américas", "CMPC": "CMPC",
    "Enel Chile": "Enel Chile", "Vapores": "Vapores CSAV", "Quiñenco": "Quiñenco", "CCU": "CCU",
    "Colbún": "Colbún", "Itaú Chile": "Banco Itaú Chile", "Parque Arauco": "Parque Arauco",
    "Mallplaza": "Mallplaza", "Cencosud Shopping": "Cencosud Shopping", "Andina-B": "Embotelladora Andina",
    "Entel": "Entel", "Aguas Andinas": "Aguas Andinas", "CAP": "CAP acero", "Concha y Toro": "Concha y Toro",
    "Engie Chile": "Engie Chile", "SMU": "SMU supermercados", "IAM": "IAM Aguas", "Ripley": "Ripley",
    "Sonda": "Sonda", "Salfacorp": "Salfacorp",
}


def por_que(acciones, max_n=3, dias=2):
    """Para cada accion, busca en Google Noticias (prensa chilena, ultimos
    `dias` dias) un titular sobre la empresa. Devuelve {nombre: {titulo, fuente,
    link, hace}} solo cuando encuentra algo. HONESTO: es un titular relacionado,
    no una explicacion verificada del movimiento."""
    import html as _html
    import feedparser
    import noticias as NT
    out = {}
    for a in acciones[:max_n]:
        nombre = a["nombre"]
        q = f'"{PRENSA_ALIAS.get(nombre, nombre)}" when:{dias}d'
        try:
            url = ("https://news.google.com/rss/search?q=" + requests.utils.quote(q) + "&hl=es-419&gl=CL&ceid=CL:es-419")
            d = feedparser.parse(requests.get(url, headers=UA, timeout=15).content)
        except Exception:
            continue
        mejor = None
        MERCADO = ("acción", "acciones", "bolsa", "resultado", "utilidad", "ganancia", "pérdida", "perdida", "dividendo",
                   "compra", "venta", "adquisici", "fusión", "fusion", "deuda", "bono", "clasificaci", "rating",
                   "guidance", "proyecci", "ipsa", "inversión", "inversion", "contrato", "licitaci", "ebitda",
                   "ingresos", "trimestre", "aumento de capital", "opa", "toma de control", "emisión", "emision",
                   "recomendaci", "precio objetivo", "corredora", "papel", "títulos", "titulos", "capitalización")
        alias = PRENSA_ALIAS.get(nombre, nombre).lower()
        primera = alias.split()[0]
        for e in d.entries[:15]:
            t = _html.unescape(e.get("title", ""))
            titulo = t.rsplit(" - ", 1)[0].strip()
            fuente = t.rsplit(" - ", 1)[-1].strip() if " - " in t else ""
            low = titulo.lower()
            # OBLIGATORIO: que nombre a la empresa y que sea un titular de negocio/mercado
            if primera not in low and alias not in low:
                continue
            n_merc = sum(1 for k in MERCADO if k in low)
            if n_merc == 0:
                continue
            # descartar prensa de otros paises y notas sociales/RSE
            fl = fuente.lower()
            if any(x in fl or x in low for x in ("méxico", "mexico", "argentin", "colombia", "perú", "peru", "puebla", "buap", "bomberos", "capacit", "voluntari", "donaci")):
                continue
            try:
                p = e.published_parsed
                horas = (dt.datetime.now(dt.timezone.utc) - dt.datetime(*p[:6], tzinfo=dt.timezone.utc)).total_seconds() / 3600
            except Exception:
                horas = 48
            sc = 2 * n_merc + (2 if horas <= 12 else (1 if horas <= 30 else 0)) + (1 if alias in low else 0)
            if mejor is None or sc > mejor["sc"]:
                mejor = {"titulo": titulo, "fuente": fuente, "link": e.get("link", ""), "horas": horas, "sc": sc}
        if mejor and mejor["sc"] >= 3:
            mejor["hace"] = NT.hace(mejor)
            out[nombre] = mejor
        time.sleep(0.2)
    return out


def resumen_mercado(b):
    """Parrafo de resumen de la sesion por reglas (sin IA)."""
    if not b:
        return ""
    ses = "la sesión de hoy" if b.get("sesion") == dt.date.today() else f"la sesión del {b['sesion'].day}-{['ene','feb','mar','abr','may','jun','jul','ago','sep','oct','nov','dic'][b['sesion'].month-1]}" if b.get("sesion") else "la sesión"
    dir_ = "sube" if b["var"] > 0.05 else ("baja" if b["var"] < -0.05 else "se mantiene")
    amp = "amplia" if max(b["n_alzas"], b["n_bajas"]) >= 0.7 * b["n"] else "mixta"
    P = [f"El IPSA estimado {dir_} {_p(abs(b['var']), 2).lstrip('+-')} en {ses}, con amplitud {amp}: "
         f"{b['n_alzas']} acciones al alza y {b['n_bajas']} a la baja."]
    if b["sectores"]:
        top, bot = b["sectores"][0], b["sectores"][-1]
        P.append(f"El sector más fuerte es {top[0]} ({_p(top[1])}) y el más débil {bot[0]} ({_p(bot[1])}).")
    if b["alzas"]:
        a = b["alzas"][0]
        s = f"Lidera {a['nombre']} ({_p(a['chg'])})"
        pq = (b.get("por_que") or {}).get(a["nombre"])
        if pq:
            s += f"; en prensa: «{pq['titulo']}» ({pq['fuente']})"
        P.append(s + ".")
    if b["bajas"]:
        a = b["bajas"][0]
        s = f"La mayor caída es {a['nombre']} ({_p(a['chg'])})"
        pq = (b.get("por_que") or {}).get(a["nombre"])
        if pq:
            s += f"; en prensa: «{pq['titulo']}» ({pq['fuente']})"
        P.append(s + ".")
    if b.get("monto_total"):
        s = f"Se transaron ${_mm(b['monto_total'])} mil millones en las {b['n']} acciones grandes"
        if b.get("monto_vs_prom") is not None:
            s += f", {_p(b['monto_vs_prom'], 0)} respecto del promedio reciente"
        P.append(s + f", con {b['mas_transadas'][0]['nombre']} como la más transada." if b.get("mas_transadas") else s + ".")
    return " ".join(P)


def _cargar_hist():
    try:
        return json.load(open(VOL_FILE))
    except Exception:
        return {}


def guardar_monto_sesion(b):
    """Guarda el monto transado de la sesion (llamar al cierre, ~18:xx) para
    construir el promedio de 20 sesiones. Devuelve True si guardo."""
    if not b or not b.get("sesion") or not b.get("monto_total"):
        return False
    hist = _cargar_hist()
    f = b["sesion"].isoformat()
    hist[f] = {"total": b["monto_total"], "top": [(a["nombre"], a["monto"]) for a in b["mas_transadas"][:5]]}
    hist = dict(sorted(hist.items())[-90:])
    try:
        json.dump(hist, open(VOL_FILE, "w"))
        return True
    except Exception:
        return False


def _mm(v):
    """Pesos -> 'mil millones' con formato chileno (1 decimal)."""
    return f"{v/1e9:,.1f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _p(v, d=1):
    return f"{v:+.{d}f}%".replace(".", ",")


def frases(b):
    """Hechos en español (formato chileno) para la IA y el texto por reglas."""
    if not b:
        return []
    meses = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]
    ses = f"{b['sesion'].day}-{meses[b['sesion'].month-1]}" if b.get("sesion") else "hoy"
    nivel = (", nivel estimado " + f"{b['nivel']:,.0f}".replace(",", ".") + " puntos") if b.get("nivel") else ""
    F = [f"Bolsa de Santiago: IPSA estimado {_p(b['var'], 2)} en la sesión del {ses}{nivel}; "
         f"{b['n_alzas']} acciones al alza y {b['n_bajas']} a la baja (sobre {b['n']} papeles, ponderación aproximada)."]
    if b["alzas"]:
        F.append("Mayores alzas: " + ", ".join(f"{a['nombre']} {_p(a['chg'])}" for a in b["alzas"][:3]) + ".")
    if b["bajas"]:
        F.append("Mayores bajas: " + ", ".join(f"{a['nombre']} {_p(a['chg'])}" for a in b["bajas"][:3]) + ".")
    if b["sectores"]:
        top, bot = b["sectores"][0], b["sectores"][-1]
        F.append(f"Sector más fuerte: {top[0]} {_p(top[1])}; más débil: {bot[0]} {_p(bot[1])}.")
    for a in (b["alzas"][:3] + b["bajas"][:3]):
        pq = (b.get("por_que") or {}).get(a["nombre"])
        if pq:
            F.append(f"Titular sobre {a['nombre']} ({_p(a['chg'])}): \"{pq['titulo']}\" ({pq['fuente']}, {pq.get('hace', '')}).")
    if b.get("monto_total"):
        s = f"Monto transado en las {b['n']} acciones grandes: ${_mm(b['monto_total'])} mil millones"
        if b.get("monto_vs_prom") is not None:
            s += f" ({_p(b['monto_vs_prom'], 0)} vs. el promedio de las últimas {min(20, b['n_hist'])} sesiones)"
        s += "; más transadas: " + ", ".join(f"{a['nombre']} ${_mm(a['monto'])} mm" for a in b["mas_transadas"][:3]) + "."
        F.append(s)
    return F
