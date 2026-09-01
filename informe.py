"""
Plantilla HTML del informe: misma estructura, CSS y componentes que el
informe de referencia (amercados 01sep2026.html): cabecera con titular,
barra pegajosa, ticker animado, indice rapido, 10 secciones numeradas,
grafico SVG del dolar y pie con descargo.
"""
import html
import datetime as dt
import config as C
import datos as DS
import grafico
from redactor import fmt, pct, _fecha_larga, _fecha_corta, _antiguedad, _q

CSS = r"""
  :root{
    --bg:#15171A;--bg2:#1D2024;--paper:#1A1D21;--ink:#EDEDEA;--soft:#8B9099;
    --copper:#C97A45;--coppersoft:#3A2A1E;--ice:#7FA8B8;--line:#2B2F35;
    --green:#5FA97E;--greenbg:#16211B;--red:#C1655A;--redbg:#241716;
    font-size:16px;
  }
  *{box-sizing:border-box;}
  html{-webkit-text-size-adjust:100%;}
  body{margin:0;background:var(--bg);color:var(--ink);font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;line-height:1.55;-webkit-font-smoothing:antialiased;overflow-x:hidden;-webkit-tap-highlight-color:rgba(201,122,69,.25);}
  img,svg{max-width:100%;}
  main{max-width:640px;margin:0 auto;padding:0 0 40px;}
  header{position:relative;padding:20px 20px 0;overflow:hidden;background:linear-gradient(180deg,#1B1E22 0%,#15171A 100%);}
  .logo-slot{display:flex;align-items:baseline;margin-bottom:20px;}
  .logo-slot .wordmark{font-family:"Iowan Old Style","Palatino Linotype",Georgia,serif;font-size:1.9rem;font-weight:500;letter-spacing:.01em;}
  .logo-slot .wordmark .a{color:var(--copper);} .logo-slot .wordmark .rest{color:#fff;}
  .logo-slot .rule{flex:1;height:1px;background:linear-gradient(90deg,var(--copper) 0%,rgba(201,122,69,0) 100%);margin-left:14px;margin-bottom:8px;}
  .eyebrow{text-transform:uppercase;letter-spacing:.18em;font-size:.62rem;color:var(--copper);font-weight:700;margin-bottom:10px;}
  h1{font-family:"Iowan Old Style","Palatino Linotype",Georgia,serif;font-size:1.55rem;line-height:1.22;margin:0 0 8px;color:#fff;font-weight:500;}
  .sub{font-size:.82rem;color:var(--soft);margin-bottom:16px;}
  .range{display:flex;justify-content:space-between;font-size:.68rem;color:var(--soft);padding-bottom:14px;}
  .andes{width:100%;height:58px;display:block;}
  .headline-frame{border-top:1px solid var(--copper);border-bottom:1px solid var(--copper);padding:12px 0;margin-bottom:16px;}
  .headline-label{text-transform:uppercase;letter-spacing:.16em;font-size:.6rem;color:var(--copper);font-weight:700;margin-bottom:8px;}
  .ticker-wrap{background:var(--paper);border-top:1px solid var(--line);border-bottom:1px solid var(--line);overflow:hidden;position:relative;padding:10px 0;}
  .ticker-track{display:flex;width:max-content;animation:ticker-scroll 34s linear infinite;}
  .ticker-wrap:hover .ticker-track{animation-play-state:paused;}
  .ticker-item{display:flex;align-items:baseline;gap:7px;padding:0 22px;white-space:nowrap;border-right:1px solid var(--line);}
  .ticker-item .tk{font-size:.68rem;color:var(--soft);text-transform:uppercase;letter-spacing:.05em;}
  .ticker-item .tv{font-size:.86rem;font-weight:700;color:#fff;}
  .ticker-item .td{font-size:.72rem;font-weight:600;}
  @keyframes ticker-scroll{from{transform:translateX(0);}to{transform:translateX(-50%);}}
  .commod-grid{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin:14px 0 4px;}
  .commod-card{background:var(--paper);border:1px solid var(--line);border-radius:10px;padding:14px;}
  .commod-card .ck{display:flex;align-items:center;gap:6px;font-size:.66rem;text-transform:uppercase;letter-spacing:.06em;color:var(--soft);font-weight:700;margin-bottom:10px;}
  .commod-card .cv{font-family:"Iowan Old Style",Georgia,serif;font-size:1.15rem;color:#fff;font-weight:500;margin-bottom:6px;}
  .commod-card .cd{font-size:.78rem;font-weight:700;}
  .sticky-bar{position:sticky;top:0;z-index:50;background:var(--bg);border-bottom:1px solid var(--line);padding:10px 20px;display:flex;align-items:center;justify-content:space-between;}
  .sticky-bar .wm{font-family:"Iowan Old Style","Palatino Linotype",Georgia,serif;font-size:1rem;font-weight:500;}
  .sticky-bar .wm .a{color:var(--copper);} .sticky-bar .wm .rest{color:#fff;}
  .sticky-bar .sdate{font-size:.64rem;color:var(--soft);text-transform:uppercase;letter-spacing:.05em;}
  .quickindex{padding:18px 20px;border-bottom:1px solid var(--line);}
  .quickindex .qi-label{text-transform:uppercase;letter-spacing:.14em;font-size:.6rem;color:var(--copper);font-weight:700;margin-bottom:12px;}
  .quickindex .qi-row{display:flex;flex-wrap:wrap;align-items:baseline;gap:0;font-size:.8rem;line-height:1.8;}
  .quickindex .qi-row a{color:#D3D4D2;text-decoration:none;} .quickindex .qi-row a:hover{color:#fff;}
  .quickindex .qi-sep{color:var(--copper);margin:0 9px;}
  section{padding:24px 20px;border-bottom:1px solid var(--line);scroll-margin-top:48px;}
  section:last-of-type{border-bottom:none;}
  .secnum{font-family:"Iowan Old Style",Georgia,serif;font-size:.68rem;color:var(--copper);letter-spacing:.1em;margin-bottom:6px;}
  h2{font-family:"Iowan Old Style","Palatino Linotype",Georgia,serif;font-size:1.1rem;margin:0 0 14px;color:#fff;font-weight:500;}
  h3{font-size:.86rem;color:var(--copper);margin:18px 0 8px;font-weight:700;text-transform:uppercase;letter-spacing:.04em;}
  p{margin:0 0 12px;font-size:.9rem;color:#D3D4D2;text-align:justify;text-justify:inter-word;}
  strong{color:#fff;font-weight:600;}
  a{color:inherit;}
  ul.newsflash{list-style:none;margin:0;padding:0;}
  ul.newsflash li{padding:13px 0;border-bottom:1px solid var(--line);font-size:.9rem;line-height:1.55;color:#DEDFE0;position:relative;padding-left:16px;}
  ul.newsflash li:last-child{border-bottom:none;}
  ul.newsflash li::before{content:"";position:absolute;left:0;top:8px;width:6px;height:1px;background:var(--copper);}
  ul.newsflash li .tag{display:inline-block;font-size:.6rem;text-transform:uppercase;letter-spacing:.06em;font-weight:700;color:var(--copper);margin-right:6px;}
  ul.plain{list-style:none;margin:0;padding:0;}
  ul.plain li{padding:11px 0;border-bottom:1px solid var(--line);font-size:.88rem;line-height:1.58;color:#DEDFE0;position:relative;padding-left:16px;}
  ul.plain li:last-child{border-bottom:none;}
  ul.plain li::before{content:"";position:absolute;left:0;top:9px;width:6px;height:1px;background:var(--copper);}
  .stripe{display:flex;gap:10px;overflow-x:auto;margin-bottom:16px;padding-bottom:4px;}
  .card{flex:0 0 auto;background:var(--paper);border:1px solid var(--line);border-radius:10px;padding:12px 14px;min-width:98px;}
  .card .k{font-size:.62rem;color:var(--soft);text-transform:uppercase;letter-spacing:.06em;margin-bottom:5px;}
  .card .v{font-size:.95rem;font-weight:600;color:#fff;} .card .d{font-size:.68rem;margin-top:3px;}
  .up{color:var(--green);} .down{color:var(--red);} .flat{color:var(--soft);}
  .table-wrap{overflow-x:auto;margin:12px 0 16px;-webkit-overflow-scrolling:touch;border:1px solid var(--line);border-radius:8px;}
  table{border-collapse:collapse;width:100%;min-width:420px;font-size:.8rem;}
  thead th{background:var(--paper);color:var(--copper);text-align:left;padding:9px 11px;font-weight:700;white-space:nowrap;font-size:.66rem;text-transform:uppercase;letter-spacing:.05em;border-bottom:1px solid var(--line);}
  tbody td{padding:9px 11px;border-bottom:1px solid var(--line);white-space:nowrap;color:#DEDFE0;}
  tbody tr:last-child td{border-bottom:none;} tbody tr:nth-child(even){background:#1C1F23;}
  .chart-card{background:var(--paper);border:1px solid var(--line);border-radius:10px;padding:14px 12px 8px;margin:14px 0;}
  .chart-title{font-size:.8rem;font-weight:700;color:#fff;margin-bottom:2px;}
  .chart-meta{font-size:.65rem;color:var(--soft);margin-bottom:10px;}
  .callout{background:var(--coppersoft);border-left:3px solid var(--copper);padding:10px 12px;font-size:.78rem;color:#E3C9AE;margin:12px 0;border-radius:2px;}
  footer{padding:18px 20px;font-size:.66rem;color:var(--soft);line-height:1.6;border-top:1px solid var(--line);}
  footer b{color:var(--copper);}
"""

ANDES = ('<svg class="andes" viewBox="0 0 400 58" preserveAspectRatio="none">'
         '<polyline points="0,58 30,34 55,45 90,18 120,40 150,27 185,48 215,23 250,42 280,14 315,38 350,29 400,45 400,58 0,58" fill="#1F2328"/>'
         '<polyline points="0,58 30,34 55,45 90,18 120,40 150,27 185,48 215,23 250,42 280,14 315,38 350,29 400,45" fill="none" stroke="#C97A45" stroke-width="1" opacity="0.55"/></svg>')

SECCIONES = [("sec1", "Lo más relevante"), ("sec2", "Panorama internacional"), ("sec3", "Chile"),
             ("sec4", "Riesgos geopolíticos"), ("sec5", "Inflación y tasas"), ("sec6", "Tipo de cambio"),
             ("sec7", "Oro, cobre y plata"), ("sec8", "Mercado bursátil"), ("sec9", "Agenda económica"),
             ("sec10", "Riesgos de la jornada")]
ROMANOS = ["I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X"]


def _cls(chg):
    if chg is None:
        return "flat"
    return "up" if chg > 0.005 else ("down" if chg < -0.005 else "flat")


def _flecha(chg, dec=1, texto=None):
    if chg is None:
        return '<span class="flat">—</span>'
    c = _cls(chg)
    sym = "▲" if c == "up" else ("▼" if c == "down" else "—")
    return f'<span class="{c}">{sym} {texto if texto is not None else pct(chg, dec)}</span>'


def _valor(q, dec=None):
    if not q or q.get("price") is None:
        return "n/d"
    return fmt(q["price"], q.get("dec", 2) if dec is None else dec)


def _ticker(D, tz):
    u, e, cu, br = _q(D, "usdclp"), _q(D, "eurclp"), _q(D, "cobre"), _q(D, "brent")
    ch = D.get("chile") or {}
    ip = D.get("ipsa")
    items = []
    if u:
        ahora = dt.datetime.now(tz)
        abierto = ahora.weekday() < 5 and 9 <= ahora.hour < 17
        if abierto:
            items.append(("Dólar (spot)", "$" + fmt(u["price"]), _flecha(u["chg"], 2)))
        else:
            # mercado chileno cerrado: se muestra el ULTIMO CIERRE (como el original)
            cierres = DS.cierres_diarios(u["candles"], 2, tz)
            if len(cierres) == 2:
                c1, c0 = cierres[-1], cierres[-2]
                dia = ["lun.", "mar.", "mié.", "jue.", "vie.", "sáb.", "dom."][c1["fecha"].weekday()]
                items.append((f"Dólar (cierre {dia})", "$" + fmt(c1["c"]), _flecha((c1["c"] - c0["c"]) / c0["c"] * 100, 2)))
            else:
                items.append(("Dólar (spot)", "$" + fmt(u["price"]), _flecha(u["chg"], 2)))
    if ip:
        items.append(("IPSA (cierre, prensa)", ("≈" if ip.get("aprox") else "") + fmt(ip["price"], 0 if ip.get("aprox") else 2), _flecha(ip.get("chg"))))
    if e:
        items.append(("Euro", "$" + fmt(e["price"]), _flecha(e["chg"])))
    if ch.get("uf"):
        items.append(("UF", "$" + fmt(ch["uf"]["valor"]), '<span class="flat">—</span>'))
    if cu:
        items.append(("Cobre", "US$" + fmt(cu["price"]), _flecha(cu["chg"])))
    if br:
        items.append(("Petróleo (Brent)", "US$" + fmt(br["price"]), _flecha(br["chg"])))
    h = "".join(f'<div class="ticker-item"><span class="tk">{k}</span><span class="tv">{v}</span><span class="td">{d}</span></div>'
                for k, v, d in items)
    return h + h   # duplicado para que la cinta sea continua


def _li(items, cls="plain", tags=None):
    if tags:
        return f'<ul class="{cls}">' + "".join(
            f'<li><span class="tag">{it["tag"]}</span>{it["html"]}</li>' for it in items) + "</ul>"
    return f'<ul class="{cls}">' + "".join(f"<li>{x}</li>" for x in items) + "</ul>"


def _sec_cambio(D, tz, cont):
    u = _q(D, "usdclp")
    ch = D.get("chile") or {}
    if not u:
        return "<p>Sin datos del dólar hoy (Yahoo no respondió).</p>"
    cierres = DS.cierres_diarios(u["candles"], 5, tz)
    ult = cierres[-1] if cierres else None
    sem = (cierres[-1]["c"] - cierres[0]["c"]) if len(cierres) >= 2 else None
    f_ult = _fecha_corta(ult["fecha"]) if ult else ""
    f_ini = _fecha_corta(cierres[0]["fecha"]) if cierres else ""
    obs = ch.get("dolar")
    stripe = f'''<div class="stripe">
    <div class="card"><div class="k">Dólar spot — ahora</div><div class="v">${fmt(u["price"])}</div><div class="d {_cls(u["chg_abs"])}">{"▲" if u["chg_abs"] > 0 else ("▼" if u["chg_abs"] < 0 else "—")} {fmt(u["chg_abs"]).replace("-", "")} ({pct(u["chg"], 2)})</div></div>
    <div class="card"><div class="k">Cierre anterior</div><div class="v">${fmt(u["prev"])}</div><div class="d flat">{f_ult}</div></div>
    {"".join([f'<div class="card"><div class="k">Var. semana</div><div class="v" style="color:{"#C1655A" if sem > 0 else "#5FA97E"};">{"▲" if sem > 0 else "▼"} {fmt(sem).replace("-", "")}</div><div class="d flat">vs. {f_ini}</div></div>']) if sem is not None else ""}
    {"".join([f'<div class="card"><div class="k">Observado BCCh</div><div class="v">${fmt(obs["valor"])}</div><div class="d flat">{obs["fecha"][8:10]}-{["ene","feb","mar","abr","may","jun","jul","ago","sep","oct","nov","dic"][int(obs["fecha"][5:7])-1]}</div></div>']) if obs else ""}
  </div>'''
    filas = []
    prev = None
    # El "dólar observado" que publica el BCCh el dia D es el PROMEDIO del dia
    # habil anterior; por eso a la fila del dia D le corresponde el observado
    # publicado el siguiente dia habil.
    obs_map = dict(ch.get("dolar_serie") or [])
    def _obs_de(fecha):
        f = fecha + dt.timedelta(days=1)
        for _ in range(4):
            if f.strftime("%Y-%m-%d") in obs_map:
                return obs_map[f.strftime("%Y-%m-%d")]
            f += dt.timedelta(days=1)
        return None
    for c in cierres:
        f = c["fecha"]
        var = ((c["c"] - prev) / prev * 100) if prev else None
        o = _obs_de(f)
        filas.append(f"<tr><td>{_fecha_corta(f)}</td><td>${fmt(c['c'])}</td><td>{_flecha(var, 2) if var is not None else '<span class=flat>—</span>'}</td><td>{('$' + fmt(o)) if o else '—'}</td></tr>")
        prev = c["c"]
    tabla = ('<div class="table-wrap"><table><thead><tr><th>Fecha</th><th>Dólar (cierre spot)</th><th>Var. diaria</th><th>Observado BCCh (prom. del día)</th></tr></thead><tbody>'
             + "".join(filas) + "</tbody></table></div>")
    serie = DS.serie_mensual(u["candles"])
    svg, prom, resumen = grafico.usdclp_12m(serie, u["price"], "hoy")
    chart = ""
    if svg:
        m0, m1 = grafico._lab(serie[0][0]), grafico._lab(serie[-1][0])
        chart = f'''<div class="chart-card">
    <div class="chart-title">USD/CLP — variación vs. promedio de los últimos 12 meses</div>
    <div class="chart-meta">Cierres mensuales, {m0} a {m1} ({m1}: mes en curso, precio actual) · Línea de 0 = promedio del período (${fmt(prom, 0)})</div>
    {svg}
  </div>
  <p>{resumen}</p>'''
    return stripe + f"<p>{cont['cambio']}</p>" + tabla + chart


def _sec_commod(D, tz):
    tarjetas = []
    for k, emoji in (("brent", "🛢️"), ("cobre", "🧲"), ("oro", "🥇"), ("plata", "🥈")):
        q = _q(D, k)
        if not q:
            continue
        ant = _antiguedad(q, tz)
        nombre = q["nombre"] + (ant.replace(" (último dato: ", " — ").rstrip(")") if ant else "")
        tarjetas.append(f'<div class="commod-card"><div class="ck">{emoji} {nombre}</div><div class="cv">US${fmt(q["price"], q["dec"])}</div><div class="cd {_cls(q["chg"])}">{_flecha(q["chg"])}</div></div>')
    grid = '<div class="commod-grid">' + "".join(tarjetas) + "</div>"
    filas = []
    for k, etiqueta in (("oro", "Oro (US$/oz)"), ("cobre", "Cobre (US$/lb)"), ("plata", "Plata (US$/oz)"), ("wti", "Petróleo WTI (US$/bbl)")):
        q = _q(D, k)
        if not q:
            continue
        ant = _antiguedad(q, tz)
        filas.append(f"<tr><td>{etiqueta}{(' — último cierre conocido: ' + ant[16:-1]) if ant else ''}</td><td>{fmt(q['prev'], q['dec'])}</td><td>{fmt(q['price'], q['dec'])}</td><td>{_flecha(q['chg'])}</td></tr>")
    tabla = ('<div class="table-wrap"><table><thead><tr><th>Metal / energía</th><th>Cierre ant.</th><th>Hoy</th><th>Var.</th></tr></thead><tbody>'
             + "".join(filas) + "</tbody></table></div>")
    return grid + tabla


def _sec_bolsa(D, tz):
    filas = []
    ip = D.get("ipsa")
    if ip:
        filas.append(f'<tr><td>IPSA (cierre, según <a href="{html.escape(ip.get("link", ""))}">{html.escape(ip["fuente"])}</a>)</td><td>{("≈" if ip.get("aprox") else "") + fmt(ip["price"], 0 if ip.get("aprox") else 2)}</td><td>{_flecha(ip.get("chg"))}</td></tr>')
    for k in ("ech", "spx", "es", "nq", "stoxx", "nikkei", "hsi", "shanghai", "vix", "btc"):
        q = _q(D, k)
        if not q:
            continue
        filas.append(f"<tr><td>{q['nombre']}{_antiguedad(q, tz)}</td><td>{(q['unidad'] if q['unidad'] not in ('%', '') else '')}{fmt(q['price'], q['dec'])}</td><td>{_flecha(q['chg'])}</td></tr>")
    return ('<div class="table-wrap"><table><thead><tr><th>Índice / activo</th><th>Último</th><th>Var.</th></tr></thead><tbody>'
            + "".join(filas) + "</tbody></table></div>")


def _sec_agenda(A, meta):
    filas = "".join(
        f"<tr><td>{_fecha_corta(e['fecha'])}{(' ' + e['hora']) if e['hora'] else ''}</td><td>{html.escape(e['titulo'])}"
        f"{(' · esperado ' + html.escape(e['forecast'])) if e.get('forecast') else ''}</td><td>{e['impacto']}</td></tr>"
        for e in A[:14])
    if not filas:
        filas = "<tr><td colspan=3>Sin eventos relevantes en los próximos días.</td></tr>"
    out = ('<div class="table-wrap"><table><thead><tr><th>Fecha (hora Chile)</th><th>Evento</th><th>Impacto</th></tr></thead><tbody>'
           + filas + "</tbody></table></div>")
    res = meta.get("resultados") or []
    if res:
        out += "<h3>Datos ya publicados hoy</h3><ul class=\"plain\">" + "".join(
            f"<li><strong>{r['hora']} {html.escape(r['titulo'])}:</strong> {html.escape(str(r['actual']))}"
            f"{(' (esperado ' + html.escape(r['forecast']) + ')') if r['forecast'] else ''}</li>" for r in res) + "</ul>"
    return out


def render(D, N, A, cont, meta, tz):
    ahora = meta["ahora"]
    fecha_larga = _fecha_larga(ahora)
    fecha_iso = ahora.strftime("%Y-%m-%d")
    fecha_corta = f"{ahora.day:02d} {['ene','feb','mar','abr','may','jun','jul','ago','sep','oct','nov','dic'][ahora.month-1]} {ahora.year}"
    qi = '<span class="qi-sep">|</span>'.join(f'<a href="#{sid}">{nombre}</a>' for sid, nombre in SECCIONES)
    modo = cont.get("modo")
    aviso = ""
    if modo != "ia":
        aviso = f'<div class="callout">Edición automática por reglas (titulares agrupados por sección). Redacción con IA no disponible hoy: {html.escape(meta.get("ia_motivo") or "")}.</div>'
    # I
    s1 = _li(cont["relevante"], "newsflash", tags=True)
    # II
    s2 = ""
    for b in cont["internacional"]:
        s2 += f"<h3>{b['h3']}</h3>" if b.get("h3") else ""
        s2 += "".join(f"<p>{p}</p>" for p in b.get("parrafos") or [])
        if b.get("items"):
            s2 += _li(b["items"])
    s3 = _li(cont["chile"])
    s4 = _li(cont["geopolitica"])
    s5 = "".join(f"<p>{p}</p>" for p in cont["tasas"]) or "<p>Sin novedades relevantes en tasas hoy.</p>"
    s6 = _sec_cambio(D, tz, cont)
    s7 = _sec_commod(D, tz) + f"<p>{cont['commodities']}</p>"
    s8 = f"<p>{cont['bolsa']}</p>" + _sec_bolsa(D, tz)
    s9 = _sec_agenda(A, meta)
    s10 = _li(cont["riesgos"])
    cuerpos = [s1, s2, s3, s4, s5, s6, s7, s8, s9, s10]
    titulos = ["Lo más relevante", "Panorama internacional", "Chile: política y economía", "Riesgos geopolíticos",
               "Inflación y tasas de política monetaria", "Tipo de cambio", "Oro, cobre y plata", "Mercado bursátil",
               "Agenda económica", "Principales riesgos de la jornada"]
    secs = "".join(f'<section id="{SECCIONES[i][0]}"><div class="secnum">{ROMANOS[i]}.</div><h2>{titulos[i]}</h2>{cuerpos[i]}</section>'
                   for i in range(10))
    fuentes = ("Fuentes: Yahoo Finance (dólar, euro, commodities, tasas y bolsas globales), mindicador.cl (UF, dólar observado, TPM), "
               "Google Noticias (titulares de prensa chilena e internacional), ForexFactory (calendario). "
               "El IPSA se toma de los titulares de prensa porque no existe una fuente gratuita en tiempo real; el litio no se incluye por la misma razón.")
    return f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover">
<meta name="format-detection" content="telephone=no">
<meta name="theme-color" content="#15171A">
<title>{C.NOMBRE} — {fecha_larga.split(' ', 1)[1]}</title>
<style>{CSS}</style>
</head>
<body>
<main>
<header>
  <div class="logo-slot"><div class="wordmark"><span class="a">A</span><span class="rest">Mercados</span></div><div class="rule"></div></div>
  <div class="eyebrow">{C.EYEBROW}</div>
  <div class="headline-frame"><div class="headline-label">El Titular AM</div><h1>{cont['titular']}</h1></div>
  <div class="sub">Lectura de 5 min · Mercados globales y locales</div>
  <div class="range"><span>{C.CIUDAD}, {fecha_larga}</span><span>Datos hasta las {ahora:%H:%M} hrs</span></div>
  {ANDES}
</header>
<div class="sticky-bar"><span class="wm"><span class="a">A</span><span class="rest">Mercados</span></span><span class="sdate">{fecha_corta}</span></div>
<div class="ticker-wrap"><div class="ticker-track">{_ticker(D, tz)}</div></div>
<div class="quickindex"><div class="qi-label">En este informe</div><div class="qi-row">{qi}</div></div>
{aviso}
{secs}
</main>
<footer>
  <b>{C.NOMBRE}</b> · {C.CIUDAD}, {fecha_larga} · Datos hasta las {ahora:%H:%M} hrs · Información de carácter referencial e informativo, elaborada automáticamente a partir de fuentes públicas de mercado y titulares de prensa. Describe lo ocurrido y el estado actual; no es pronóstico, no constituye asesoría financiera ni recomendación de inversión.<br>{fuentes}{(' · Redacción: IA (' + html.escape(meta.get('ia_uso', C.AI_MODEL)) + ')') if modo == 'ia' else ''}
</footer>
</body>
</html>"""
