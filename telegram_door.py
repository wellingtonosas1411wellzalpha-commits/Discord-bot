import asyncio
import json
import os
import time
import urllib.parse
import urllib.request

API = "https://api.telegram.org/bot{token}/{method}"
REPO = "https://github.com/wellingtonosas1411wellzalpha-commits/Discord-bot"

def tg(token, method, **params):
    url = API.format(token=token, method=method)
    data = urllib.parse.urlencode(params).encode()
    req = urllib.request.Request(url, data=data)
    with urllib.request.urlopen(req, timeout=40) as resp:
        return json.loads(resp.read().decode())

def send(token, chat_id, text):
    tg(token, "sendMessage", chat_id=chat_id, text=str(text)[:4000])

def run_async(coro):
    return asyncio.run(coro)

def menu_text():
    return """Xephon on Telegram

FUN
.ping
.8ball
.joke
.translate <language> <text>

ECONOMY
.bal
.daily
.work
.lb
.withdraw <amount>
.deposit <amount>
.fish
.beg
.dig
.loan <amount>
.payloan <amount>
.donate <telegram_id> <amount>
.rob <telegram_id>

JOBS
.jobs
.setjob <job>
.myjob

PETS
.pet
.buypet <type> <name>
.feedpet
.collectpet

SHOP
.shop
.buy <item> [amount]
.use <item>
.inventory

MARKET
.market
.sell <item> <qty> <price>
.buylisting <id>
.cancellisting <id>

GAMBLING
.cf <heads/tails> <amount>
.roll <amount>
.roulette <red/black/green> <amount>
.slot <amount>
.mines <bet> [mines]
.mines <1-25>
.mines cashout
.blackjack <bet>
.blackjack hit
.blackjack stand

INFO
.updateinfo
.versions
.repo

Discord-only commands stay on Discord.
"""

def handle(token, text, chat_id, user_id, name):
    from core import (
        build_balance_text, get_balance, do_daily, do_work, do_fish, do_beg, do_dig,
        do_withdraw, do_deposit, do_donate, do_rob, take_loan, pay_loan,
        build_jobs_list_text, build_myjob_text, set_job, build_leaderboard_text,
        buy_pet, feed_pet, collect_pet_income, build_pet_text,
        build_shop_text, handle_buy, build_inventory_text, use_global_item,
        build_market_text, create_listing, buy_listing, cancel_listing,
        start_mines, dig_mines, cashout_mines,
        start_blackjack, hit_blackjack, stand_blackjack,
        run_coinflip, do_dice, run_slot, run_roulette,
        get_8ball_answer, get_joke, translate_text, build_translate_response,
        build_updateinfo_text, build_version_history_text,
    )
    uid = f"telegram:{user_id}"
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

    if cmd in ("start", "help", "menu"):
        send(token, chat_id, menu_text())
        return
    if cmd == "ping":
        send(token, chat_id, "Pong")
        return
    if cmd == "bal":
        get_balance(uid)
        send(token, chat_id, build_balance_text(uid))
        return
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
            send(token, chat_id, do_donate(uid, f"telegram:{args[0]}", args[1]))
        return
    if cmd == "rob":
        if need(1, "Usage: .rob <telegram_id>"):
            send(token, chat_id, do_rob(uid, f"telegram:{args[0]}"))
        return
    if cmd == "jobs":
        send(token, chat_id, build_jobs_list_text()); return
    if cmd == "myjob":
        send(token, chat_id, build_myjob_text(uid)); return
    if cmd == "setjob":
        if need(1, "Usage: .setjob <job>"):
            send(token, chat_id, set_job(uid, args[0]))
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
            send(token, chat_id, "Usage: .mines <bet> [mines], .mines <1-25>, or .mines cashout")
            return
        if args[0].lower() == "cashout":
            send(token, chat_id, cashout_mines(uid)); return
        if args[0].isdigit() and int(args[0]) <= 25 and len(args) == 1:
            send(token, chat_id, dig_mines(uid, args[0])); return
        send(token, chat_id, start_mines(uid, args[0], args[1] if len(args) > 1 else None))
        return
    if cmd in ("blackjack", "bj"):
        if not args:
            send(token, chat_id, "Usage: .blackjack <bet>, .blackjack hit, .blackjack stand")
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
    if cmd == "translate":
        if need(2, "Usage: .translate <language> <text>"):
            translated = run_async(translate_text(args[0], " ".join(args[1:])))
            send(token, chat_id, build_translate_response(args[0], translated))
        return
    if cmd == "updateinfo":
        send(token, chat_id, build_updateinfo_text()); return
    if cmd == "versions":
        send(token, chat_id, build_version_history_text()); return
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
                    handle(token, text, chat["id"], user["id"], user.get("first_name") or "You")
        except Exception as e:
            print(f"Telegram door error: {e}")
            time.sleep(3)
