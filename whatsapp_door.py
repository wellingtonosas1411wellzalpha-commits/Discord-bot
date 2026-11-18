import json
import os
import subprocess
import threading
import time
import uuid

PROC = {"proc": None}
WAITERS = {}
LAST_ERROR = {"text": "WhatsApp door has not started"}

def send_line(proc, payload):
    try:
        proc.stdin.write(json.dumps(payload) + "\n")
        proc.stdin.flush()
    except Exception as e:
        print(f"WhatsApp send failed: {e}")

def request_pair(phone: str, timeout: int = 40):
    proc = PROC.get("proc")
    if proc is None or proc.poll() is not None:
        return None, LAST_ERROR["text"]
    req_id = uuid.uuid4().hex[:8]
    event = threading.Event()
    box = {}
    WAITERS[req_id] = (event, box)
    send_line(proc, {"type": "pair", "phone": phone, "id": req_id})
    event.wait(timeout)
    WAITERS.pop(req_id, None)
    if box.get("code"):
        return box["code"], None
    return None, box.get("error") or LAST_ERROR["text"] or "No code came back"

def handle_text(text, phone, name):
    from core import wid, canonical_user, claim_link_code, build_balance_text, get_balance
    raw_uid = wid(phone)
    uid = canonical_user(raw_uid)
    parts = (text or "").strip().split()
    if not parts:
        return "Send .menu"
    cmd = parts[0].lower().lstrip("./")
    args = parts[1:]
    if cmd in ("start", "help", "menu"):
        return "Xephon on WhatsApp.\n.ping\n.bal\n.link <code>\n.link on Discord first."
    if cmd == "link":
        if not args:
            return f"Your WhatsApp number: {phone}\nOn Discord, run .link\nThen send .link <code> here."
        linked = claim_link_code(args[0], raw_uid)
        if not linked:
            return "That code is not valid. Run .link on Discord first."
        return "Linked. Discord, Telegram, and WhatsApp now share money and stats."
    if cmd == "ping":
        return "Pong"
    if cmd == "bal":
        get_balance(uid)
        return build_balance_text(uid)
    return "Try .ping, .bal, or .link"

def run():
    here = os.path.dirname(os.path.abspath(__file__))
    js = os.path.join(here, "whatsapp_door.js")
    if not os.path.exists(js):
        print("WhatsApp door off: missing whatsapp_door.js")
        return
    if not os.path.exists(os.path.join(here, "node_modules", "@whiskeysockets", "baileys")):
        LAST_ERROR["text"] = "Baileys is not installed. Render build needs npm install."
        print(LAST_ERROR["text"])
        return
    print("WhatsApp door starting")
    while True:
        try:
            proc = subprocess.Popen(
                ["node", js],
                cwd=here,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
            )
            PROC["proc"] = proc
            for line in proc.stdout:
                line = line.strip()
                if not line:
                    continue
                if not line.startswith("{"):
                    print(f"WhatsApp: {line}")
                    continue
                try:
                    data = json.loads(line)
                except Exception:
                    print(f"WhatsApp: {line}")
                    continue
                kind = data.get("type")
                if kind == "code":
                    waiter = WAITERS.get(data.get("id"))
                    if waiter:
                        waiter[1]["code"] = data.get("code")
                        waiter[0].set()
                elif kind == "error":
                    LAST_ERROR["text"] = data.get("error") or "WhatsApp error"
                    waiter = WAITERS.get(data.get("id"))
                    if waiter:
                        waiter[1]["error"] = LAST_ERROR["text"]
                        waiter[0].set()
                elif kind == "message":
                    reply = handle_text(data.get("text", ""), data.get("from", ""), data.get("name") or "You")
                    send_line(proc, {"type": "send", "chat": data.get("chat"), "text": reply})
            code = proc.wait()
            LAST_ERROR["text"] = f"WhatsApp door stopped ({code})"
        except Exception as e:
            LAST_ERROR["text"] = str(e)
            print(f"WhatsApp door error: {e}")
        time.sleep(10)
