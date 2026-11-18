import asyncio
import json
import os
import time
import urllib.parse
import urllib.request

API = "https://api.telegram.org/bot{token}/{method}"
REPO = "https://github.com/wellingtonosas1411wellzalpha-commits/Discord-bot"
DISCORD_ONLY = {
    "poll", "afk", "ncm", "delete", "react", "botban", "botunban", "xban",
    "xunban", "bans", "antidelete", "antibadword", "storage", "clearcache",
    "restart", "auth", "stats", "activity", "reset", "ptag", "checkall",
    "give", "take", "syncroles", "levelroles", "setlevelrole",
}

def tg(token, method, **params):
    url = API.format(token=token, method=method)
    data = urllib.parse.urlencode(params).encode()
    req = urllib.request.Request(url, data=data)
    with urllib.request.urlopen(req, timeout=40) as resp:
        return json.loads(resp.read().decode())

def clean_box(text):
    lines = []
    for line in str(text).splitlines():
        if line.endswith(" |"):
            line = line[:-2].rstrip()
        elif line.endswith("|") and line.startswith("|"):
            line = line[:-1].rstrip()
        if line.startswith("+") and line.endswith("+"):
            line = line[:-1]
        lines.append(line)
    return "\n".join(lines)

def send(token, chat_id, text):
    text = clean_box(str(text))[:4000]
    params = {"chat_id": chat_id, "text": text}
    if "```" in text:
        params["parse_mode"] = "Markdown"
    tg(token, "sendMessage", **params)

def run_async(coro):
    return asyncio.run(coro)

def menu_text():
    return """XEPHONGPT
.xephongpt <message>
.xephongpt on / off
.xephongpt wild / ai / normal

FUN
.ping
.8ball
.joke
.translate <language> <text>
.trt <language> <text>

INFO
.profile
.updateinfo
.versions

ECONOMY
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
.rob <telegram_id>
.loan <amount>
.payloan <amount>
.donate <telegram_id> <amount>

JOBS
.jobs
.setjob <job>
.myjob
.treasury

PETS
.buypet <type> <name>
.feedpet
.collectpet
.pet

MARRIAGE
.marry <telegram_id>
.marryaccept
.divorce
.partner

ACHIEVEMENTS
.achievements

MARKET
.sell <item> <qty> <price>
.market
.buylisting <id>
.cancellisting <id>

SHOP
.shop
.buy <item> [amount]
.use <item>
.inventory

GAMBLING
.cf <heads/tails> <amount>
.roll <amount>
.roulette <red/black/green> <amount>
.mines <bet>
.blackjack <bet>
.slot <amount>

UTILITY
.cds
.help
.menu
.repo
.link <code>

Discord-only: roles, bans, delete, react, ptag, poll, ncm, owner tools.
"""

def profile_text(uid, name):
    from core import (
        get_balance, get_level_data, xp_for_level, get_job, get_pet,
        get_partner, get_user_achievements, ACHIEVEMENTS, build_inventory_text,
    )
    bal = get_balance(uid)
    level = get_level_data(uid)
    needed = xp_for_level(level["level"])
    job = get_job(uid) or "None"
    pet = get_pet(uid)
    pet_line = pet[0] if isinstance(pet, (list, tuple)) and pet else (pet or "None")
    partner = get_partner(uid) or "Not married"
    earned = len(get_user_achievements(uid))
    total = len(ACHIEVEMENTS)
    return (
        f"Profile: {name}\n"
        f"Wallet: ${bal['wallet']:,}\n"
        f"Bank: ${bal['bank']:,}\n"
        f"Total: ${bal['wallet'] + bal['bank']:,}\n"
        f"Level: {level['level']}\n"
        f"XP: {level['xp']} / {needed}\n"
        f"Job: {job}\n"
        f"Pet: {pet_line}\n"
        f"Partner: {partner}\n"
        f"Achievements: {earned} / {total}\n\n"
        + build_inventory_text(name, uid)
    )

def handle(token, text, chat_id, user_id, name, replied_to_bot=False):
    from core import (
        tid, canonical_user, claim_link_code, build_balance_text, get_balance,
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
    raw_uid = tid(user_id)
    uid = canonical_user(raw_uid)
    parts = (text or "").strip().split()
    if not parts:
        return
    cmd = parts[0].lower().lstrip("./")
    args = parts[1:]

    def need(n, usage):
        if len(args) < n:
            send(token, chat_id, usage)
            return False
        return True

    if cmd in DISCORD_ONLY:
        send(token, chat_id, f".{cmd} is Discord only.")
        return
    session = get_kiragpt_session(uid)
    raw = (text or "").strip()
    if session.get("active") and replied_to_bot and not raw.startswith(".") and not raw.startswith("/"):
        reply = run_async(generate_code_response(raw, mode=session.get("mode", "normal"), history=session.get("history")))
        session.setdefault("history", []).append({"role": "user", "content": raw[:1500]})
        session["history"].append({"role": "assistant", "content": reply[:1500]})
        session["history"] = session["history"][-20:]
        send(token, chat_id, reply)
        return
    if cmd in ("start", "help", "menu"):
        send(token, chat_id, menu_text()); return
    if cmd == "link":
        if not args:
            send(token, chat_id, f"Your Telegram ID: {user_id}\nOn Discord, run .link\nThen send .link <code> here.")
            return
        linked = claim_link_code(args[0], raw_uid)
        if not linked:
            send(token, chat_id, "That code is not valid. Run .link on Discord first.")
            return
        send(token, chat_id, "Linked. Discord and Telegram now share money and stats.")
        return
    if cmd == "ping":
        send(token, chat_id, "Pong"); return
    if cmd == "xephongpt":
        session = get_kiragpt_session(uid)
        if args and args[0].lower() == "on":
            session["active"] = True
            send(token, chat_id, "XephonGPT on. Just type normally.")
            return
        if args and args[0].lower() == "off":
            session["active"] = False
            send(token, chat_id, "XephonGPT off.")
            return
        if len(args) >= 2 and args[1].lower() == "on" and args[0].lower() in ("wild", "ai", "normal"):
            session["mode"] = args[0].lower()
            send(token, chat_id, f"Mode set to {args[0].lower()}.")
            return
        prompt = " ".join(args).strip()
        if not prompt:
            send(token, chat_id, "Usage: .xephongpt <message>")
            return
        reply = run_async(generate_code_response(prompt, mode=session.get("mode", "normal"), history=session.get("history")))
        session.setdefault("history", []).append({"role": "user", "content": prompt[:1500]})
        session["history"].append({"role": "assistant", "content": reply[:1500]})
        session["history"] = session["history"][-20:]
        send(token, chat_id, reply)
        return
    if cmd == "bal":
        get_balance(uid)
        send(token, chat_id, build_balance_text(uid)); return
    if cmd == "daily":
        send(token, chat_id, do_daily(uid)); return
    if cmd == "work":
        send(token, chat_id, do_work(uid)); return
    if cmd == "fish":
        send(token, chat_id, do_fish(uid)); return
    if cmd == "beg":
        send(token, chat_id, do_beg(uid)); return
    if cmd == "dig":
        send(token, chat_id, do_dig(uid)); return
    if cmd == "lb":
        send(token, chat_id, build_leaderboard_text()); return
    if cmd == "rank":
        send(token, chat_id, build_rank_text(uid, name or "You")); return
    if cmd == "ranklb":
        send(token, chat_id, build_ranklb_text()); return
    if cmd == "withdraw":
        if need(1, "Usage: .withdraw <amount>"):
            send(token, chat_id, do_withdraw(uid, args[0]))
        return
    if cmd == "deposit":
        if need(1, "Usage: .deposit <amount>"):
            send(token, chat_id, do_deposit(uid, args[0]))
        return
    if cmd == "loan":
        if need(1, "Usage: .loan <amount>"):
            send(token, chat_id, take_loan(uid, args[0]))
        return
    if cmd == "payloan":
        if need(1, "Usage: .payloan <amount>"):
            send(token, chat_id, pay_loan(uid, args[0]))
        return
    if cmd == "donate":
        if need(2, "Usage: .donate <telegram_id> <amount>"):
            send(token, chat_id, do_donate(uid, canonical_user(tid(args[0])), args[1]))
        return
    if cmd == "rob":
        if need(1, "Usage: .rob <telegram_id>"):
            send(token, chat_id, do_rob(uid, canonical_user(tid(args[0]))))
        return
    if cmd == "jobs":
        send(token, chat_id, build_jobs_list_text()); return
    if cmd == "myjob":
        send(token, chat_id, build_myjob_text(uid)); return
    if cmd == "setjob":
        if need(1, "Usage: .setjob <job>"):
            send(token, chat_id, set_job(uid, args[0]))
        return
    if cmd == "treasury":
        send(token, chat_id, f"Treasury: ${get_treasury():,}\nBot bank: ${get_bot_bank():,}")
        return
    if cmd == "pet":
        send(token, chat_id, build_pet_text(name or "You", uid)); return
    if cmd == "buypet":
        if need(2, "Usage: .buypet <type> <name>"):
            send(token, chat_id, buy_pet(uid, args[0], " ".join(args[1:])))
        return
    if cmd == "feedpet":
        send(token, chat_id, feed_pet(uid)); return
    if cmd == "collectpet":
        send(token, chat_id, collect_pet_income(uid)); return
    if cmd == "marry":
        if need(1, "Usage: .marry <telegram_id>"):
            send(token, chat_id, propose_marriage(uid, canonical_user(tid(args[0]))))
        return
    if cmd == "marryaccept":
        send(token, chat_id, accept_marriage(uid)); return
    if cmd == "divorce":
        send(token, chat_id, do_divorce(uid)); return
    if cmd == "partner":
        send(token, chat_id, f"Partner: {get_partner(uid) or 'Not married'}"); return
    if cmd == "achievements":
        send(token, chat_id, build_achievements_text(name or "You", uid)); return
    if cmd == "shop":
        send(token, chat_id, build_shop_text(0)); return
    if cmd == "buy":
        if need(1, "Usage: .buy <item> [amount]"):
            amount = int(args[1]) if len(args) > 1 and args[1].isdigit() else 1
            send(token, chat_id, handle_buy(uid, 0, args[0], amount))
        return
    if cmd == "use":
        if need(1, "Usage: .use <item>"):
            send(token, chat_id, use_global_item(uid, args[0]))
        return
    if cmd == "inventory":
        send(token, chat_id, build_inventory_text(name or "You", uid)); return
    if cmd == "market":
        send(token, chat_id, build_market_text()); return
    if cmd == "sell":
        if need(3, "Usage: .sell <item> <qty> <price>"):
            ok, msg = create_listing(uid, args[0], args[1], args[2])
            send(token, chat_id, msg)
        return
    if cmd == "buylisting":
        if need(1, "Usage: .buylisting <id>"):
            send(token, chat_id, buy_listing(uid, args[0]))
        return
    if cmd == "cancellisting":
        if need(1, "Usage: .cancellisting <id>"):
            send(token, chat_id, cancel_listing(uid, args[0]))
        return
    if cmd == "cf":
        if need(2, "Usage: .cf <heads/tails> <amount>"):
            send(token, chat_id, run_async(run_coinflip(uid, args[0], args[1])))
        return
    if cmd == "roll":
        if need(1, "Usage: .roll <amount>"):
            send(token, chat_id, do_dice(uid, args[0]))
        return
    if cmd == "roulette":
        if need(2, "Usage: .roulette <red/black/green> <amount>"):
            box = {"text": ""}
            async def send_func(t):
                box["text"] = t
                return None
            async def edit_func(message, t):
                box["text"] = t
            run_async(run_roulette(uid, args[0], args[1], send_func, edit_func))
            send(token, chat_id, box["text"] or "Roulette failed.")
        return
    if cmd == "slot":
        if need(1, "Usage: .slot <amount>"):
            box = {"text": ""}
            async def send_func(t):
                box["text"] = t
                return None
            async def edit_func(message, t):
                box["text"] = t
            run_async(run_slot(uid, args[0], send_func, edit_func))
            send(token, chat_id, box["text"] or "Slot failed.")
        return
    if cmd == "mines":
        if not args:
            send(token, chat_id, "Usage: .mines <bet>, .mines <1-25>, or .mines cashout")
            return
        if args[0].lower() == "cashout":
            send(token, chat_id, cashout_mines(uid)); return
        if args[0].isdigit() and int(args[0]) <= 25 and len(args) == 1:
            send(token, chat_id, dig_mines(uid, args[0])); return
        send(token, chat_id, start_mines(uid, args[0], args[1] if len(args) > 1 else None))
        return
    if cmd in ("blackjack", "bj"):
        if not args:
            send(token, chat_id, "Usage: .blackjack <bet>, hit, or stand")
            return
        if args[0].lower() == "hit":
            send(token, chat_id, hit_blackjack(uid)); return
        if args[0].lower() == "stand":
            send(token, chat_id, stand_blackjack(uid)); return
        send(token, chat_id, start_blackjack(uid, args[0])); return
    if cmd == "8ball":
        send(token, chat_id, get_8ball_answer()); return
    if cmd == "joke":
        send(token, chat_id, get_joke()); return
    if cmd in ("translate", "trt"):
        if need(2, "Usage: .translate <language> <text>"):
            translated = run_async(translate_text(args[0], " ".join(args[1:])))
            send(token, chat_id, build_translate_response(args[0], translated))
        return
    if cmd == "profile":
        send(token, chat_id, profile_text(uid, name or "You")); return
    if cmd == "updateinfo":
        send(token, chat_id, build_updateinfo_text()); return
    if cmd == "versions":
        send(token, chat_id, build_version_history_text()); return
    if cmd == "cds":
        send(token, chat_id, build_cooldowns_text(uid)); return
    if cmd == "repo":
        send(token, chat_id, REPO); return
    send(token, chat_id, "Unknown command. Send .menu")

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
                    replied = msg.get("reply_to_message") or {}
                    replied_to_bot = bool((replied.get("from") or {}).get("is_bot"))
                    handle(token, text, chat["id"], user["id"], user.get("first_name") or "You", replied_to_bot)
        except Exception as e:
            print(f"Telegram door error: {e}")
            time.sleep(3)
