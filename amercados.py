#!/usr/bin/env python3
"""
AMercados — informe matinal de mercados (HTML) a Telegram.

Comandos:
  python3 amercados.py test         -> manda "hola" a Telegram (prueba el token)
  python3 amercados.py chatid       -> muestra tu CHAT_ID
  python3 amercados.py datos        -> imprime los datos de mercado del momento
  python3 amercados.py noticias     -> imprime los titulares por seccion
  python3 amercados.py build        -> genera el HTML en salida/ (no envia)
  python3 amercados.py build --sin-ia  -> idem, forzando la redaccion por reglas
  python3 amercados.py send         -> genera y ENVIA a Telegram
  python3 amercados.py send --gate  -> solo envia si es la hora (dias habiles, 1 vez/dia)
  python3 amercados.py flash        -> flash intradia: precios + titulares nuevos (sin IA)
  python3 amercados.py flash --gate -> solo a las horas FLASH_HORAS, una vez cada una
  python3 amercados.py selftest     -> prueba todo sin enviar nada
"""
import os
import re
import sys
import json
import shutil
import datetime as dt
import zoneinfo
import config as C

HERE = os.path.dirname(os.path.abspath(__file__))
SALIDA = os.path.join(HERE, "salida")
DOCS = os.path.join(HERE, "docs")
STATE = os.path.join(HERE, "state.json")
TZ = zoneinfo.ZoneInfo(C.TIMEZONE)


def _state():
    try:
        return json.load(open(STATE))
    except Exception:
        return {}


def _save_state(s):
    json.dump(s, open(STATE, "w"), indent=1)


def _es_habil(ahora):
    feriado = ahora.strftime("%m-%d") in C.FERIADOS_CL or ahora.strftime("%Y-%m-%d") in C.FERIADOS_CL
    return ahora.weekday() < 5 and not feriado


def _toca_enviar(ahora):
    """True si estamos en la ventana horaria y no se envio hoy."""
    if C.SOLO_DIAS_HABILES and not _es_habil(ahora):
        return False, "fin de semana o feriado"
    if not (C.REPORT_HORA <= ahora.hour < C.REPORT_HORA + 2):
        return False, f"fuera de la ventana {C.REPORT_HORA:02d}:00-{C.REPORT_HORA+1:02d}:59"
    if _state().get("ultimo_envio") == ahora.strftime("%Y-%m-%d"):
        return False, "ya se envió hoy"
    return True, ""


def construir(sin_ia=False, verbose=True):
    """Recolecta todo y genera el HTML. Devuelve (ruta, contenido, meta)."""
    import datos, noticias, agenda, redactor, informe
    if sin_ia:
        C.USE_AI = False
    ahora = dt.datetime.now(TZ)
    meta = {"ahora": ahora}
    if verbose:
        print(f"[{ahora:%H:%M}] recolectando datos de mercado...")
    D = datos.recolectar()
    if verbose:
        ok = sum(1 for v in D["yahoo"].values() if v)
        print(f"   Yahoo: {ok}/{len(D['yahoo'])} instrumentos · mindicador: {'ok' if D['chile'] else 'FALLO'} · IPSA prensa: {'ok' if D['ipsa'] else 'sin dato'}")
        print("   agenda...")
    A = agenda.proximos(TZ)
    meta["resultados"] = agenda.resultados_hoy(TZ)
    if verbose:
        print(f"   {len(A)} eventos · noticias...")
    N = noticias.recolectar()
    if verbose:
        print("   " + " · ".join(f"{s}:{len(v)}" for s, v in N.items()))
        print(f"   redactando ({'IA ' + C.AI_MODEL if C.USE_AI else 'reglas'})...")
    cont = redactor.redactar(D, N, A, meta, TZ)
    if verbose:
        print(f"   modo: {cont['modo']}" + (f" ({meta.get('ia_motivo')})" if cont["modo"] != "ia" else f" ({meta.get('ia_uso')})"))
    html_txt = informe.render(D, N, A, cont, meta, TZ)
    meta["noticias"] = N
    os.makedirs(SALIDA, exist_ok=True)
    nombre = f"amercados-{ahora:%Y-%m-%d}.html"
    ruta = os.path.join(SALIDA, nombre)
    open(ruta, "w", encoding="utf-8").write(html_txt)
    shutil.copy(ruta, os.path.join(SALIDA, "ultimo.html"))
    # copia para GitHub Pages (docs/index.html = ultimo; docs/AAAA-MM-DD.html = archivo)
    os.makedirs(DOCS, exist_ok=True)
    shutil.copy(ruta, os.path.join(DOCS, "index.html"))
    shutil.copy(ruta, os.path.join(DOCS, f"{ahora:%Y-%m-%d}.html"))
    if verbose:
        print(f"   listo: {ruta}")
    return ruta, cont, meta


def _texto_plano(s):
    s = re.sub(r"<a [^>]*>", "", s).replace("</a>", "")
    s = re.sub(r"<span[^>]*>", "", s).replace("</span>", "")
    return s


def enviar(ruta, cont, meta):
    import telegram as T
    ahora = meta["ahora"]
    titular = cont["titular"]
    pie = f"📰 <b>{C.NOMBRE}</b> · {ahora:%d-%m-%Y}\n{titular}"
    ok = T.send_document(ruta, caption=pie, filename=f"AMercados-{ahora:%Y-%m-%d}.html")
    L = ["<b>Lo más relevante</b>"]
    for it in cont["relevante"][:4]:
        L.append(f"• <b>{it['tag']}</b> · {_texto_plano(it['html'])}")
    if C.PAGES_URL:
        L.append(f"\n🔗 Ver en el navegador: {C.PAGES_URL}")
    if cont.get("modo") != "ia":
        L.append(f"\n<i>Edición por reglas (IA no disponible: {meta.get('ia_motivo')})</i>")
    ok2 = T.send(("\n".join(L))[:4000])
    if ok and ok2:
        s = _state()
        s["ultimo_envio"] = ahora.strftime("%Y-%m-%d")
        s["ultimo_modo"] = cont.get("modo")
        _save_state(s)
        # todo lo que salió en el informe ya está "visto": el flash traerá solo lo nuevo
        import noticias
        N = meta.get("noticias") or {}
        noticias.marcar_vistas([it for s_, its in N.items() for it in its])
        print("   enviado a Telegram ✅")
    return ok and ok2


def _toca_flash(ahora):
    if C.SOLO_DIAS_HABILES and not _es_habil(ahora):
        return False, "fin de semana o feriado"
    if ahora.hour not in C.FLASH_HORAS:
        return False, f"no es hora de flash ({', '.join(f'{h:02d}:00' for h in C.FLASH_HORAS)})"
    hechos = _state().get("flashes", {}).get(ahora.strftime("%Y-%m-%d"), [])
    if ahora.hour in hechos:
        return False, "este flash ya se envió"
    return True, ""


def _linea_precios(D):
    from redactor import fmt, pct, _q
    P = []
    u = _q(D, "usdclp")
    if u:
        P.append(f"💵 Dólar <b>${fmt(u['price'])}</b> ({pct(u['chg'], 2)})")
    ip = D.get("ipsa")
    if ip:
        P.append(f"📈 IPSA <b>{'≈' if ip.get('aprox') else ''}{fmt(ip['price'], 0 if ip.get('aprox') else 2)}</b>"
                 + (f" ({pct(ip['chg'])})" if ip.get("chg") is not None else "") + " (prensa)")
    for k, emoji in (("cobre", "🧲"), ("brent", "🛢️"), ("oro", "🥇")):
        q = _q(D, k)
        if q:
            P.append(f"{emoji} {q['nombre']} <b>US${fmt(q['price'], q['dec'])}</b> ({pct(q['chg'])})")
    for k, emoji in (("spx", "🇺🇸"), ("vix", "😬")):
        q = _q(D, k)
        if q:
            P.append(f"{emoji} {q['nombre']} <b>{fmt(q['price'], 1 if k == 'vix' else 0)}</b> ({pct(q['chg'])})")
    return "\n".join(P)


def flash(gate=False):
    """Mensaje corto: precios del momento + titulares nuevos + datos publicados hoy."""
    import datos, noticias, agenda, telegram as T
    from redactor import _fecha_corta
    ahora = dt.datetime.now(TZ)
    if gate:
        toca, motivo = _toca_flash(ahora)
        if not toca:
            print(f"[{ahora:%Y-%m-%d %H:%M} Chile] flash no se envía: {motivo}.")
            return
    print(f"[{ahora:%H:%M}] flash: datos...")
    D = datos.recolectar()
    print("   noticias...")
    N = noticias.recolectar()
    nuevas = noticias.nuevas(N, top=C.FLASH_TOP)
    res = agenda.resultados_hoy(TZ)
    L = [f"⚡ <b>{C.NOMBRE} · Flash {ahora:%H:%M}</b> · {ahora:%d-%m-%Y}", _linea_precios(D), ""]
    if nuevas:
        L.append("<b>Titulares nuevos</b>")
        for it in nuevas:
            L.append(f"• <a href=\"{it['link']}\">{it['titulo']}</a> · <i>{it['fuente']}</i>")
    else:
        L.append("<i>Sin titulares nuevos desde el último envío.</i>")
    if res:
        L.append("")
        L.append("<b>Datos publicados hoy</b>")
        for r in res[:5]:
            L.append(f"• {r['hora']} {r['titulo']}: <b>{r['actual']}</b>"
                     + (f" (esperado {r['forecast']})" if r['forecast'] else ""))
    L.append("")
    L.append(f"<i>Foto del momento, no pronóstico. Datos hasta las {ahora:%H:%M}.</i>")
    ok = T.send("\n".join(L)[:4000])
    if ok:
        noticias.marcar_vistas(nuevas)
        s = _state()
        s.setdefault("flashes", {})
        s["flashes"] = {ahora.strftime("%Y-%m-%d"): sorted(set(s["flashes"].get(ahora.strftime("%Y-%m-%d"), []) + [ahora.hour]))}
        _save_state(s)
        print(f"   flash enviado ✅ ({len(nuevas)} titulares nuevos)")
    return ok


def main():
    args = sys.argv[1:]
    cmd = args[0] if args else "help"
    if cmd == "test":
        import telegram as T
        print("ok" if T.send(f"👋 {C.NOMBRE} conectado.") else "fallo")
    elif cmd == "chatid":
        import telegram as T
        T.chat_id()
    elif cmd == "datos":
        import datos, redactor
        D = datos.recolectar()
        for h in redactor.frases_datos(D, TZ, {}):
            print("-", h)
    elif cmd == "noticias":
        import noticias
        for sec, items in noticias.recolectar().items():
            print(f"\n== {sec} ({len(items)})")
            for it in items:
                print(f"  [{it['score']:>2}] {it['titulo']} · {it['fuente']}")
    elif cmd == "build":
        ruta, cont, meta = construir(sin_ia="--sin-ia" in args)
        if "--abrir" in args:
            os.system(f'open "{ruta}"')
    elif cmd == "send":
        ahora = dt.datetime.now(TZ)
        if "--gate" in args:
            toca, motivo = _toca_enviar(ahora)
            if not toca:
                print(f"[{ahora:%Y-%m-%d %H:%M} Chile] no se envía: {motivo}.")
                return
        ruta, cont, meta = construir(sin_ia="--sin-ia" in args)
        enviar(ruta, cont, meta)
    elif cmd == "flash":
        flash(gate="--gate" in args)
    elif cmd == "selftest":
        print("1) datos"); import datos, noticias, agenda
        D = datos.recolectar(); assert D["yahoo"].get("usdclp"), "sin dólar"
        print("2) agenda"); A = agenda.proximos(TZ); print(f"   {len(A)} eventos")
        print("3) noticias"); N = noticias.recolectar(); assert N.get("relevante"), "sin titulares"
        print("4) informe por reglas"); ruta, cont, meta = construir(sin_ia=True, verbose=False)
        assert os.path.getsize(ruta) > 20000
        print(f"   OK -> {ruta}")
        print("selftest OK ✅  (no se envió nada)")
    else:
        print(__doc__)


if __name__ == "__main__":
    main()
