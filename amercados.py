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
  python3 amercados.py health       -> avisa si hoy no salio el informe (lo usa la nube)
  python3 amercados.py actualizar   -> edicion viva: regenera la pagina con datos frescos y el texto de hoy
  python3 amercados.py actualizar --gate -> solo a las horas ACTUALIZAR_HORAS (dias habiles)
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
EDICION = os.path.join(HERE, "edicion_hoy.json")   # texto editorial del dia (para la edicion viva)
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
    try:
        import dolar
        meta["dolar"] = dolar.analizar(D)
        if verbose and meta["dolar"]:
            print(f"   dólar: {meta['dolar']['presion']} ({meta['dolar']['score']:+d})")
    except Exception as e:
        print("   (aviso) análisis del dólar falló:", str(e)[:80])
        meta["dolar"] = None
    if verbose:
        print(f"   {len(A)} eventos · noticias...")
    N = noticias.recolectar()
    if verbose:
        print("   " + " · ".join(f"{s}:{len(v)}" for s, v in N.items()))
    # leer el cuerpo de las notas mas relevantes (solo sirve si hay IA que lo lea)
    if C.USE_AI and C.ANTHROPIC_API_KEY and C.LEER_NOTAS > 0:
        import lector
        orden = N.get("relevante", []) + [x for s, its in N.items() if s != "relevante" for x in its[:3]]
        vistos, lista = set(), []
        for it in orden:
            if id(it) not in vistos:
                vistos.add(id(it)); lista.append(it)
        n_ok = lector.enriquecer(lista, max_notas=C.LEER_NOTAS, tiempo_max=C.LEER_TIEMPO_MAX)
        # los mismos dicts estan en las secciones (misma referencia) -> ya quedaron enriquecidos
        if verbose:
            print(f"   notas leídas: {n_ok} con texto de {min(len(lista), C.LEER_NOTAS)}")
    if verbose:
        print(f"   redactando ({'IA ' + C.AI_MODEL if C.USE_AI else 'reglas'})...")
    _avisar_salud(D, N, ahora, "informe")
    cont = redactor.redactar(D, N, A, meta, TZ)
    if verbose:
        print(f"   modo: {cont['modo']}" + (f" ({meta.get('ia_motivo')})" if cont["modo"] != "ia" else f" ({meta.get('ia_uso')})"))
    html_txt = informe.render(D, N, A, cont, meta, TZ)
    meta["noticias"] = N
    # guardar el texto editorial del dia para la "edicion viva" (actualizar)
    try:
        json.dump({"fecha": ahora.strftime("%Y-%m-%d"), "hora": ahora.strftime("%H:%M"), "cont": cont},
                  open(EDICION, "w"), ensure_ascii=False)
    except Exception as e:
        print("   (aviso) no se pudo guardar edicion_hoy.json:", str(e)[:60])
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


def _avisar_salud(D, N, ahora, origen):
    """Si faltan datos clave o no hay titulares, avisa por Telegram (1 vez/dia)."""
    import telegram as T
    problemas = []
    if not (D.get("yahoo") or {}).get("usdclp"):
        problemas.append("Yahoo Finance no entregó el dólar")
    faltan = [k for k, v in (D.get("yahoo") or {}).items() if v is None]
    if len(faltan) >= 5:
        problemas.append(f"Yahoo sin dato para {len(faltan)} instrumentos ({', '.join(faltan[:5])}…)")
    if not D.get("chile"):
        problemas.append("mindicador.cl no respondió (UF, observado, TPM)")
    if not N.get("relevante"):
        problemas.append("Google Noticias no devolvió titulares")
    if not problemas:
        return
    s = _state()
    if s.get("aviso_salud") == ahora.strftime("%Y-%m-%d"):
        return
    T.send(f"⚠️ <b>{C.NOMBRE} · aviso</b> ({origen} {ahora:%H:%M})\n" + "\n".join(f"• {p}" for p in problemas)
           + "\n<i>El envío salió igual, con lo que había.</i>")
    s["aviso_salud"] = ahora.strftime("%Y-%m-%d")
    _save_state(s)


def health():
    """Chequeo desde la nube: si ya pasó la ventana del informe y no se envió
    hoy (día hábil), avisa por Telegram una vez."""
    import telegram as T
    ahora = dt.datetime.now(TZ)
    if C.SOLO_DIAS_HABILES and not _es_habil(ahora):
        return
    s = _state()
    hoy = ahora.strftime("%Y-%m-%d")
    if ahora.hour >= C.REPORT_HORA + 2 and s.get("ultimo_envio") != hoy and s.get("aviso_faltante") != hoy:
        T.send(f"⚠️ <b>{C.NOMBRE}</b>: hoy {ahora:%d-%m} NO se envió el informe de la mañana "
               f"(revisa GitHub Actions o corre <code>python3 amercados.py send</code>).")
        s["aviso_faltante"] = hoy
        _save_state(s)
        print("aviso de informe faltante enviado")
    else:
        print("salud ok")


def _guardar_cierre_ipsa(D, ahora):
    """Al flash de la tarde: si la prensa ya publicó el cierre EXACTO del IPSA
    de hoy, se guarda para que el informe de mañana lo use (sin '≈')."""
    ip = D.get("ipsa")
    if not ip or ip.get("aprox"):
        return
    if ip.get("market_time") and dt.datetime.fromtimestamp(ip["market_time"], TZ).date() != ahora.date():
        return
    s = _state()
    s["ipsa_cierre"] = {"fecha": ahora.strftime("%Y-%m-%d"), "price": ip["price"], "chg": ip.get("chg"),
                        "fuente": ip.get("fuente"), "link": ip.get("link"), "texto": ip.get("texto")}
    _save_state(s)


def _escribir_salidas(html_txt, ahora):
    os.makedirs(SALIDA, exist_ok=True)
    ruta = os.path.join(SALIDA, f"amercados-{ahora:%Y-%m-%d}.html")
    open(ruta, "w", encoding="utf-8").write(html_txt)
    shutil.copy(ruta, os.path.join(SALIDA, "ultimo.html"))
    os.makedirs(DOCS, exist_ok=True)
    shutil.copy(ruta, os.path.join(DOCS, "index.html"))
    shutil.copy(ruta, os.path.join(DOCS, f"{ahora:%Y-%m-%d}.html"))
    return ruta


def actualizar(gate=False):
    """Edicion viva: vuelve a generar la pagina con DATOS frescos y el TEXTO
    editorial guardado del informe de la mañana (sin IA, sin Telegram)."""
    import datos, agenda, informe, dolar
    ahora = dt.datetime.now(TZ)
    if gate:
        if C.SOLO_DIAS_HABILES and not _es_habil(ahora):
            print(f"[{ahora:%Y-%m-%d %H:%M} Chile] actualizar: fin de semana o feriado."); return
        if ahora.hour not in C.ACTUALIZAR_HORAS:
            print(f"[{ahora:%Y-%m-%d %H:%M} Chile] actualizar: no es hora ({', '.join(f'{h:02d}:00' for h in C.ACTUALIZAR_HORAS)})."); return
        hechas = _state().get("actualizaciones", {}).get(ahora.strftime("%Y-%m-%d"), [])
        if ahora.hour in hechas:
            print("actualizar: esta hora ya se hizo."); return
    try:
        ed = json.load(open(EDICION))
    except Exception:
        ed = None
    if not ed or ed.get("fecha") != ahora.strftime("%Y-%m-%d"):
        print("actualizar: no hay texto editorial de hoy (aún no salió el informe de la mañana); no se actualiza.")
        return
    print(f"[{ahora:%H:%M}] edición viva: datos...")
    D = datos.recolectar()
    A = agenda.proximos(TZ)
    meta = {"ahora": ahora, "texto_de": ed.get("hora", ""), "resultados": agenda.resultados_hoy(TZ)}
    try:
        meta["dolar"] = dolar.analizar(D)
    except Exception as e:
        print("   (aviso) análisis del dólar falló:", str(e)[:80]); meta["dolar"] = None
    cont = ed["cont"]
    html_txt = informe.render(D, {}, A, cont, meta, TZ)
    ruta = _escribir_salidas(html_txt, ahora)
    s = _state()
    s.setdefault("actualizaciones", {})
    s["actualizaciones"] = {ahora.strftime("%Y-%m-%d"): sorted(set(s["actualizaciones"].get(ahora.strftime("%Y-%m-%d"), []) + [ahora.hour]))}
    _save_state(s)
    print(f"   página actualizada: {ruta} (texto de las {ed.get('hora')})")
    return ruta


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
    _guardar_cierre_ipsa(D, ahora)
    print("   noticias...")
    N = noticias.recolectar()
    _avisar_salud(D, N, ahora, "flash")
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
    if C.PAGES_URL:
        L.append("")
        L.append(f"🔗 Informe completo actualizado: {C.PAGES_URL}")
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
    elif cmd == "health":
        health()
    elif cmd == "actualizar":
        actualizar(gate="--gate" in args)
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
