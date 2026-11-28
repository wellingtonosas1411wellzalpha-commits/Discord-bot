import asyncio
import json
import os
from pathlib import Path
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
    "give", "take", "syncroles", "levelroles", "setlevelrole", "pair",
    "avatar", "userinfo", "authdiscord", "checkalldiscord",
}

def run_async(coro):
    return asyncio.run(coro)

def menu_text():
    return """╭━━━〔 ✦ XEPHON ✦ 〕━━━╮
┃  🌌  Xephon AI Hub
┃  🧑‍💻  Developed by Kira
┃  🏷️  WhatsApp door
╰━━━━━━━━━━━━━━━━━━╯

╭〔 🎮 FUN 〕╮
┃ ➤ .ping
┃ ➤ .8ball
┃ ➤ .joke
┃ ➤ .translate <language> <text>
╰──────────╯

╭〔 🤖 XEPHONGPT 〕╮
┃ ➤ .xgpt on / off
┃ ➤ .xgpt wild / ai / normal
┃ ➤ .xgpt <message>
╰──────────────╯

╭〔 💰 ECONOMY 〕╮
┃ ➤ .bal
┃ ➤ .daily
┃ ➤ .work
┃ ➤ .lb
┃ ➤ .withdraw <amount>
┃ ➤ .deposit <amount>
┃ ➤ .fish
┃ ➤ .beg
┃ ➤ .dig
┃ ➤ .rob <number>
┃ ➤ .loan <amount>
┃ ➤ .payloan <amount>
┃ ➤ .donate <number> <amount>
╰─────────────╯

╭〔 💼 JOBS 〕╮
┃ ➤ .jobs
┃ ➤ .setjob <job>
┃ ➤ .myjob
┃ ➤ .treasury
╰──────────╯

╭〔 🐾 PETS 〕╮
┃ ➤ .pet
┃ ➤ .buypet <type> <name>
┃ ➤ .feedpet
┃ ➤ .collectpet
╰──────────╯

╭〔 🛒 SHOP 〕╮
┃ ➤ .shop
┃ ➤ .buy <item> [amount]
┃ ➤ .use <item>
┃ ➤ .inventory
╰──────────╯

╭〔 📈 MARKET 〕╮
┃ ➤ .market
┃ ➤ .sell <item> <qty> <price>
┃ ➤ .buylisting <id>
┃ ➤ .cancellisting <id>
╰────────────╯

╭〔 🎰 GAMBLING 〕╮
┃ ➤ .cf <heads/tails> <amount>
┃ ➤ .roll <amount>
┃ ➤ .roulette <red/black/green> <amount>
┃ ➤ .slot <amount>
┃ ➤ .mines <bet>
┃ ➤ .blackjack <bet>
╰──────────────╯

╭〔 📊 INFO 〕╮
┃ ➤ .profile
┃ ➤ .rank
┃ ➤ .ranklb
┃ ➤ .achievements
┃ ➤ .cds
┃ ➤ .updateinfo
┃ ➤ .versions
┃ ➤ .repo
╰──────────╯

╭〔 🛠️ UTILITY 〕╮
┃ ➤ .link <code>
┃ ➤ .afk [reason]
┃ ➤ .delete
┃ ➤ .react <emoji>
┃ ➤ .poll question | option | option
┃ ➤ .tag <message>
┃ ➤ .ncm on / off
┃ ➤ .marry @person
┃ ➤ .marryaccept
┃ ➤ .divorce
┃ ➤ .partner
╰─────────────╯

╭〔 🛡️ ADMIN 〕╮
┃ ➤ .botban <number>
┃ ➤ .botunban <number>
┃ ➤ .xban <number> <category>
┃ ➤ .xunban <number> <category>
┃ ➤ .bans
┃ ➤ .storage
┃ ➤ .clearcache
┃ ➤ .restart
┃ ➤ .activity
┃ ➤ .auth on / off
┃ ➤ .antidelete on / off
┃ ➤ .antibadword on / off
┃ ➤ .checkall
┃ ➤ .reset
╰───────────╯

Role commands stay on Discord.
"""


AUTH_DIR = Path("wa_auth")

def restore_whatsapp_auth():
    from core import get_meta
    raw = get_meta("wa_auth_files")
    if not raw:
        return
    try:
        files = json.loads(raw)
    except Exception:
        return
    AUTH_DIR.mkdir(exist_ok=True)
    for name, content in files.items():
        (AUTH_DIR / name).write_bytes(base64.b64decode(content))

def save_whatsapp_auth():
    import base64
    from core import set_meta
    if not AUTH_DIR.exists():
        return
    files = {}
    for path in AUTH_DIR.iterdir():
        if path.is_file():
            files[path.name] = base64.b64encode(path.read_bytes()).decode()
    if files:
        set_meta("wa_auth_files", json.dumps(files))

def safe(fn, *args):
    try:
        return fn(*args)
    except Exception as e:
        return f"Command failed: {e.__class__.__name__}: {e}"

def handle_text(text, phone, name, meta=None):
    from core import (
        wid, canonical_user, claim_link_code, build_balance_text, get_balance, active_mines_games,
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
        get_kiragpt_session, set_afk, do_reset, build_storage_text,
        bot_bans, x_bans, save_bans, BAN_CATEGORIES,
    )
    raw_uid = wid(phone)
    uid = canonical_user(raw_uid)
    raw = (text or "").strip()
    parts = raw.split()
    chat = (meta or {}).get("chat") or ""

    def tagged(meta, args):
        nums = []
        for item in (meta or {}).get("mentions") or []:
            if isinstance(item, dict):
                for key in ("phone", "id"):
                    digits = "".join(ch for ch in str(item.get(key) or "") if ch.isdigit())
                    if digits:
                        nums.append(digits)
            else:
                digits = "".join(ch for ch in str(item) if ch.isdigit())
                if digits:
                    nums.append(digits)
        for part in args:
            digits = "".join(ch for ch in str(part) if ch.isdigit())
            if digits and len(digits) >= 8:
                nums.append(digits)
        return list(dict.fromkeys(nums))
    if not parts:
        return "Send .menu"
    cmd = parts[0].lower().lstrip("./")
    args = parts[1:]

    from core import get_meta, set_meta, ncm_enabled, parse_ncm_request, is_wa_owner, has_beginner_role, load_links, clean_wa
    if cmd not in ("link", "ping") and not is_wa_owner(phone):
        linked = load_links().get(raw_uid)
        allowed = bool(linked) and run_async(has_beginner_role(linked))
        if not allowed:
            return "Link this WhatsApp to a Discord account with the Beginner role first. Run .link on Discord, then .link <code> here."
    owner_cmds = {"xgpt", "xephongpt", "ncm", "botban", "xban", "unbotban", "unxban", "storage", "clearcache", "reset", "update", "restart", "auth", "antidelete", "antibadword", "mute", "unmute", "antilink"}
    sender_ids = [phone, (meta or {}).get("phone"), (meta or {}).get("lid"), (meta or {}).get("from")]
    if cmd in owner_cmds and not is_wa_owner(phone, load_links().get(raw_uid, ""), sender_ids):
        shown = clean_wa((meta or {}).get("lid") or (meta or {}).get("phone") or phone)
        return f"Owner only. Your WhatsApp ID is {shown}. On Discord, run .waowner {shown}"
    if not raw.startswith(".") and not raw.startswith("/"):
        words = {part.strip(".,!?").lower() for part in raw.split()}
        if get_meta("wa_gpt_on") == "on" and (words.intersection({"z", "x", "xephon"}) or (meta or {}).get("replyToBot")):
            if not is_wa_owner(phone):
                linked = load_links().get(raw_uid)
                if not (linked and run_async(has_beginner_role(linked))):
                    return "Link this WhatsApp to a Discord account with the Beginner role first."
            mode = get_meta("wa_gpt_mode") or "normal"
            history = json.loads(get_meta("wa_gpt_history") or "[]")
            try:
                reply = run_async(generate_code_response(raw, mode=mode, history=history))
                history.append({"role": "user", "content": raw[:1200]})
                history.append({"role": "assistant", "content": reply[:1200]})
                set_meta("wa_gpt_history", json.dumps(history[-20:]))
                return reply
            except Exception as e:
                return f"XephonGPT failed: {e}"
        if ncm_enabled.get(uid):
            pending = json.loads(get_meta(f"ncm_pending:{uid}") or "{}")
            if pending and raw.lower() in ("yes", "y", "confirm"):
                set_meta(f"ncm_pending:{uid}", "{}")
                if pending.get("action") == "remove":
                    return {"type": "group_remove", "chat": chat, "phone": pending.get("phone"), "text": f"Removed {pending.get('phone')}."}
                if pending.get("action") == "add":
                    return {"type": "group_add", "chat": chat, "phone": pending.get("phone"), "text": f"Added {pending.get('phone')}."}
            cleaned = raw.lower()
            for lead in ("x ", "z ", "xephon "):
                if cleaned.startswith(lead):
                    cleaned = cleaned[len(lead):]
            if cleaned.startswith("remove "):
                nums = tagged(meta, cleaned.split())
                if nums:
                    set_meta(f"ncm_pending:{uid}", json.dumps({"action": "remove", "phone": nums[0]}))
                    return f"Remove {nums[0]} from this group? Reply yes."
            if cleaned.startswith("add "):
                nums = tagged(meta, cleaned.split())
                if nums:
                    set_meta(f"ncm_pending:{uid}", json.dumps({"action": "add", "phone": nums[0]}))
                    return f"Add {nums[0]} to this group? Reply yes."
            matched, ncm_args = run_async(parse_ncm_request(raw))
            if matched:
                raw = f".{matched} {ncm_args}".strip()
                parts = raw.split()
                cmd = parts[0].lower().lstrip("./")
                args = parts[1:]

    if cmd in ROLE_ONLY:
        return f".{cmd} needs Discord roles, so it stays on Discord."
    if cmd in ("start", "help", "menu"):
        return {
            "type": "image",
            "file": os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "banner.png"),
            "text": menu_text(),
        }
    if cmd == "link":
        if not args:
            return f"Your WhatsApp number: {phone}\nOn Discord, run .link\nThen send .link <code> here."
        linked = claim_link_code(args[0], raw_uid)
        return "Linked. Discord and WhatsApp now share money and stats." if linked else "That code is not valid. Run .link on Discord first."
    if cmd == "ping":
        return "Pong"
    if cmd in ("xgpt", "xephongpt"):
        if args and args[0].lower() == "on":
            set_meta("wa_gpt_on", "on")
            return "XGPT is on for everyone. Type Z, X, or Xephon to talk."
        if args and args[0].lower() == "off":
            set_meta("wa_gpt_on", "off")
            set_meta("wa_gpt_history", "[]")
            return "XGPT is off."
        if args and args[0].lower() in ("wild", "normal", "mode"):
            set_meta("wa_gpt_mode", args[0].lower())
            return f"Mode set to {args[0].lower()}."
        prompt = " ".join(args).strip()
        if not prompt:
            return "Usage: .xgpt <message>"
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
    if cmd in ("mines", "mine"):
        if not args:
            return "Usage: .mines <bet> [mines], .mines <1-25>, or .mines cashout"
        if args[0].lower() == "cashout":
            return safe(cashout_mines, uid)
        if uid in active_mines_games:
            if len(args) != 1:
                return "Type .mines <1-25> to dig or .mines cashout"
            return safe(dig_mines, uid, args[0])
        bet_str, mines_str = args[0], args[1] if len(args) > 1 else None
        if mines_str and bet_str.isdigit() and mines_str.isdigit():
            first, second = int(bet_str), int(mines_str)
            if 1 <= first <= 24 and second > 24:
                bet_str, mines_str = mines_str, bet_str
        return safe(start_mines, uid, bet_str, mines_str)
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
        from core import build_updateinfo_plain
        return build_updateinfo_plain()
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
    if cmd == "afk":
        reason = " ".join(args) or "busy"
        set_afk(uid, reason)
        return f"You are now afk, reason: {reason}"
    if cmd == "botban":
        if not args:
            return "Usage: .botban <number>"
        bot_bans.add(wid(args[0]))
        save_bans()
        return "Bot banned."
    if cmd == "botunban":
        if not args:
            return "Usage: .botunban <number>"
        bot_bans.discard(wid(args[0]))
        save_bans()
        return "Bot unbanned."
    if cmd == "xban":
        if len(args) < 2:
            return "Usage: .xban <number> <category>"
        category = args[1].lower()
        if category not in BAN_CATEGORIES:
            return "Category must be one of: " + ", ".join(sorted(BAN_CATEGORIES))
        x_bans.setdefault(wid(args[0]), set()).add(category)
        save_bans()
        return f"Banned from {category}."
    if cmd == "xunban":
        if len(args) < 2:
            return "Usage: .xunban <number> <category>"
        x_bans.get(wid(args[0]), set()).discard(args[1].lower())
        save_bans()
        return "Category unbanned."
    if cmd == "bans":
        return f"Bot bans: {len(bot_bans)}\nCategory bans: {len(x_bans)}"
    if cmd == "storage":
        return safe(build_storage_text)
    if cmd == "reset":
        return safe(do_reset, uid, False)
    info = meta or {}
    if cmd == "delete":
        if not info.get("quoted"):
            return "Reply to the message you want to delete."
        quoted_sender = info.get("quotedParticipant") or info.get("participant")
        return [
            {"type": "delete", "chat": info.get("chat"), "msgId": info.get("quoted"), "participant": quoted_sender},
            {"type": "delete", "chat": info.get("chat"), "msgId": info.get("msgId"), "participant": info.get("participant")},
        ]
    if cmd == "react":
        if not info.get("quoted"):
            return "Reply to the message you want to react to."
        custom = [part for part in args if not part.isdigit()]
        count = next((int(part) for part in args if part.isdigit()), 100)
        emoji = custom[-1] if custom else "👍"
        if count > 1 and not custom:
            burst = " ".join((["👍", "😂", "🔥", "❤️", "🎉", "👀", "💯", "😎"] * ((count // 8) + 1))[:min(count, 500)])
            return {"type": "send", "chat": info.get("chat"), "text": burst}
        note = "Reacted."
        if len(custom) > 1 or count > 1:
            note = "WhatsApp keeps one real reaction. Extra ones are sent as a fake burst."
            extra = " ".join((custom or ["👍"]) * min(count, 100))
            return [
                {"type": "react", "chat": info.get("chat"), "msgId": info.get("quoted"), "participant": info.get("participant"), "emoji": emoji, "text": ""},
                {"type": "send", "chat": info.get("chat"), "text": extra},
            ]
        return {"type": "react", "chat": info.get("chat"), "msgId": info.get("quoted"), "participant": info.get("participant"), "emoji": emoji, "text": note}
    if cmd == "poll":
        body = " ".join(args)
        bits = [part.strip() for part in body.split("|") if part.strip()]
        if len(bits) < 3:
            return "Usage: .poll question | option | option"
        return {"type": "poll", "chat": info.get("chat"), "question": bits[0], "options": bits[1:], "text": "Poll sent."}
    if cmd in ("tag", "ptag"):
        if not info.get("isGroup"):
            return "Use .tag in a WhatsApp group."
        return {"type": "ptag", "chat": info.get("chat"), "text": " ".join(args) or "Hey"}

    if cmd == "auth":
        state = (args[0].lower() if args else "")
        if state not in ("on", "off"):
            current = "on" if get_meta(f"auth:{chat}") != "off" else "off"
            return f"Auth is {current}. Use .auth on or .auth off."
        set_meta(f"auth:{chat}", state)
        return f"Bot responses turned {state} for this chat."
    if cmd == "activity":
        from core import build_activity_text
        return build_activity_text()
    if cmd == "storage":
        return build_storage_text()
    if cmd == "clearcache":
        from core import do_clearcache
        return do_clearcache()
    if cmd == "antidelete":
        state = (args[0].lower() if args else "")
        if state not in ("on", "off"):
            current = "on" if get_meta(f"antidelete:{chat}") == "on" else "off"
            return f"Antidelete is {current}."
        set_meta(f"antidelete:{chat}", state)
        return f"Antidelete is {state}."
    if cmd == "antibadword":
        key = f"abw:{chat}"
        data = json.loads(get_meta(key) or '{"on": false, "words": []}')
        action = (args[0].lower() if args else "list")
        if action in ("on", "off"):
            data["on"] = action == "on"
            set_meta(key, json.dumps(data))
            return f"Antibadword is {action}."
        if action == "add" and len(args) > 1:
            word = " ".join(args[1:]).lower()
            data.setdefault("words", [])
            if word not in data["words"]:
                data["words"].append(word)
            set_meta(key, json.dumps(data))
            return f"Added bad word: {word}"
        if action == "remove" and len(args) > 1:
            word = " ".join(args[1:]).lower()
            data["words"] = [w for w in data.get("words", []) if w != word]
            set_meta(key, json.dumps(data))
            return f"Removed bad word: {word}"
        words = ", ".join(data.get("words") or []) or "none"
        return f"Antibadword is {'on' if data.get('on') else 'off'}. Words: {words}"
    if cmd == "ncm":
        from core import set_ncm
        state = (args[0].lower() if args else "")
        if state not in ("on", "off"):
            return "Use .ncm on or .ncm off."
        set_ncm(uid, state == "on")
        return f"No Command Mode is {state}."
    if cmd == "checkall":
        names = ["ping", "menu", "bal", "shop", "jobs", "pet", "market", "versions", "storage", "activity"]
        return "Checkall ready.\n" + "\n".join(f".{name} is registered" for name in names)
    if cmd == "restart":
        from core import trigger_render_deploy
        ok, msg = trigger_render_deploy()
        return "Xephon is going offline to apply the latest commit." if ok else f"Could not restart.\n{msg}"
    if cmd == "marry":
        nums = tagged(meta, args)
        if not nums:
            return "Tag the person. Example: .marry @number"
        return propose_marriage(uid, wid(nums[0]))
    if cmd == "marryaccept":
        from core import accept_marriage
        return accept_marriage(uid)
    if cmd == "divorce":
        return do_divorce(uid)
    if cmd == "partner":
        nums = tagged(meta, args)
        target = wid(nums[0]) if nums else uid
        partner_id = get_partner(target)
        if not partner_id:
            return "Not married."
        return f"Married to {partner_id}."

    if chat:
        data = json.loads(get_meta(f"abw:{chat}") or '{"on": false, "words": []}')
        if data.get("on"):
            lowered = raw.lower()
            hit = next((word for word in data.get("words", []) if word and word in lowered), None)
            if hit:
                return {"type": "delete", "chat": chat, "msgId": (meta or {}).get("msgId"), "participant": (meta or {}).get("participant"), "text": f"Removed a blocked word."}

    
    if cmd == "mute":
        ids_to_add = set(tagged(meta, args))
        if not ids_to_add:
            return "Tag the person. Example: .mute @number"
        key = f"mute:{chat}"
        ids = set(json.loads(get_meta(key) or "[]"))
        ids.update(ids_to_add)
        set_meta(key, json.dumps(sorted(ids)))
        shown = next((item for item in ids_to_add if item.startswith("234") and len(item) <= 15), "")
        return f"Muted {shown or 'that person'}."
    if cmd == "unmute":
        ids_to_remove = set(tagged(meta, args))
        key = f"mute:{chat}"
        ids = set(json.loads(get_meta(key) or "[]"))
        if not ids_to_remove:
            set_meta(key, "[]")
            return "Unmuted everyone in this chat."
        ids -= ids_to_remove
        set_meta(key, json.dumps(sorted(ids)))
        return f"Unmuted {next(iter(ids_to_remove))}."
    if cmd == "antilink":
        state = (args[0].lower() if args else "")
        if state not in ("on", "off"):
            current = "on" if get_meta(f"antilink:{chat}") == "on" else "off"
            return f"Antilink is {current}."
        set_meta(f"antilink:{chat}", state)
        return f"Antilink is {state}."
    if cmd == "purge":
        return {"type": "purge", "chat": chat, "count": 10}
    if cmd == "clear":
        return {"type": "clear", "chat": chat, "count": 10}
    if cmd == "update":
        set_meta("wa_update_chat", chat)
        save_whatsapp_auth()
        from core import trigger_render_deploy
        ok, msg = trigger_render_deploy()
        if not ok:
            return f"Could not update.\n{msg}"
        return "Updating ⚡ Xephon is shutting down. The new build is coming online."

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
    os.makedirs(os.path.join(here, "wa_auth"), exist_ok=True)
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
                if kind in ("code", "ready", "creds"):
                    save_auth(here)
                if kind == "ready":
                    from core import get_meta, set_meta, build_updateinfo_text
                    chat = get_meta("wa_update_chat")
                    if chat:
                        set_meta("wa_update_chat", "")
                        send_line(proc, {"type": "send", "chat": chat, "text": build_updateinfo_text()})
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
                elif kind == "deleted":
                    from core import get_meta
                    chat = data.get("chat") or ""
                    if get_meta(f"antidelete:{chat}") == "on":
                        who = data.get("name") or data.get("from") or "Someone"
                        text = data.get("text") or ""
                        send_line(proc, {"type": "send", "chat": chat, "text": f"@{data.get('from','')} tried to delete: {text}"})
                    continue
                elif kind == "message":
                    try:
                        raw_text = (data.get("text") or "").strip()
                        from core import canonical_user, get_meta, ncm_enabled, wid, clean_wa
                        chat = data.get("chat") or ""
                        sender_ids = {
                            clean_wa(data.get("from")),
                            clean_wa(data.get("phone")),
                            clean_wa(data.get("lid")),
                        }
                        sender_ids.discard("")
                        muted = set(json.loads(get_meta(f"mute:{chat}") or "[]"))
                        if sender_ids & muted:
                            send_line(proc, {"type": "delete", "chat": chat, "msgId": data.get("msgId"), "participant": data.get("participant")})
                            continue
                        text_lower = raw_text.lower()
                        link_bits = ("http://", "https://", "www.", "wa.me", "chat.whatsapp.com", "t.me/", "discord.gg", "bit.ly", "youtu", ".com", ".ng", ".app", ".net", ".org")
                        if get_meta(f"antilink:{chat}") == "on" and any(bit in text_lower for bit in link_bits):
                            send_line(proc, {"type": "delete", "chat": chat, "msgId": data.get("msgId"), "participant": data.get("participant")})
                            continue
                        bad = json.loads(get_meta(f"abw:{chat}") or '{"on": false, "words": []}')
                        if bad.get("on") and any(word and word in text_lower for word in bad.get("words", [])):
                            send_line(proc, {"type": "delete", "chat": chat, "msgId": data.get("msgId"), "participant": data.get("participant")})
                            continue
                        is_command = raw_text.startswith(".") or raw_text.startswith("/")
                        if not is_command:
                            uid = canonical_user(wid(data.get("from", "")))
                            words = {part.strip(".,!?").lower() for part in raw_text.split()}
                            gpt_open = get_meta("wa_gpt_on") == "on" and bool(words.intersection({"z", "x", "xephon"}) or data.get("replyToBot"))
                            if not gpt_open and not ncm_enabled.get(uid):
                                continue
                        reply = handle_text(
                            raw_text,
                            data.get("from", ""),
                            data.get("name") or "You",
                            data,
                        )
                    except Exception as e:
                        reply = f"Command failed: {e.__class__.__name__}: {e}"
                    replies = reply if isinstance(reply, list) else [reply]
                    for item in replies:
                        if isinstance(item, dict):
                            item.setdefault("chat", data.get("chat"))
                            send_line(proc, item)
                            if item.get("text") and item.get("type") not in ("ptag", "send", "react", "delete", "poll", "image", "clear", "purge"):
                                send_line(proc, {
                                    "type": "send",
                                    "chat": data.get("chat"),
                                    "text": item.get("text"),
                                    "msgId": data.get("msgId"),
                                    "participant": data.get("participant"),
                                    "quote": raw_text[:120],
                                })
                        else:
                            send_line(proc, {
                                "type": "send",
                                "chat": data.get("chat"),
                                "text": item,
                                "msgId": data.get("msgId"),
                                "participant": data.get("participant"),
                                "quote": raw_text[:120],
                            })
            code = proc.wait()
            LAST_ERROR["text"] = f"WhatsApp door stopped ({code})"
        except Exception as e:
            LAST_ERROR["text"] = str(e)
            print(f"WhatsApp door error: {e}")
        time.sleep(10)
