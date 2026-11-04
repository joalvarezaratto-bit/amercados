"""
Calendario de resultados (estados financieros) de empresas chilenas.

- Fechas CONFIRMADAS: resultados_cl.json (tabla CMF que trajo el usuario y
  fechas oficiales sueltas). Para cargar un trimestre nuevo se agrega un bloque.
- Fechas ESTIMADAS: los trimestres que aun no estan cargados se proyectan solos
  a partir del ultimo trimestre confirmado: cada empresa conserva su "distancia"
  al cierre (ej. BCI publica ~30 dias despues), ajustada al plazo legal de la CMF
  (60 dias mar/sep, 75 jun, 90 dic-anual; NCG 431) y a dias habiles. Se rotulan
  "estimada" en el informe y en Telegram.
- PRENSA: el dia que una empresa publica, se busca en Google Noticias el titular
  de sus resultados (utilidad, ganancias, ebitda...) para confirmar y resumir.
  Cache en resultados_prensa.json (versionado).
No predice si los resultados seran buenos o malos.
"""
import os
import json
import time
import datetime as dt
import requests
import config as C

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "resultados_cl.json")
PRENSA = os.path.join(HERE, "resultados_prensa.json")
UA = {"User-Agent": "Mozilla/5.0"}

CIERRES = {1: (3, 31), 2: (6, 30), 3: (9, 30), 4: (12, 31)}
PLAZO = {1: 60, 2: 75, 3: 60, 4: 90}          # dias corridos (CMF, NCG 431)
DIAS = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]

# como suele aparecer cada empresa en la prensa (para buscar el titular)
ALIAS = {
    "Banco Santander Chile": "Santander Chile", "Celulosa Arauco y Constitución": "Arauco",
    "Embotelladora Andina": "Andina", "Engie Energía Chile": "Engie", "Empresas CMPC": "CMPC",
    "Empresas Copec": "Copec", "Sociedad Matriz SAAM": "SAAM", "Viña Concha y Toro": "Concha y Toro",
    "Viña San Pedro Tarapacá": "VSPT", "CSAV/Vapores": "Vapores", "Coca-Cola Embonor": "Embonor",
    "Administradora Americana de Inversiones (AAISA)": "AAISA", "GTD Grupo Teleductos": "GTD",
    "Soquimich Comercial": "Soquimich Comercial", "Naturgy Chile Gas Natural": "Naturgy Chile",
    "Cristalerías de Chile": "Cristalerías", "Salmones Camanchaca": "Salmones Camanchaca",
    "Clínica Las Condes": "Clínica Las Condes", "LATAM Airlines": "Latam",
}
CLAVES = ("resultado", "utilidad", "ganancia", "pérdida", "perdida", "ebitda", "ingresos", "trimestre",
          "3t", "2t", "1t", "4t", "estados financieros", "beneficio", "margen", "ventas")


# ------------------------------------------------------------------ datos
def _cargar():
    try:
        return json.load(open(DATA, encoding="utf-8"))
    except Exception as e:
        print("  (aviso) resultados_cl.json:", str(e)[:80])
        return {"trimestres": [], "confirmadas_sueltas": {}}


def _q_de(corte):
    """date de cierre -> (anio, q)."""
    return corte.year, {3: 1, 6: 2, 9: 3, 12: 4}[corte.month]


def _nombre_q(y, q):
    return f"{q}Q{str(y)[2:]}"


def _siguiente(y, q):
    return (y + 1, 1) if q == 4 else (y, q + 1)


def _corte(y, q):
    m, d = CIERRES[q]
    return dt.date(y, m, d)


def _habil(f):
    s = f.strftime("%m-%d")
    return f.weekday() < 5 and s not in C.FERIADOS_CL and f.isoformat() not in C.FERIADOS_CL


def _ajustar(f, tope):
    """Mueve la fecha a dia habil (sab->vie, dom->lun) sin pasar el plazo legal."""
    if f.weekday() == 5:
        f -= dt.timedelta(days=1)
    elif f.weekday() == 6:
        f += dt.timedelta(days=1)
    if f > tope:
        f = tope
    while not _habil(f):
        f -= dt.timedelta(days=1)
    return f


def _offset_estimado(off, q_base, q_obj):
    """Distancia al cierre en el trimestre objetivo. El anual (4Q) tiene 90 dias
    y las empresas lo usan bastante mas (BCI: 30 dias en 3Q -> 57 en 4Q)."""
    anual_b, anual_o = q_base == 4, q_obj == 4
    if anual_b == anual_o:
        return off
    if anual_o:
        return round(off * 1.5 + 12)
    return max(20, round((off - 12) / 1.5))


def calendario():
    """Lista de {fecha, empresa, trimestre, estado('confirmada'|'estimada')}.
    Incluye los trimestres confirmados y proyecta los 3 siguientes."""
    raw = _cargar()
    out, confirmados = [], {}
    base = None   # (y, q, {empresa: offset})
    for t in raw.get("trimestres", []):
        corte = dt.date.fromisoformat(t["corte"])
        y, q = _q_de(corte)
        offs = {}
        for fs, emps in t.get("fechas", {}).items():
            f = dt.date.fromisoformat(fs)
            for e in emps:
                out.append({"fecha": f, "empresa": e, "trimestre": t["trimestre"], "estado": "confirmada"})
                offs[e] = (f - corte).days
        confirmados[(y, q)] = True
        if base is None or (y, q) > (base[0], base[1]):
            base = (y, q, offs)
    if not base:
        return out
    sueltas = {k: v for k, v in (raw.get("confirmadas_sueltas") or {}).items() if not k.startswith("_")}
    y, q = base[0], base[1]
    for _ in range(3):
        y, q = _siguiente(y, q)
        if (y, q) in confirmados:
            continue
        nq = _nombre_q(y, q)
        corte = _corte(y, q)
        tope = corte + dt.timedelta(days=PLAZO[q])
        fijas = sueltas.get(nq, {})
        for e, off in base[2].items():
            if e in fijas:
                out.append({"fecha": dt.date.fromisoformat(fijas[e]), "empresa": e, "trimestre": nq, "estado": "confirmada"})
                continue
            f = _ajustar(corte + dt.timedelta(days=_offset_estimado(off, base[1], q)), tope)
            out.append({"fecha": f, "empresa": e, "trimestre": nq, "estado": "estimada"})
    out.sort(key=lambda x: (x["fecha"], x["empresa"]))
    return out


def ultimo_actualizado():
    t = (_cargar().get("trimestres") or [{}])[-1]
    return t.get("trimestre", ""), t.get("actualizado", ""), t.get("fuente", "")


def proximos(hoy, dias=14, cal=None):
    cal = cal if cal is not None else calendario()
    lim = hoy + dt.timedelta(days=dias)
    return [x for x in cal if hoy <= x["fecha"] <= lim]


def del_dia(f, cal=None):
    cal = cal if cal is not None else calendario()
    return [x for x in cal if x["fecha"] == f]


def dia_habil_anterior(hoy):
    f = hoy - dt.timedelta(days=1)
    while not _habil(f):
        f -= dt.timedelta(days=1)
    return f


def temporada(hoy, cal=None):
    """Avance de la temporada en curso: {trimestre, publicadas, total, estado}
    para el trimestre cuyo periodo de publicacion contiene hoy (o el proximo)."""
    cal = cal if cal is not None else calendario()
    por_q = {}
    for x in cal:
        por_q.setdefault(x["trimestre"], []).append(x)
    for nq, xs in por_q.items():
        ini, fin = min(x["fecha"] for x in xs), max(x["fecha"] for x in xs)
        if ini - dt.timedelta(days=14) <= hoy <= fin:
            pub = sum(1 for x in xs if x["fecha"] < hoy)
            est = "estimada" if any(x["estado"] == "estimada" for x in xs) else "confirmada"
            return {"trimestre": nq, "publicadas": pub, "total": len(xs), "estado": est,
                    "inicio": ini, "fin": fin}
    return None


def proxima_temporada(hoy, cal=None):
    """Primer trimestre cuya primera fecha es futura: {trimestre, inicio, estado}."""
    cal = cal if cal is not None else calendario()
    fut = {}
    for x in cal:
        if x["fecha"] >= hoy:
            fut.setdefault(x["trimestre"], []).append(x)
    if not fut:
        return None
    nq = min(fut, key=lambda k: min(x["fecha"] for x in fut[k]))
    xs = fut[nq]
    return {"trimestre": nq, "inicio": min(x["fecha"] for x in xs),
            "estado": "estimada" if any(x["estado"] == "estimada" for x in xs) else "confirmada"}


# ------------------------------------------------------------------ prensa
def _cargar_prensa():
    try:
        return json.load(open(PRENSA, encoding="utf-8"))
    except Exception:
        return {}


def titular_resultados(empresa, dias=3):
    """Titular de prensa chilena sobre los resultados de la empresa (o None)."""
    import html as _html
    import feedparser
    alias = ALIAS.get(empresa, empresa)
    q = f'"{alias}" (utilidad OR resultados OR ganancias OR pérdida OR ebitda) when:{dias}d'
    try:
        url = "https://news.google.com/rss/search?q=" + requests.utils.quote(q) + "&hl=es-419&gl=CL&ceid=CL:es-419"
        d = feedparser.parse(requests.get(url, headers=UA, timeout=15).content)
    except Exception:
        return None
    low_alias = alias.lower()
    primera = low_alias.split()[0]
    mejor = None
    for e in d.entries[:15]:
        t = _html.unescape(e.get("title", ""))
        titulo = t.rsplit(" - ", 1)[0].strip()
        fuente = t.rsplit(" - ", 1)[-1].strip() if " - " in t else ""
        low = titulo.lower()
        if primera not in low and low_alias not in low:
            continue
        n = sum(1 for k in CLAVES if k in low)
        if n == 0:
            continue
        if any(x in (fuente + " " + low).lower() for x in ("méxico", "mexico", "argentin", "colombia", "perú", "peru", "brasil")):
            continue
        sc = 2 * n + (1 if low_alias in low else 0)
        if mejor is None or sc > mejor["sc"]:
            mejor = {"titulo": titulo, "fuente": fuente, "link": e.get("link", ""), "sc": sc}
    if mejor and mejor["sc"] >= 2:
        mejor.pop("sc", None)
        return mejor
    return None


def prensa_de(empresas_fecha, max_busquedas=12):
    """Para [(empresa, fecha)] devuelve {empresa: titular}. Usa cache; busca
    solo las que faltan (maximo `max_busquedas` por corrida)."""
    cache = _cargar_prensa()
    out, n = {}, 0
    for emp, f in empresas_fecha:
        k = f"{f.isoformat()}|{emp}"
        if k in cache and cache[k]:
            out[emp] = cache[k]
            continue
        if n >= max_busquedas:
            continue
        n += 1
        r = titular_resultados(emp)
        if r:
            cache[k] = r
            out[emp] = r
        time.sleep(0.25)
    # limpiar entradas de mas de 120 dias
    lim = (dt.date.today() - dt.timedelta(days=120)).isoformat()
    cache = {k: v for k, v in cache.items() if k.split("|")[0] >= lim}
    try:
        json.dump(cache, open(PRENSA, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    except Exception:
        pass
    return out


# ------------------------------------------------------------------ textos
def agrupar_prensa(pr):
    """{empresa: titular} -> [(titular, [empresas])] sin repetir el mismo titular."""
    out = {}
    for emp, t in pr.items():
        k = t.get("titulo", "").lower()
        if k not in out:
            out[k] = (t, [])
        out[k][1].append(emp)
    return list(out.values())


def fecha_corta(f):
    meses = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]
    return f"{DIAS[f.weekday()][:3]} {f.day}-{meses[f.month-1]}"


def _lista(xs):
    nombres = [x["empresa"] for x in xs]
    est = any(x["estado"] == "estimada" for x in xs)
    return ", ".join(nombres) + (" <i>(estimada)</i>" if est else "")


def bloque_telegram(hoy, con_prensa=True, semana=False):
    """Texto HTML para el mensaje matinal de Telegram (o '' si no hay nada que decir)."""
    cal = calendario()
    L = []
    ayer = dia_habil_anterior(hoy)
    pub_ayer = del_dia(ayer, cal)
    if pub_ayer and (hoy - ayer).days <= 4:
        L.append(f"<b>Publicaron ({fecha_corta(ayer)}):</b> {_lista(pub_ayer)}")
        if con_prensa:
            pr = prensa_de([(x["empresa"], x["fecha"]) for x in pub_ayer], max_busquedas=8)
            for t, _e in agrupar_prensa(pr)[:4]:
                L.append(f"   ▸ <a href=\"{t['link']}\">{t['titulo']}</a> · <i>{t['fuente']}</i>")
    hoy_l = del_dia(hoy, cal)
    if hoy_l:
        L.append(f"<b>Hoy publican:</b> {_lista(hoy_l)}")
    dias = 7 if semana else 4
    prox = [x for x in proximos(hoy + dt.timedelta(days=1), dias - 1, cal)]
    if prox:
        grupos = {}
        for x in prox:
            grupos.setdefault(x["fecha"], []).append(x)
        L.append("<b>Próximos:</b>")
        for f in sorted(grupos):
            L.append(f"   • {fecha_corta(f)}: {_lista(grupos[f])}")
    t = temporada(hoy, cal)
    if t and L:
        L.append(f"<i>Temporada {t['trimestre']}: {t['publicadas']}/{t['total']} empresas ya publicaron"
                 + (" · fechas estimadas" if t["estado"] == "estimada" else "") + ".</i>")
    if not L:
        p = proxima_temporada(hoy, cal)
        if p and (p["inicio"] - hoy).days <= 21:
            L.append(f"Temporada {p['trimestre']} parte el {fecha_corta(p['inicio'])}"
                     + (" (estimado)" if p["estado"] == "estimada" else "") + ".")
    if not L:
        return ""
    return "📅 <b>Resultados empresas chilenas</b>\n" + "\n".join(L)


def bloque_flash(hoy):
    """Para el flash de la tarde: empresas de hoy con titular de prensa si ya salio."""
    xs = del_dia(hoy, calendario())
    if not xs:
        return ""
    pr = prensa_de([(x["empresa"], x["fecha"]) for x in xs], max_busquedas=8)
    L = [f"📅 <b>Resultados hoy:</b> {_lista(xs)}"]
    for t, _e in agrupar_prensa(pr)[:4]:
        L.append(f"   ▸ <a href=\"{t['link']}\">{t['titulo']}</a> · <i>{t['fuente']}</i>")
    if not pr:
        L.append("   <i>Aún sin titulares de prensa (suelen publicar después del cierre).</i>")
    return "\n".join(L)


def aviso_cargar(hoy, estado):
    """Una vez por trimestre: si la proxima temporada sigue ESTIMADA y parte en
    <= 21 dias, recordar al usuario que mande el calendario oficial. Devuelve texto o ''."""
    p = proxima_temporada(hoy)
    if not p or p["estado"] != "estimada" or (p["inicio"] - hoy).days > 21:
        return ""
    k = "aviso_resultados_" + p["trimestre"]
    if estado.get(k):
        return ""
    estado[k] = hoy.isoformat()
    return (f"📅 La temporada de resultados <b>{p['trimestre']}</b> parte aprox. el {fecha_corta(p['inicio'])}. "
            "Por ahora las fechas son <b>estimadas</b> (según el trimestre anterior). "
            "Cuando tengas el calendario oficial (CMF), mándaselo a Claude para cargarlo.")


if __name__ == "__main__":
    hoy = dt.date.today()
    cal = calendario()
    print(f"{len(cal)} filas · temporada: {temporada(hoy, cal)}")
    from collections import Counter
    for (nq, est), n in sorted(Counter((x['trimestre'], x['estado']) for x in cal).items()):
        print(f"  {nq} {est}: {n}")
    print()
    print(bloque_telegram(hoy, con_prensa="--prensa" in os.sys.argv, semana=True))
