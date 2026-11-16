import json
import os
import time
import urllib.parse
import urllib.request

API = "https://api.telegram.org/bot{token}/{method}"

def tg(token, method, **params):
    url = API.format(token=token, method=method)
    data = urllib.parse.urlencode(params).encode()
    req = urllib.request.Request(url, data=data)
    with urllib.request.urlopen(req, timeout=40) as resp:
        return json.loads(resp.read().decode())

def send(token, chat_id, text):
    tg(token, "sendMessage", chat_id=chat_id, text=text[:4000])

def handle(token, text, chat_id, user_id):
    from core import build_balance_text, get_balance
    uid = f"telegram:{user_id}"
    raw = (text or "").strip()
    cmd = raw.split()[0].lower().lstrip("./")
    if cmd in ("start", "help", "menu"):
        send(token, chat_id, "Xephon on Telegram.\n.ping\n.bal")
        return
    if cmd == "ping":
        send(token, chat_id, "Pong")
        return
    if cmd == "bal":
        get_balance(uid)
        send(token, chat_id, build_balance_text(uid))
        return
    send(token, chat_id, "Try .ping or .bal")

def run():
    token = os.getenv("TELEGRAM_TOKEN", "").strip()
    if not token:
        print("Telegram door off: no TELEGRAM_TOKEN")
        return
    print("Telegram door on")
    offset = 0
    while True:
        try:
            data = tg(token, "getUpdates", offset=offset, timeout=25)
            for update in data.get("result", []):
                offset = update["update_id"] + 1
                msg = update.get("message") or {}
                text = msg.get("text")
                chat = msg.get("chat") or {}
                user = msg.get("from") or {}
                if text and chat.get("id") and user.get("id"):
                    handle(token, text, chat["id"], user["id"])
        except Exception as e:
            print(f"Telegram door error: {e}")
            time.sleep(3)
