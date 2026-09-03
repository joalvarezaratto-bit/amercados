"""
Seccion Cripto: bitcoin, ether, solana y XRP (Yahoo, gratis), indice de
Miedo y Codicia (alternative.me, gratis) y dominancia de bitcoin +
capitalizacion total (CoinGecko, gratis, sin key).

HONESTO: precios y sentimiento del momento; no es recomendacion.
"""
import time
import datetime as dt
import requests
import config as C
import datos as DS

UA = {"User-Agent": "Mozilla/5.0"}
MONEDAS = [("BTC-USD", "Bitcoin", "BTC"), ("ETH-USD", "Ether", "ETH"),
           ("SOL-USD", "Solana", "SOL"), ("XRP-USD", "XRP", "XRP")]


def _var(candles, dias):
    """% de cambio entre el cierre de hace `dias` velas y el ultimo."""
    if len(candles) <= dias:
        return None
    a, b = candles[-1 - dias]["c"], candles[-1]["c"]
    return (b / a - 1) * 100 if a else None


def recolectar():
    out = {"monedas": [], "fng": None, "global": None}
    for sym, nombre, tk in MONEDAS:
        d = DS.yahoo(sym, rng="1y")
        if d and d.get("price"):
            cs = d.get("candles") or []
            out["monedas"].append({"sym": sym, "nombre": nombre, "tk": tk, "price": d["price"], "chg": d["chg"],
                                   "v7": _var(cs, 7), "v30": _var(cs, 30), "candles": cs, "market_time": d.get("market_time")})
        time.sleep(0.2)
    try:
        j = requests.get("https://api.alternative.me/fng/?limit=2", headers=UA, timeout=15).json()["data"]
        out["fng"] = {"valor": int(j[0]["value"]), "clase": j[0]["value_classification"],
                      "ayer": int(j[1]["value"]) if len(j) > 1 else None}
    except Exception as e:
        print("  (aviso) miedo/codicia:", str(e)[:60])
    try:
        g = requests.get("https://api.coingecko.com/api/v3/global", headers=UA, timeout=15).json()["data"]
        out["global"] = {"btc_dom": g["market_cap_percentage"]["btc"], "eth_dom": g["market_cap_percentage"]["eth"],
                         "mcap": g["total_market_cap"]["usd"], "mcap_24h": g["market_cap_change_percentage_24h_usd"]}
    except Exception as e:
        print("  (aviso) coingecko:", str(e)[:60])
    return out if out["monedas"] else None


_CLASE = {"Extreme Fear": "miedo extremo", "Fear": "miedo", "Neutral": "neutral", "Greed": "codicia", "Extreme Greed": "codicia extrema"}


def clase_es(c):
    return _CLASE.get(c, c.lower())


def _n(v, dec=0):
    s = f"{v:,.{dec}f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".")


def _p(v, dec=1):
    return f"{v:+.{dec}f}%".replace(".", ",")


def frases(k):
    """Hechos en español (formato chileno) para la IA y el texto por reglas."""
    if not k:
        return []
    F = []
    for m in k["monedas"]:
        dec = 2 if m["price"] < 100 else 0
        F.append(f"{m['nombre']} ({m['tk']}): US${_n(m['price'], dec)} ({_p(m['chg'])} hoy"
                 + (f", {_p(m['v7'])} en 7 días" if m.get("v7") is not None else "")
                 + (f", {_p(m['v30'])} en 30 días" if m.get("v30") is not None else "") + ").")
    if k.get("fng"):
        f = k["fng"]
        F.append(f"Índice de miedo y codicia: {f['valor']}/100 ({clase_es(f['clase'])})" + (f", ayer {f['ayer']}" if f.get("ayer") is not None else "") + ".")
    if k.get("global"):
        g = k["global"]
        F.append(f"Dominancia de bitcoin {_n(g['btc_dom'], 1)}%, ether {_n(g['eth_dom'], 1)}%; capitalización total US${_n(g['mcap'] / 1e12, 2)} billones ({_p(g['mcap_24h'])} en 24 h).")
    return F
