"""
Grafico SVG (sin librerias) del USD/CLP: variacion de los cierres mensuales
de los ultimos 12 meses respecto del promedio del periodo. Misma geometria
que el informe de referencia (viewBox 360x205, linea 0 = promedio).
"""
MESES = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]


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
    extra = dot(i_min, 2.8) + txt(i_min, f"${vals[i_min]:,.0f} ({_lab(serie[i_min][0])}, mín.)".replace(",", "."), 12)
    if i_max != n - 1:
        extra += dot(i_max, 2.8) + txt(i_max, f"${vals[i_max]:,.0f} ({_lab(serie[i_max][0])}, máx.)".replace(",", "."), -8)
    extra += dot(n - 1, 2.8) + txt(n - 1, f"${vals[-1]:,.0f} ({etiqueta_hoy or _lab(serie[-1][0])})".replace(",", "."), -8 if ys[-1] > 60 else 14)
    svg = f'''<svg viewBox="0 0 360 205" xmlns="http://www.w3.org/2000/svg" style="width:100%;height:auto;display:block;">
  <defs><linearGradient id="usdArea" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0%" stop-color="#C97A45" stop-opacity="0.35"/><stop offset="100%" stop-color="#C97A45" stop-opacity="0.02"/>
  </linearGradient></defs>
  <line x1="40" y1="105" x2="346" y2="105" stroke="#C97A45" stroke-width="1.4" stroke-dasharray="4,3" opacity="0.85"/>
  <rect x="18" y="99" width="20" height="13" fill="#1A1D21"/>
  <text x="34" y="108" font-size="9" fill="#C97A45" font-weight="700" text-anchor="end" font-family="-apple-system,Segoe UI,sans-serif">0</text>
  <rect x="296" y="108" width="50" height="12" fill="#1A1D21"/>
  <text x="346" y="117" font-size="7.5" fill="#C97A45" font-weight="700" text-anchor="end" font-family="-apple-system,Segoe UI,sans-serif">prom. ${prom:,.0f}</text>
  <polygon points="{pts} {xs[-1]:.1f},190 {xs[0]:.1f},190" fill="url(#usdArea)"/>
  <polyline points="{pts}" fill="none" stroke="#C97A45" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"/>
  {extra}{labs}
</svg>'''.replace(f"prom. ${prom:,.0f}", f"prom. ${prom:,.0f}".replace(",", "."))
    # resumen en palabras (para el parrafo bajo el grafico)
    arriba = [_lab(serie[i][0]) for i in range(n) if desv[i] > amp * 0.25]
    abajo = [_lab(serie[i][0]) for i in range(n) if desv[i] < -amp * 0.25]
    resumen = (f"En los últimos 12 meses el dólar promedió ${prom:,.0f}. "
               f"Máximo mensual ${vals[i_max]:,.0f} ({_lab(serie[i_max][0])}, {vals[i_max]-prom:+,.0f} vs. promedio) "
               f"y mínimo ${vals[i_min]:,.0f} ({_lab(serie[i_min][0])}, {vals[i_min]-prom:+,.0f}). "
               f"Hoy está {vals[-1]-prom:+,.0f} respecto del promedio.").replace(",", ".")
    return svg, prom, resumen
