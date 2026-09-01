"""
Redaccion del informe.

Dos caminos:
  1) IA (Claude, SDK oficial `anthropic`): recibe los DATOS ya calculados y
     los TITULARES por seccion, y devuelve un JSON con el titular del dia,
     "lo mas relevante", los parrafos de cada seccion y los riesgos. Se le
     exige NO inventar: solo puede usar lo que se le entrega.
  2) REGLAS (sin IA o si la IA falla/no tiene saldo): titulares agrupados por
     seccion + frases armadas con los datos. El informe SIEMPRE sale.

Ambos caminos comparten `frases_datos()` (hechos numericos en español),
asi la IA y el respaldo cuentan la misma historia con los mismos numeros.
"""
import os
import re
import json
import time
import html
import datetime as dt
import config as C
import datos as DS

HERE = os.path.dirname(os.path.abspath(__file__))
_BREAKER_FILE = os.path.join(HERE, "ai_breaker.json")
_BREAKER_TTL = 6 * 3600


# ------------------------------------------------------------------ formato
def fmt(v, dec=2):
    """1234.5 -> '1.234,50' (formato chileno)."""
    if v is None:
        return "n/d"
    s = f"{v:,.{dec}f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".")


def pct(v, dec=1):
    if v is None:
        return "n/d"
    return f"{v:+.{dec}f}%".replace(".", ",")


def _q(D, k):
    return (D.get("yahoo") or {}).get(k) or {}


def _dia_semana(d):
    return ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"][d.weekday()]


def _fecha_larga(d):
    meses = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto",
             "septiembre", "octubre", "noviembre", "diciembre"]
    return f"{_dia_semana(d)} {d.day} de {meses[d.month-1]} de {d.year}"


def _fecha_corta(d):
    meses = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]
    return f"{d.day}-{meses[d.month-1]}"


def _dir(chg, up="sube", down="baja", flat="se mantiene"):
    if chg is None:
        return flat
    return up if chg > 0.05 else (down if chg < -0.05 else flat)


def _antiguedad(q, tz):
    """'' si el dato es reciente; si no, ' (último dato: 21-ago)'."""
    mt = q.get("market_time")
    if not mt:
        return ""
    h = DS.edad_horas(mt)
    if h is not None and h > 30:
        f = dt.datetime.fromtimestamp(mt, tz)
        return f" (último dato: {_fecha_corta(f)})"
    return ""


# ------------------------------------------------------------------ hechos
def frases_datos(D, tz, meta):
    """Lista de frases con los numeros del dia (para la IA y para el respaldo)."""
    F = []
    u = _q(D, "usdclp")
    ch = D.get("chile") or {}
    if u:
        cierres = DS.cierres_diarios(u["candles"], 6)
        F.append(f"Dólar spot (interbancario, Yahoo) ahora ${fmt(u['price'])}, "
                 f"{_dir(u['chg'])} {pct(u['chg'], 2)} vs. el cierre anterior de ${fmt(u['prev'])}.")
        if len(cierres) >= 5:
            F.append(f"Variación semanal del dólar: {fmt(cierres[-1]['c'] - cierres[0]['c'])} pesos "
                     f"(de ${fmt(cierres[0]['c'])} el {_fecha_corta(dt.datetime.fromtimestamp(cierres[0]['t'], tz))} "
                     f"a ${fmt(cierres[-1]['c'])} el {_fecha_corta(dt.datetime.fromtimestamp(cierres[-1]['t'], tz))}).")
    if ch.get("dolar"):
        F.append(f"Dólar observado del Banco Central para hoy: ${fmt(ch['dolar']['valor'])} "
                 f"(promedio del día hábil anterior).")
    if ch.get("uf"):
        F.append(f"UF de hoy: ${fmt(ch['uf']['valor'])}.")
    if ch.get("tpm"):
        F.append(f"TPM del Banco Central de Chile: {fmt(ch['tpm']['valor'], 2)}%.")
    if ch.get("tasa_desempleo"):
        F.append(f"Desempleo en Chile (INE, dato más reciente {ch['tasa_desempleo']['fecha'][:7]}): {fmt(ch['tasa_desempleo']['valor'], 1)}%.")
    if ch.get("imacec"):
        F.append(f"Imacec más reciente ({ch['imacec']['fecha'][:7]}): {pct(ch['imacec']['valor'])} interanual.")
    e = _q(D, "eurclp")
    if e:
        F.append(f"Euro: ${fmt(e['price'])} ({pct(e['chg'], 2)}).")
    for k, nombre, unidad, dec in (("brent", "Petróleo Brent", "US$", 2), ("wti", "Petróleo WTI", "US$", 2),
                                   ("cobre", "Cobre (COMEX, US$/lb)", "US$", 2), ("oro", "Oro (US$/oz)", "US$", 0),
                                   ("plata", "Plata (US$/oz)", "US$", 2)):
        q = _q(D, k)
        if q:
            F.append(f"{nombre}: {unidad}{fmt(q['price'], dec)}, {_dir(q['chg'])} {pct(q['chg'])} vs. cierre anterior{_antiguedad(q, tz)}.")
    d = _q(D, "dxy")
    if d:
        F.append(f"Dollar index (DXY): {fmt(d['price'])} ({pct(d['chg'])}).")
    for k, nombre in (("us5y", "Tesoro EE.UU. 5 años"), ("us10y", "Tesoro EE.UU. 10 años"), ("us30y", "Tesoro EE.UU. 30 años")):
        q = _q(D, k)
        if q and q.get("price"):
            pb = (q["price"] - q["prev"]) * 100 if q.get("prev") else None
            F.append(f"{nombre}: {fmt(q['price'], 2)}%" + (f" ({pb:+.0f} puntos base)" if pb is not None else "") + ".")
    v = _q(D, "vix")
    if v:
        F.append(f"VIX (índice de volatilidad): {fmt(v['price'], 1)} ({pct(v['chg'])}).")
    for k in ("spx", "es", "nq", "stoxx", "nikkei", "hsi", "shanghai"):
        q = _q(D, k)
        if q:
            F.append(f"{q['nombre']}: {fmt(q['price'], 0)} ({pct(q['chg'])}){_antiguedad(q, tz)}.")
    b = _q(D, "btc")
    if b:
        F.append(f"Bitcoin: US${fmt(b['price'], 0)} ({pct(b['chg'])}).")
    br = _q(D, "usdbrl")
    if br:
        F.append(f"Real brasileño (USD/BRL): {fmt(br['price'], 3)} ({pct(br['chg'])}).")
    ip = D.get("ipsa")
    if ip:
        F.append(f"IPSA según prensa ({ip['fuente']}): {'cerca de ' if ip.get('aprox') else ''}{fmt(ip['price'], 2 if not ip.get('aprox') else 0)} puntos"
                 + (f", {pct(ip['chg'])}" if ip.get("chg") is not None else "") + f". Titular: \"{ip['texto']}\".")
    ech = _q(D, "ech")
    if ech:
        F.append(f"ETF de acciones chilenas ECH (en dólares, NYSE): US${fmt(ech['price'])} ({pct(ech['chg'])}).")
    return F


# ------------------------------------------------------------------ IA
def _breaker_open():
    try:
        return time.time() < json.load(open(_BREAKER_FILE)).get("until", 0)
    except Exception:
        return False


def _trip_breaker(motivo):
    try:
        json.dump({"until": time.time() + _BREAKER_TTL, "motivo": motivo}, open(_BREAKER_FILE, "w"))
    except Exception:
        pass


_SYSTEM = """Eres el editor de AMercados, un informe matinal de mercados en español de Chile, escrito para un lector inversionista sin formación técnica. Estilo: sobrio, claro, periodístico-financiero (como el Diario Financiero), frases cortas, sin adjetivos grandilocuentes.

REGLAS ESTRICTAS:
1. Usa SOLO los DATOS y TITULARES entregados. NO inventes cifras, nombres, fechas ni hechos. Si un tema no tiene titulares, dilo brevemente o deja la sección corta.
2. Los titulares son solo títulos (no tienes el cuerpo de las notas): no agregues detalles que el titular no contiene.
3. Es un informe de lo que PASÓ y del estado ACTUAL (foto del momento), NO un pronóstico. No predigas si el dólar, la bolsa o el cobre van a subir o bajar. Puedes señalar qué eventos o niveles vigilar.
4. Nada de consejos de inversión.
5. Cuando cites una cifra, usa exactamente la entregada (formato chileno: $934,30; 11.315 puntos; US$92,21).
6. Puedes usar <strong>…</strong> para resaltar (solo esa etiqueta HTML). Sin markdown.

Responde ÚNICAMENTE con un JSON válido con esta forma exacta (sin texto antes ni después):
{
 "titular": "Titular del día en una frase larga (20-35 palabras) que conecte el hecho global principal con su efecto en dólar/IPSA/cobre",
 "relevante": [ {"tag": "Ormuz|Petróleo|Chile|Fed|Cobre|Bolsa|...", "html": "1-2 frases con <strong> en el dato clave"} ],   // 4 ítems
 "internacional": [ {"h3": "Subtítulo corto", "parrafos": ["párrafo", "párrafo"]} ],   // 2-3 bloques
 "chile": ["ítem 1-2 frases con <strong> en lo importante", ...],   // 5-8 ítems: política, fiscal, empresas, datos
 "geopolitica": ["<strong>Tema:</strong> explicación de por qué importa para los mercados", ...],   // 3-4 ítems
 "tasas": ["párrafo sobre inflación y tasas (Fed, Tesoro, TPM Chile) con las cifras entregadas", ...],   // 1-2 párrafos
 "cambio": "párrafo del dólar/peso: nivel, variación, qué lo movió (cobre, DXY, riesgo global) según los titulares",
 "commodities": "párrafo sobre petróleo, cobre, oro y plata con las cifras y titulares entregados",
 "bolsa": "párrafo sobre IPSA (según prensa), Wall Street y bolsas globales con las cifras entregadas",
 "riesgos": ["<strong>Riesgo:</strong> por qué importa hoy", ...]   // 4-5 ítems, incluye eventos de la agenda
}"""


def _prompt_usuario(D, N, A, meta, hechos, tz):
    L = [f"FECHA: {_fecha_larga(meta['ahora'])}, {meta['ahora']:%H:%M} hora de Chile.", "", "DATOS DE MERCADO:"]
    L += [f"- {h}" for h in hechos]
    L.append("")
    L.append("AGENDA (próximos días):")
    for e in A[:12]:
        L.append(f"- {_fecha_corta(e['fecha'])} {e['hora']} · {e['titulo']} · impacto {e['impacto']}"
                 + (f" · esperado {e['forecast']}" if e.get("forecast") else ""))
    res = meta.get("resultados") or []
    if res:
        L.append("")
        L.append("DATOS ECONÓMICOS PUBLICADOS HOY:")
        for r in res:
            L.append(f"- {r['hora']} {r['titulo']}: {r['actual']} (esperado {r['forecast'] or 'n/d'}, previo {r['previous'] or 'n/d'})")
    nombres = {"internacional": "PANORAMA INTERNACIONAL", "chile": "CHILE (política y economía)",
               "geopolitica": "GEOPOLÍTICA", "tasas": "INFLACIÓN Y TASAS", "cambio": "TIPO DE CAMBIO",
               "commodities": "COMMODITIES", "bolsa": "BOLSA"}
    for sec, nombre in nombres.items():
        items = N.get(sec) or []
        L.append("")
        L.append(f"TITULARES · {nombre}:")
        if not items:
            L.append("- (sin titulares hoy)")
        for it in items[:C.NOTICIAS_TOP_POR_SECCION]:
            L.append(f"- {it['titulo']} ({it['fuente']})")
    return "\n".join(L)


def _extraer_json(texto):
    texto = texto.strip()
    if texto.startswith("```"):
        texto = re.sub(r"^```(?:json)?\s*|\s*```$", "", texto, flags=re.S)
    try:
        return json.loads(texto)
    except Exception:
        i, j = texto.find("{"), texto.rfind("}")
        if i >= 0 and j > i:
            return json.loads(texto[i:j + 1])
    raise ValueError("la IA no devolvió JSON")


def redactar_ia(D, N, A, meta, hechos, tz):
    """Devuelve el dict de contenido o None (y el motivo en meta['ia_motivo'])."""
    if not C.USE_AI:
        meta["ia_motivo"] = "USE_AI = False en config.py"
        return None
    if not C.ANTHROPIC_API_KEY:
        meta["ia_motivo"] = "sin ANTHROPIC_API_KEY"
        return None
    if _breaker_open():
        meta["ia_motivo"] = "IA apagada temporalmente tras un error (saldo/permiso); reintenta en unas horas"
        return None
    try:
        import anthropic
    except ImportError:
        meta["ia_motivo"] = "falta instalar el paquete anthropic (pip3 install anthropic)"
        return None
    client = anthropic.Anthropic(api_key=C.ANTHROPIC_API_KEY)
    prompt = _prompt_usuario(D, N, A, meta, hechos, tz)
    try:
        with client.messages.stream(
            model=C.AI_MODEL,
            max_tokens=16000,
            system=_SYSTEM,
            output_config={"effort": C.AI_EFFORT},
            messages=[{"role": "user", "content": prompt}],
        ) as stream:
            resp = stream.get_final_message()
        if resp.stop_reason == "refusal":
            meta["ia_motivo"] = "la IA rechazó la solicitud"
            return None
        texto = "".join(b.text for b in resp.content if b.type == "text")
        cont = _extraer_json(texto)
        u = resp.usage
        meta["ia_uso"] = f"{u.input_tokens} tokens entrada / {u.output_tokens} salida ({C.AI_MODEL})"
        return cont
    except anthropic.AuthenticationError as e:
        _trip_breaker("auth"); meta["ia_motivo"] = f"API key inválida ({e.message[:80]})"
    except anthropic.PermissionDeniedError as e:
        _trip_breaker("perm"); meta["ia_motivo"] = f"sin permiso ({e.message[:80]})"
    except anthropic.BadRequestError as e:
        msg = e.message
        if "credit balance" in msg:
            _trip_breaker("saldo")
            meta["ia_motivo"] = "la cuenta de Anthropic no tiene saldo (cargar créditos en console.anthropic.com)"
        else:
            meta["ia_motivo"] = f"error de solicitud: {msg[:120]}"
    except anthropic.RateLimitError:
        meta["ia_motivo"] = "límite de uso de la API alcanzado (reintenta más tarde)"
    except anthropic.APIStatusError as e:
        meta["ia_motivo"] = f"error de la API ({e.status_code})"
    except anthropic.APIConnectionError:
        meta["ia_motivo"] = "sin conexión con la API de Anthropic"
    except Exception as e:
        meta["ia_motivo"] = f"respuesta no utilizable: {str(e)[:100]}"
    return None


# ------------------------------------------------------------------ reglas
def _li_titular(it):
    t = html.escape(it["titulo"])
    f = html.escape(it.get("fuente") or "")
    link = it.get("link") or ""
    if link:
        return f'<a href="{html.escape(link)}" style="color:inherit;text-decoration:none;">{t}</a>' + (f' <span style="color:#8B9099;font-size:.78rem;">· {f}</span>' if f else "")
    return t + (f' <span style="color:#8B9099;font-size:.78rem;">· {f}</span>' if f else "")


def _tag_de(sec):
    return {"internacional": "Global", "chile": "Chile", "geopolitica": "Geopolítica", "tasas": "Tasas",
            "cambio": "Dólar", "commodities": "Commodities", "bolsa": "Bolsa"}.get(sec, "Hoy")


def redactar_reglas(D, N, A, meta, hechos, tz):
    n = C.NOTICIAS_MOSTRAR_SIN_IA
    rel = N.get("relevante") or []
    u = _q(D, "usdclp")
    ip = D.get("ipsa")
    partes = []
    if rel:
        partes.append(rel[0]["titulo"].rstrip("."))
    if u:
        partes.append(f"el dólar {_dir(u['chg'], 'sube', 'baja', 'se mantiene')} a ${fmt(u['price'])}")
    if ip:
        partes.append(f"el IPSA {'cerró en' if ip.get('chg') is None else ('subió a' if ip['chg'] > 0 else 'cayó a')} {fmt(ip['price'], 0)} puntos según prensa")
    titular = "; ".join(partes) if partes else "Informe matinal de mercados"
    relevante = [{"tag": _tag_de(it.get("seccion")), "html": _li_titular(it)} for it in rel[:4]]

    def lista(sec):
        return [_li_titular(it) for it in (N.get(sec) or [])[:n]] or ["Sin titulares relevantes en las últimas 24 horas."]

    internacional = [{"h3": "Titulares del día", "parrafos": []}]
    internacional[0]["items"] = lista("internacional")
    tasas_txt = [h for h in hechos if any(x in h for x in ("Tesoro", "TPM", "DXY"))]
    cambio_txt = " ".join(h for h in hechos if h.startswith(("Dólar", "Variación semanal", "Euro", "Real")))
    comm_txt = " ".join(h for h in hechos if h.startswith(("Petróleo", "Cobre", "Oro", "Plata")))
    bolsa_txt = " ".join(h for h in hechos if h.startswith(("IPSA", "ETF", "S&P", "Futuro", "Euro Stoxx", "Nikkei", "Hang", "Shanghái", "VIX")))
    riesgos = []
    for e in A:
        if e["impacto"] == "Alto":
            riesgos.append(f"<strong>{html.escape(e['titulo'])} ({_fecha_corta(e['fecha'])}):</strong> evento de alto impacto en la agenda.")
        if len(riesgos) >= 3:
            break
    for it in (N.get("geopolitica") or [])[:2]:
        riesgos.append(f"<strong>Geopolítica:</strong> {_li_titular(it)}")
    v = _q(D, "vix")
    if v and v.get("price") and v["price"] >= 25:
        riesgos.append(f"<strong>Volatilidad alta:</strong> el VIX está en {fmt(v['price'], 1)} (sobre 25 = nerviosismo en Wall Street).")
    for k in ("brent", "cobre", "usdclp"):
        q = _q(D, k)
        if q and abs(q.get("chg") or 0) >= 2:
            riesgos.append(f"<strong>Movimiento brusco en {q['nombre'].lower()}:</strong> {pct(q['chg'])} vs. el cierre anterior.")
    return {
        "titular": html.escape(titular),
        "relevante": relevante,
        "internacional": internacional,
        "chile": lista("chile"),
        "geopolitica": lista("geopolitica"),
        "tasas": tasas_txt + ["Titulares: " + " · ".join(_li_titular(it) for it in (N.get("tasas") or [])[:4])] if N.get("tasas") else tasas_txt,
        "cambio": cambio_txt + (" Titulares: " + " · ".join(_li_titular(it) for it in (N.get("cambio") or [])[:3]) if N.get("cambio") else ""),
        "commodities": comm_txt + (" Titulares: " + " · ".join(_li_titular(it) for it in (N.get("commodities") or [])[:3]) if N.get("commodities") else ""),
        "bolsa": bolsa_txt + (" Titulares: " + " · ".join(_li_titular(it) for it in (N.get("bolsa") or [])[:4]) if N.get("bolsa") else ""),
        "riesgos": riesgos or ["Sin riesgos destacados detectados por reglas."],
    }


def _validar(cont):
    """Asegura que el JSON de la IA tenga todas las llaves con el tipo esperado."""
    ok = isinstance(cont, dict) and isinstance(cont.get("titular"), str) and cont["titular"].strip()
    ok = ok and isinstance(cont.get("relevante"), list) and all(isinstance(x, dict) and "html" in x for x in cont["relevante"])
    ok = ok and isinstance(cont.get("internacional"), list) and all(isinstance(x, dict) and isinstance(x.get("parrafos"), list) for x in cont["internacional"])
    for k in ("chile", "geopolitica", "tasas", "riesgos"):
        ok = ok and isinstance(cont.get(k), list) and all(isinstance(x, str) for x in cont[k])
    for k in ("cambio", "commodities", "bolsa"):
        ok = ok and isinstance(cont.get(k), str)
    return bool(ok)


def _sanear(s):
    """Solo se permite <strong>; cualquier otra etiqueta se escapa."""
    s = str(s)
    s = s.replace("<strong>", "\x01").replace("</strong>", "\x02")
    s = html.escape(s, quote=False)
    return s.replace("\x01", "<strong>").replace("\x02", "</strong>")


def redactar(D, N, A, meta, tz):
    hechos = frases_datos(D, tz, meta)
    meta["hechos"] = hechos
    cont = redactar_ia(D, N, A, meta, hechos, tz)
    if cont is not None and not _validar(cont):
        meta["ia_motivo"] = "la IA devolvió un JSON incompleto"
        cont = None
    if cont is not None:
        cont["titular"] = _sanear(cont["titular"]).replace("<strong>", "").replace("</strong>", "")
        cont["relevante"] = [{"tag": _sanear(x.get("tag", "Hoy")), "html": _sanear(x["html"])} for x in cont["relevante"][:5]]
        cont["internacional"] = [{"h3": _sanear(x.get("h3", "")), "parrafos": [_sanear(p) for p in x["parrafos"]]} for x in cont["internacional"]]
        for k in ("chile", "geopolitica", "tasas", "riesgos"):
            cont[k] = [_sanear(x) for x in cont[k]]
        for k in ("cambio", "commodities", "bolsa"):
            cont[k] = _sanear(cont[k])
        cont["modo"] = "ia"
        return cont
    cont = redactar_reglas(D, N, A, meta, hechos, tz)
    cont["modo"] = "reglas"
    return cont
