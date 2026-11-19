import asyncio
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

import asyncio

ROLE_ONLY = {
    "poll", "afk", "ncm", "delete", "react", "botban", "botunban", "xban",
    "xunban", "bans", "antidelete", "antibadword", "storage", "clearcache",
    "restart", "auth", "stats", "activity", "reset", "ptag", "checkall",
    "give", "take", "syncroles", "levelroles", "setlevelrole", "pair",
}

def run_async(coro):
    return asyncio.run(coro)

def menu_text():
    return """XEPHON ON WHATSAPP

.ping
.8ball
.joke
.translate <language> <text>
.xephongpt on / off
.xephongpt <message>

.bal
.daily
.work
.lb
.rank
.ranklb
.withdraw <amount>
.deposit <amount>
.fish
.beg
.dig
.rob <number>
.loan <amount>
.payloan <amount>
.donate <number> <amount>

.jobs
.setjob <job>
.myjob
.treasury

.pet
.buypet <type> <name>
.feedpet
.collectpet

.shop
.buy <item> [amount]
.use <item>
.inventory

.market
.sell <item> <qty> <price>
.buylisting <id>
.cancellisting <id>

.cf <heads/tails> <amount>
.roll <amount>
.roulette <red/black/green> <amount>
.slot <amount>
.mines <bet>
.blackjack <bet>

.profile
.achievements
.cds
.updateinfo
.versions
.repo
.link <code>

Role commands stay on Discord.
"""

def safe(fn, *args):
    try:
        return fn(*args)
    except Exception as e:
        return f"Command failed: {e.__class__.__name__}: {e}"

def handle_text(text, phone, name):
    from core import (
        wid, canonical_user, claim_link_code, build_balance_text, get_balance,
        do_daily, do_work, do_fish, do_beg, do_dig, do_withdraw, do_deposit,
        do_donate, do_rob, take_loan, pay_loan, build_jobs_list_text,
        build_myjob_text, set_job, build_leaderboard_text, build_rank_text,
        build_ranklb_text, buy_pet, feed_pet, collect_pet_income, build_pet_text,
        build_shop_text, handle_buy, build_inventory_text, use_global_item,
        build_market_text, create_listing, buy_listing, cancel_listing,
        start_mines, dig_mines, cashout_mines, start_blackjack, hit_blackjack,
        stand_blackjack, run_coinflip, do_dice, run_slot, run_roulette,
        get_8ball_answer, get_joke, translate_text, build_translate_response,
        build_updateinfo_text, build_version_history_text, build_achievements_text,
        build_cooldowns_text, get_treasury, get_bot_bank, propose_marriage,
        accept_marriage, do_divorce, get_partner, generate_code_response,
        get_kiragpt_session,
    )
    raw_uid = wid(phone)
    uid = canonical_user(raw_uid)
    raw = (text or "").strip()
    parts = raw.split()
    if not parts:
        return "Send .menu"
    cmd = parts[0].lower().lstrip("./")
    args = parts[1:]
    session = get_kiragpt_session(uid)

    if session.get("active") and not raw.startswith(".") and not raw.startswith("/"):
        try:
            reply = run_async(generate_code_response(raw, mode=session.get("mode", "normal"), history=session.get("history")))
            session.setdefault("history", []).append({"role": "user", "content": raw[:1500]})
            session["history"].append({"role": "assistant", "content": reply[:1500]})
            session["history"] = session["history"][-20:]
            return reply
        except Exception as e:
            return f"XephonGPT failed: {e}"

    if cmd in ROLE_ONLY:
        return f".{cmd} needs Discord roles, so it stays on Discord."
    if cmd in ("start", "help", "menu"):
        return menu_text()
    if cmd == "link":
        if not args:
            return f"Your WhatsApp number: {phone}\nOn Discord, run .link\nThen send .link <code> here."
        linked = claim_link_code(args[0], raw_uid)
        return "Linked. Discord and WhatsApp now share money and stats." if linked else "That code is not valid. Run .link on Discord first."
    if cmd == "ping":
        return "Pong"
    if cmd == "xephongpt":
        if args and args[0].lower() == "on":
            session["active"] = True
            return "XephonGPT on. Just type normally."
        if args and args[0].lower() == "off":
            session["active"] = False
            return "XephonGPT off."
        if len(args) >= 2 and args[1].lower() == "on" and args[0].lower() in ("wild", "ai", "normal"):
            session["mode"] = args[0].lower()
            return f"Mode set to {args[0].lower()}."
        prompt = " ".join(args).strip()
        if not prompt:
            return "Usage: .xephongpt <message>"
        reply = run_async(generate_code_response(prompt, mode=session.get("mode", "normal"), history=session.get("history")))
        return reply
    if cmd == "bal":
        get_balance(uid)
        return safe(build_balance_text, uid)
    if cmd == "daily":
        return safe(do_daily, uid)
    if cmd == "work":
        return safe(do_work, uid)
    if cmd == "fish":
        return safe(do_fish, uid)
    if cmd == "beg":
        return safe(do_beg, uid)
    if cmd == "dig":
        return safe(do_dig, uid)
    if cmd == "lb":
        return safe(build_leaderboard_text)
    if cmd == "rank":
        return safe(build_rank_text, uid, name or "You")
    if cmd == "ranklb":
        return safe(build_ranklb_text)
    if cmd == "withdraw":
        return safe(do_withdraw, uid, args[0]) if args else "Usage: .withdraw <amount>"
    if cmd == "deposit":
        return safe(do_deposit, uid, args[0]) if args else "Usage: .deposit <amount>"
    if cmd == "loan":
        return safe(take_loan, uid, args[0]) if args else "Usage: .loan <amount>"
    if cmd == "payloan":
        return safe(pay_loan, uid, args[0]) if args else "Usage: .payloan <amount>"
    if cmd == "donate":
        return safe(do_donate, uid, wid(args[0]), args[1]) if len(args) >= 2 else "Usage: .donate <number> <amount>"
    if cmd == "rob":
        return safe(do_rob, uid, wid(args[0])) if args else "Usage: .rob <number>"
    if cmd == "jobs":
        return safe(build_jobs_list_text)
    if cmd == "myjob":
        return safe(build_myjob_text, uid)
    if cmd == "setjob":
        return safe(set_job, uid, args[0]) if args else "Usage: .setjob <job>"
    if cmd == "treasury":
        return f"Treasury: ${get_treasury():,}\nBot bank: ${get_bot_bank():,}"
    if cmd == "pet":
        return safe(build_pet_text, name or "You", uid)
    if cmd == "buypet":
        return safe(buy_pet, uid, args[0], " ".join(args[1:])) if len(args) >= 2 else "Usage: .buypet <type> <name>"
    if cmd == "feedpet":
        return safe(feed_pet, uid)
    if cmd == "collectpet":
        return safe(collect_pet_income, uid)
    if cmd == "shop":
        return safe(build_shop_text, 0)
    if cmd == "buy":
        if not args:
            return "Usage: .buy <item> [amount]"
        amount = int(args[1]) if len(args) > 1 and args[1].isdigit() else 1
        return safe(handle_buy, uid, 0, args[0], amount)
    if cmd == "use":
        return safe(use_global_item, uid, args[0]) if args else "Usage: .use <item>"
    if cmd == "inventory":
        return safe(build_inventory_text, name or "You", uid)
    if cmd == "market":
        return safe(build_market_text)
    if cmd == "sell":
        if len(args) < 3:
            return "Usage: .sell <item> <qty> <price>"
        ok, msg = create_listing(uid, args[0], args[1], args[2])
        return msg
    if cmd == "buylisting":
        return safe(buy_listing, uid, args[0]) if args else "Usage: .buylisting <id>"
    if cmd == "cancellisting":
        return safe(cancel_listing, uid, args[0]) if args else "Usage: .cancellisting <id>"
    if cmd == "cf":
        return run_async(run_coinflip(uid, args[0], args[1])) if len(args) >= 2 else "Usage: .cf <heads/tails> <amount>"
    if cmd == "roll":
        return safe(do_dice, uid, args[0]) if args else "Usage: .roll <amount>"
    if cmd == "roulette":
        if len(args) < 2:
            return "Usage: .roulette <red/black/green> <amount>"
        box = {"text": ""}
        async def send_func(t):
            box["text"] = t
            return None
        async def edit_func(message, t):
            box["text"] = t
        run_async(run_roulette(uid, args[0], args[1], send_func, edit_func))
        return box["text"] or "Roulette failed."
    if cmd == "slot":
        if not args:
            return "Usage: .slot <amount>"
        box = {"text": ""}
        async def send_func(t):
            box["text"] = t
            return None
        async def edit_func(message, t):
            box["text"] = t
        run_async(run_slot(uid, args[0], send_func, edit_func))
        return box["text"] or "Slot failed."
    if cmd == "mines":
        if not args:
            return "Usage: .mines <bet>, .mines <1-25>, or .mines cashout"
        if args[0].lower() == "cashout":
            return safe(cashout_mines, uid)
        if args[0].isdigit() and int(args[0]) <= 25 and len(args) == 1:
            return safe(dig_mines, uid, args[0])
        return safe(start_mines, uid, args[0], args[1] if len(args) > 1 else None)
    if cmd in ("blackjack", "bj"):
        if not args:
            return "Usage: .blackjack <bet>, hit, or stand"
        if args[0].lower() == "hit":
            return safe(hit_blackjack, uid)
        if args[0].lower() == "stand":
            return safe(stand_blackjack, uid)
        return safe(start_blackjack, uid, args[0])
    if cmd == "8ball":
        return safe(get_8ball_answer)
    if cmd == "joke":
        return safe(get_joke)
    if cmd in ("translate", "trt"):
        if len(args) < 2:
            return "Usage: .translate <language> <text>"
        translated = run_async(translate_text(args[0], " ".join(args[1:])))
        return build_translate_response(args[0], translated)
    if cmd == "profile":
        bal = get_balance(uid)
        return f"Profile: {name}\nWallet: ${bal['wallet']:,}\nBank: ${bal['bank']:,}\n" + safe(build_rank_text, uid, name or "You")
    if cmd == "achievements":
        return safe(build_achievements_text, name or "You", uid)
    if cmd == "cds":
        return safe(build_cooldowns_text, uid)
    if cmd == "updateinfo":
        return safe(build_updateinfo_text)
    if cmd == "versions":
        return safe(build_version_history_text)
    if cmd == "repo":
        return "https://github.com/wellingtonosas1411wellzalpha-commits/Discord-bot"
    if cmd == "marry":
        return safe(propose_marriage, uid, wid(args[0])) if args else "Usage: .marry <number>"
    if cmd == "marryaccept":
        return safe(accept_marriage, uid)
    if cmd == "divorce":
        return safe(do_divorce, uid)
    if cmd == "partner":
        return f"Partner: {get_partner(uid) or 'Not married'}"
    return "Unknown command. Send .menu"

def load_saved_auth(here):
    try:
        from core import get_meta
        raw = get_meta("wa_auth_zip")
        if not raw:
            return
        import base64, io, zipfile
        folder = os.path.join(here, "wa_auth")
        os.makedirs(folder, exist_ok=True)
        with zipfile.ZipFile(io.BytesIO(base64.b64decode(raw))) as z:
            z.extractall(folder)
        print("WhatsApp login restored")
    except Exception as e:
        print(f"Could not restore WhatsApp login: {e}")

def save_auth(here):
    folder = os.path.join(here, "wa_auth")
    if not os.path.isdir(folder):
        return
    try:
        import base64, io, zipfile
        from core import set_meta
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as z:
            for root, dirs, files in os.walk(folder):
                for name in files:
                    path = os.path.join(root, name)
                    z.write(path, os.path.relpath(path, folder))
        set_meta("wa_auth_zip", base64.b64encode(buf.getvalue()).decode())
    except Exception as e:
        print(f"Could not save WhatsApp login: {e}")

def run():
    here = os.path.dirname(os.path.abspath(__file__))
    load_saved_auth(here)
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
                if kind in ("code", "ready"):
                    save_auth(here)
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
