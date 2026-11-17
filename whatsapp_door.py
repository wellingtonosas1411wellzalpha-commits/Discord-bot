import json
import os
import subprocess
import time

def send_line(proc, payload):
    try:
        proc.stdin.write(json.dumps(payload) + "\n")
        proc.stdin.flush()
    except Exception as e:
        print(f"WhatsApp send failed: {e}")

def announce_code(code):
    print(f"WHATSAPP PAIR CODE: {code}")
    try:
        import asyncio
        from core import bot
        import discord

        async def go():
            await bot.wait_until_ready()
            app = await bot.application_info()
            owner = app.owner
            text = (
                f"{owner.mention} WhatsApp pairing code: `{code}`\n"
                "On the phone: WhatsApp → Linked devices → Link with phone number → enter this code."
            )
            sent = False
            for guild in bot.guilds:
                member = guild.get_member(owner.id)
                channel = discord.utils.get(guild.text_channels, name="general") or guild.system_channel
                if channel is None:
                    continue
                try:
                    await channel.send(text, allowed_mentions=discord.AllowedMentions(users=True))
                    sent = True
                    break
                except Exception as e:
                    print(f"WhatsApp code channel send failed: {e}")
            if not sent:
                try:
                    await owner.send(f"WhatsApp pairing code: {code}")
                except Exception as e:
                    print(f"WhatsApp code DM failed: {e}")

        bot.loop.create_task(go()) if bot.loop and bot.loop.is_running() else None
        if not (bot.loop and bot.loop.is_running()):
            import threading
            def later():
                for _ in range(30):
                    if getattr(bot, "loop", None) and bot.loop.is_running():
                        asyncio.run_coroutine_threadsafe(go(), bot.loop)
                        return
                    time.sleep(2)
            threading.Thread(target=later, daemon=True).start()
        else:
            asyncio.run_coroutine_threadsafe(go(), bot.loop)
    except Exception as e:
        print(f"Could not announce WhatsApp code: {e}")

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
    phone = os.getenv("WHATSAPP_PHONE", "").strip()
    if not phone:
        print("WhatsApp door off: no WHATSAPP_PHONE")
        return
    here = os.path.dirname(os.path.abspath(__file__))
    js = os.path.join(here, "whatsapp_door.js")
    if not os.path.exists(js):
        print("WhatsApp door off: missing whatsapp_door.js")
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
                    announce_code(data.get("code"))
                elif kind == "message":
                    reply = handle_text(data.get("text", ""), data.get("from", ""), data.get("name") or "You")
                    send_line(proc, {"type": "send", "chat": data.get("chat"), "text": reply})
            proc.wait()
        except Exception as e:
            print(f"WhatsApp door error: {e}")
        time.sleep(5)
