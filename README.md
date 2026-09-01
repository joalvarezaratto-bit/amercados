# AMercados — informe matinal de mercados

Genera cada mañana (días hábiles, ~07:05 hora de Chile) un informe HTML con el
formato de *AMercados* (titular del día, lo más relevante, panorama internacional,
Chile, geopolítica, tasas, dólar con gráfico de 12 meses, commodities, bolsa,
agenda y riesgos) y lo manda a Telegram como archivo + resumen.

## Fuentes (todas gratis, sin API key)
- **Yahoo Finance**: dólar, EUR/USD, cobre, Brent/WTI, oro, plata, DXY, bonos del Tesoro, VIX, bolsas, bitcoin, real, ETF Chile (ECH).
- **mindicador.cl**: UF, dólar observado del Banco Central, TPM, IPC, Imacec, desempleo.
- **Google Noticias** (RSS): titulares de prensa chilena e internacional en español, por sección.
- **ForexFactory**: calendario económico (EE.UU. y China) + eventos fijos en `config.py` (Banco Central, Fed, IPC INE).
- **IPSA**: no existe fuente gratuita en tiempo real (Yahoo lo tiene congelado); se lee de los titulares de prensa y se rotula "según prensa".

## Redacción
- Con **IA** (Claude, `USE_AI = True` y API key con saldo): redacta titular, párrafos y riesgos a partir de los datos y titulares, con la regla de **no inventar**.
- Sin IA (o si falla): edición **por reglas** (titulares agrupados + frases con los datos). El informe siempre sale.

## Comandos
```
python3 amercados.py build            # genera salida/amercados-AAAA-MM-DD.html (no envía)
python3 amercados.py build --abrir    # idem y lo abre en el navegador
python3 amercados.py send             # genera y envía a Telegram
python3 amercados.py send --gate      # solo si es la hora (lo usa la nube)
python3 amercados.py selftest         # prueba todo sin enviar
python3 amercados.py datos | noticias | test | chatid
```

## Nube (GitHub Actions)
`.github/workflows/informe.yml` corre cada hora y envía una vez al día. Secrets
necesarios en el repo: `TELEGRAM_TOKEN`, `CHAT_ID`, `ANTHROPIC_API_KEY` (opcional).
Si el repo es público, activa GitHub Pages (carpeta `docs/`) y pon la URL en
`config.PAGES_URL` para que el mensaje incluya el link.

Honestidad: describe lo ocurrido y el estado actual; no es pronóstico ni asesoría.
