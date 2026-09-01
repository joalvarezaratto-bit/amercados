"""
Datos de mercado para el informe. Todo GRATIS y sin API key:
  - Yahoo Finance: dolar, euro, cobre, petroleo, oro, plata, tasas USA, bolsas...
  - mindicador.cl: UF, dolar observado (Banco Central), TPM, IPC, Imacec, desempleo.
  - Google Finance (pagina publica): IPSA (Yahoo lo tiene congelado).

Honesto con la FRESCURA: cada dato trae la hora de su ultima actualizacion.
Si un dato esta viejo (mercado cerrado, feed caido) el informe lo dice
("ultimo cierre conocido: fecha") en vez de presentarlo como de hoy.
"""
import os
import re
import json
import time
import datetime as dt
import requests
import config as C

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE_FILE = os.path.join(HERE, "cache_mercado.json")
TTL = 600   # 10 min: no repetir la misma consulta
UA = {"User-Agent": "Mozilla/5.0"}   # OJO: un User-Agent "de Chrome completo" hace que Yahoo responda 429


def _cache_read():
    try:
        return json.load(open(CACHE_FILE))
    except Exception:
        return {}


def _cache_write(d):
    try:
        json.dump(d, open(CACHE_FILE, "w"))
    except Exception:
        pass


def limpiar_velas(candles, factor=3.0):
    """Recorta 'bad ticks' de Yahoo: mechas absurdas (max/min muy lejos del
    cierre) que ensucian rangos y graficos. Aprendido en dolar-bot."""
    if len(candles) < 10:
        return candles
    rangos = sorted(abs(c["h"] - c["l"]) / c["c"] for c in candles if c["c"])
    med = rangos[len(rangos) // 2] or 0.001
    out = []
    for c in candles:
        c = dict(c)
        if c["c"] and abs(c["h"] - c["l"]) / c["c"] > factor * med * 4:
            c["h"] = max(c["o"], c["c"])
            c["l"] = min(c["o"], c["c"])
        out.append(c)
    return out


def _yahoo(symbol, interval="1d", rng="1y"):
    """Historico + precio en vivo de un simbolo. Failover query1 -> query2."""
    res, err = None, ""
    for host in ("query1", "query2"):
        try:
            r = requests.get(f"https://{host}.finance.yahoo.com/v8/finance/chart/{symbol}",
                             params={"interval": interval, "range": rng},
                             headers=UA, timeout=20)
            res = r.json()["chart"]["result"][0]
            break
        except Exception as e:
            err = str(e)[:60]
    if res is None:
        print(f"  (aviso) Yahoo {symbol}: {err}")
        return None
    try:
        meta = res["meta"]
        ts = res.get("timestamp") or []
        q = res["indicators"]["quote"][0]
        candles = []
        for i in range(len(ts)):
            o, h, l, c = q["open"][i], q["high"][i], q["low"][i], q["close"][i]
            if None in (o, h, l, c):
                continue
            candles.append({"t": ts[i], "o": o, "h": h, "l": l, "c": c})
        candles = limpiar_velas(candles)
        price = meta.get("regularMarketPrice")
        if price is None and candles:
            price = candles[-1]["c"]
        mt = meta.get("regularMarketTime") or (candles[-1]["t"] if candles else None)
        # cierre anterior = penultima vela si la ultima es la de HOY (en formacion);
        # si la ultima vela ya es de un dia pasado, el cierre anterior es esa.
        prev = None
        if candles:
            hoy_utc = dt.datetime.now(dt.timezone.utc).date()
            ult = dt.datetime.fromtimestamp(candles[-1]["t"], dt.timezone.utc).date()
            if ult >= hoy_utc and len(candles) >= 2:
                prev = candles[-2]["c"]
            elif abs(candles[-1]["c"] - (price or 0)) < 1e-9 and len(candles) >= 2:
                prev = candles[-2]["c"]
            else:
                prev = candles[-1]["c"]
        if not prev:
            prev = meta.get("previousClose") or meta.get("chartPreviousClose") or price
        chg = ((price - prev) / prev * 100) if (price and prev) else 0.0
        return {"symbol": symbol, "price": price, "prev": prev, "chg": chg,
                "chg_abs": (price - prev) if (price and prev) else 0.0,
                "candles": candles, "market_time": mt, "ts": time.time(),
                "day_high": meta.get("regularMarketDayHigh"),
                "day_low": meta.get("regularMarketDayLow")}
    except Exception as e:
        print(f"  (aviso) Yahoo {symbol} parse: {str(e)[:80]}")
        return None


def yahoo(symbol, force=False):
    cache = _cache_read()
    d = cache.get(symbol)
    if d and not force and time.time() - d.get("ts", 0) < TTL:
        return d
    fresh = _yahoo(symbol)
    if fresh:
        cache[symbol] = fresh
        _cache_write(cache)
        return fresh
    return d   # ultima copia conocida (o None)


def mindicador():
    """Indicadores oficiales de Chile (UF, dolar observado, TPM, IPC...)."""
    try:
        d = requests.get("https://mindicador.cl/api", headers=UA, timeout=20).json()
        out = {}
        for k in ("uf", "dolar", "euro", "ipc", "tpm", "libra_cobre", "imacec",
                  "tasa_desempleo", "utm"):
            v = d.get(k)
            if v:
                out[k] = {"valor": v.get("valor"), "fecha": (v.get("fecha") or "")[:10]}
        # serie del dolar observado (ultimos dias) para la tabla
        try:
            s = requests.get("https://mindicador.cl/api/dolar", headers=UA, timeout=20).json()
            out["dolar_serie"] = [(x["fecha"][:10], x["valor"]) for x in s.get("serie", [])[:8]]
        except Exception:
            out["dolar_serie"] = []
        return out
    except Exception as e:
        print("  (aviso) mindicador:", str(e)[:80])
        return {}


def ipsa():
    """IPSA: NO hay fuente numerica gratuita confiable (Yahoo lo tiene congelado,
    Google Finance/TradingView/Bolsa de Santiago lo bloquean). Se lee de los
    TITULARES de prensa ("IPSA cierra en 11.315 puntos, -1,1%") via Google
    Noticias. Devuelve {price, chg, texto, fuente, link} o None. Se rotula
    como "según prensa" en el informe (honestidad con la fuente)."""
    import html as _html
    import feedparser
    try:
        url = ("https://news.google.com/rss/search?q=" +
               requests.utils.quote("IPSA Bolsa de Santiago puntos when:2d") +
               "&hl=es-419&gl=CL&ceid=CL:es-419")
        d = feedparser.parse(requests.get(url, headers=UA, timeout=20).content)
    except Exception as e:
        print("  (aviso) IPSA prensa:", str(e)[:80])
        return None
    mejor = None
    for e in d.entries[:30]:
        t = _html.unescape(e.get("title", ""))
        m = re.search(r"(\d{1,2}\.\d{3}(?:,\d{1,2})?)\s*puntos", t)
        if not m or "ipsa" not in t.lower():
            continue
        price = float(m.group(1).replace(".", "").replace(",", "."))
        chg = None
        mp = re.search(r"([+-]?\d{1,2},\d{1,2})\s*%", t)
        if mp:
            chg = float(mp.group(1).replace(",", "."))
            low = t.lower()
            if chg > 0 and any(w in low for w in ("baja", "cae", "retroced", "pierde", "cede")):
                chg = -chg
        try:
            p = e.published_parsed
            ts = dt.datetime(*p[:6], tzinfo=dt.timezone.utc).timestamp()
        except Exception:
            ts = 0
        antes = t[max(0, m.start() - 25):m.start()].lower()
        aprox = any(w in antes for w in ("cerca", "próximo", "proximo", "torno", "casi", "sobre", "bajo"))
        precision = (2 if "," in m.group(1) else 1) + (0 if aprox else 1) + (1 if chg is not None else 0)
        cand = {"symbol": "IPSA", "price": price, "chg": chg, "texto": t.rsplit(" - ", 1)[0],
                "aprox": aprox, "precision": precision,
                "fuente": t.rsplit(" - ", 1)[-1] if " - " in t else "prensa",
                "link": e.get("link", ""), "market_time": ts}
        # gana el mas RECIENTE (mismo dia) y, a igual dia, el mas preciso
        if mejor is None:
            mejor = cand
        else:
            mismo_dia = abs(ts - mejor["market_time"]) < 20 * 3600
            if (mismo_dia and precision > mejor["precision"]) or (not mismo_dia and ts > mejor["market_time"]):
                mejor = cand
    return mejor


def serie_mensual(candles, meses=12):
    """Cierre de cada mes (ultimo dia con dato) para el grafico de 12 meses."""
    por_mes = {}
    for c in candles:
        d = dt.datetime.fromtimestamp(c["t"], dt.timezone.utc)
        por_mes[(d.year, d.month)] = c["c"]
    claves = sorted(por_mes)[-meses:]
    return [((y, m), por_mes[(y, m)]) for (y, m) in claves]


def cierres_diarios(candles, n=5):
    """Ultimos n cierres diarios COMPLETOS (excluye la vela de hoy si aun se forma)."""
    hoy_utc = dt.datetime.now(dt.timezone.utc).date()
    comp = [c for c in candles
            if dt.datetime.fromtimestamp(c["t"], dt.timezone.utc).date() < hoy_utc]
    return comp[-n:]


def edad_horas(market_time):
    if not market_time:
        return None
    return (time.time() - market_time) / 3600


def recolectar():
    """Junta TODO lo que necesita el informe. Nunca lanza excepcion: lo que
    falla queda en None y el informe lo dice."""
    out = {"yahoo": {}, "generado": time.time()}
    for k, (sym, nombre, unidad, dec) in C.YAHOO.items():
        d = yahoo(sym)
        if d:
            d = dict(d)
            d.update({"nombre": nombre, "unidad": unidad, "dec": dec})
        out["yahoo"][k] = d
    # Euro en pesos = EUR/USD x USD/CLP (el historial directo EURCLP=X de Yahoo
    # esta desfasado y daria variaciones falsas)
    eu, us = out["yahoo"].get("eurusd"), out["yahoo"].get("usdclp")
    if eu and us and eu.get("price") and us.get("price"):
        price = eu["price"] * us["price"]
        prev = (eu["prev"] or eu["price"]) * (us["prev"] or us["price"])
        out["yahoo"]["eurclp"] = {"symbol": "EURUSD=X*USDCLP=X", "price": price, "prev": prev,
                                  "chg": (price - prev) / prev * 100, "chg_abs": price - prev,
                                  "candles": [], "market_time": min(eu["market_time"] or 0, us["market_time"] or 0) or None,
                                  "ts": time.time(), "nombre": "Euro", "unidad": "$", "dec": 2}
    else:
        out["yahoo"]["eurclp"] = None
    out["chile"] = mindicador()
    out["ipsa"] = ipsa()
    return out
