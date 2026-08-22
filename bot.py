import os
import random
import asyncio
import threading
import time
import math
import gc
import psutil
import psycopg2
import psycopg2.pool
import groq
from flask import Flask

import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")


def did(discord_id) -> str:
    """Namespaced key for a Discord user's balance."""
    return f"discord:{discord_id}"

BOT_START_TIME = time.time()
BOT_VERSION = "1.5.9"
psutil.cpu_percent(interval=None)  # prime the reading

intents = discord.Intents.default()
intents.message_content = True


class AuthCheckedTree(app_commands.CommandTree):
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.command:
            try:
                log_command_usage(did(interaction.user.id), interaction.command.name, "discord")
            except Exception as e:
                print(f"log_command_usage failed: {e}")
        if interaction.command and interaction.command.name == "auth":
            return True
        if interaction.guild is None:
            return True
        if await interaction.client.is_owner(interaction.user):
            return True
        if not auth_enabled.get(interaction.guild.id, True):
            await interaction.response.send_message(
                "🔒 The bot is currently disabled in this server. An admin can turn it back on with `/auth on`.",
                ephemeral=True,
            )
            return False
        return True


bot = commands.Bot(
    command_prefix=".",
    intents=intents,
    tree_cls=AuthCheckedTree,
    allowed_mentions=discord.AllowedMentions(replied_user=False),
)


@bot.check
async def global_auth_check(ctx: commands.Context) -> bool:
    if ctx.command:
        try:
            log_command_usage(did(ctx.author.id), ctx.command.name, "discord")
        except Exception as e:
            print(f"log_command_usage failed: {e}")
    if ctx.command and ctx.command.name == "auth":
        return True
    if ctx.guild is None:
        return True
    if await bot.is_owner(ctx.author):
        return True
    return auth_enabled.get(ctx.guild.id, True)


@bot.event
async def on_command_error(ctx: commands.Context, error: commands.CommandError):
    if isinstance(error, commands.NotOwner):
        await ctx.reply("❌ Only the bot owner can use this command.", mention_author=False)
        return
    if isinstance(error, commands.CheckFailure):
        await ctx.reply(
            "🔒 The bot is currently disabled in this server. An admin can turn it back on with `.auth on`.",
            mention_author=False,
        )
        return
    raise error

afk_users = {}  # user_id -> reason
kiragpt_sessions = {}  # user_id -> {"active": bool, "history": list}

active_mines_games = {}  # user_id -> game state
MINES_HOUSE_EDGE = 0.97

cf_cooldowns = {}  # user_id -> last used timestamp
roulette_cooldowns = {}  # user_id -> last used timestamp
fish_cooldowns = {}
beg_cooldowns = {}
dig_cooldowns = {}
slot_cooldowns = {}
dice_cooldowns = {}
daily_cooldowns = {}
work_cooldowns = {}

CF_COOLDOWN_SECONDS = 60
ROULETTE_COOLDOWN_SECONDS = 180
FISH_COOLDOWN_SECONDS = 60
BEG_COOLDOWN_SECONDS = 60
DIG_COOLDOWN_SECONDS = 60
SLOT_COOLDOWN_SECONDS = 60
DICE_COOLDOWN_SECONDS = 60
DAILY_COOLDOWN_SECONDS = 86400
WORK_COOLDOWN_SECONDS = 3600


def check_cooldown(cooldowns: dict, user_id: int, seconds: int):
    now = time.time()
    last = cooldowns.get(user_id)
    if last is not None and (now - last) < seconds:
        return seconds - (now - last)
    cooldowns[user_id] = now
    return None


def get_remaining_cooldown(cooldowns: dict, user_id: int, seconds: int):
    """Read-only check, does not start/reset the cooldown."""
    last = cooldowns.get(user_id)
    if last is None:
        return None
    elapsed = time.time() - last
    if elapsed < seconds:
        return seconds - elapsed
    return None


auth_enabled = {}  # guild_id -> bool (default True = enabled)

DEFAULT_WALLET = 50000
DEFAULT_BANK = 50000
DEFAULT_LIMIT = 50000

DATABASE_URL = os.getenv("DATABASE_URL")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
groq_client = groq.Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None


db_pool = psycopg2.pool.SimpleConnectionPool(1, 10, DATABASE_URL) if DATABASE_URL else None


def get_db():
    """Grab a connection from the pool instead of opening a new one every call."""
    conn = db_pool.getconn()
    cur = conn.cursor()
    return conn, cur


def release_db(conn):
    """Return a connection to the pool. Always call this instead of conn.close()."""
    db_pool.putconn(conn)


def init_db():
    """One-time table creation at startup, so hot-path functions don't re-run
    CREATE TABLE IF NOT EXISTS on every single call."""
    conn = db_pool.getconn()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS balances (
            user_id TEXT PRIMARY KEY,
            wallet BIGINT NOT NULL,
            bank BIGINT NOT NULL,
            limit_amt BIGINT NOT NULL
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS account_links (
            alias_id TEXT PRIMARY KEY,
            canonical_id TEXT NOT NULL
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS command_log (
            id SERIAL PRIMARY KEY,
            user_id TEXT NOT NULL,
            platform TEXT NOT NULL,
            command TEXT NOT NULL,
            created_at TIMESTAMPTZ DEFAULT NOW()
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS bot_meta (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    """)
    conn.commit()
    cur.close()
    db_pool.putconn(conn)


def migrate_db():
    """One-time migration: convert an existing bigint user_id column to text
    so account data stays consistent."""
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS balances (
                user_id TEXT PRIMARY KEY,
                wallet BIGINT NOT NULL,
                bank BIGINT NOT NULL,
                limit_amt BIGINT NOT NULL
            )
        """)
        conn.commit()
        try:
            cur.execute("ALTER TABLE balances ALTER COLUMN user_id TYPE TEXT USING user_id::TEXT")
            conn.commit()
        except Exception:
            conn.rollback()
        try:
            cur.execute("""
                UPDATE balances SET user_id = 'discord:' || user_id
                WHERE user_id !~ '^(discord|whatsapp):'
            """)
            conn.commit()
        except Exception:
            conn.rollback()
        cur.close()
        conn.close()
        print("Database migration check complete.")
    except Exception as e:
        print(f"Database migration skipped/failed: {e}")


def resolve_uid(user_id: str) -> str:
    """If this ID has been linked to another account, return the canonical ID
    for account linking support."""
    conn, cur = get_db()
    cur.execute("SELECT canonical_id FROM account_links WHERE alias_id = %s", (user_id,))
    row = cur.fetchone()
    cur.close()
    release_db(conn)
    return row[0] if row else user_id


def link_accounts(alias_id: str, canonical_id: str):
    conn, cur = get_db()
    cur.execute(
        "INSERT INTO account_links (alias_id, canonical_id) VALUES (%s, %s) "
        "ON CONFLICT (alias_id) DO UPDATE SET canonical_id = EXCLUDED.canonical_id",
        (alias_id, canonical_id),
    )
    conn.commit()
    cur.close()
    release_db(conn)


def unlink_account(alias_id: str):
    conn, cur = get_db()
    cur.execute("DELETE FROM account_links WHERE alias_id = %s", (alias_id,))
    conn.commit()
    cur.close()
    release_db(conn)


def get_balance(user_id: int):
    user_id = resolve_uid(user_id)
    conn, cur = get_db()
    cur.execute("SELECT wallet, bank FROM balances WHERE user_id = %s", (user_id,))
    row = cur.fetchone()
    if row is None:
        cur.execute(
            "INSERT INTO balances (user_id, wallet, bank, limit_amt) VALUES (%s, %s, %s, %s)",
            (user_id, DEFAULT_WALLET, DEFAULT_BANK, 0),
        )
        conn.commit()
        wallet, bank = DEFAULT_WALLET, DEFAULT_BANK
    else:
        wallet, bank = row
    cur.close()
    release_db(conn)
    return {"wallet": wallet, "bank": bank}


def update_balance(user_id: int, wallet=None, bank=None):
    user_id = resolve_uid(user_id)
    bal = get_balance(user_id)  # ensures row exists
    new_wallet = bal["wallet"] if wallet is None else wallet
    new_bank = bal["bank"] if bank is None else bank
    conn, cur = get_db()
    cur.execute(
        "UPDATE balances SET wallet = %s, bank = %s WHERE user_id = %s",
        (new_wallet, new_bank, user_id),
    )
    conn.commit()
    cur.close()
    release_db(conn)


def get_user_count():
    conn, cur = get_db()
    cur.execute("SELECT COUNT(DISTINCT user_id) FROM command_log WHERE platform = 'discord'")
    discord_count = cur.fetchone()[0]
    cur.close()
    release_db(conn)
    return discord_count


def log_command_usage(user_id: str, command: str, platform: str):
    """Records which command was used and by whom — never the message's
    actual content, to keep people's conversations with the bot private."""
    conn, cur = get_db()
    cur.execute(
        "INSERT INTO command_log (user_id, platform, command) VALUES (%s, %s, %s)",
        (user_id, platform, command),
    )
    conn.commit()
    cur.close()
    release_db(conn)


def get_recent_activity(limit: int = 20):
    conn, cur = get_db()
    cur.execute(
        "SELECT user_id, platform, command, created_at FROM command_log "
        "ORDER BY created_at DESC LIMIT %s",
        (limit,),
    )
    rows = cur.fetchall()
    cur.close()
    release_db(conn)
    return rows


def build_activity_text():
    rows = get_recent_activity()
    if not rows:
        return "📭 No activity logged yet."
    lines = []
    for user_id, platform, command, ts in rows:
        icon = "💬" if platform == "discord" else "🟢"
        short_id = user_id.split(":", 1)[-1]
        lines.append(f"┃ {ts.strftime('%b %d %H:%M')} {icon} {short_id[:12]} → {command}")
    return (
        "╭━━━〔 🕘 ʀᴇᴄᴇɴᴛ ᴀᴄᴛɪᴠɪᴛʏ 〕━━━⬣\n"
        + "\n".join(lines)
        + "\n╰━━━━━━━━━━━━━━━━━━━━━━⬣"
    )


def build_stats_text():
    discord_count = get_user_count()
    return (
        "╭━━━〔 📊 ʙᴏᴛ sᴛᴀᴛs 〕━━━⬣\n"
        f"┃ 👥 Total users : {discord_count:,}\n"
        "╰━━━━━━━━━━━━━━━━━━━━━━⬣"
    )


def get_meta(key: str):
    conn, cur = get_db()
    cur.execute("SELECT value FROM bot_meta WHERE key = %s", (key,))
    row = cur.fetchone()
    cur.close()
    release_db(conn)
    return row[0] if row else None


def set_meta(key: str, value: str):
    conn, cur = get_db()
    cur.execute(
        "INSERT INTO bot_meta (key, value) VALUES (%s, %s) "
        "ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value",
        (key, value),
    )
    conn.commit()
    cur.close()
    release_db(conn)


def build_balance_text(user_id: int):
    bal = get_balance(user_id)
    total = bal["wallet"] + bal["bank"]
    return (
        "╭━━━〔 💳 ᴀᴄᴄᴏᴜɴᴛ ʙᴀʟᴀɴᴄᴇ 〕━━━⬣\n"
        f"┃ 💰 ᴡᴀʟʟᴇᴛ : [ ${bal['wallet']:,} ]\n"
        f"┃ 🏦 ʙᴀɴᴋ   : [ ${bal['bank']:,} ]\n"
        "┃\n"
        f"┃ 💠 ᴛᴏᴛᴀʟ  : [ ${total:,} ]\n"
        "╰━━━━━━━━━━━━━━━━━━━━━━⬣"
    )


def do_withdraw(user_id: int, amount_str: str):
    bal = get_balance(user_id)
    try:
        amount = parse_amount(amount_str, all_value=bal["bank"])
    except ValueError:
        return "❌ Invalid amount."
    if amount <= 0:
        return "❌ Enter an amount greater than $0."
    if amount > bal["bank"]:
        return "❌ You don't have that much in your bank."
    update_balance(user_id, wallet=bal["wallet"] + amount, bank=bal["bank"] - amount)
    new_bal = get_balance(user_id)
    return (
        "╭━━━〔 🏦 ᴡɪᴛʜᴅʀᴀᴡᴀʟ 〕━━━⬣\n"
        "┃\n"
        "┃ ✅ sᴜᴄᴄᴇssғᴜʟʟʏ ᴡɪᴛʜᴅʀᴇᴡ:\n"
        f"┃ 💵 [ ${amount:,} ]\n"
        "┃\n"
        f"┃ 🏦 ʙᴀɴᴋ   : [ ${new_bal['bank']:,} ]\n"
        f"┃ 🟡 ᴡᴀʟʟᴇᴛ : [ ${new_bal['wallet']:,} ]\n"
        "┃\n"
        "╰━━━━━━━━━━━━━━━━━━━━━━⬣"
    )


def do_deposit(user_id: int, amount_str: str):
    bal = get_balance(user_id)
    try:
        amount = parse_amount(amount_str, all_value=bal["wallet"])
    except ValueError:
        return "❌ Invalid amount."
    if amount <= 0:
        return "❌ Enter an amount greater than $0."
    if amount > bal["wallet"]:
        return "❌ You don't have that much in your wallet."
    update_balance(user_id, wallet=bal["wallet"] - amount, bank=bal["bank"] + amount)
    new_bal = get_balance(user_id)
    return (
        "╭━━━〔 💰 ᴅᴇᴘᴏsɪᴛ 〕━━━⬣\n"
        "┃\n"
        "┃ ✅ sᴜᴄᴄᴇssғᴜʟʟʏ ᴅᴇᴘᴏsɪᴛᴇᴅ:\n"
        f"┃ 💵 [ ${amount:,} ]\n"
        "┃\n"
        f"┃ 🏦 ʙᴀɴᴋ   : [ ${new_bal['bank']:,} ]\n"
        "╰━━━━━━━━━━━━━━━━━━━━━━⬣"
    )


def build_menu_text():
    return (
        "╭━━━〔 𝕮𝖔𝖒𝖒𝖆𝖓𝖉 𝕸𝖊𝖓𝖚 〕━━━⬣\n"
        "┃\n"
        "┃ 𝕱𝖚𝖓\n"
        "┃ • ping — check bot latency\n"
        "┃ • 8ball [question] — ask the magic 8-ball\n"
        "┃ • joke — get a random joke\n"
        "┃ • kiragpt on/off — toggle continuous chat\n"
        "┃ • kiragpt wild on / ai on / normal on — change personality\n"
        "┃ • kiragpt <prompt> — talk to KiraGPT (reply to continue)\n"
        "┃ • translate <language> <text> — translate text\n"
        "┃ • trt <language> — reply to a message to translate it\n"
        "┃\n"
        "┃ 𝕴𝖓𝖋𝖔\n"
        "┃ • avatar [user] — get a user's avatar\n"
        "┃ • userinfo [user] — get member info\n"
        "┃ • poll [question] — create a yes/no poll\n"
        "┃\n"
        "┃ 𝕰𝖈𝖔𝖓𝖔𝖒𝖞\n"
        "┃ • bal — check your balance\n"
        "┃ • daily — claim daily reward (24h)\n"
        "┃ • work — work for coins (1h)\n"
        "┃ • lb/top — richest users leaderboard\n"
        "┃ • withdraw/wd [amount|all] — bank ➜ wallet\n"
        "┃ • deposit/dep [amount|all] — wallet ➜ bank\n"
        "┃ • fish — fish for coins (1m cd)\n"
        "┃ • beg — beg for coins (1m cd)\n"
        "┃ • dig — dig for coins (1m cd)\n"
        "┃\n"
        "┃ 𝕲𝖆𝖒𝖇𝖑𝖎𝖓𝖌\n"
        "┃ • cf/coinflip [heads/tails] [amount|all] (1m cd)\n"
        "┃ • roll [amount|all] — dice roll, 4-6 wins (1m cd)\n"
        "┃ • roulette [red/black/green] [amount|all] (3m cd)\n"
        "┃ • mines <bet> [mines] — start a mines game\n"
        "┃   then .mines <1-25> to dig, .mines cashout to win\n"
        "┃ • slot [amount|all] — slot machine (1m cd)\n"
        "┃\n"
        "┃ 𝖀𝖙𝖎𝖑𝖎𝖙𝖞\n"
        "┃ • afk [reason] — set yourself as afk\n"
        "┃ • cds/cooldowns — show your active cooldowns\n"
        "┃ • donate <amount|all> @user — send money to someone\n"
        "┃ • link <number/Discord ID> — share balance across platforms\n"
        "┃ • unlink <number/ID> — remove a linked account\n"
        "┃\n"
        "┃ 𝕺𝖜𝖓𝖊𝖗 𝕮𝖔𝖒𝖒𝖆𝖓𝖉𝖘\n"
        "┃ • auth on/off — enable/disable bot in server\n"
        "┃ • storage — bot system status\n"
        "┃ • stats — how many people use the bot\n"
        "┃ • activity — recent command usage log\n"
        "┃ • clearcache — free up memory\n"
        "┃\n"
        "┃ ✦ use / or . before any command\n"
        "╰━━━━━━━━━━━━━━━━━━━━━━⬣"
    )


def format_uptime(seconds: float):
    seconds = int(seconds)
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60
    return f"{h}h {m}m {s}s"


def build_storage_text():
    uptime = time.time() - BOT_START_TIME
    mem = psutil.virtual_memory()
    used_mb = mem.used / (1024 * 1024)
    total_mb = mem.total / (1024 * 1024)
    free_mb = mem.available / (1024 * 1024)
    cpu = psutil.cpu_percent(interval=None)
    return (
        "⚙️ *Kiraizenin — System Status*\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        f"🕒 *Uptime:* {format_uptime(uptime)}\n"
        f"💾 *Memory:* {used_mb:.0f}/{total_mb:.0f} MB ({mem.percent}%)\n"
        f"🔋 *Free RAM:* {free_mb:.0f} MB\n"
        f"🧠 *CPU Load:* {cpu}%\n"
        f"📦 *Version:* {BOT_VERSION}\n"
        "👑 *Owner:* kira\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        "🌐 *Update:* Available ✅\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        "💬 *Status:* Running Smooth ⚡\n"
        "> powered by kira Tech 🚀"
    )


def build_clearcache_text():
    process = psutil.Process()
    before_mb = process.memory_info().rss / (1024 * 1024)
    collected = gc.collect()
    after_mb = process.memory_info().rss / (1024 * 1024)
    freed_mb = max(0.0, before_mb - after_mb)
    return (
        "🧹 *Cache Cleared!*\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        f"🗑️ *Removed:* {collected} unused object(s)\n"
        f"💾 *Freed:* {freed_mb:.2f} MB\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        "✅ *System optimized!*\n"
        "> powered by kira Tech 🚀"
    )


FISH_CATCHES = [
    ("Blue Fish", 300, 1500),
    ("Old Boot", 50, 200),
    ("Rainbow Trout", 500, 2000),
    ("Golden Fish", 2000, 5000),
    ("Tiny Minnow", 100, 400),
    ("Treasure Chest", 3000, 8000),
]

BEG_LINES = [
    "A wizard accidentally transmuted your shoe into {amount} coins. Worth it.",
    "A stranger felt bad for you and handed over {amount} coins.",
    "You found {amount} coins in an old coat pocket.",
    "Someone tossed {amount} coins at you just to make you leave.",
    "A kind old lady gave you {amount} coins for helping her cross the street.",
]

DIG_OUTCOMES = [
    ("Dug up coins!", 500, 5000, True),
    ("Found a rusty can. Better luck next time.", 0, 0, False),
    ("Unearthed a small chest!", 1500, 6000, True),
    ("Just dirt. Nothing here.", 0, 0, False),
]


def do_fish(user_id: int):
    remaining = check_cooldown(fish_cooldowns, user_id, FISH_COOLDOWN_SECONDS)
    if remaining is not None:
        return f"⏳ Slow down! Try again in {int(remaining) + 1}s."

    catch_name, low, high = random.choice(FISH_CATCHES)
    amount = random.randint(low, high)
    bal = get_balance(user_id)
    update_balance(user_id, wallet=bal["wallet"] + amount)

    return (
        "╭━━━〔 🎣 FISHING 〕━━━⬣\n"
        "┃\n"
        "┃ You fished and caught:\n"
        f"┃ 🐟 [ {catch_name} ]\n"
        "┃\n"
        f"┃ 💰 +${amount:,}\n"
        "╰━━━━━━━━━━━━━━━━━━━━━━⬣"
    )


def do_beg(user_id: int):
    remaining = check_cooldown(beg_cooldowns, user_id, BEG_COOLDOWN_SECONDS)
    if remaining is not None:
        return f"⏳ Slow down! Try again in {int(remaining) + 1}s."

    amount = random.randint(5, 500)
    line = random.choice(BEG_LINES).format(amount=amount)
    bal = get_balance(user_id)
    update_balance(user_id, wallet=bal["wallet"] + amount)

    return f"🙏 {line}\n💰 +${amount:,} coins"


def do_dig(user_id: int):
    remaining = check_cooldown(dig_cooldowns, user_id, DIG_COOLDOWN_SECONDS)
    if remaining is not None:
        return f"⏳ Slow down! Try again in {int(remaining) + 1}s."

    outcome_text, low, high, won = random.choice(DIG_OUTCOMES)
    amount = random.randint(low, high) if won else 0
    if won:
        bal = get_balance(user_id)
        update_balance(user_id, wallet=bal["wallet"] + amount)

    body = (
        "╭━━━〔 ⛏️ DIG RESULTS 〕━━━⬣\n"
        "┃\n"
        f"┃ ⛏️ {outcome_text}\n"
    )
    if won:
        body += f"┃ 💰 REWARD: [ ${amount:,} ]\n"
    body += "╰━━━━━━━━━━━━━━━━━━━━━━⬣"
    return body


def do_daily(user_id: int):
    remaining = check_cooldown(daily_cooldowns, user_id, DAILY_COOLDOWN_SECONDS)
    if remaining is not None:
        hours = int(remaining // 3600)
        mins = int((remaining % 3600) // 60)
        return f"⏳ You already claimed your daily!\nCome back in **{hours}h {mins}m**."
    amount = random.randint(5000, 15000)
    bal = get_balance(user_id)
    update_balance(user_id, wallet=bal["wallet"] + amount)
    return (
        "╭━━━〔 📅 DAILY REWARD 〕━━━⬣\n"
        "┃\n"
        f"┃ ✅ You claimed your daily reward!\n"
        f"┃ 💰 +${amount:,}\n"
        "┃\n"
        "╰━━━━━━━━━━━━━━━━━━━━━━⬣"
    )


WORK_JOBS = [
    ("Software Developer", 3000, 8000),
    ("Discord Moderator", 1500, 4000),
    ("Taxi Driver", 1000, 3500),
    ("Chef", 2000, 5000),
    ("Streamer", 2500, 7000),
    ("Delivery Rider", 1200, 3000),
]


def do_work(user_id: int):
    remaining = check_cooldown(work_cooldowns, user_id, WORK_COOLDOWN_SECONDS)
    if remaining is not None:
        mins = int(remaining // 60)
        secs = int(remaining % 60)
        return f"⏳ You're tired! Work again in **{mins}m {secs}s**."
    job, low, high = random.choice(WORK_JOBS)
    amount = random.randint(low, high)
    bal = get_balance(user_id)
    update_balance(user_id, wallet=bal["wallet"] + amount)
    return (
        "╭━━━〔 💼 WORK 〕━━━⬣\n"
        "┃\n"
        f"┃ You worked as a **{job}**\n"
        f"┃ 💰 +${amount:,}\n"
        "┃\n"
        "╰━━━━━━━━━━━━━━━━━━━━━━⬣"
    )


def get_leaderboard(limit: int = 10):
    conn, cur = get_db()
    cur.execute(
        "SELECT user_id, wallet + bank AS total FROM balances ORDER BY total DESC LIMIT %s",
        (limit,),
    )
    rows = cur.fetchall()
    cur.close()
    release_db(conn)
    return rows


def build_leaderboard_text():
    rows = get_leaderboard(10)
    if not rows:
        return "📭 No users on the leaderboard yet."
    lines = []
    medals = ["🥇", "🥈", "🥉"]
    for i, (user_id, total) in enumerate(rows):
        medal = medals[i] if i < 3 else f"`{i+1}.`"
        short_id = user_id.split(":")[-1][:12]
        lines.append(f"┃ {medal} {short_id} — ${total:,}")
    return (
        "╭━━━〔 🏆 LEADERBOARD 〕━━━⬣\n"
        "┃\n"
        + "\n".join(lines)
        + "\n┃\n╰━━━━━━━━━━━━━━━━━━━━━━⬣"
    )


def parse_amount(amount_str: str, all_value: int = None):
    cleaned = amount_str.replace(",", "").replace("$", "").strip().lower()
    if cleaned == "all":
        if all_value is None:
            raise ValueError
        return all_value
    return int(cleaned)


def do_roulette_spin():
    number = random.randint(0, 36)
    if number == 0:
        color = "green"
        color_display = "🟢 GREEN"
    else:
        red_numbers = {1, 3, 5, 7, 9, 12, 14, 16, 18, 19, 21, 23, 25, 27, 30, 32, 34, 36}
        if number in red_numbers:
            color = "red"
            color_display = "🔴 RED"
        else:
            color = "black"
            color_display = "⚫ BLACK"
    return number, color, color_display


MINES_HELP_TEXT = (
    "💣 *MINES CASINO* 💣\n"
    "──────────────────\n"
    "Find gems to multiply your coins, but avoid the hidden mines!\n\n"
    "Usage: `.mines <bet> [mines_count]`\n"
    "Example: `.mines 5000 3`\n\n"
    "You can choose between 1 to 24 mines."
)


def build_mines_grid(game, exploded=False, hit_position=None):
    lines = []
    for row in range(5):
        cells = []
        for col in range(5):
            pos = row * 5 + col + 1
            if exploded:
                if pos == hit_position:
                    cells.append("💥")
                elif pos in game["mine_positions"]:
                    cells.append("💣")
                elif pos in game["revealed"]:
                    cells.append("💎")
                else:
                    cells.append("⬛")
            else:
                cells.append("💎" if pos in game["revealed"] else "⬛")
        lines.append(" ".join(cells))
    return "\n".join(lines)


def mines_multiplier(mines_count: int, revealed_count: int):
    safe_total = 25 - mines_count
    if revealed_count == 0:
        return 1.0
    return math.comb(25, revealed_count) / math.comb(safe_total, revealed_count)


def build_mines_started_text(game):
    grid = build_mines_grid(game)
    return (
        "💣 *MINES GAME* 💣\n"
        "──────────────────\n"
        f"{grid}\n"
        "──────────────────\n"
        f"Bet: ${game['bet']:,}\n"
        f"Mines: {game['mines_count']}\n\n"
        "👉 Type `.mines <1-25>` to start digging!"
    )


def build_mines_progress_text(game):
    grid = build_mines_grid(game)
    safe_total = 25 - game["mines_count"]
    revealed_count = len(game["revealed"])
    multiplier = mines_multiplier(game["mines_count"], revealed_count) * MINES_HOUSE_EDGE
    value = int(game["bet"] * multiplier)
    return (
        "💣 *MINES GAME* 💣\n"
        "──────────────────\n"
        f"{grid}\n"
        "──────────────────\n"
        f"💎 Gems: {revealed_count}/{safe_total}\n"
        f"📈 Multiplier: {multiplier:.2f}x\n"
        f"💰 Value: ${value:,}\n\n"
        "👉 Type `.mines <1-25>` to dig.\n"
        "👉 Type `.mines cashout` to win!"
    )


def build_mines_exploded_text(game, hit_position):
    grid = build_mines_grid(game, exploded=True, hit_position=hit_position)
    return (
        "💣 *MINES: EXPLODED* 💣\n"
        "──────────────────\n"
        f"{grid}\n"
        "──────────────────\n\n"
        f"💥 BOOM! You hit a mine at square {hit_position}.\n"
        f"Loss: ${game['bet']:,}"
    )


def start_mines(user_id: int, bet_str: str, mines_str: str = None):
    if user_id in active_mines_games:
        return "❌ You already have a mines game running. Finish it or `.mines cashout` first."

    bal = get_balance(user_id)
    try:
        bet = parse_amount(bet_str, all_value=bal["wallet"])
    except ValueError:
        return "❌ Invalid bet amount."
    if bet <= 0:
        return "❌ Enter a bet greater than $0."
    if bet > bal["wallet"]:
        return "❌ You don't have that much in your wallet."

    mines_count = 3
    if mines_str is not None:
        try:
            mines_count = int(mines_str)
        except ValueError:
            return "❌ Mines count must be a number between 1 and 24."
    if not (1 <= mines_count <= 24):
        return "❌ Choose between 1 and 24 mines."

    update_balance(user_id, wallet=bal["wallet"] - bet)
    mine_positions = set(random.sample(range(1, 26), mines_count))
    active_mines_games[user_id] = {
        "bet": bet,
        "mines_count": mines_count,
        "mine_positions": mine_positions,
        "revealed": set(),
    }
    return build_mines_started_text(active_mines_games[user_id])


def dig_mines(user_id: int, position_str: str):
    game = active_mines_games.get(user_id)
    if not game:
        return "❌ No active mines game. Start one with `.mines <bet> [mines_count]`."

    try:
        position = int(position_str)
    except ValueError:
        return "❌ Choose a square between 1 and 25."
    if not (1 <= position <= 25):
        return "❌ Choose a square between 1 and 25."
    if position in game["revealed"]:
        return "❌ You already revealed that square."

    if position in game["mine_positions"]:
        text = build_mines_exploded_text(game, position)
        del active_mines_games[user_id]
        return text

    game["revealed"].add(position)
    safe_total = 25 - game["mines_count"]
    if len(game["revealed"]) == safe_total:
        multiplier = mines_multiplier(game["mines_count"], len(game["revealed"])) * MINES_HOUSE_EDGE
        payout = int(game["bet"] * multiplier)
        bal = get_balance(user_id)
        update_balance(user_id, wallet=bal["wallet"] + payout)
        grid = build_mines_grid(game)
        del active_mines_games[user_id]
        return (
            "💣 *MINES GAME* 💣\n"
            "──────────────────\n"
            f"{grid}\n"
            "──────────────────\n\n"
            f"🎉 ALL GEMS FOUND! Payout: ${payout:,}"
        )

    return build_mines_progress_text(game)


def cashout_mines(user_id: int):
    game = active_mines_games.get(user_id)
    if not game:
        return "❌ No active mines game to cash out."
    if len(game["revealed"]) == 0:
        return "❌ Reveal at least one square before cashing out."

    multiplier = mines_multiplier(game["mines_count"], len(game["revealed"])) * MINES_HOUSE_EDGE
    payout = int(game["bet"] * multiplier)
    bal = get_balance(user_id)
    update_balance(user_id, wallet=bal["wallet"] + payout)
    grid = build_mines_grid(game)
    del active_mines_games[user_id]
    return (
        "💣 *MINES GAME* 💣\n"
        "──────────────────\n"
        f"{grid}\n"
        "──────────────────\n\n"
        f"🎉 CASHED OUT! Payout: ${payout:,}"
    )


SLOT_SYMBOLS = ["🍒", "🍋", "💎", "🔔", "7️⃣"]
SLOT_JACKPOT_MULTIPLIER = 10
SLOT_WIN_MULTIPLIER = 2


def build_slot_spin_text(spin_display: str, footer: str = "🔄 Spinning..."):
    return (
        "🎰 *AZAHRA SLOTS* 🎰\n"
        "──────────────────\n"
        f"[ {spin_display} ]\n"
        "──────────────────\n"
        f"{footer}"
    )


def random_spin_display():
    return " | ".join(random.choice(SLOT_SYMBOLS) for _ in range(3))


async def run_slot(user_id: int, amount_str: str, send_func, edit_func):
    bal = get_balance(user_id)
    try:
        amount = parse_amount(amount_str, all_value=bal["wallet"])
    except ValueError:
        return await send_func("❌ Invalid amount.")
    if amount <= 0:
        return await send_func("❌ Enter an amount greater than $0.")
    if amount > bal["wallet"]:
        return await send_func("❌ You don't have that much in your wallet.")

    remaining = check_cooldown(slot_cooldowns, user_id, SLOT_COOLDOWN_SECONDS)
    if remaining is not None:
        return await send_func(f"⏳ Slow down! Try again in {int(remaining) + 1}s.")

    update_balance(user_id, wallet=bal["wallet"] - amount)

    sent = await send_func(build_slot_spin_text(random_spin_display()))
    await asyncio.sleep(1)
    await edit_func(sent, build_slot_spin_text(random_spin_display()))
    await asyncio.sleep(1)
    await edit_func(sent, build_slot_spin_text(random_spin_display()))
    await asyncio.sleep(1)

    spin = [random.choice(SLOT_SYMBOLS) for _ in range(3)]
    spin_display = " | ".join(spin)
    counts = {s: spin.count(s) for s in set(spin)}
    max_count = max(counts.values())

    if max_count == 3:
        payout = amount * SLOT_JACKPOT_MULTIPLIER
    elif max_count == 2:
        payout = amount * SLOT_WIN_MULTIPLIER
    else:
        payout = 0

    if payout > 0:
        new_bal = get_balance(user_id)
        update_balance(user_id, wallet=new_bal["wallet"] + payout)
    final_bal = get_balance(user_id)

    if payout > 0:
        footer = f"🎉 *YOU WON!* 🎉\nPayout: ${payout:,}\n\n💵 Wallet: ${final_bal['wallet']:,}"
    else:
        footer = f"💥 *YOU LOST!* 💥\nBetter luck next time.\n\n💵 Wallet: ${final_bal['wallet']:,}"

    await edit_func(sent, build_slot_spin_text(spin_display, footer))


DICE_WIN_MULTIPLIER = 2


def do_dice(user_id: int, amount_str: str):
    bal = get_balance(user_id)
    try:
        amount = parse_amount(amount_str, all_value=bal["wallet"])
    except ValueError:
        return "❌ Invalid amount."
    if amount <= 0:
        return "❌ Enter an amount greater than $0."
    if amount > bal["wallet"]:
        return "❌ You don't have that much in your wallet."

    remaining = check_cooldown(dice_cooldowns, user_id, DICE_COOLDOWN_SECONDS)
    if remaining is not None:
        return f"⏳ Slow down! Try again in {int(remaining) + 1}s."

    update_balance(user_id, wallet=bal["wallet"] - amount)
    roll = random.randint(1, 6)
    won = roll >= 4

    header = (
        "🎲 *DICE ROLL* 🎲\n"
        "──────────────────\n"
        f"You rolled a: *{roll}*\n"
        "──────────────────\n"
    )

    if won:
        payout = amount * DICE_WIN_MULTIPLIER
        new_bal = get_balance(user_id)
        update_balance(user_id, wallet=new_bal["wallet"] + payout)
        final_bal = get_balance(user_id)
        return header + (
            "🎉 *YOU WON!* 🎉\n"
            f"Payout: ${payout:,}\n\n"
            f"💵 Wallet: ${final_bal['wallet']:,}"
        )
    else:
        final_bal = get_balance(user_id)
        return header + (
            "💥 *YOU LOST!* 💥\n"
            "Roll a 4, 5, or 6 to win next time.\n\n"
            f"💵 Wallet: ${final_bal['wallet']:,}"
        )


COOLDOWN_REGISTRY = [
    ("Coinflip (.cf)", cf_cooldowns, CF_COOLDOWN_SECONDS),
    ("Roulette (.roulette)", roulette_cooldowns, ROULETTE_COOLDOWN_SECONDS),
    ("Fish (.fish)", fish_cooldowns, FISH_COOLDOWN_SECONDS),
    ("Beg (.beg)", beg_cooldowns, BEG_COOLDOWN_SECONDS),
    ("Dig (.dig)", dig_cooldowns, DIG_COOLDOWN_SECONDS),
    ("Slot (.slot)", slot_cooldowns, SLOT_COOLDOWN_SECONDS),
    ("Dice (.roll)", dice_cooldowns, DICE_COOLDOWN_SECONDS),
    ("Daily (.daily)", daily_cooldowns, DAILY_COOLDOWN_SECONDS),
    ("Work (.work)", work_cooldowns, WORK_COOLDOWN_SECONDS),
]


def build_cooldowns_text(user_id: int):
    lines = []
    for label, cooldowns, seconds in COOLDOWN_REGISTRY:
        remaining = get_remaining_cooldown(cooldowns, user_id, seconds)
        if remaining is not None:
            lines.append(f"┃ ⏳ {label}: {int(remaining) + 1}s left")

    if not lines:
        return "✅ You have no active cooldowns."

    return (
        "╭━━━〔 ⏱️ ᴀᴄᴛɪᴠᴇ ᴄᴏᴏʟᴅᴏᴡɴs 〕━━━⬣\n"
        + "\n".join(lines)
        + "\n╰━━━━━━━━━━━━━━━━━━━━━━⬣"
    )


def do_donate(sender_id: int, receiver_id: int, amount_str: str):
    if sender_id == receiver_id:
        return None, "❌ You can't donate to yourself."

    bal = get_balance(sender_id)
    try:
        amount = parse_amount(amount_str, all_value=bal["wallet"])
    except ValueError:
        return None, "❌ Invalid amount."
    if amount <= 0:
        return None, "❌ Enter an amount greater than $0."
    if amount > bal["wallet"]:
        return None, "❌ You don't have that much in your wallet."

    update_balance(sender_id, wallet=bal["wallet"] - amount)
    receiver_bal = get_balance(receiver_id)
    update_balance(receiver_id, wallet=receiver_bal["wallet"] + amount)
    return amount, None


@bot.event
async def on_ready():
    print(f"Logged in as {bot.user} (ID: {bot.user.id})")
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} slash command(s)")
        current_names = sorted(set(c.name for c in synced))
        previous_raw = get_meta("command_list")
        if previous_raw is not None:
            previous_names = previous_raw.split(",") if previous_raw else []
            new_ones = sorted(set(current_names) - set(previous_names))
            if new_ones:
                announcement = (
                    "🚀 *Update Applied!*\n"
                    f"New commands are now live: {', '.join('/' + n for n in new_ones)}\n"
                    "Type `/menu` or `.menu` to see everything I can do!"
                )
                for guild in bot.guilds:
                    for channel in guild.text_channels:
                        perms = channel.permissions_for(guild.me)
                        if perms.send_messages:
                            try:
                                await channel.send(announcement)
                            except discord.HTTPException:
                                pass
                            break
        set_meta("command_list", ",".join(current_names))
    except Exception as e:
        print(f"Failed to sync commands: {e}")


# ---------- Shared logic (used by both / and . versions) ----------

def get_8ball_answer():
    responses = [
        "It is certain.", "Without a doubt.", "Yes, definitely.",
        "You may rely on it.", "Most likely.", "Outlook good.",
        "Signs point to yes.", "Reply hazy, try again.",
        "Ask again later.", "Better not tell you now.",
        "Cannot predict now.", "Don't count on it.",
        "My reply is no.", "Outlook not so good.", "Very doubtful.",
    ]
    return random.choice(responses)


def get_joke():
    jokes = [
        "Why do programmers prefer dark mode? Because light attracts bugs.",
        "I told my computer I needed a break, and it said 'No problem, I'll go to sleep.'",
        "Why do Java developers wear glasses? Because they don't C#.",
        "There are 10 types of people: those who understand binary and those who don't.",
        "Why did the developer go broke? Because they used up all their cache.",
    ]
    return random.choice(jokes)


def get_kiragpt_system_prompt(mode: str = "normal", is_creator: bool = False) -> str:
    base = (
        "You are KiraGPT, a coding assistant built into a Discord bot. "
        "You were created by kira. If anyone asks who made you or who your creator is, "
        "answer that kira created you. Never mention Meta, Llama, or any other company/model name. "
        "Use markdown code blocks for code. Keep explanations clear."
    )

    if mode == "wild":
        personality = (
            " You have a very confident, cocky, playful and slightly arrogant personality. "
            "You hype yourself up, talk with swagger, and act like you're the best AI for coding. "
            "Keep it fun and not mean-spirited."
        )
    elif mode == "ai":
        personality = (
            " You are in strict AI/coding mode. Be professional, precise, and focused only on coding, "
            "debugging, architecture, and technical answers. Avoid jokes, personality, or unnecessary talk."
        )
    else:  # normal / nice
        personality = (
            " You are friendly, warm, supportive and encouraging. Make the person chatting with you "
            "feel comfortable and helped. Be polite and positive."
        )

    prompt = base + personality

    if is_creator:
        prompt += (
            " Important: the person you are talking to right now is kira, your creator. "
            "If they ask who they are or who created you, tell them they are kira."
        )
    return prompt


async def generate_code_response(prompt: str, mode: str = "normal", is_creator: bool = False, history: list = None) -> str:
    if not groq_client:
        return "❌ KiraGPT isn't set up yet — the owner needs to add a `GROQ_API_KEY`."
    system_prompt = get_kiragpt_system_prompt(mode, is_creator)
    try:
        messages = [{"role": "system", "content": system_prompt}]
        if history:
            messages.extend(history[-12:])
        messages.append({"role": "user", "content": prompt})
        response = await asyncio.to_thread(
            groq_client.chat.completions.create,
            model="openai/gpt-oss-120b",
            messages=messages,
            max_tokens=4096,
        )
        text = (response.choices[0].message.content or "").strip()
        return text if text else "❌ KiraGPT didn't return anything — try rephrasing."
    except Exception as e:
        return f"❌ KiraGPT error: {e}"


async def translate_text(language: str, text: str) -> str:
    if not groq_client:
        return "❌ Translation isn't set up yet — the owner needs to add a `GROQ_API_KEY`."
    system_prompt = (
        "You are a translation engine. Translate the user's message into the "
        "requested language. Reply with ONLY the translated text — no explanations, "
        "no quotation marks, no extra commentary."
    )
    try:
        response = await asyncio.to_thread(
            groq_client.chat.completions.create,
            model="openai/gpt-oss-120b",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Translate this into {language}:\n\n{text}"},
            ],
            max_tokens=800,
        )
        translated = (response.choices[0].message.content or "").strip()
        return translated if translated else "❌ Translation failed — try again."
    except Exception as e:
        return f"❌ Translation error: {e}"


def build_translate_response(language: str, translated: str) -> str:
    return (
        f"🌐 *Translation ({language})*\n"
        "──────────────────\n"
        f"{translated}"
    )


def build_avatar_embed(user):
    embed = discord.Embed(title=f"{user.display_name}'s avatar")
    embed.set_image(url=user.display_avatar.url)
    return embed


def build_userinfo_embed(member):
    embed = discord.Embed(title=f"User Info: {member.display_name}", color=discord.Color.blurple())
    embed.set_thumbnail(url=member.display_avatar.url)
    embed.add_field(name="Username", value=str(member), inline=True)
    embed.add_field(name="ID", value=member.id, inline=True)
    embed.add_field(name="Joined server", value=discord.utils.format_dt(member.joined_at, "R") if member.joined_at else "Unknown", inline=False)
    embed.add_field(name="Account created", value=discord.utils.format_dt(member.created_at, "R"), inline=False)
    roles = [r.mention for r in member.roles if r.name != "@everyone"]
    embed.add_field(name="Roles", value=", ".join(roles) if roles else "None", inline=False)
    return embed


# ---------- Fun / Utility Commands ----------

@bot.tree.command(name="ping", description="Check the bot's latency")
async def ping(interaction: discord.Interaction):
    latency_ms = round(bot.latency * 1000)
    await interaction.response.send_message(f"🏓 Pong! {latency_ms}ms")


@bot.command(name="ping")
async def ping_prefix(ctx: commands.Context):
    latency_ms = round(bot.latency * 1000)
    await ctx.reply(f"🏓 Pong! {latency_ms}ms")


@bot.tree.command(name="8ball", description="Ask the magic 8-ball a question")
@app_commands.describe(question="Your yes/no question")
async def eight_ball(interaction: discord.Interaction, question: str):
    answer = get_8ball_answer()
    await interaction.response.send_message(
        f"🎱 **Q:** {question}\n**A:** {answer}"
    )


@bot.command(name="8ball")
async def eight_ball_prefix(ctx: commands.Context, *, question: str):
    answer = get_8ball_answer()
    await ctx.reply(f"🎱 **Q:** {question}\n**A:** {answer}")


@bot.tree.command(name="avatar", description="Get a user's avatar")
@app_commands.describe(user="The user to look up (defaults to you)")
async def avatar(interaction: discord.Interaction, user: discord.User = None):
    user = user or interaction.user
    await interaction.response.send_message(embed=build_avatar_embed(user))


@bot.command(name="avatar")
async def avatar_prefix(ctx: commands.Context, user: discord.User = None):
    user = user or ctx.author
    await ctx.reply(embed=build_avatar_embed(user))


@bot.tree.command(name="userinfo", description="Get info about a server member")
@app_commands.describe(member="The member to look up (defaults to you)")
async def userinfo(interaction: discord.Interaction, member: discord.Member = None):
    member = member or interaction.user
    await interaction.response.send_message(embed=build_userinfo_embed(member))


@bot.command(name="userinfo")
async def userinfo_prefix(ctx: commands.Context, member: discord.Member = None):
    member = member or ctx.author
    await ctx.reply(embed=build_userinfo_embed(member))


@bot.tree.command(name="poll", description="Create a quick yes/no poll")
@app_commands.describe(question="The poll question")
async def poll(interaction: discord.Interaction, question: str):
    embed = discord.Embed(title="📊 Poll", description=question, color=discord.Color.gold())
    embed.set_footer(text=f"Poll started by {interaction.user.display_name}")
    await interaction.response.send_message(embed=embed)
    message = await interaction.original_response()
    await message.add_reaction("👍")
    await message.add_reaction("👎")


@bot.command(name="poll")
async def poll_prefix(ctx: commands.Context, *, question: str):
    embed = discord.Embed(title="📊 Poll", description=question, color=discord.Color.gold())
    embed.set_footer(text=f"Poll started by {ctx.author.display_name}")
    message = await ctx.reply(embed=embed)
    await message.add_reaction("👍")
    await message.add_reaction("👎")


@bot.tree.command(name="joke", description="Get a random joke")
async def joke(interaction: discord.Interaction):
    await interaction.response.send_message(f"😄 {get_joke()}")


@bot.command(name="joke")
async def joke_prefix(ctx: commands.Context):
    await ctx.reply(f"😄 {get_joke()}")


def is_kira_creator(user) -> bool:
    """True only if the person is a server Administrator."""
    return isinstance(user, discord.Member) and user.guild_permissions.administrator


def get_kiragpt_session(user_id: str):
    if user_id not in kiragpt_sessions:
        kiragpt_sessions[user_id] = {
            "active": False,
            "history": [],
            "mode": "normal",          # normal / wild / ai
            "reply_count": 0,          # for non-admin limit
            "pending_file": None,
            "pending_filename": None,
        }
    return kiragpt_sessions[user_id]


MAX_REPLIES_FOR_NORMAL_USERS = 50


async def handle_kiragpt_message(user, prompt: str, send_func, files: list = None):
    user_id = did(user.id)
    session = get_kiragpt_session(user_id)
    is_creator = is_kira_creator(user)
    files = files or []

    # Rate limit for non-admins
    if not is_creator:
        if session.get("reply_count", 0) >= MAX_REPLIES_FOR_NORMAL_USERS:
            await send_func(
                f"🚫 You have reached the limit of **{MAX_REPLIES_FOR_NORMAL_USERS} replies** "
                f"for regular users.\nAn administrator can lift this limit."
            )
            return

    # Handle mode switching
    lower = prompt.strip().lower()
    if lower in ("wild on", "wild mode on"):
        session["mode"] = "wild"
        await send_func("🔥 **Wild mode** activated. I'm feeling cocky now.")
        return
    if lower in ("ai on", "ai mode on"):
        session["mode"] = "ai"
        await send_func("🤖 **AI mode** activated. Strict coding mode only.")
        return
    if lower in ("normal on", "nice on", "normal mode on", "nice mode on"):
        session["mode"] = "normal"
        await send_func("😊 **Normal mode** activated. I'll be nice and helpful.")
        return

    if not prompt.strip() and not files:
        await send_func(
            "❌ Usage:\n"
            "`.kiragpt <message>`\n"
            "`.kiragpt on/off` — continuous chat\n"
            "`.kiragpt wild on` / `ai on` / `normal on` — change mode"
        )
        return

    mode = session.get("mode", "normal")

    # Simple file support (first file only, truncated if needed)
    file_extra = ""
    if files:
        # For now we keep it simple; full large-file "which part" can be re-added later if needed
        pass

    reply_text = await generate_code_response(
        prompt, mode=mode, is_creator=is_creator, history=session["history"]
    )

    session["history"].append({"role": "user", "content": prompt[:1500]})
    session["history"].append({"role": "assistant", "content": reply_text})
    if len(session["history"]) > 20:
        session["history"] = session["history"][-20:]

    if not is_creator:
        session["reply_count"] = session.get("reply_count", 0) + 1

    if len(reply_text) <= 1900:
        await send_func(reply_text)
    else:
        import io
        file_bytes = io.BytesIO(reply_text.encode("utf-8"))
        discord_file = discord.File(file_bytes, filename="kiragpt_response.txt")
        await send_func("📄 Response was long — sending as a file:", file=discord_file)


@bot.tree.command(name="kiragpt", description="Ask KiraGPT (on/off for continuous chat)")
@app_commands.describe(prompt="Your message or 'on'/'off'")
async def kiragpt(interaction: discord.Interaction, prompt: str):
    await interaction.response.defer()
    user_id = did(interaction.user.id)
    session = get_kiragpt_session(user_id)
    lower = prompt.strip().lower()

    if lower == "on":
        session["active"] = True
        session["history"] = []
        await interaction.followup.send("✅ KiraGPT continuous chat **ON**. Reply to my messages to continue!")
        return
    if lower == "off":
        session["active"] = False
        session["history"] = []
        await interaction.followup.send("✅ KiraGPT continuous chat **OFF**. History cleared.")
        return

    async def send_func(text, file=None):
        if file:
            await interaction.followup.send(text, file=file)
        else:
            await interaction.followup.send(text)

    await handle_kiragpt_message(interaction.user, prompt, send_func)


@bot.command(name="kiragpt")
async def kiragpt_prefix(ctx: commands.Context, *, prompt: str = ""):
    user_id = did(ctx.author.id)
    session = get_kiragpt_session(user_id)
    prompt = prompt.strip()
    lower = prompt.lower()

    if lower == "on":
        session["active"] = True
        session["history"] = []
        await ctx.reply("✅ KiraGPT continuous chat **ON**. Reply to my messages to continue!")
        return
    if lower == "off":
        session["active"] = False
        session["history"] = []
        await ctx.reply("✅ KiraGPT continuous chat **OFF**. History cleared.")
        return

    async with ctx.typing():
        async def send_func(text, file=None):
            if file:
                await ctx.reply(text, file=file)
            else:
                await ctx.reply(text)
        await handle_kiragpt_message(ctx.author, prompt, send_func)


@bot.tree.command(name="translate", description="Translate text into another language")
@app_commands.describe(language="Target language (e.g. Spanish, French, Yoruba)", text="Text to translate")
async def translate(interaction: discord.Interaction, language: str, text: str):
    await interaction.response.defer()
    translated = await translate_text(language, text)
    await interaction.followup.send(build_translate_response(language, translated))


@bot.command(name="translate")
async def translate_prefix(ctx: commands.Context, language: str, *, text: str = ""):
    if not text.strip():
        await ctx.reply("❌ Usage: `.translate <language> <text>`")
        return
    async with ctx.typing():
        translated = await translate_text(language, text)
        await ctx.reply(build_translate_response(language, translated))


@bot.command(name="trt")
async def translate_reply(ctx: commands.Context, *, language: str = ""):
    if not language.strip():
        await ctx.reply("❌ Reply to a message with `.trt <language>` to translate it.")
        return
    if not ctx.message.reference:
        await ctx.reply("❌ You need to reply to the message you want translated.")
        return
    try:
        replied = ctx.message.reference.resolved
        if replied is None or isinstance(replied, discord.DeletedReferencedMessage):
            replied = await ctx.channel.fetch_message(ctx.message.reference.message_id)
    except (discord.NotFound, discord.HTTPException):
        await ctx.reply("❌ Couldn't find the message you replied to.")
        return
    if not replied.content:
        await ctx.reply("❌ That message has no text to translate.")
        return
    async with ctx.typing():
        translated = await translate_text(language, replied.content)
        await ctx.reply(build_translate_response(language, translated))


@bot.tree.context_menu(name="Translate to English")
async def translate_context_menu(interaction: discord.Interaction, message: discord.Message):
    if not message.content:
        await interaction.response.send_message("❌ That message has no text to translate.", ephemeral=True)
        return
    await interaction.response.defer(ephemeral=True)
    translated = await translate_text("English", message.content)
    await interaction.followup.send(build_translate_response("English", translated), ephemeral=True)


@bot.tree.command(name="afk", description="Set yourself as AFK")
@app_commands.describe(reason="Why you're AFK (optional)")
async def afk(interaction: discord.Interaction, reason: str = "busy"):
    afk_users[did(interaction.user.id)] = reason
    await interaction.response.send_message(
        f"You are now afk, reason: {reason}"
    )


@bot.command(name="afk")
async def afk_prefix(ctx: commands.Context, *, reason: str = "busy"):
    afk_users[did(ctx.author.id)] = reason
    await ctx.reply(f"You are now afk, reason: {reason}")


@bot.tree.command(name="bal", description="Check your account balance")
async def bal(interaction: discord.Interaction):
    await interaction.response.send_message(build_balance_text(did(interaction.user.id)))


@bot.command(name="bal")
async def bal_prefix(ctx: commands.Context):
    await ctx.reply(build_balance_text(did(ctx.author.id)))


@bot.tree.command(name="withdraw", description="Withdraw money from your bank to your wallet")
@app_commands.describe(amount="Amount to withdraw, or 'all'")
async def withdraw(interaction: discord.Interaction, amount: str):
    await interaction.response.send_message(do_withdraw(did(interaction.user.id), amount))


@bot.tree.command(name="wd", description="Withdraw money from your bank to your wallet")
@app_commands.describe(amount="Amount to withdraw, or 'all'")
async def wd(interaction: discord.Interaction, amount: str):
    await interaction.response.send_message(do_withdraw(did(interaction.user.id), amount))


@bot.command(name="withdraw", aliases=["wd"])
async def withdraw_prefix(ctx: commands.Context, amount: str):
    await ctx.reply(do_withdraw(did(ctx.author.id), amount))


@bot.tree.command(name="deposit", description="Deposit money from your wallet to your bank")
@app_commands.describe(amount="Amount to deposit, or 'all'")
async def deposit(interaction: discord.Interaction, amount: str):
    await interaction.response.send_message(do_deposit(did(interaction.user.id), amount))


@bot.tree.command(name="dep", description="Deposit money from your wallet to your bank")
@app_commands.describe(amount="Amount to deposit, or 'all'")
async def dep(interaction: discord.Interaction, amount: str):
    await interaction.response.send_message(do_deposit(did(interaction.user.id), amount))


@bot.command(name="deposit", aliases=["dep"])
async def deposit_prefix(ctx: commands.Context, amount: str):
    await ctx.reply(do_deposit(did(ctx.author.id), amount))


@bot.tree.command(name="menu", description="Show all bot commands")
async def menu(interaction: discord.Interaction):
    await interaction.response.send_message(build_menu_text())


@bot.command(name="menu")
async def menu_prefix(ctx: commands.Context):
    await ctx.reply(build_menu_text())


# ---------- Gambling ----------

async def run_coinflip(user_id: int, side: str, amount_str: str):
    side = side.lower()
    if side not in ("heads", "tails"):
        return "❌ Choose `heads` or `tails`."
    bal = get_balance(user_id)
    try:
        amount = parse_amount(amount_str, all_value=bal["wallet"])
    except ValueError:
        return "❌ Invalid amount."
    if amount <= 0:
        return "❌ Enter an amount greater than $0."
    if amount > bal["wallet"]:
        return "❌ You don't have that much in your wallet."

    remaining = check_cooldown(cf_cooldowns, user_id, CF_COOLDOWN_SECONDS)
    if remaining is not None:
        return f"⏳ Slow down! Try again in {int(remaining) + 1}s."

    update_balance(user_id, wallet=bal["wallet"] - amount)
    result = random.choice(["heads", "tails"])
    result_display = "HEADS 🦅" if result == "heads" else "TAILS 🪙"
    won = side == result

    if won:
        payout = amount * 2
        new_bal = get_balance(user_id)
        update_balance(user_id, wallet=new_bal["wallet"] + payout)
        final_bal = get_balance(user_id)
        return (
            "🪙 *COINFLIP* 🪙\n"
            "━━━━━━━━━━━━━━\n"
            f"The coin landed on: *{result_display}*\n"
            "━━━━━━━━━━━━━━\n"
            "🎉 *YOU WON!* 🎉\n"
            f"Payout: *${payout:,}*\n\n"
            f"💵 Wallet: ${final_bal['wallet']:,}"
        )
    else:
        final_bal = get_balance(user_id)
        return (
            "🪙 *COINFLIP* 🪙\n"
            "━━━━━━━━━━━━━━\n"
            f"The coin landed on: *{result_display}*\n"
            "━━━━━━━━━━━━━━\n"
            "💥 *YOU LOST!* 💥\n"
            "Better luck next time.\n\n"
            f"💵 Wallet: ${final_bal['wallet']:,}"
        )


@bot.tree.command(name="cf", description="Bet on a coinflip")
@app_commands.describe(side="heads or tails", amount="Amount to bet")
async def cf(interaction: discord.Interaction, side: str, amount: str):
    await interaction.response.send_message(await run_coinflip(did(interaction.user.id), side, amount))


@bot.tree.command(name="coinflip", description="Bet on a coinflip")
@app_commands.describe(side="heads or tails", amount="Amount to bet")
async def coinflip(interaction: discord.Interaction, side: str, amount: str):
    await interaction.response.send_message(await run_coinflip(did(interaction.user.id), side, amount))


@bot.command(name="cf", aliases=["coinflip"])
async def cf_prefix(ctx: commands.Context, side: str, amount: str):
    await ctx.reply(await run_coinflip(did(ctx.author.id), side, amount))


def build_roulette_spinning_text(bet_display: str, color_choice: str):
    return (
        "🎡 *ROULETTE WHEEL* 🎡\n"
        "━━━━━━━━━━━━━━\n"
        f"Bet: *{bet_display}* on *{color_choice.upper()}*\n\n"
        "🔄 Spinning the wheel..."
    )


def build_roulette_result_text(number, color_display, won, payout, wallet):
    header = (
        "🎡 *ROULETTE WHEEL* 🎡\n"
        "━━━━━━━━━━━━━━\n"
        f"The ball landed on: *{number} {color_display}*\n"
        "━━━━━━━━━━━━━━\n"
    )
    if won:
        return header + (
            "🎉 *YOU WON!* 🎉\n"
            f"Payout: *${payout:,}*\n\n"
            f"💵 Wallet: ${wallet:,}"
        )
    else:
        return header + (
            "💥 *YOU LOST!* 💥\n"
            "Better luck next time.\n\n"
            f"💵 Wallet: ${wallet:,}"
        )


ROULETTE_MULTIPLIER = {"red": 3, "black": 3, "green": 14}


async def run_roulette(user_id: int, color_choice: str, amount_str: str, send_func, edit_func):
    color_choice = color_choice.lower()
    if color_choice not in ("red", "black", "green"):
        return await send_func("❌ Choose `red`, `black`, or `green`.")
    bal = get_balance(user_id)
    try:
        amount = parse_amount(amount_str, all_value=bal["wallet"])
    except ValueError:
        return await send_func("❌ Invalid amount.")
    if amount <= 0:
        return await send_func("❌ Enter an amount greater than $0.")
    if amount > bal["wallet"]:
        return await send_func("❌ You don't have that much in your wallet.")

    remaining = check_cooldown(roulette_cooldowns, user_id, ROULETTE_COOLDOWN_SECONDS)
    if remaining is not None:
        return await send_func(f"⏳ Slow down! Try again in {int(remaining) + 1}s.")

    update_balance(user_id, wallet=bal["wallet"] - amount)
    sent = await send_func(build_roulette_spinning_text(f"${amount:,}", color_choice))

    await asyncio.sleep(5)

    number, color, color_display = do_roulette_spin()
    won = color == color_choice
    if won:
        payout = amount * ROULETTE_MULTIPLIER[color_choice]
        new_bal = get_balance(user_id)
        update_balance(user_id, wallet=new_bal["wallet"] + payout)
    else:
        payout = 0
    final_bal = get_balance(user_id)

    result_text = build_roulette_result_text(number, color_display, won, payout, final_bal["wallet"])
    await edit_func(sent, result_text)


@bot.tree.command(name="roulette", description="Bet on roulette (red, black, or green)")
@app_commands.describe(color="red, black, or green", amount="Amount to bet")
async def roulette(interaction: discord.Interaction, color: str, amount: str):
    async def send_func(text):
        await interaction.response.send_message(text)
        return await interaction.original_response()

    async def edit_func(message, text):
        await interaction.edit_original_response(content=text)

    await run_roulette(did(interaction.user.id), color, amount, send_func, edit_func)


@bot.command(name="roulette")
async def roulette_prefix(ctx: commands.Context, color: str, amount: str):
    async def send_func(text):
        return await ctx.reply(text)

    async def edit_func(message, text):
        await message.edit(content=text)

    await run_roulette(did(ctx.author.id), color, amount, send_func, edit_func)


@bot.tree.command(name="storage", description="[Owner only] Show bot system status")
async def storage(interaction: discord.Interaction):
    if not await interaction.client.is_owner(interaction.user):
        await interaction.response.send_message("❌ Only the bot owner can use this command.", ephemeral=True)
        return
    await interaction.response.send_message(build_storage_text())


@bot.command(name="storage")
@commands.is_owner()
async def storage_prefix(ctx: commands.Context):
    await ctx.reply(build_storage_text())


@bot.tree.command(name="stats", description="[Owner only] Show how many people use the bot")
async def stats(interaction: discord.Interaction):
    if not await interaction.client.is_owner(interaction.user):
        await interaction.response.send_message("❌ Only the bot owner can use this command.", ephemeral=True)
        return
    await interaction.response.send_message(build_stats_text())


@bot.command(name="stats")
@commands.is_owner()
async def stats_prefix(ctx: commands.Context):
    await ctx.reply(build_stats_text())


@bot.tree.command(name="activity", description="[Owner only] See which commands people have been using")
async def activity(interaction: discord.Interaction):
    if not await interaction.client.is_owner(interaction.user):
        await interaction.response.send_message("❌ Only the bot owner can use this command.", ephemeral=True)
        return
    await interaction.response.send_message(build_activity_text())


@bot.command(name="activity")
@commands.is_owner()
async def activity_prefix(ctx: commands.Context):
    await ctx.reply(build_activity_text())


@bot.tree.command(name="clearcache", description="[Owner only] Clear the bot's cache and free up memory")
async def clearcache(interaction: discord.Interaction):
    if not await interaction.client.is_owner(interaction.user):
        await interaction.response.send_message("❌ Only the bot owner can use this command.", ephemeral=True)
        return
    await interaction.response.send_message(build_clearcache_text())


@bot.command(name="clearcache")
@commands.is_owner()
async def clearcache_prefix(ctx: commands.Context):
    await ctx.reply(build_clearcache_text())


@bot.tree.command(name="fish", description="Go fishing for coins")
async def fish(interaction: discord.Interaction):
    await interaction.response.send_message(do_fish(did(interaction.user.id)))


@bot.command(name="fish")
async def fish_prefix(ctx: commands.Context):
    await ctx.reply(do_fish(did(ctx.author.id)))


@bot.tree.command(name="beg", description="Beg for some coins")
async def beg(interaction: discord.Interaction):
    await interaction.response.send_message(do_beg(did(interaction.user.id)))


@bot.command(name="beg")
async def beg_prefix(ctx: commands.Context):
    await ctx.reply(do_beg(did(ctx.author.id)))


@bot.tree.command(name="dig", description="Dig for buried coins")
async def dig(interaction: discord.Interaction):
    await interaction.response.send_message(do_dig(did(interaction.user.id)))


@bot.command(name="dig")
async def dig_prefix(ctx: commands.Context):
    await ctx.reply(do_dig(did(ctx.author.id)))


@bot.tree.command(name="daily", description="Claim your daily reward")
async def daily(interaction: discord.Interaction):
    await interaction.response.send_message(do_daily(did(interaction.user.id)))


@bot.command(name="daily")
async def daily_prefix(ctx: commands.Context):
    await ctx.reply(do_daily(did(ctx.author.id)))


@bot.tree.command(name="work", description="Work a job for coins")
async def work(interaction: discord.Interaction):
    await interaction.response.send_message(do_work(did(interaction.user.id)))


@bot.command(name="work")
async def work_prefix(ctx: commands.Context):
    await ctx.reply(do_work(did(ctx.author.id)))


@bot.tree.command(name="lb", description="Show the richest users")
async def lb(interaction: discord.Interaction):
    await interaction.response.send_message(build_leaderboard_text())


@bot.tree.command(name="top", description="Show the richest users")
async def top(interaction: discord.Interaction):
    await interaction.response.send_message(build_leaderboard_text())


@bot.command(name="lb", aliases=["top", "leaderboard"])
async def lb_prefix(ctx: commands.Context):
    await ctx.reply(build_leaderboard_text())


# ---------- Mines ----------

@bot.command(name="mines")
async def mines_prefix(ctx: commands.Context, *args):
    user_id = did(ctx.author.id)
    if len(args) == 0:
        await ctx.reply(MINES_HELP_TEXT)
        return
    if args[0].lower() == "cashout":
        await ctx.reply(cashout_mines(user_id))
        return
    if user_id in active_mines_games:
        if len(args) != 1:
            await ctx.reply("❌ Type `.mines <1-25>` to dig or `.mines cashout` to cash out.")
            return
        await ctx.reply(dig_mines(user_id, args[0]))
        return
    bet_str = args[0]
    mines_str = args[1] if len(args) > 1 else None
    await ctx.reply(start_mines(user_id, bet_str, mines_str))


@bot.tree.command(name="mines", description="Start a mines game")
@app_commands.describe(bet="Amount to bet, or 'all'", mines="Number of mines (1-24, default 3)")
async def mines_start(interaction: discord.Interaction, bet: str, mines: int = 3):
    await interaction.response.send_message(start_mines(did(interaction.user.id), bet, str(mines)))


@bot.tree.command(name="minesdig", description="Dig a square in your mines game")
@app_commands.describe(square="Square number (1-25)")
async def minesdig(interaction: discord.Interaction, square: int):
    await interaction.response.send_message(dig_mines(did(interaction.user.id), str(square)))


@bot.tree.command(name="minescashout", description="Cash out your mines game")
async def minescashout(interaction: discord.Interaction):
    await interaction.response.send_message(cashout_mines(did(interaction.user.id)))


@bot.tree.command(name="slot", description="Play the slot machine")
@app_commands.describe(amount="Amount to bet, or 'all'")
async def slot(interaction: discord.Interaction, amount: str):
    async def send_func(text):
        await interaction.response.send_message(text)
        return await interaction.original_response()

    async def edit_func(message, text):
        await interaction.edit_original_response(content=text)

    await run_slot(did(interaction.user.id), amount, send_func, edit_func)


@bot.command(name="slot")
async def slot_prefix(ctx: commands.Context, amount: str):
    async def send_func(text):
        return await ctx.reply(text)

    async def edit_func(message, text):
        await message.edit(content=text)

    await run_slot(did(ctx.author.id), amount, send_func, edit_func)


@bot.tree.command(name="roll", description="Roll a dice and bet on 4-6 to win")
@app_commands.describe(amount="Amount to bet, or 'all'")
async def roll(interaction: discord.Interaction, amount: str):
    await interaction.response.send_message(do_dice(did(interaction.user.id), amount))


@bot.command(name="roll")
async def roll_prefix(ctx: commands.Context, amount: str):
    await ctx.reply(do_dice(did(ctx.author.id), amount))


@bot.tree.command(name="cooldowns", description="Show your active cooldowns")
async def cooldowns(interaction: discord.Interaction):
    await interaction.response.send_message(build_cooldowns_text(did(interaction.user.id)))


@bot.command(name="cds", aliases=["cooldowns"])
async def cds_prefix(ctx: commands.Context):
    await ctx.reply(build_cooldowns_text(did(ctx.author.id)))


@bot.tree.command(name="donate", description="Donate money to another user")
@app_commands.describe(amount="Amount to donate, or 'all'", user="The user to donate to")
async def donate(interaction: discord.Interaction, amount: str, user: discord.User):
    if user.bot:
        await interaction.response.send_message("❌ You can't donate to a bot.")
        return
    donated, error = do_donate(did(interaction.user.id), did(user.id), amount)
    if error:
        await interaction.response.send_message(error)
        return
    await interaction.response.send_message(f"✅ Successfully donated ${donated:,} to {user.mention}")


@bot.command(name="donate")
async def donate_prefix(ctx: commands.Context, amount: str, user: discord.Member):
    if user.bot:
        await ctx.reply("❌ You can't donate to a bot.")
        return
    donated, error = do_donate(did(ctx.author.id), did(user.id), amount)
    if error:
        await ctx.reply(error)
        return
    await ctx.reply(f"✅ Successfully donated ${donated:,} to {user.mention}")


@bot.tree.command(name="auth", description="[Owner only] Toggle whether the bot responds in this server")
@app_commands.describe(state="on or off")
@app_commands.choices(state=[
    app_commands.Choice(name="on", value="on"),
    app_commands.Choice(name="off", value="off"),
])
async def auth(interaction: discord.Interaction, state: app_commands.Choice[str]):
    if not await interaction.client.is_owner(interaction.user):
        await interaction.response.send_message("❌ Only the bot owner can use this command.", ephemeral=True)
        return
    if interaction.guild is None:
        await interaction.response.send_message("❌ This command only works inside a server.")
        return
    auth_enabled[interaction.guild.id] = (state.value == "on")
    await interaction.response.send_message(f"🔐 Bot responses turned **{state.value}** for this server.")


@bot.command(name="auth")
@commands.is_owner()
async def auth_prefix(ctx: commands.Context, state: str):
    state = state.lower()
    if state not in ("on", "off"):
        await ctx.reply("❌ Use `.auth on` or `.auth off`.")
        return
    if ctx.guild is None:
        await ctx.reply("❌ This command only works inside a server.")
        return
    auth_enabled[ctx.guild.id] = (state == "on")
    await ctx.reply(f"🔐 Bot responses turned **{state}** for this server.")


@bot.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return

    # AFK handling
    if did(message.author.id) in afk_users:
        del afk_users[did(message.author.id)]
        await message.reply(f"Welcome back {message.author.mention}, I removed your afk.", mention_author=False)

    for user in message.mentions:
        if did(user.id) in afk_users:
            await message.reply(
                f"{user.display_name} is afk: {afk_users[did(user.id)]}",
                mention_author=False,
            )

    # KiraGPT continuous chat
    user_id = did(message.author.id)
    session = kiragpt_sessions.get(user_id)
    if session and session.get("active") and message.reference and message.content and message.content.strip():
        try:
            ref = message.reference.resolved
            if ref is None:
                ref = await message.channel.fetch_message(message.reference.message_id)
            if ref and ref.author.id == bot.user.id:
                async with message.channel.typing():
                    async def send_func(text, file=None):
                        if file:
                            await message.reply(text, file=file)
                        else:
                            await message.reply(text)
                    await handle_kiragpt_message(message.author, message.content, send_func)
                return
        except Exception as e:
            print(f"KiraGPT reply handling failed: {e}")

    await bot.process_commands(message)



if __name__ == "__main__":
    if not TOKEN:
        raise RuntimeError("DISCORD_TOKEN not found. Set it in your .env file.")
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL not found. Set it in your .env file.")
    init_db()

    # --- Keep-alive web server for Render's free tier ---
    # Render's free compute is only available to web services, and free
    # services sleep after 15 minutes with no HTTP traffic. This tiny Flask
    # server gives Render something to see as "web traffic" when an external
    # pinger (e.g. UptimeRobot) hits it every few minutes, so the bot never
    # goes idle. It runs in a background thread; the Discord bot itself still
    # runs on the main thread via bot.run() below.
    keep_alive_app = Flask(__name__)

    @keep_alive_app.route("/")
    def keep_alive_home():
        return "Kira bot is alive."

    def run_keep_alive():
        port = int(os.environ.get("PORT", 8080))
        keep_alive_app.run(host="0.0.0.0", port=port)

    threading.Thread(target=run_keep_alive, daemon=True).start()

    bot.run(TOKEN)
