"""
Agenda economica: ForexFactory (USD alto impacto + China) + eventos fijos
de config (Banco Central de Chile, Fed, IPC del INE).
Misma fuente keyless que news-bot/dolar-bot. OJO: ForexFactory da HTTP 429
si se pide muchas veces seguidas -> cache en disco 3 h.
"""
import os
import json
import time
import datetime as dt
import requests
import config as C

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE_FILE = os.path.join(HERE, "cache_calendario.json")
URL = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"
URL_NEXT = "https://nfs.faireconomy.media/ff_calendar_nextweek.json"
UA = {"User-Agent": "Mozilla/5.0"}
TTL = 3 * 3600

CLAVE = ("federal funds", "fomc", "cpi", "pce", "non-farm", "nonfarm", "payroll",
         "unemployment", "gdp", "retail sales", "ism", "pmi", "inflation")
_TRAD = {
    "Federal Funds Rate": "Decisión de tasas de la Fed",
    "FOMC Statement": "Comunicado de la Fed (FOMC)",
    "FOMC Press Conference": "Conferencia de prensa de la Fed",
    "CPI m/m": "IPC EE.UU. (mensual)", "CPI y/y": "IPC EE.UU. (anual)",
    "Core CPI m/m": "IPC subyacente EE.UU. (mensual)",
    "Core PCE Price Index m/m": "PCE subyacente EE.UU. (mensual)",
    "Non-Farm Employment Change": "Nóminas no agrícolas EE.UU. (empleo)",
    "Unemployment Rate": "Tasa de desempleo EE.UU.",
    "Unemployment Claims": "Solicitudes de subsidio por desempleo EE.UU.",
    "Advance GDP q/q": "PIB EE.UU. (adelantado)", "Prelim GDP q/q": "PIB EE.UU. (preliminar)",
    "Retail Sales m/m": "Ventas minoristas EE.UU.",
    "Core Retail Sales m/m": "Ventas minoristas subyacentes EE.UU.",
    "ISM Manufacturing PMI": "PMI manufacturero ISM EE.UU.",
    "ISM Services PMI": "PMI de servicios ISM EE.UU.",
    "Manufacturing PMI": "PMI manufacturero China", "Non-Manufacturing PMI": "PMI no manufacturero China",
    "Caixin Manufacturing PMI": "PMI manufacturero Caixin China",
    "Caixin Services PMI": "PMI de servicios Caixin China",
    "Trade Balance": "Balanza comercial China", "GDP q/y": "PIB China",
    "Industrial Production y/y": "Producción industrial China",
    "JOLTS Job Openings": "Vacantes de empleo JOLTS EE.UU.",
    "PPI m/m": "Precios al productor EE.UU.", "Core PPI m/m": "PPI subyacente EE.UU.",
    "Prelim UoM Consumer Sentiment": "Confianza del consumidor (U. Michigan)",
    "CB Consumer Confidence": "Confianza del consumidor (Conference Board)",
    "Fed Chair Warsh Speaks": "Habla el presidente de la Fed, Warsh",
    "Fed Chair Powell Speaks": "Habla el presidente de la Fed, Powell",
}


def _traducir(t, pais):
    if t in _TRAD:
        return _TRAD[t]
    suf = " (China)" if pais == "CNY" else " (EE.UU.)"
    return t + suf


def _fetch():
    data = []
    for u in (URL, URL_NEXT):
        try:
            r = requests.get(u, headers=UA, timeout=20)
            if r.status_code == 200:
                data += r.json()
        except Exception as e:
            print("  (aviso) calendario:", str(e)[:80])
    if data:
        json.dump({"ts": time.time(), "data": data}, open(CACHE_FILE, "w"))
        return data
    try:
        return json.load(open(CACHE_FILE)).get("data", [])
    except Exception:
        return []


def _get():
    try:
        c = json.load(open(CACHE_FILE))
        if time.time() - c.get("ts", 0) < TTL:
            return c.get("data", [])
    except Exception:
        pass
    return _fetch()


def _parse(s):
    try:
        d = dt.datetime.fromisoformat(s)
        if d.tzinfo is None:
            d = d.replace(tzinfo=dt.timezone.utc)
        return d
    except Exception:
        return None


def proximos(tz, dias=None):
    """Eventos desde hoy hasta `dias` adelante, ordenados. Cada uno:
    {fecha(date), hora('HH:MM' o ''), titulo, impacto('Alto'|'Medio'), forecast, previous, origen}."""
    dias = dias or C.AGENDA_DIAS
    hoy = dt.datetime.now(tz).date()
    lim = hoy + dt.timedelta(days=dias)
    out = []
    for e in _get():
        if e.get("country") not in ("USD", "CNY"):
            continue
        imp = e.get("impact", "")
        if imp not in ("High", "Medium"):
            continue
        titulo = e.get("title", "")
        if imp == "Medium" and not any(k in titulo.lower() for k in CLAVE):
            continue
        f = _parse(e.get("date", ""))
        if not f:
            continue
        fl = f.astimezone(tz)
        if fl.date() < hoy or fl.date() > lim:
            continue
        out.append({"fecha": fl.date(), "hora": f"{fl:%H:%M}", "titulo": _traducir(titulo, e["country"]),
                    "impacto": "Alto" if imp == "High" else "Medio",
                    "forecast": e.get("forecast", ""), "previous": e.get("previous", ""),
                    "origen": "ff"})
    for fs, desc, imp in C.EVENTOS_FIJOS:
        try:
            f = dt.date.fromisoformat(fs)
        except Exception:
            continue
        if hoy <= f <= lim:
            out.append({"fecha": f, "hora": "", "titulo": desc, "impacto": imp,
                        "forecast": "", "previous": "", "origen": "fijo"})
    # IPC INE (aprox. dia 8 de cada mes)
    for k in range(0, 2):
        y, m = hoy.year, hoy.month + k
        if m > 12:
            y, m = y + 1, m - 12
        f = dt.date(y, m, C.IPC_INE_DIA)
        if hoy <= f <= lim:
            out.append({"fecha": f, "hora": "", "titulo": "IPC de Chile (INE) — fecha aproximada",
                        "impacto": "Alto", "forecast": "", "previous": "", "origen": "aprox"})
    # sin duplicados fed (FF + fijo el mismo dia): se dejan ambos, es info distinta (hora)
    out.sort(key=lambda x: (x["fecha"], x["hora"] or "99:99"))
    return out


def resultados_hoy(tz):
    """Reportes de HOY (USD/CNY) ya publicados con 'actual'."""
    hoy = dt.datetime.now(tz)
    out = []
    for e in _get():
        if e.get("country") not in ("USD", "CNY") or e.get("impact") not in ("High", "Medium"):
            continue
        f = _parse(e.get("date", ""))
        if not f:
            continue
        fl = f.astimezone(tz)
        if fl.date() != hoy.date() or fl > hoy or not e.get("actual"):
            continue
        out.append({"hora": f"{fl:%H:%M}", "titulo": _traducir(e.get("title", ""), e["country"]),
                    "actual": e.get("actual"), "forecast": e.get("forecast", ""),
                    "previous": e.get("previous", "")})
    return out
