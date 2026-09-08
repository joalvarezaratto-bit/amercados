"""
Renta fija chilena desde la Base de Datos Estadisticos del Banco Central
(API SIETE, cuenta gratuita, autenticacion por TOKEN). Series diarias de tasas de bonos BCP (pesos) y
BCU (UF). Calcula cambio diario en puntos base, curva, inflacion implicita
(BCP - BCU) y spread vs. Tesoro EE.UU.

Comandos: `amercados.py rentafija buscar [texto]` para descubrir codigos de
series; `amercados.py rentafija` para probar con los codigos de config.
HONESTO: son tasas de mercado secundario publicadas por el BCCh; si la API
no responde, la seccion se omite y lo dice.
"""
import os
import json
import time
import datetime as dt
import requests
import config as C

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE_FILE = os.path.join(HERE, "cache_rentafija.json")
URL = "https://si3.bcentral.cl/SieteRestWS/SieteRestWS.ashx"
UA = {"User-Agent": "Mozilla/5.0"}
TTL = 3600


def _ok():
    return bool(C.BCCH_TOKEN)


def _get(params):
    p = {"token": C.BCCH_TOKEN}
    p.update(params)
    r = requests.get(URL, params=p, headers=UA, timeout=30)
    r.raise_for_status()
    return r.json()


def buscar(texto="BCP", frecuencia="DAILY"):
    """Lista series cuyo nombre contiene `texto` (para elegir codigos)."""
    if not _ok():
        print("Falta BCCH_TOKEN en secrets_local.py (token de la API del Banco Central)")
        return []
    j = _get({"function": "SearchSeries", "frequency": frecuencia})
    out = []
    for s in j.get("SeriesInfos", []) or []:
        nombre = s.get("spanishTitle") or s.get("englishTitle") or ""
        if texto.lower() in nombre.lower():
            out.append((s.get("seriesId"), nombre, s.get("lastObservation")))
    return out


def serie(codigo, dias=400):
    """Observaciones diarias {fecha: valor} de una serie (con cache 1 h)."""
    try:
        cache = json.load(open(CACHE_FILE))
    except Exception:
        cache = {}
    c = cache.get(codigo)
    if c and time.time() - c.get("ts", 0) < TTL:
        return {k: v for k, v in c["obs"].items()}
    hoy = dt.date.today()
    j = _get({"function": "GetSeries", "timeseries": codigo,
              "firstdate": (hoy - dt.timedelta(days=dias)).isoformat(), "lastdate": hoy.isoformat()})
    obs = {}
    for o in (j.get("Series") or {}).get("Obs") or []:
        v = o.get("value")
        try:
            v = float(v)
        except Exception:
            continue
        if v != v:   # NaN
            continue
        f = o.get("indexDateString") or ""
        # formato dd-mm-yyyy
        try:
            d = dt.datetime.strptime(f, "%d-%m-%Y").date().isoformat()
        except Exception:
            d = f
        obs[d] = v
    cache[codigo] = {"ts": time.time(), "obs": obs}
    try:
        json.dump(cache, open(CACHE_FILE, "w"))
    except Exception:
        pass
    return obs


def recolectar():
    """Devuelve {clave: {nombre, moneda, fecha, valor, prev, pb, hist}} o None."""
    if not _ok() or not C.RENTA_FIJA:
        return None
    out = {}
    for k, (codigo, nombre, moneda) in C.RENTA_FIJA.items():
        try:
            obs = serie(codigo)
        except Exception as e:
            print("  (aviso) BCCh", k, str(e)[:80])
            continue
        fechas = sorted(obs)
        if len(fechas) < 2:
            continue
        f1, f0 = fechas[-1], fechas[-2]
        out[k] = {"nombre": nombre, "moneda": moneda, "fecha": f1, "valor": obs[f1], "prev": obs[f0],
                  "pb": (obs[f1] - obs[f0]) * 100, "hist": [(f, obs[f]) for f in fechas[-90:]]}
        time.sleep(0.2)
    return out or None


def analizar(rf, us10y=None):
    """Curva, inflacion implicita y spread."""
    if not rf:
        return None
    clp = {k: v for k, v in rf.items() if v["moneda"] == "CLP"}
    uf = {k: v for k, v in rf.items() if v["moneda"] == "UF"}
    def plazo(k):
        return int("".join(ch for ch in k if ch.isdigit()) or 0)
    implicita = {}
    for kp, vp in clp.items():
        for ku, vu in uf.items():
            if plazo(kp) == plazo(ku):
                implicita[plazo(kp)] = vp["valor"] - vu["valor"]
    spread = None
    b10 = next((v for k, v in clp.items() if plazo(k) == 10), None)
    if b10 and us10y:
        spread = (b10["valor"] - us10y) * 100
    return {"clp": dict(sorted(clp.items(), key=lambda kv: plazo(kv[0]))),
            "uf": dict(sorted(uf.items(), key=lambda kv: plazo(kv[0]))),
            "implicita": implicita, "spread_pb": spread, "fecha": max(v["fecha"] for v in rf.values())}


def frases(a):
    if not a:
        return []
    F = []
    if a["clp"]:
        F.append("Bonos en pesos (BCP): " + ", ".join(f"{v['nombre']} {v['valor']:.2f}% ({v['pb']:+.0f} pb)" for v in a["clp"].values()) + ".")
    if a["uf"]:
        F.append("Bonos en UF (BCU): " + ", ".join(f"{v['nombre']} {v['valor']:.2f}% ({v['pb']:+.0f} pb)" for v in a["uf"].values()) + ".")
    if a["implicita"]:
        F.append("Inflación implícita (BCP menos BCU): " + ", ".join(f"{p} años {v:.2f}%" for p, v in sorted(a["implicita"].items())) + ".")
    if a.get("spread_pb") is not None:
        F.append(f"Spread Chile 10 años vs. Tesoro EE.UU.: {a['spread_pb']:+.0f} pb.")
    return [x.replace(".", ",") if False else x for x in F]
