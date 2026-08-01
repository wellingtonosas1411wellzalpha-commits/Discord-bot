import os
import random
import asyncio
import time
import math
import gc
import psutil
import psycopg2
import aiohttp
from aiohttp import web

import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")


def did(discord_id) -> str:
    """Namespaced key for a Discord user, so balances never collide with WhatsApp."""
    return f"discord:{discord_id}"


def wid(phone_number: str) -> str:
    """Namespaced key for a WhatsApp user (by phone number)."""
    return f"whatsapp:{phone_number}"

BOT_START_TIME = time.time()
BOT_VERSION = "1.0.0"
psutil.cpu_percent(interval=None)  # prime the reading

intents = discord.Intents.default()
intents.message_content = True


class AuthCheckedTree(app_commands.CommandTree):
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
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

active_mines_games = {}  # user_id -> game state
MINES_HOUSE_EDGE = 0.97

cf_cooldowns = {}  # user_id -> last used timestamp
roulette_cooldowns = {}  # user_id -> last used timestamp
fish_cooldowns = {}
beg_cooldowns = {}
dig_cooldowns = {}
slot_cooldowns = {}
dice_cooldowns = {}
CF_COOLDOWN_SECONDS = 60
ROULETTE_COOLDOWN_SECONDS = 180
FISH_COOLDOWN_SECONDS = 60
BEG_COOLDOWN_SECONDS = 60
DIG_COOLDOWN_SECONDS = 60
SLOT_COOLDOWN_SECONDS = 60
DICE_COOLDOWN_SECONDS = 60


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
WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN")
WHATSAPP_PHONE_NUMBER_ID = os.getenv("WHATSAPP_PHONE_NUMBER_ID")
WHATSAPP_VERIFY_TOKEN = os.getenv("WHATSAPP_VERIFY_TOKEN")
WHATSAPP_OWNER_NUMBER = os.getenv("WHATSAPP_OWNER_NUMBER", "")


def get_db():
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
    return conn, cur


def migrate_db():
    """One-time migration: convert an existing bigint user_id column to text
    so both Discord and WhatsApp IDs can share the same balances table."""
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


def get_balance(user_id: int):
    conn, cur = get_db()
    cur.execute("SELECT wallet, bank, limit_amt FROM balances WHERE user_id = %s", (user_id,))
    row = cur.fetchone()
    if row is None:
        cur.execute(
            "INSERT INTO balances (user_id, wallet, bank, limit_amt) VALUES (%s, %s, %s, %s)",
            (user_id, DEFAULT_WALLET, DEFAULT_BANK, DEFAULT_LIMIT),
        )
        conn.commit()
        wallet, bank, limit_amt = DEFAULT_WALLET, DEFAULT_BANK, DEFAULT_LIMIT
    else:
        wallet, bank, limit_amt = row
    cur.close()
    conn.close()
    return {"wallet": wallet, "bank": bank, "limit": limit_amt}


def update_balance(user_id: int, wallet=None, bank=None, limit_amt=None):
    bal = get_balance(user_id)  # ensures row exists
    new_wallet = bal["wallet"] if wallet is None else wallet
    new_bank = bal["bank"] if bank is None else bank
    new_limit = bal["limit"] if limit_amt is None else limit_amt
    conn, cur = get_db()
    cur.execute(
        "UPDATE balances SET wallet = %s, bank = %s, limit_amt = %s WHERE user_id = %s",
        (new_wallet, new_bank, new_limit, user_id),
    )
    conn.commit()
    cur.close()
    conn.close()


def get_meta(key: str):
    conn, cur = get_db()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS bot_meta (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    """)
    conn.commit()
    cur.execute("SELECT value FROM bot_meta WHERE key = %s", (key,))
    row = cur.fetchone()
    cur.close()
    conn.close()
    return row[0] if row else None


def set_meta(key: str, value: str):
    conn, cur = get_db()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS bot_meta (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    """)
    cur.execute(
        "INSERT INTO bot_meta (key, value) VALUES (%s, %s) "
        "ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value",
        (key, value),
    )
    conn.commit()
    cur.close()
    conn.close()


def build_balance_text(user_id: int):
    bal = get_balance(user_id)
    total = bal["wallet"] + bal["bank"]
    return (
        "╭━━━〔 💳 ᴀᴄᴄᴏᴜɴᴛ ʙᴀʟᴀɴᴄᴇ 〕━━━⬣\n"
        f"┃ 💰 ᴡᴀʟʟᴇᴛ : [ ${bal['wallet']:,} ]\n"
        f"┃ 🏦 ʙᴀɴᴋ   : [ ${bal['bank']:,} ]\n"
        f"┃ 📈 ʟɪᴍɪᴛ  : [ ${bal['limit']:,} ]\n"
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
        "┃\n"
        "┃ 𝕴𝖓𝖋𝖔\n"
        "┃ • avatar [user] — get a user's avatar\n"
        "┃ • userinfo [user] — get member info\n"
        "┃ • poll [question] — create a yes/no poll\n"
        "┃\n"
        "┃ 𝕰𝖈𝖔𝖓𝖔𝖒𝖞\n"
        "┃ • bal — check your balance\n"
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
        "┃\n"
        "┃ 𝕺𝖜𝖓𝖊𝖗 𝕮𝖔𝖒𝖒𝖆𝖓𝖉𝖘\n"
        "┃ • auth on/off — enable/disable bot in server\n"
        "┃ • storage — bot system status\n"
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
    print(f"Logged in as {bot.user} (ID: {bot.did(user.id)})")
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

    if did(message.author.id) in afk_users:
        del afk_users[did(message.author.id)]
        await message.reply(f"Welcome back {message.author.mention}, I removed your afk.", mention_author=False)

    for user in message.mentions:
        if did(user.id) in afk_users:
            await message.reply(
                f"{user.display_name} is afk: {afk_users[did(user.id)]}",
                mention_author=False,
            )

    await bot.process_commands(message)


# ---------- WhatsApp bridge ----------

async def send_whatsapp_message(to: str, text: str):
    if not (WHATSAPP_TOKEN and WHATSAPP_PHONE_NUMBER_ID):
        print("WhatsApp not configured — skipping send.")
        return
    url = f"https://graph.facebook.com/v21.0/{WHATSAPP_PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json",
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "text",
        "text": {"body": text},
    }
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=payload) as resp:
                if resp.status >= 300:
                    body = await resp.text()
                    print(f"WhatsApp send failed ({resp.status}): {body}")
    except Exception as e:
        print(f"WhatsApp send error: {e}")


async def run_roulette_whatsapp(user_id: str, color_choice: str, amount_str: str):
    """Roulette without the multi-step animation, since WhatsApp text messages can't be edited here."""
    color_choice = color_choice.lower()
    if color_choice not in ("red", "black", "green"):
        return "❌ Choose `red`, `black`, or `green`."
    bal = get_balance(user_id)
    try:
        amount = parse_amount(amount_str, all_value=bal["wallet"])
    except ValueError:
        return "❌ Invalid amount."
    if amount <= 0:
        return "❌ Enter an amount greater than $0."
    if amount > bal["wallet"]:
        return "❌ You don't have that much in your wallet."
    remaining = check_cooldown(roulette_cooldowns, user_id, ROULETTE_COOLDOWN_SECONDS)
    if remaining is not None:
        return f"⏳ Slow down! Try again in {int(remaining) + 1}s."

    update_balance(user_id, wallet=bal["wallet"] - amount)
    number, color, color_display = do_roulette_spin()
    won = color == color_choice
    if won:
        payout = amount * ROULETTE_MULTIPLIER[color_choice]
        new_bal = get_balance(user_id)
        update_balance(user_id, wallet=new_bal["wallet"] + payout)
    else:
        payout = 0
    final_bal = get_balance(user_id)
    return build_roulette_result_text(number, color_display, won, payout, final_bal["wallet"])


async def run_slot_whatsapp(user_id: str, amount_str: str):
    """Slots without the multi-step animation, for the same reason as roulette above."""
    bal = get_balance(user_id)
    try:
        amount = parse_amount(amount_str, all_value=bal["wallet"])
    except ValueError:
        return "❌ Invalid amount."
    if amount <= 0:
        return "❌ Enter an amount greater than $0."
    if amount > bal["wallet"]:
        return "❌ You don't have that much in your wallet."
    remaining = check_cooldown(slot_cooldowns, user_id, SLOT_COOLDOWN_SECONDS)
    if remaining is not None:
        return f"⏳ Slow down! Try again in {int(remaining) + 1}s."

    update_balance(user_id, wallet=bal["wallet"] - amount)
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
    return build_slot_spin_text(spin_display, footer)


WHATSAPP_UNSUPPORTED_NOTE = (
    "❌ That command needs Discord features (avatars, mentions, buttons) "
    "that don't exist on WhatsApp. Try it on Discord instead."
)


async def handle_whatsapp_command(sender: str, text_body: str):
    text_body = (text_body or "").strip()
    if not text_body:
        return None

    parts = text_body.split()
    cmd = parts[0].lower().lstrip(".").lstrip("/")
    args = parts[1:]
    uid = wid(sender)

    if cmd in ("menu", "help"):
        return build_menu_text()

    if cmd == "ping":
        return "🏓 Pong!"

    if cmd == "8ball":
        if not args:
            return "❌ Usage: .8ball <question>"
        return f"🎱 **Q:** {' '.join(args)}\n**A:** {get_8ball_answer()}"

    if cmd == "joke":
        return f"😄 {get_joke()}"

    if cmd == "bal":
        return build_balance_text(uid)

    if cmd in ("withdraw", "wd"):
        if not args:
            return "❌ Usage: .withdraw <amount|all>"
        return do_withdraw(uid, args[0])

    if cmd in ("deposit", "dep"):
        if not args:
            return "❌ Usage: .deposit <amount|all>"
        return do_deposit(uid, args[0])

    if cmd in ("cf", "coinflip"):
        if len(args) < 2:
            return "❌ Usage: .cf <heads/tails> <amount|all>"
        return await run_coinflip(uid, args[0], args[1])

    if cmd == "roll":
        if not args:
            return "❌ Usage: .roll <amount|all>"
        return do_dice(uid, args[0])

    if cmd == "roulette":
        if len(args) < 2:
            return "❌ Usage: .roulette <red/black/green> <amount|all>"
        return await run_roulette_whatsapp(uid, args[0], args[1])

    if cmd == "slot":
        if not args:
            return "❌ Usage: .slot <amount|all>"
        return await run_slot_whatsapp(uid, args[0])

    if cmd == "fish":
        return do_fish(uid)

    if cmd == "beg":
        return do_beg(uid)

    if cmd == "dig":
        return do_dig(uid)

    if cmd == "mines":
        if not args:
            return MINES_HELP_TEXT
        if args[0].lower() == "cashout":
            return cashout_mines(uid)
        if uid in active_mines_games:
            return dig_mines(uid, args[0])
        mines_count = args[1] if len(args) > 1 else None
        return start_mines(uid, args[0], mines_count)

    if cmd in ("cds", "cooldowns"):
        return build_cooldowns_text(uid)

    if cmd == "donate":
        if len(args) < 2:
            return "❌ Usage: .donate <amount> <phone number>"
        amount_str, target_number = args[0], args[1]
        donated, error = do_donate(uid, wid(target_number), amount_str)
        if error:
            return error
        return f"✅ Successfully donated ${donated:,} to {target_number}"

    if cmd == "afk":
        reason = " ".join(args) if args else "busy"
        afk_users[uid] = reason
        return f"You are now afk, reason: {reason}"

    if cmd in ("storage", "clearcache", "auth"):
        if not WHATSAPP_OWNER_NUMBER or sender != WHATSAPP_OWNER_NUMBER:
            return "❌ Only the bot owner can use this command."
        if cmd == "storage":
            return build_storage_text()
        if cmd == "clearcache":
            return build_clearcache_text()
        return "❌ Auth toggling isn't available on WhatsApp yet."

    if cmd in ("avatar", "userinfo", "poll"):
        return WHATSAPP_UNSUPPORTED_NOTE

    return None  # unknown text — stay silent rather than spam replies


async def whatsapp_verify(request: web.Request):
    mode = request.query.get("hub.mode")
    token = request.query.get("hub.verify_token")
    challenge = request.query.get("hub.challenge")
    if mode == "subscribe" and token and WHATSAPP_VERIFY_TOKEN and token == WHATSAPP_VERIFY_TOKEN:
        return web.Response(text=challenge or "")
    return web.Response(status=403)


async def whatsapp_receive(request: web.Request):
    try:
        data = await request.json()
        entry = data.get("entry", [])[0]
        change = entry.get("changes", [])[0]
        value = change.get("value", {})
        messages = value.get("messages")
        if messages:
            msg = messages[0]
            sender = msg.get("from")
            text_body = msg.get("text", {}).get("body", "")
            reply_text = await handle_whatsapp_command(sender, text_body)
            if reply_text and sender:
                await send_whatsapp_message(sender, reply_text)
    except (KeyError, IndexError):
        pass
    except Exception as e:
        print(f"Error handling WhatsApp webhook: {e}")
    return web.Response(text="EVENT_RECEIVED")


async def start_webhook_server():
    app = web.Application()
    app.router.add_get("/webhook", whatsapp_verify)
    app.router.add_post("/webhook", whatsapp_receive)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.getenv("PORT", 8080))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    print(f"WhatsApp webhook server listening on port {port}")


async def main():
    if not TOKEN:
        raise RuntimeError("DISCORD_TOKEN not found. Set it in your .env file.")
    migrate_db()
    await start_webhook_server()
    async with bot:
        await bot.start(TOKEN)


if __name__ == "__main__":
    asyncio.run(main())
