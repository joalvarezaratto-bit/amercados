"""
Seccion "Dolar en profundidad": el mismo cerebro cuantitativo del dolar-bot,
adaptado al informe.

  MOTORES del USD/CLP: cobre (relacion INVERSA), DXY (DIRECTA), real brasileño
  (DIRECTA) y bono 10 años EE.UU. (DIRECTA). Cada uno pesa segun la
  CORRELACION medida en las ultimas semanas (no pesos fijos).
  VALOR JUSTO: regresion cobre+DXY+real -> donde "deberia" estar el dolar.
  TENDENCIA (medias 20/50), RSI, volatilidad (ATR), soportes/resistencias,
  Fibonacci, CARRY (TPM Chile - tasa EE.UU.), REGIMEN de riesgo (VIX) y
  VALORACION vs 3 años.

HONESTO (validado con backtest en dolar-bot): el puntaje de presion NO predice
el movimiento del dia siguiente. Es un NOWCAST: describe que esta empujando al
dolar AHORA. Se presenta como tablero, no como pronostico.
"""
import datetime as dt
import numpy as np
import requests
import config as C

UA = {"User-Agent": "Mozilla/5.0"}


# ------------------------------------------------------------ matematica
def _fecha(ts):
    return dt.datetime.fromtimestamp(ts, dt.timezone.utc).strftime("%Y-%m-%d")


def alinear(series):
    mapas = {}
    for k, candles in series.items():
        if not candles:
            return None
        mapas[k] = {_fecha(c["t"]): c["c"] for c in candles}
    comunes = None
    for m in mapas.values():
        comunes = set(m) if comunes is None else (comunes & set(m))
    comunes = sorted(comunes)
    if len(comunes) < 30:
        return None
    return {k: np.array([mapas[k][d] for d in comunes], dtype=float) for k in mapas}


def retornos(p):
    return np.diff(np.log(np.asarray(p, dtype=float)))


def correlacion(a, b, ventana):
    a, b = a[-ventana:], b[-ventana:]
    if len(a) < 10 or np.std(a) == 0 or np.std(b) == 0:
        return 0.0
    return float(np.corrcoef(a, b)[0, 1])


def rsi(p, n=14):
    p = np.asarray(p, dtype=float)
    if len(p) < n + 1:
        return None
    d = np.diff(p)
    up, dn = np.where(d > 0, d, 0.0), np.where(d < 0, -d, 0.0)
    ag, ap = up[:n].mean(), dn[:n].mean()
    for i in range(n, len(d)):
        ag = (ag * (n - 1) + up[i]) / n
        ap = (ap * (n - 1) + dn[i]) / n
    if ap == 0:
        return 100.0
    return float(100 - 100 / (1 + ag / ap))


def atr_pct(candles, n=14):
    if len(candles) < n + 1:
        return None
    trs = [max(c["h"] - c["l"], abs(c["h"] - p["c"]), abs(c["l"] - p["c"]))
           for p, c in zip(candles[:-1], candles[1:])]
    return float(np.mean(trs[-n:]) / candles[-1]["c"] * 100)


def sma(candles, n):
    cl = [c["c"] for c in candles]
    return sum(cl[-n:]) / n if len(cl) >= n else None


def sma_serie(candles, n):
    cl = np.array([c["c"] for c in candles], dtype=float)
    if len(cl) < n:
        return []
    return list(np.convolve(cl, np.ones(n) / n, mode="valid"))


def tendencia(d):
    if not d or not d.get("candles"):
        return ("sin dato", 0)
    p, s1, s2 = d["price"], sma(d["candles"], C.DOLAR_SMA_CORTA), sma(d["candles"], C.DOLAR_SMA_LARGA)
    if not s1 or not s2:
        return ("dato insuficiente", 0)
    if p > s1 > s2:
        return ("alcista", +1)
    if p < s1 < s2:
        return ("bajista", -1)
    return ("lateral", 0)


def niveles_sr(candles, price, k=3, max_n=3):
    highs, lows = [], []
    for i in range(k, len(candles) - k):
        win = candles[i - k:i + k + 1]
        if candles[i]["h"] == max(c["h"] for c in win):
            highs.append(candles[i]["h"])
        if candles[i]["l"] == min(c["l"] for c in win):
            lows.append(candles[i]["l"])
    grupos = []
    for p in sorted(highs + lows):
        for g in grupos:
            if abs(p - g["p"]) / price <= 0.006:
                g["p"] = (g["p"] * g["n"] + p) / (g["n"] + 1)
                g["n"] += 1
                break
        else:
            grupos.append({"p": p, "n": 1})
    sop = sorted([g["p"] for g in grupos if g["p"] < price * 0.999], reverse=True)
    res = sorted([g["p"] for g in grupos if g["p"] > price * 1.001])
    return sop[:max_n], res[:max_n]


FIB = [0.0, 0.236, 0.382, 0.5, 0.618, 0.786, 1.0]


def fibonacci(candles, lookback=70):
    v = candles[-lookback:]
    if len(v) < 10:
        return None
    hi_i = max(range(len(v)), key=lambda i: v[i]["h"])
    lo_i = min(range(len(v)), key=lambda i: v[i]["l"])
    hi, lo = v[hi_i]["h"], v[lo_i]["l"]
    if hi == lo:
        return None
    sube = hi_i > lo_i
    levels = {r: (hi - (hi - lo) * r) if sube else (lo + (hi - lo) * r) for r in FIB}
    price = candles[-1]["c"]
    cerca = min(levels.items(), key=lambda kv: abs(kv[1] - price))
    return {"dir": "alza" if sube else "baja", "hi": hi, "lo": lo, "levels": levels, "cerca": cerca}


def valor_justo(arr, ventana=60):
    if not all(k in arr for k in ("clp", "cobre", "dxy", "brl")):
        return None
    n = min(ventana, len(arr["clp"]))
    if n < 30:
        return None
    y = arr["clp"][-n:]
    X = np.column_stack([arr["cobre"][-n:], arr["dxy"][-n:], arr["brl"][-n:], np.ones(n)])
    try:
        beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    except Exception:
        return None
    pred = X @ beta
    sd = np.std(y - pred)
    if sd == 0:
        return None
    gap = float(y[-1] - pred[-1])
    return {"predicho": float(pred[-1]), "real": float(y[-1]), "gap": gap, "z": float(gap / sd)}


def _closes_3y(sym):
    for host in ("query1", "query2"):
        try:
            r = requests.get(f"https://{host}.finance.yahoo.com/v8/finance/chart/{sym}",
                             params={"interval": "1d", "range": "3y"}, headers=UA, timeout=20)
            res = r.json()["chart"]["result"][0]
            return [x for x in res["indicators"]["quote"][0]["close"] if x is not None]
        except Exception:
            continue
    return []


# ------------------------------------------------------------ analisis
def analizar(D):
    """Recibe el dict de datos.recolectar(). Devuelve el analisis o None."""
    Y = D.get("yahoo") or {}
    u = Y.get("usdclp")
    if not u or not u.get("price") or len(u.get("candles") or []) < 60:
        return None
    price = u["price"]
    motores = {"cobre": Y.get("cobre"), "dxy": Y.get("dxy"), "brl": Y.get("usdbrl"), "bono": Y.get("us10y")}
    series = {"clp": u["candles"]}
    for k, d in motores.items():
        if d and d.get("candles"):
            series[k] = d["candles"]
    arr = alinear(series)
    cl = [c["c"] for c in u["candles"]]
    r = rsi(cl)
    atrp = atr_pct(u["candles"])
    correls, aportes, valor = {}, {}, None
    if arr and "clp" in arr:
        r_clp = retornos(arr["clp"])
        for k in motores:
            if k in arr:
                correls[k] = correlacion(r_clp, retornos(arr[k]), C.DOLAR_VENTANA_CORR)
        valor = valor_justo(arr)

    senales, score = [], 0.0
    t_clp = tendencia(u)
    if t_clp[1] != 0:
        s20 = sma(u["candles"], C.DOLAR_SMA_CORTA)
        fuerza = 1.0
        if s20 and atrp:
            atr_abs = atrp / 100 * price
            fuerza = max(0.35, min(1.0, abs(price - s20) / (1.5 * atr_abs))) if atr_abs else 1.0
        ap = t_clp[1] * 30 * fuerza
        score += ap
        senales.append((f"Tendencia propia {t_clp[0]} (medias {C.DOLAR_SMA_CORTA}/{C.DOLAR_SMA_LARGA}, fuerza {fuerza:.0%})", ap))
    if r is not None:
        ap = (r - 50) / 50 * 12
        score += ap
        senales.append((f"RSI {r:.0f}: momentum {'alcista' if r >= 50 else 'bajista'}", ap))
        if r >= 70:
            score -= 5
            senales.append((f"RSI {r:.0f} en sobrecompra: riesgo de agotamiento al alza", -5))
        elif r <= 30:
            score += 5
            senales.append((f"RSI {r:.0f} en sobreventa: riesgo de rebote del dólar", +5))
    nombres = {"cobre": "Cobre", "dxy": "DXY", "brl": "Real (USD/BRL)", "bono": "Bono 10 años EE.UU."}
    for k, d in motores.items():
        if k not in correls or not d or d.get("price") is None:
            continue
        corr = correls[k]
        sd = float(retornos(arr[k]).std()) if (arr and k in arr) else 0.0
        z = (d["chg"] / 100.0 / sd) if sd > 0 else 0.0
        ap = max(-16, min(16, corr * z * 12))
        aportes[k] = ap
        if abs(ap) < 1:
            continue
        score += ap
        fz = "fuerte" if abs(corr) >= 0.5 else ("media" if abs(corr) >= 0.3 else "débil")
        senales.append((f"{nombres[k]} {d['chg']:+.2f}% (correlación {corr:+.2f}, {fz}): empuja el dólar "
                        f"{'al alza' if ap > 0 else 'a la baja'}".replace(".", ","), ap))
    if valor:
        z = max(-2, min(2, valor["z"]))
        ap = -z * 6.5
        score += ap
        if valor["z"] >= 1:
            senales.append((f"Dólar caro vs. sus motores ({valor['gap']:+.0f} sobre su valor justo {valor['predicho']:.0f})", ap))
        elif valor["z"] <= -1:
            senales.append((f"Dólar barato vs. sus motores ({valor['gap']:+.0f} bajo su valor justo {valor['predicho']:.0f})", ap))
    fib = fibonacci(u["candles"])
    if fib:
        ratio, nivel = fib["cerca"]
        if 0 < ratio < 1 and abs(price - nivel) / price <= 0.004:
            senales.append((f"Precio sobre el retroceso de Fibonacci {ratio:.3f} ({nivel:.0f}): zona de posible giro".replace(".", ",", 1), 0))
    score = int(max(-100, min(100, round(score))))
    if score >= 40:
        presion = "Presión al alza fuerte"
    elif score >= 15:
        presion = "Presión al alza leve"
    elif score <= -40:
        presion = "Presión a la baja fuerte"
    elif score <= -15:
        presion = "Presión a la baja leve"
    else:
        presion = "Motores equilibrados"
    sop, res = niveles_sr(u["candles"], price)

    # ----- contexto estrategico -----
    ch = D.get("chile") or {}
    tpm = (ch.get("tpm") or {}).get("valor") or C.TPM_FALLBACK
    irx = (Y.get("irx") or {}).get("price")
    carry = {"tpm": tpm, "us": irx, "diff": tpm - irx} if (tpm is not None and irx is not None) else None
    vixd, spxd = Y.get("vix") or {}, Y.get("spx") or {}
    regimen = None
    if vixd.get("price") is not None:
        v = vixd["price"]
        nivel = "risk-on (calma)" if v < 16 else ("neutral" if v < 22 else ("nervioso" if v < 30 else "risk-off (miedo)"))
        regimen = {"vix": v, "vix_chg": vixd.get("chg", 0.0), "spx_chg": spxd.get("chg"), "nivel": nivel}
    valoracion = None
    closes3 = _closes_3y(C.YAHOO["usdclp"][0])
    if len(closes3) >= 200:
        a3 = np.array(closes3, dtype=float)
        valoracion = {"prom": float(a3.mean()), "pctl": int((a3 < price).mean() * 100),
                      "min": float(a3.min()), "max": float(a3.max())}

    # ----- riesgos -----
    riesgos = []
    if r is not None and r >= 70:
        riesgos.append(f"RSI {r:.0f}: sobrecompra, el dólar puede estar agotándose al alza.")
    elif r is not None and r <= 30:
        riesgos.append(f"RSI {r:.0f}: sobreventa, riesgo de rebote del dólar.")
    for nivel in C.NIVELES_CLAVE:
        if abs(price - nivel) / price <= 0.004:
            riesgos.append(f"Precio pegado al nivel clave {nivel:,}: puede rebotar o romper con fuerza.".replace(",", "."))
            break
    if valor and abs(valor["z"]) >= 1.3:
        lado = "caro (peso muy débil)" if valor["z"] > 0 else "barato (peso muy fuerte)"
        riesgos.append(f"Dólar estirado vs. sus motores: {lado}, {valor['gap']:+.0f} pesos; riesgo de corrección.")
    if atrp and atrp >= 1.4:
        riesgos.append(f"Volatilidad elevada (~{atrp:.1f}% por día): movimientos más amplios de lo habitual.")
    if correls and all(abs(x) < 0.3 for x in correls.values()):
        riesgos.append("Los motores (cobre, DXY, real, bono) están desconectados del peso: manda algo local (política, flujos).")
    if regimen and regimen["vix"] >= 22:
        riesgos.append(f"Régimen de aversión al riesgo (VIX {regimen['vix']:.0f}): las monedas emergentes sufren aunque el cobre esté bien.")

    return {"price": price, "chg": u["chg"], "score": score, "presion": presion,
            "senales": sorted(senales, key=lambda s: -abs(s[1])), "soportes": sop, "resistencias": res,
            "motores": motores, "nombres": nombres, "trend": t_clp, "rsi": r, "atr_pct": atrp,
            "correls": correls, "aportes": aportes, "valor": valor, "fib": fib,
            "carry": carry, "regimen": regimen, "valoracion": valoracion, "riesgos": riesgos,
            "sma20": sma(u["candles"], C.DOLAR_SMA_CORTA), "sma50": sma(u["candles"], C.DOLAR_SMA_LARGA),
            "candles": u["candles"]}


def frases(a):
    """Hechos del analisis en español (para la IA y para el texto por reglas)."""
    if not a:
        return []
    F = [f"Dólar {a['price']:.2f} ({a['chg']:+.2f}%): tendencia {a['trend'][0]} por medias móviles "
         f"(media 20 días {a['sma20']:.0f}, media 50 días {a['sma50']:.0f})."]
    F.append(f"Presión de los motores ahora: {a['presion'].lower()} (puntaje {a['score']:+d} de -100 a +100; es foto del momento, no pronóstico).")
    for k, d in a["motores"].items():
        if d and k in a["correls"]:
            ap = a["aportes"].get(k, 0)
            emp = "empuja al alza" if ap > 1 else ("empuja a la baja" if ap < -1 else "sin empuje relevante hoy")
            F.append(f"{a['nombres'][k]}: {d['price']:.2f} ({d['chg']:+.2f}%), correlación 40 días con el dólar {a['correls'][k]:+.2f}, {emp}.")
    v = a.get("valor")
    if v:
        est = "caro" if v["z"] >= 1 else ("barato" if v["z"] <= -1 else "en línea")
        F.append(f"Valor justo según cobre+DXY+real: {v['predicho']:.0f}; el dólar está {est} ({v['gap']:+.0f} pesos).")
    if a.get("rsi") is not None:
        F.append(f"RSI 14 días: {a['rsi']:.0f}. Volatilidad típica {a['atr_pct']:.1f}% por día.")
    if a["soportes"] or a["resistencias"]:
        F.append("Soportes: " + ", ".join(f"{p:.0f}" for p in a["soportes"]) + ". Resistencias: " + ", ".join(f"{p:.0f}" for p in a["resistencias"]) + ".")
    if a.get("fib"):
        rc, pc = a["fib"]["cerca"]
        F.append(f"Fibonacci: impulso reciente {a['fib']['dir']} entre {a['fib']['lo']:.0f} y {a['fib']['hi']:.0f}; nivel más cercano {rc:.3f} = {pc:.0f}.")
    c = a.get("carry")
    if c:
        F.append(f"Carry (TPM Chile {c['tpm']:.2f}% menos tasa corta EE.UU. {c['us']:.2f}%): {c['diff']:+.2f} puntos.")
    rg = a.get("regimen")
    if rg:
        F.append(f"Régimen de riesgo global: {rg['nivel']} (VIX {rg['vix']:.1f}, {rg['vix_chg']:+.1f}%).")
    vl = a.get("valoracion")
    if vl:
        F.append(f"Valoración 3 años: percentil {vl['pctl']} (promedio {vl['prom']:.0f}, rango {vl['min']:.0f}-{vl['max']:.0f}).")
    return F
