# =====================================================================
#  CONFIGURACION de AMercados  ->  este es el UNICO archivo que editas.
# =====================================================================
#
#  AMercados genera cada mañana un informe HTML (estilo "Informe matinal")
#  con mercados globales, Chile, tipo de cambio, commodities, agenda y
#  riesgos, y lo manda a Telegram. Todo con fuentes GRATIS y sin API key
#  (Yahoo Finance, mindicador.cl, Google Noticias, ForexFactory), salvo la
#  redaccion con IA (Claude), que es opcional y cuesta centavos por informe.
#
import os

# ---------------------------------------------------------------------
#  Secretos: 1) variables de entorno (nube)  2) secrets_local.py (tu Mac)
# ---------------------------------------------------------------------
try:
    import secrets_local as _sl
    _LOCAL_TOKEN = getattr(_sl, "TELEGRAM_TOKEN", "")
    _LOCAL_CHAT = getattr(_sl, "CHAT_ID", 0)
    _LOCAL_AI = getattr(_sl, "ANTHROPIC_API_KEY", "")
except ImportError:
    _LOCAL_TOKEN, _LOCAL_CHAT, _LOCAL_AI = "", 0, ""


def _pick(env_name, local):
    v = os.environ.get(env_name)
    return v if v else local


TELEGRAM_TOKEN = _pick("TELEGRAM_TOKEN", _LOCAL_TOKEN)
CHAT_ID = int(_pick("CHAT_ID", _LOCAL_CHAT or 0))
ANTHROPIC_API_KEY = _pick("ANTHROPIC_API_KEY", _LOCAL_AI)

# ---------------------------------------------------------------------
#  Identidad del informe
# ---------------------------------------------------------------------
NOMBRE = "AMercados"
EYEBROW = "Informe matinal"
CIUDAD = "Santiago"
TIMEZONE = "America/Santiago"

# ---------------------------------------------------------------------
#  Horario: el informe se manda UNA vez al dia, en dias habiles, cuando
#  en Chile son las REPORT_HORA (con `report --gate`). En la nube el cron
#  corre cada hora y el bot decide si ya es la hora (robusto al horario
#  de verano). Se recuerda en state.json que ya se envio hoy.
# ---------------------------------------------------------------------
REPORT_HORA = 7          # 7 = entre 07:00 y 08:59 hora Chile (ventana de 2 h)
SOLO_DIAS_HABILES = True

# "Flash" intradía: mensaje corto a Telegram (precios del momento + titulares
# NUEVOS desde el último envío), sin volver a redactar el informe. Se manda a
# estas horas de Chile (durante esa hora, una vez). Lista vacía = sin flashes.
FLASH_HORAS = [13, 18]
FLASH_TOP = 4            # máximo de titulares nuevos por flash

FERIADOS_CL = {
    "01-01", "05-01", "05-21", "06-20", "06-29", "07-16", "08-15",
    "09-18", "09-19", "10-31", "11-01", "12-08", "12-25",
    "2026-04-03", "2026-04-04", "2026-10-12", "2026-11-16",
    "2027-03-26", "2027-03-27", "2027-10-11",
}

# ---------------------------------------------------------------------
#  Redaccion con IA (Claude). Si USE_AI = False o la API key no tiene
#  saldo, el informe IGUAL sale: usa la redaccion por reglas (titulares
#  agrupados por seccion + frases armadas con los datos). Con IA, cada
#  seccion se redacta como el ejemplo (parrafos, titular del dia, riesgos).
#  Costo aprox. por informe: Opus 5 ~US$0,10-0,15; Sonnet 5 ~US$0,05.
# ---------------------------------------------------------------------
USE_AI = True
AI_MODEL = "claude-opus-5"        # alternativa mas barata: "claude-sonnet-5"
AI_EFFORT = "medium"              # low | medium | high  (mas alto = mas caro y lento)

# ---------------------------------------------------------------------
#  Simbolos de Yahoo Finance (gratis, sin API key).
#  Cada entrada: clave interna -> (simbolo, nombre, unidad, decimales)
# ---------------------------------------------------------------------
YAHOO = {
    "usdclp":  ("USDCLP=X",  "Dólar",              "$",   2),
    # OJO: el historial de EURCLP=X en Yahoo viene desfasado (da % falsos); el euro
    # en pesos se CALCULA como EUR/USD x USD/CLP (ver datos.recolectar).
    "eurusd":  ("EURUSD=X",  "EUR/USD",            "",    4),
    "cobre":   ("HG=F",      "Cobre",              "US$", 2),   # US$/libra
    "brent":   ("BZ=F",      "Petróleo (Brent)",   "US$", 2),
    "wti":     ("CL=F",      "Petróleo (WTI)",     "US$", 2),
    "oro":     ("GC=F",      "Oro",                "US$", 2),
    "plata":   ("SI=F",      "Plata",              "US$", 2),
    "dxy":     ("DX-Y.NYB",  "Dollar index (DXY)", "",    2),
    "us5y":    ("^FVX",      "Tesoro 5 años",      "%",   2),
    "us10y":   ("^TNX",      "Tesoro 10 años",     "%",   2),
    "us30y":   ("^TYX",      "Tesoro 30 años",     "%",   2),
    "vix":     ("^VIX",      "VIX",                "",    2),
    "spx":     ("^GSPC",     "S&P 500",            "",    2),
    "es":      ("ES=F",      "Futuro S&P 500",     "",    2),
    "nq":      ("NQ=F",      "Futuro Nasdaq 100",  "",    2),
    "stoxx":   ("^STOXX50E", "Euro Stoxx 50",      "",    2),
    "nikkei":  ("^N225",     "Nikkei 225",         "",    2),
    "hsi":     ("^HSI",      "Hang Seng",          "",    2),
    "shanghai":("000001.SS", "Shanghái",           "",    2),
    "btc":     ("BTC-USD",   "Bitcoin",            "US$", 0),
    "usdbrl":  ("USDBRL=X",  "Real (USD/BRL)",     "",    3),
    "usdmxn":  ("USDMXN=X",  "Peso mex. (USD/MXN)","",    3),
    "ech":     ("ECH",       "ETF Chile (ECH)",    "US$", 2),
}

# IPSA: Yahoo dejo de actualizar ^IPSA (dato congelado desde jul-2026), asi
# que se lee de Google Finance (pagina publica). Si falla, se usa el ETF ECH
# como referencia y se avisa en el informe.
IPSA_GOOGLE_URL = "https://www.google.com/finance/quote/IPSA:INDEXBCS"

# ---------------------------------------------------------------------
#  Noticias: busquedas en Google Noticias (RSS gratis) por seccion.
#  "cl" = prensa chilena, "intl" = prensa internacional en español.
#  Puedes agregar/quitar busquedas; `when:1d` = ultimas 24 horas.
# ---------------------------------------------------------------------
NOTICIAS = {
    "internacional": [
        ("intl", "Wall Street futuros bolsas hoy when:1d"),
        ("intl", "mercados globales dólar bonos Tesoro when:1d"),
        ("intl", "Fed Reserva Federal Warsh tasas when:1d"),
        ("intl", "Europa BCE economía when:1d"),
        ("intl", "China economía datos when:1d"),
    ],
    "chile": [
        ("cl", "Chile economía Hacienda OR \"Banco Central\" when:1d"),
        ("cl", "Chile Gobierno Congreso \"proyecto de ley\" OR presupuesto when:1d"),
        ("cl", "Chile cobre Codelco minería producción when:1d"),
        ("cl", "Chile empresas resultados OR utilidades OR \"gerente general\" when:1d"),
        ("cl", "Chile empleo OR IPC OR Imacec OR INE when:1d"),
        ("cl", "Kast Gobierno reforma OR anuncio when:1d"),
    ],
    "geopolitica": [
        ("intl", "Irán Ormuz Israel ataque when:1d"),
        ("intl", "Ucrania Rusia guerra negociación when:1d"),
        ("intl", "Trump aranceles comercio China when:1d"),
        ("intl", "Venezuela OPEP petróleo EE.UU. when:1d"),
        ("intl", "Taiwán China tensión when:1d"),
    ],
    "tasas": [
        ("intl", "inflación tasas de interés Fed BCE decisión when:1d"),
        ("cl", "Banco Central TPM tasa inflación Chile when:2d"),
    ],
    "cambio": [
        ("cl", "dólar peso chileno tipo de cambio when:1d"),
    ],
    "commodities": [
        ("intl", "precio del petróleo Brent OPEP when:1d"),
        ("intl", "precio del cobre oro plata litio when:1d"),
    ],
    "bolsa": [
        ("cl", "IPSA Bolsa de Santiago acciones when:1d"),
        ("cl", "Chile resultados trimestre utilidades empresa OR holding when:1d"),
        ("intl", "Wall Street cierre acciones resultados when:1d"),
    ],
}
NOTICIAS_TOP_POR_SECCION = 8     # titulares maximos que se le pasan a la IA por seccion
# Lectura del CUERPO de las notas mas relevantes (para que la IA tenga contenido,
# no solo titulos). Se leen hasta LEER_NOTAS notas, con tope de tiempo. Algunos
# medios bloquean: esas quedan solo con el titular.
LEER_NOTAS = 18
LEER_TIEMPO_MAX = 120            # segundos
NOTICIAS_MOSTRAR_SIN_IA = 6      # titulares por seccion cuando NO hay IA

# Palabras que suben la relevancia de un titular (para elegir "lo mas relevante").
KW = {
    "fed": 3, "reserva federal": 3, "tasas": 2, "inflación": 2, "dólar": 2,
    "cobre": 3, "petróleo": 3, "ormuz": 4, "irán": 3, "ataque": 2, "guerra": 2,
    "aranceles": 3, "trump": 2, "banco central": 3, "tpm": 3, "ipc": 2,
    "imacec": 2, "hacienda": 2, "presupuesto": 2, "ipsa": 3, "wall street": 3,
    "bolsa": 1, "china": 2, "recesión": 3, "crisis": 2, "récord": 2, "bce": 2,
    "empleo": 1, "desempleo": 2, "codelco": 2, "litio": 1, "bonos": 2,
}

# Titulares de otros paises que se cuelan (se descartan salvo que mencionen Chile).
EXCLUIR = ("venezuela bolívar", "banxico", "peso mexicano", "peso colombiano",
           "peso argentino", "sol peruano", "dólar blue")

# ---------------------------------------------------------------------
#  Agenda economica.
#  a) ForexFactory (gratis): reportes USD alto impacto + China (mueve el cobre).
#  b) Eventos FIJOS que ForexFactory no cubre (Chile) o que conviene tener
#     siempre a la vista. Formato: ("AAAA-MM-DD", "descripcion", "Alto|Medio").
#     Fechas del Banco Central: verificar en bcentral.cl (calendario RPM).
# ---------------------------------------------------------------------
AGENDA_DIAS = 10   # cuantos dias hacia adelante mirar
EVENTOS_FIJOS = [
    ("2026-09-08", "Reunión de Política Monetaria del Banco Central de Chile (TPM)", "Alto"),
    ("2026-09-15", "Reunión de la Fed (FOMC), día 1", "Alto"),
    ("2026-09-16", "Reunión de la Fed (FOMC): decisión de tasas", "Alto"),
    ("2026-10-27", "Reunión de Política Monetaria del Banco Central de Chile (TPM)", "Alto"),
    ("2026-10-28", "Reunión de la Fed (FOMC): decisión de tasas", "Alto"),
    ("2026-12-09", "Reunión de la Fed (FOMC): decisión de tasas", "Alto"),
    ("2026-12-15", "Reunión de Política Monetaria del Banco Central de Chile (TPM)", "Alto"),
]
# El INE publica el IPC de Chile alrededor del dia 8 de cada mes (fecha aprox.).
IPC_INE_DIA = 8

# ---------------------------------------------------------------------
#  Publicacion. Si activas GitHub Pages en el repo, pon aqui la URL para
#  que el mensaje de Telegram incluya el link (ademas del archivo HTML).
# ---------------------------------------------------------------------
PAGES_URL = ""   # ej. "https://joalvarezaratto-bit.github.io/amercados/"
