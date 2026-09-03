"""
Grafico SVG (sin librerias) del USD/CLP: variacion de los cierres mensuales
de los ultimos 12 meses respecto del promedio del periodo. Misma geometria
que el informe de referencia (viewBox 360x205, linea 0 = promedio).
"""
MESES = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]


def _m(v):
    """1234 -> '1.234' (miles con punto, sin decimales)."""
    return f"{v:,.0f}".replace(",", ".")


def _lab(ym):
    y, m = ym
    return f"{MESES[m-1]}-{str(y)[2:]}"


def usdclp_12m(serie, precio_hoy=None, etiqueta_hoy=""):
    """serie = [((año, mes), cierre), ...] (12 puntos). Devuelve (svg, promedio, resumen)."""
    if len(serie) < 4:
        return "", None, ""
    vals = [v for _, v in serie]
    if precio_hoy:
        vals[-1] = precio_hoy    # el mes en curso se dibuja con el precio actual
    prom = sum(vals) / len(vals)
    desv = [v - prom for v in vals]
    amp = max(abs(d) for d in desv) or 1
    X0, X1, Y0, YM, Y1 = 40.0, 346.0, 33.0, 105.0, 185.0
    n = len(vals)
    xs = [X0 + (X1 - X0) * i / (n - 1) for i in range(n)]
    ys = [YM - d / amp * (YM - Y0) for d in desv]
    pts = " ".join(f"{x:.1f},{y:.1f}" for x, y in zip(xs, ys))
    i_min = min(range(n), key=lambda i: vals[i])
    i_max = max(range(n), key=lambda i: vals[i])
    labs = "".join(
        f'<text x="{xs[i]:.1f}" y="20" font-size="8" fill="#8B9099" text-anchor="middle" '
        f'font-family="-apple-system,Segoe UI,sans-serif">{_lab(serie[i][0])}</text>'
        for i in sorted(set([0, n // 3, 2 * n // 3, n - 1])))
    def dot(i, r=2.6):
        return (f'<circle cx="{xs[i]:.1f}" cy="{ys[i]:.1f}" r="{r}" fill="#C97A45" '
                f'stroke="#15171A" stroke-width="1"/>')
    def txt(i, t, dy):
        x = min(max(xs[i], 60), 320)
        return (f'<text x="{x:.1f}" y="{ys[i]+dy:.1f}" font-size="8" fill="#EDEDEA" '
                f'text-anchor="middle" font-weight="600" font-family="-apple-system,Segoe UI,sans-serif">{t}</text>')
    hits = "".join(f'<circle class="hit" cx="{xs[i]:.1f}" cy="{ys[i]:.1f}" r="9" data-tip="{_lab(serie[i][0])}: ${_m(vals[i])} ({desv[i]:+.0f} vs. prom.)"/>' for i in range(n))
    extra = dot(i_min, 2.8) + txt(i_min, f"${_m(vals[i_min])} ({_lab(serie[i_min][0])}, mín.)", 12)
    if i_max != n - 1:
        extra += dot(i_max, 2.8) + txt(i_max, f"${_m(vals[i_max])} ({_lab(serie[i_max][0])}, máx.)", -8)
    extra += dot(n - 1, 2.8) + txt(n - 1, f"${_m(vals[-1])} ({etiqueta_hoy or _lab(serie[-1][0])})", -8 if ys[-1] > 60 else 14)
    svg = f'''<svg viewBox="0 0 360 205" xmlns="http://www.w3.org/2000/svg" style="width:100%;height:auto;display:block;">
  <defs><linearGradient id="usdArea" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0%" stop-color="#C97A45" stop-opacity="0.35"/><stop offset="100%" stop-color="#C97A45" stop-opacity="0.02"/>
  </linearGradient></defs>
  <line x1="40" y1="105" x2="346" y2="105" stroke="#C97A45" stroke-width="1.4" stroke-dasharray="4,3" opacity="0.85"/>
  <rect x="18" y="99" width="20" height="13" fill="#1A1D21"/>
  <text x="34" y="108" font-size="9" fill="#C97A45" font-weight="700" text-anchor="end" font-family="-apple-system,Segoe UI,sans-serif">0</text>
  <rect x="296" y="108" width="50" height="12" fill="#1A1D21"/>
  <text x="346" y="117" font-size="7.5" fill="#C97A45" font-weight="700" text-anchor="end" font-family="-apple-system,Segoe UI,sans-serif">prom. ${_m(prom)}</text>
  <polygon points="{pts} {xs[-1]:.1f},190 {xs[0]:.1f},190" fill="url(#usdArea)"/>
  <polyline points="{pts}" fill="none" stroke="#C97A45" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"/>
  {extra}{labs}{hits}
</svg>'''
    # resumen en palabras (para el parrafo bajo el grafico)
    arriba = [_lab(serie[i][0]) for i in range(n) if desv[i] > amp * 0.25]
    abajo = [_lab(serie[i][0]) for i in range(n) if desv[i] < -amp * 0.25]
    resumen = (f"En los últimos 12 meses el dólar promedió ${_m(prom)}. "
               f"Máximo mensual ${_m(vals[i_max])} ({_lab(serie[i_max][0])}, {vals[i_max]-prom:+.0f} vs. promedio) "
               f"y mínimo ${_m(vals[i_min])} ({_lab(serie[i_min][0])}, {vals[i_min]-prom:+.0f}). "
               f"Hoy está {vals[-1]-prom:+.0f} respecto del promedio.")
    return svg, prom, resumen


# ---------------------------------------------------------------- velas dólar
def _f0(v):
    return f"{v:,.0f}".replace(",", ".")


def velas_dolar(a, n=60):
    """Grafico SVG de velas diarias del USD/CLP con medias 20/50 (y su cinta),
    soportes, resistencias y Fibonacci. Etiquetas en una columna derecha
    (sin tapar velas). a = dolar.analizar()."""
    import datetime as dt
    import dolar as DL
    candles = a["candles"]
    if len(candles) < 30:
        return ""
    v = candles[-n:]
    s20 = DL.sma_serie(candles, 20)[-len(v):]
    s50 = DL.sma_serie(candles, 50)[-len(v):]
    niveles = a["resistencias"][:2] + a["soportes"][:2]
    lo = min([c["l"] for c in v] + niveles)
    hi = max([c["h"] for c in v] + niveles)
    pad = (hi - lo) * 0.10 or 1
    lo, hi = lo - pad, hi + pad
    X0, X1, Y0, Y1 = 4.0, 318.0, 10.0, 208.0     # area de velas
    GX = 324.0                                    # inicio de la columna de etiquetas
    W = (X1 - X0) / len(v)
    def y(p):
        return Y1 - (p - lo) / (hi - lo) * (Y1 - Y0)
    def x(i):
        return X0 + W * (i + 0.5)
    F = 'font-family="-apple-system,Segoe UI,Helvetica,sans-serif"'
    out = []
    # fondo del area + rejilla
    out.append(f'<rect x="{X0}" y="{Y0}" width="{X1-X0}" height="{Y1-Y0}" fill="#16191D" rx="4"/>')
    for k in range(1, 5):
        yy = Y0 + (Y1 - Y0) * k / 5
        out.append(f'<line x1="{X0}" y1="{yy:.1f}" x2="{X1}" y2="{yy:.1f}" stroke="#262A30" stroke-width="0.7"/>')
    # cinta entre medias (tendencia): cobre si m20>m50, hielo si m20<m50
    if s20 and s50:
        off = len(v) - len(s50)
        k = len(s50)
        top = " ".join(f"{x(i+off):.1f},{y(s20[len(s20)-k+i]):.1f}" for i in range(k))
        bot = " ".join(f"{x(i+off):.1f},{y(s50[i]):.1f}" for i in range(k - 1, -1, -1))
        col = "#C97A45" if s20[-1] >= s50[-1] else "#7FA8B8"
        out.append(f'<polygon points="{top} {bot}" fill="{col}" opacity="0.10"/>')
    # niveles (lineas)
    for p in a["resistencias"][:2]:
        out.append(f'<line x1="{X0}" y1="{y(p):.1f}" x2="{X1}" y2="{y(p):.1f}" stroke="#C1655A" stroke-width="0.9" stroke-dasharray="5,3" opacity="0.75"/>')
    for p in a["soportes"][:2]:
        out.append(f'<line x1="{X0}" y1="{y(p):.1f}" x2="{X1}" y2="{y(p):.1f}" stroke="#5FA97E" stroke-width="0.9" stroke-dasharray="5,3" opacity="0.75"/>')
    fib = a.get("fib")
    fib_ok = fib and 0 < fib["cerca"][0] < 1 and lo < fib["cerca"][1] < hi
    if fib_ok:
        pc = fib["cerca"][1]
        out.append(f'<line x1="{X0}" y1="{y(pc):.1f}" x2="{X1}" y2="{y(pc):.1f}" stroke="#E3C9AE" stroke-width="0.8" stroke-dasharray="1.5,3" opacity="0.8"/>')
    # medias
    def poly(serie, color, w):
        off = len(v) - len(serie)
        pts = " ".join(f"{x(i+off):.1f},{y(p):.1f}" for i, p in enumerate(serie))
        return f'<polyline points="{pts}" fill="none" stroke="{color}" stroke-width="{w}" stroke-linejoin="round" stroke-linecap="round"/>'
    if s50:
        out.append(poly(s50, "#7FA8B8", 1.3))
    if s20:
        out.append(poly(s20, "#C97A45", 1.5))
    # barras de rango del dia (max-min), coloreadas por si el cierre subio o
    # bajo vs el dia anterior (las velas FX de Yahoo traen apertura = cierre,
    # asi que un cuerpo de vela no aporta). Encima, la linea de cierres con
    # relleno suave: es lo que se lee de un vistazo.
    bw = max(2.2, W * 0.55)
    for i, c in enumerate(v):
        prev = v[i-1]["c"] if i > 0 else c["o"]
        col = "#5FA97E" if c["c"] >= prev else "#C1655A"
        xx = x(i)
        out.append(f'<rect x="{xx-bw/2:.1f}" y="{y(c["h"]):.1f}" width="{bw:.1f}" height="{max(1.0, y(c["l"])-y(c["h"])):.1f}" rx="1" fill="{col}" opacity="0.38"/>')
    pts = " ".join(f"{x(i):.1f},{y(c['c']):.1f}" for i, c in enumerate(v))
    out.append('<defs><linearGradient id="clpArea" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stop-color="#EDEDEA" stop-opacity="0.16"/><stop offset="100%" stop-color="#EDEDEA" stop-opacity="0"/></linearGradient></defs>')
    out.append(f'<polygon points="{pts} {x(len(v)-1):.1f},{Y1} {x(0):.1f},{Y1}" fill="url(#clpArea)"/>')
    out.append(f'<polyline points="{pts}" fill="none" stroke="#EDEDEA" stroke-width="1.6" stroke-linejoin="round" stroke-linecap="round"/>')
    # precio actual: linea + punto
    p = a["price"]
    out.append(f'<line x1="{X0}" y1="{y(p):.1f}" x2="{X1}" y2="{y(p):.1f}" stroke="#EDEDEA" stroke-width="0.7" stroke-dasharray="2,3" opacity="0.55"/>')
    out.append(f'<circle cx="{x(len(v)-1):.1f}" cy="{y(p):.1f}" r="2.6" fill="#fff" stroke="#15171A" stroke-width="1"/>')
    # ---- columna derecha: eje + pildoras sin choques ----
    for k in range(0, 6):
        yy = Y0 + (Y1 - Y0) * k / 5
        pv = hi - (hi - lo) * k / 5
        out.append(f'<text x="{GX}" y="{yy+2.5:.1f}" font-size="6.5" fill="#5F6570" {F}>{_f0(pv)}</text>')
    pills = [(y(p), f"${p:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."), "#EDEDEA", "#15171A", True)]
    for r_ in a["resistencias"][:2]:
        pills.append((y(r_), f"R {_f0(r_)}", "#3A2220", "#E4A79E", False))
    for s_ in a["soportes"][:2]:
        pills.append((y(s_), f"S {_f0(s_)}", "#1B2A21", "#9AD1B0", False))
    if fib_ok:
        pills.append((y(fib["cerca"][1]), f"Fib {fib['cerca'][0]:.3f}".replace(".", ","), "#3A2A1E", "#E3C9AE", False))
    pills.sort(key=lambda t: t[0])
    PH = 11.0
    ys = [t[0] for t in pills]
    for i in range(1, len(ys)):          # empujar hacia abajo si se pisan
        if ys[i] - ys[i-1] < PH + 1:
            ys[i] = ys[i-1] + PH + 1
    for i in range(len(ys) - 2, -1, -1):  # y hacia arriba si se salen
        if ys[i+1] - ys[i] < PH + 1:
            ys[i] = ys[i+1] - PH - 1
    for (yy0, txt, bg, fg, bold), yy in zip(pills, ys):
        w = 6 + 4.2 * len(txt)
        out.append(f'<line x1="{X1}" y1="{yy0:.1f}" x2="{GX+24}" y2="{yy:.1f}" stroke="{fg}" stroke-width="0.5" opacity="0.45"/>')
        out.append(f'<rect x="{GX+24}" y="{yy-PH/2:.1f}" width="{w:.0f}" height="{PH}" rx="3" fill="{bg}"/>')
        out.append(f'<text x="{GX+24+w/2:.1f}" y="{yy+2.6:.1f}" font-size="7" fill="{fg}" text-anchor="middle" {"font-weight=\"700\"" if bold else ""} {F}>{txt}</text>')
    # zonas invisibles para el tooltip (una por dia)
    for i, c in enumerate(v):
        f = dt.datetime.fromtimestamp(c["t"], dt.timezone.utc)
        prev = v[i-1]["c"] if i > 0 else c["o"]
        chg = (c["c"] / prev - 1) * 100 if prev else 0
        tip = (f"{f.day} {_lab((f.year, f.month)).split('-')[0]} · cierre ${c['c']:,.2f} ({chg:+.2f}%)&lt;br&gt;máx {c['h']:,.0f} · mín {c['l']:,.0f}"
               .replace(",", "X").replace(".", ",").replace("X", "."))
        out.append(f'<rect class="hit" x="{x(i)-W/2:.1f}" y="{Y0}" width="{W:.1f}" height="{Y1-Y0}" data-tip="{tip}"/>')
    # fechas
    for i in (0, len(v) // 3, 2 * len(v) // 3, len(v) - 1):
        f = dt.datetime.fromtimestamp(v[i]["t"], dt.timezone.utc)
        anc = "start" if i == 0 else ("end" if i == len(v) - 1 else "middle")
        out.append(f'<text x="{x(i):.1f}" y="{Y1+11}" font-size="7" fill="#8B9099" text-anchor="{anc}" {F}>{f.day} {_lab((f.year, f.month)).split("-")[0]}</text>')
    return ('<svg viewBox="0 0 400 222" xmlns="http://www.w3.org/2000/svg" style="width:100%;height:auto;display:block;">'
            + "".join(out) + "</svg>")


LEYENDA_VELAS = ('<div style="display:flex;flex-wrap:wrap;gap:12px;font-size:.66rem;color:#8B9099;margin-top:8px;">'
                 '<span><i style="display:inline-block;width:14px;height:2px;background:#C97A45;vertical-align:middle;margin-right:5px;"></i>media 20 días</span>'
                 '<span><i style="display:inline-block;width:14px;height:2px;background:#7FA8B8;vertical-align:middle;margin-right:5px;"></i>media 50 días</span>'
                 '<span><i style="display:inline-block;width:14px;height:0;border-top:2px dashed #C1655A;vertical-align:middle;margin-right:5px;"></i>resistencia</span>'
                 '<span><i style="display:inline-block;width:14px;height:0;border-top:2px dashed #5FA97E;vertical-align:middle;margin-right:5px;"></i>soporte</span>'
                 '<span><i style="display:inline-block;width:14px;height:0;border-top:2px dotted #E3C9AE;vertical-align:middle;margin-right:5px;"></i>Fibonacci</span>'
                 '<span><i style="display:inline-block;width:14px;height:2px;background:#EDEDEA;vertical-align:middle;margin-right:5px;"></i>cierre diario</span>'
                 '<span><i style="display:inline-block;width:6px;height:10px;background:#5FA97E;opacity:.5;vertical-align:middle;margin-right:2px;"></i><i style="display:inline-block;width:6px;height:10px;background:#C1655A;opacity:.5;vertical-align:middle;margin-right:5px;"></i>rango del día (sube / baja)</span>'
                 '<span><i style="display:inline-block;width:14px;height:8px;background:#C97A45;opacity:.25;vertical-align:middle;margin-right:5px;"></i>cinta de tendencia (entre medias)</span></div>')


def barras_bolsa(b, max_n=30):
    """Barras horizontales (verde/rojo) con la variacion diaria de cada accion,
    ordenadas de mayor alza a mayor baja. b = bolsa.analizar()."""
    if not b or not b.get("acciones"):
        return ""
    acc = b["acciones"][:max_n]
    n = len(acc)
    RH = 11.0
    H = n * RH + 14
    W = 400
    LX, RX = 118.0, 356.0
    mid = (LX + RX) / 2
    amp = max(abs(a["chg"]) for a in acc) or 1
    def x(v):
        return mid + (v / amp) * (RX - LX) / 2 * 0.96
    F = 'font-family="-apple-system,Segoe UI,Helvetica,sans-serif"'
    out = [f'<line x1="{mid:.1f}" y1="6" x2="{mid:.1f}" y2="{H-8}" stroke="#3A3F46" stroke-width="0.8"/>']
    for k in (-1, -0.5, 0.5, 1):
        xx = x(k * amp)
        out.append(f'<line x1="{xx:.1f}" y1="6" x2="{xx:.1f}" y2="{H-8}" stroke="#23272C" stroke-width="0.6"/>')
        lab = f"{k*amp:+.1f}%".replace(".", ",")
        out.append(f'<text x="{xx:.1f}" y="{H-1}" font-size="6" fill="#5F6570" text-anchor="middle" {F}>{lab}</text>')
    for i, a in enumerate(acc):
        yy = 8 + i * RH
        col = "#5FA97E" if a["chg"] >= 0 else "#C1655A"
        x0, x1 = (mid, x(a["chg"])) if a["chg"] >= 0 else (x(a["chg"]), mid)
        out.append(f'<text x="{LX-6}" y="{yy+7.5}" font-size="7" fill="#D3D4D2" text-anchor="end" {F}>{a["nombre"]}</text>')
        tip = f"{a['nombre']} · ${a['price']:,.2f} · {a['chg']:+.2f}% · {a['sector']}".replace(",", "X").replace(".", ",").replace("X", ".")
        out.append(f'<rect x="{x0:.1f}" y="{yy+1.5}" width="{max(0.8, x1-x0):.1f}" height="{RH-3}" rx="1.5" fill="{col}" opacity="0.85"/>')
        out.append(f'<rect class="hit" x="{LX-110}" y="{yy}" width="{RX-LX+120}" height="{RH}" data-tip="{tip}"/>')
        tx = (x1 + 3) if a["chg"] >= 0 else (x0 - 3)
        anc = "start" if a["chg"] >= 0 else "end"
        lab = f"{a['chg']:+.1f}%".replace(".", ",")
        out.append(f'<text x="{tx:.1f}" y="{yy+7.5}" font-size="6.5" fill="{col}" text-anchor="{anc}" font-weight="600" {F}>{lab}</text>')
    return (f'<svg viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg" style="width:100%;height:auto;display:block;">'
            + "".join(out) + "</svg>")
