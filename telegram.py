"""Envio a Telegram (mensaje, foto, documento). Sin dependencias raras."""
import requests
import config as C

API = "https://api.telegram.org/bot{token}/{method}"


def _url(method):
    return API.format(token=C.TELEGRAM_TOKEN, method=method)


def send(text):
    if not C.CHAT_ID:
        print("ERROR: CHAT_ID = 0. Corre primero: python3 amercados.py chatid")
        return False
    r = requests.post(_url("sendMessage"), data={"chat_id": C.CHAT_ID, "text": text[:4096],
                      "parse_mode": "HTML", "disable_web_page_preview": "true"}, timeout=30).json()
    if not r.get("ok"):
        print("Telegram error:", r)
        return False
    return True


def send_document(path, caption="", filename=None):
    """Manda un archivo (el HTML del informe). El pie va limitado a 1024 chars."""
    if not C.CHAT_ID:
        print("ERROR: CHAT_ID = 0.")
        return False
    with open(path, "rb") as f:
        files = {"document": (filename or path.split("/")[-1], f, "text/html")}
        r = requests.post(_url("sendDocument"),
                          data={"chat_id": C.CHAT_ID, "caption": caption[:1024], "parse_mode": "HTML"},
                          files=files, timeout=90).json()
    if not r.get("ok"):
        print("Telegram error:", r)
        return False
    return True


def chat_id():
    """Muestra los chats que le han escrito al bot (para copiar tu CHAT_ID)."""
    r = requests.get(_url("getUpdates"), timeout=30).json()
    vistos = set()
    for u in r.get("result", []):
        m = u.get("message") or u.get("channel_post") or {}
        c = m.get("chat", {})
        if c.get("id") and c["id"] not in vistos:
            vistos.add(c["id"])
            print(f"  chat_id = {c['id']}  ({c.get('first_name') or c.get('title')})")
    if not vistos:
        print("  Nadie le ha escrito al bot todavia. Mandale 'hola' y vuelve a correr esto.")
