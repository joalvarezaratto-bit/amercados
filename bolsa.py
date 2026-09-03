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
            "market_time": hora, "sesion": sesion}


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
    return F
