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
from discord.ext import tasks
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")


def did(discord_id) -> str:
    """Namespaced key for a Discord user's balance."""
    return f"discord:{discord_id}"

BOT_START_TIME = time.time()
BOT_VERSION = "1.11.4"

# Newest version first. Update this on every change.
VERSION_HISTORY = [
    {
        "version": "1.11.4",
        "date": "2026-08-30",
        "changes": [
            "Fixed a market race condition: cancelling a listing at the same instant someone else bought it could duplicate the item (buyer got it AND seller got it back). Cancel now uses the same row-locked, rowcount-checked pattern as buy",
        ],
    },
    {
        "version": "1.11.3",
        "date": "2026-08-30",
        "changes": [
            "First job paycheck now waits the full 3 days instead of paying on the next hourly check",
            ".shop / .buy no longer crash if used in DMs",
            "Market buy now deletes the listing, moves coins, and gives the item in one database commit",
            "Stopped posting update announcements in every server on startup",
        ],
    },
    {
        "version": "1.11.2",
        "date": "2026-08-30",
        "changes": [
            "Fixed .versions/.history failing with 'The application did not respond' — the full changelog had grown past Discord's 2000-character message limit, so the send itself was silently rejected; it now shows the most recent entries and notes how many older ones were left out",
        ],
    },
    {
        "version": "1.11.1",
        "date": "2026-08-30",
        "changes": [
            "Fixed /profile timing out with 'The application did not respond' — it does 7 database lookups (more than any other command), which could exceed Discord's 3-second response window; now defers the response and surfaces real errors instead of failing silently",
        ],
    },
    {
        "version": "1.11.0",
        "date": "2026-08-30",
        "changes": [
            "Added .profile — every stat for a player in one place: wallet/bank, level & XP, job & salary, pet, marriage partner, achievements progress, and inventory",
        ],
    },
    {
        "version": "1.10.0",
        "date": "2026-08-30",
        "changes": [
            "Added .take (Administrator-only) — strip a role from a user directly, mirrors .give",
            "Added .give/.take/.setlevelrole/.levelroles to the menu and help text (they existed but were missing from both)",
        ],
    },
    {
        "version": "1.9.3",
        "date": "2026-08-30",
        "changes": [
            "Fixed level roles failing silently — a missing role, missing bot permission, or role hierarchy issue now shows a warning instead of nothing at all",
            "Added .syncroles to retroactively re-apply any level role rewards you've earned but don't have",
        ],
    },
    {
        "version": "1.9.2",
        "date": "2026-08-30",
        "changes": [
            ".setjob no longer takes a job argument — it now randomly assigns one from the job pool",
        ],
    },
    {
        "version": "1.9.1",
        "date": "2026-08-30",
        "changes": [
            "Job salaries x10 across the board",
            "Salary now pays out every 3 days (was every 6 hours)",
            "Changing jobs (.setjob) is now limited to once every 2 weeks",
        ],
    },
    {
        "version": "1.9.0",
        "date": "2026-08-29",
        "changes": [
            "Added jobs & salary: .setjob pays out automatically every 6h, even offline, taxed into the server treasury",
            "Added bank interest: your .bank balance now earns 2% daily",
            "Added pets: .buypet, .feedpet, .collectpet, .pet — adopt a pet that earns passive income while fed",
            "Added marriage: .marry, .marryaccept, .divorce, .partner",
            "Added achievements: .achievements tracks milestones like First Blood, Jackpot, Veteran, and more",
            "Added a player market: .sell, .market, .buylisting, .cancellisting — trade global items with other players (5% tax)",
            "Added .treasury to see how much tax has been collected",
        ],
    },
    {
        "version": "1.8.4",
        "date": "2026-08-29",
        "changes": [
            "Removed dead account-linking code (account_links table + resolve_uid) — nothing ever wrote to it, so it was an unused DB lookup on every economy command",
            "Removed unused DEFAULT_LIMIT constant and an unused parameter on add_message_xp",
        ],
    },
    {
        "version": "1.8.3",
        "date": "2026-08-28",
        "changes": [
            "Added a version history log (.versions)",
        ],
    },
    {
        "version": "1.8.2",
        "date": "2026-08-28",
        "changes": [
            "Added Guard — blocks the next robbery against you, then is used up",
            "Guard costs 50,000 coins and is stackable",
        ],
    },
    {
        "version": "1.8.1",
        "date": "2026-08-27",
        "changes": [
            "Lucky Potion now also affects roulette, slot, mines, and blackjack",
            "KiraGPT's 50-reply limit now persists across restarts",
            "Buying a Gun/Fishing Rod/Shovel you already own is now blocked",
            "Removed unused leftover shop-admin code",
        ],
    },
    {
        "version": "1.8.0",
        "date": "2026-08-27",
        "changes": [
            "Global shop items: Vx, V9, Lucky Potion, Gun, Fishing Rod, Shovel",
            "Fish / dig / rob require the matching tool",
            "Short spaced menu + .help <command>",
        ],
    },
    {
        "version": "1.7.0",
        "date": "2026-08-22",
        "changes": [
            "Shop and inventory",
            "Blackjack, rob, level role rewards",
        ],
    },
]

LATEST_UPDATE_INFO = VERSION_HISTORY[0]
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
    help_command=None,
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
active_blackjack_games = {}  # user_id -> game state
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
DAILY_COOLDOWN_SECONDS = 86400
WORK_COOLDOWN_SECONDS = 3600


def apply_cd_boost(user_id, seconds: int) -> int:
    """Halve cooldown if Vx / V9 boost is active."""
    until = get_cd_boost_until(user_id)
    if until and time.time() < until:
        return max(1, seconds // 2)
    return seconds


def check_cooldown(cooldowns: dict, user_id: int, seconds: int):
    seconds = apply_cd_boost(user_id, seconds)
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


def check_persistent_cooldown(command_name: str, user_id: int, seconds: int):
    """Database-backed cooldown check that survives bot restarts. Use for
    long cooldowns (daily, work) where an in-memory dict getting wiped by a
    redeploy would let people bypass the limit. Returns remaining seconds if
    still on cooldown, else None (and records this use as the new start)."""
    seconds = apply_cd_boost(user_id, seconds)
    uid = user_id
    conn, cur = get_db()
    cur.execute(
        "SELECT last_used FROM persistent_cooldowns WHERE user_id = %s AND command_name = %s",
        (uid, command_name),
    )
    row = cur.fetchone()
    now = time.time()
    if row is not None:
        elapsed = now - row[0].timestamp()
        if elapsed < seconds:
            cur.close()
            release_db(conn)
            return seconds - elapsed
        cur.execute(
            "UPDATE persistent_cooldowns SET last_used = NOW() WHERE user_id = %s AND command_name = %s",
            (uid, command_name),
        )
    else:
        cur.execute(
            "INSERT INTO persistent_cooldowns (user_id, command_name, last_used) VALUES (%s, %s, NOW())",
            (uid, command_name),
        )
    conn.commit()
    cur.close()
    release_db(conn)
    return None


auth_enabled = {}  # guild_id -> bool (default True = enabled)

DEFAULT_WALLET = 50000
DEFAULT_BANK = 50000
XP_PER_MESSAGE_MIN = 15
XP_PER_MESSAGE_MAX = 25
XP_MESSAGE_COOLDOWN_SECONDS = 60
XP_LEVEL_UP_REWARD = 1000
ROB_COOLDOWN_SECONDS = 3600
ROB_SUCCESS_CHANCE = 0.45
ROB_MAX_STEAL_PERCENT = 0.25
ROB_FAIL_PENALTY_PERCENT = 0.10

TAX_RATE = 0.10  # skimmed off salary and successful robs, feeds the server treasury
TREASURY_META_KEY = "treasury_balance"

SALARY_INTERVAL_HOURS = 72  # every 3 days
JOBS = {
    "intern": {"label": "Intern", "pay": 20000},
    "developer": {"label": "Software Developer", "pay": 50000},
    "moderator": {"label": "Discord Moderator", "pay": 40000},
    "streamer": {"label": "Streamer", "pay": 60000},
    "chef": {"label": "Chef", "pay": 35000},
    "pilot": {"label": "Pilot", "pay": 80000},
}

SETJOB_COOLDOWN_SECONDS = 14 * 24 * 3600  # once every 2 weeks

MARKET_TAX_RATE = 0.05  # market sales are taxed lightly too

PET_TYPES = {
    "dog": {"name": "Dog", "price": 20000, "hourly_income": 300},
    "cat": {"name": "Cat", "price": 20000, "hourly_income": 300},
    "dragon": {"name": "Dragon", "price": 200000, "hourly_income": 2500},
    "hamster": {"name": "Hamster", "price": 5000, "hourly_income": 80},
}
PET_FEED_COST = 500
PET_HUNGER_PER_FEED = 40
PET_HUNGER_DECAY_PER_HOUR = 5  # hunger lost per hour since last feeding
PET_STARVING_THRESHOLD = 20  # below this, pet stops earning until fed

BANK_INTEREST_RATE = 0.02  # daily interest on bank balance

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
    cur.execute("""
        CREATE TABLE IF NOT EXISTS levels (
            user_id TEXT PRIMARY KEY,
            xp BIGINT NOT NULL DEFAULT 0,
            level INTEGER NOT NULL DEFAULT 1,
            last_xp_gain TIMESTAMPTZ
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS persistent_cooldowns (
            user_id TEXT NOT NULL,
            command_name TEXT NOT NULL,
            last_used TIMESTAMPTZ NOT NULL,
            PRIMARY KEY (user_id, command_name)
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS shop_items (
            item_id SERIAL PRIMARY KEY,
            guild_id TEXT NOT NULL,
            name TEXT NOT NULL,
            price BIGINT NOT NULL,
            description TEXT,
            role_id TEXT
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS inventory (
            user_id TEXT NOT NULL,
            item_id INTEGER NOT NULL,
            quantity INTEGER NOT NULL DEFAULT 1,
            PRIMARY KEY (user_id, item_id)
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS level_roles (
            guild_id TEXT NOT NULL,
            level INTEGER NOT NULL,
            role_id TEXT NOT NULL,
            PRIMARY KEY (guild_id, level)
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS global_inventory (
            user_id TEXT NOT NULL,
            item_key TEXT NOT NULL,
            quantity INTEGER NOT NULL DEFAULT 0,
            PRIMARY KEY (user_id, item_key)
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS user_effects (
            user_id TEXT PRIMARY KEY,
            lucky_stacks INTEGER NOT NULL DEFAULT 0,
            cd_boost_until DOUBLE PRECISION
        )
    """)
    cur.execute("ALTER TABLE user_effects ADD COLUMN IF NOT EXISTS kiragpt_reply_count INTEGER NOT NULL DEFAULT 0")
    cur.execute("""
        CREATE TABLE IF NOT EXISTS jobs (
            user_id TEXT PRIMARY KEY,
            job TEXT NOT NULL,
            last_salary TIMESTAMPTZ
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS marriages (
            user_id TEXT PRIMARY KEY,
            partner_id TEXT NOT NULL,
            married_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS pets (
            user_id TEXT PRIMARY KEY,
            pet_type TEXT NOT NULL,
            pet_name TEXT NOT NULL,
            hunger INTEGER NOT NULL DEFAULT 100,
            last_fed TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            last_collected TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS achievements (
            user_id TEXT NOT NULL,
            achievement_key TEXT NOT NULL,
            earned_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            PRIMARY KEY (user_id, achievement_key)
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS market_listings (
            listing_id SERIAL PRIMARY KEY,
            seller_id TEXT NOT NULL,
            item_key TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            price BIGINT NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)
    conn.commit()
    cur.close()
    db_pool.putconn(conn)


def get_balance(user_id: int):
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


def xp_for_level(level: int) -> int:
    """Total XP required to reach the given level. Simple increasing curve."""
    return 5 * (level ** 2) + 50 * level + 100


def get_level_data(user_id: int):
    conn, cur = get_db()
    cur.execute("SELECT xp, level, last_xp_gain FROM levels WHERE user_id = %s", (user_id,))
    row = cur.fetchone()
    if row is None:
        cur.execute(
            "INSERT INTO levels (user_id, xp, level) VALUES (%s, 0, 1)",
            (user_id,),
        )
        conn.commit()
        xp, level, last_xp_gain = 0, 1, None
    else:
        xp, level, last_xp_gain = row
    cur.close()
    release_db(conn)
    return {"xp": xp, "level": level, "last_xp_gain": last_xp_gain}


def get_level_role(guild_id: int, level: int):
    """Returns the role_id configured for this level in this guild, or None."""
    conn, cur = get_db()
    cur.execute(
        "SELECT role_id FROM level_roles WHERE guild_id = %s AND level = %s",
        (str(guild_id), level),
    )
    row = cur.fetchone()
    cur.close()
    release_db(conn)
    return int(row[0]) if row else None


def set_level_role(guild_id: int, level: int, role_id: int):
    conn, cur = get_db()
    cur.execute(
        "INSERT INTO level_roles (guild_id, level, role_id) VALUES (%s, %s, %s) "
        "ON CONFLICT (guild_id, level) DO UPDATE SET role_id = EXCLUDED.role_id",
        (str(guild_id), level, str(role_id)),
    )
    conn.commit()
    cur.close()
    release_db(conn)


def list_level_roles(guild_id: int):
    conn, cur = get_db()
    cur.execute(
        "SELECT level, role_id FROM level_roles WHERE guild_id = %s ORDER BY level",
        (str(guild_id),),
    )
    rows = cur.fetchall()
    cur.close()
    release_db(conn)
    return rows


def add_message_xp(user_id: int):
    """Award XP for a message, respecting a per-user cooldown. Returns the new
    level if the user leveled up this call, else None."""
    data = get_level_data(user_id)
    now = time.time()
    if data["last_xp_gain"] is not None:
        elapsed = now - data["last_xp_gain"].timestamp()
        if elapsed < XP_MESSAGE_COOLDOWN_SECONDS:
            return None

    gained = random.randint(XP_PER_MESSAGE_MIN, XP_PER_MESSAGE_MAX)
    new_xp = data["xp"] + gained
    new_level = data["level"]
    leveled_up = False
    while new_xp >= xp_for_level(new_level):
        new_xp -= xp_for_level(new_level)
        new_level += 1
        leveled_up = True

    conn, cur = get_db()
    cur.execute(
        "UPDATE levels SET xp = %s, level = %s, last_xp_gain = NOW() WHERE user_id = %s",
        (new_xp, new_level, user_id),
    )
    conn.commit()
    cur.close()
    release_db(conn)

    if leveled_up:
        bal = get_balance(user_id)
        update_balance(user_id, wallet=bal["wallet"] + XP_LEVEL_UP_REWARD)
        return new_level
    return None


def get_xp_leaderboard(limit: int = 10):
    """Returns a list of (user_id, level, xp) tuples, highest level first."""
    conn, cur = get_db()
    cur.execute(
        "SELECT user_id, level, xp FROM levels ORDER BY level DESC, xp DESC LIMIT %s",
        (limit,),
    )
    rows = cur.fetchall()
    cur.close()
    release_db(conn)
    return rows


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


def get_treasury() -> int:
    value = get_meta(TREASURY_META_KEY)
    return int(value) if value else 0


def add_to_treasury(amount: int):
    if amount <= 0:
        return
    set_meta(TREASURY_META_KEY, str(get_treasury() + amount))


def apply_tax(amount: int, rate: float = TAX_RATE):
    """Splits an amount into (net, tax). The tax portion is added to the
    server treasury. Use this on salary and successful robs."""
    if amount <= 0:
        return amount, 0
    tax = int(amount * rate)
    net = amount - tax
    add_to_treasury(tax)
    return net, tax



def build_balance_text(user_id: int):
    bal = get_balance(user_id)
    total = bal["wallet"] + bal["bank"]
    achievement_line = ""
    if total >= 1_000_000 and grant_achievement(user_id, "high_roller"):
        achievement_line = f"┃\n┃ 🏅 Achievement unlocked: **{ACHIEVEMENTS['high_roller']['label']}**\n"
    return (
        "╭━━━〔 💳 ᴀᴄᴄᴏᴜɴᴛ ʙᴀʟᴀɴᴄᴇ 〕━━━⬣\n"
        f"┃ 💰 ᴡᴀʟʟᴇᴛ : [ ${bal['wallet']:,} ]\n"
        f"┃ 🏦 ʙᴀɴᴋ   : [ ${bal['bank']:,} ]\n"
        "┃\n"
        f"┃ 💠 ᴛᴏᴛᴀʟ  : [ ${total:,} ]\n"
        f"{achievement_line}"
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


COMMAND_HELP = {
    "ping": "Check the bot's latency.\nUsage: `.ping`",
    "8ball": "Ask the magic 8-ball a question.\nUsage: `.8ball <question>`",
    "joke": "Get a random joke.\nUsage: `.joke`",
    "kiragpt": "Talk to KiraGPT.\n`.kiragpt on/off` continuous chat\n`.kiragpt wild on` / `ai on` / `normal on`\n`.kiragpt <message>`",
    "translate": "Translate text.\nUsage: `.translate <language> <text>`",
    "trt": "Reply to a message to translate it.\nUsage: `.trt <language>`",
    "avatar": "Get a user's avatar.\nUsage: `.avatar [user]`",
    "userinfo": "Get member info.\nUsage: `.userinfo [user]`",
    "profile": "See every stat for a player in one place: economy, level, job, pet, marriage, achievements, and inventory.\nUsage: `.profile [user]`",
    "poll": "Create a yes/no poll.\nUsage: `.poll <question>`",
    "updateinfo": "See the latest bot update notes.\nUsage: `.updateinfo`",
    "versions": "See the full version history log.\nUsage: `.versions`",
    "bal": "Check wallet and bank balance.\nUsage: `.bal`",
    "daily": "Claim daily coins (24h cooldown).\nUsage: `.daily`",
    "work": "Work a job for coins (1h cooldown).\nUsage: `.work`",
    "lb": "Show the richest users.\nUsage: `.lb` or `.top`",
    "rank": "Check level and XP.\nUsage: `.rank [user]`",
    "ranklb": "Level leaderboard.\nUsage: `.ranklb`",
    "withdraw": "Move coins from bank to wallet.\nUsage: `.withdraw <amount|all>`",
    "deposit": "Move coins from wallet to bank.\nUsage: `.deposit <amount|all>`",
    "fish": "Fish for coins. Requires a Fishing Rod (`.buy fishing rod`).\nUsage: `.fish`",
    "beg": "Beg for coins (1m cooldown).\nUsage: `.beg`",
    "dig": "Dig for coins. Requires a Shovel (`.buy shovel`).\nUsage: `.dig`",
    "rob": "Try to steal coins. Requires a Gun (`.buy gun`).\nUsage: `.rob @user`",
    "shop": "View global and server shop items.\nUsage: `.shop`",
    "buy": "Buy an item.\nUsage: `.buy vx` / `.buy gun` / `.buy <id>`",
    "use": "Use a consumable item.\nUsage: `.use vx` / `.use v9` / `.use lucky`",
    "inventory": "See owned items.\nUsage: `.inventory [user]`",
    "cf": "Bet on a coinflip.\nUsage: `.cf heads/tails <amount|all>`",
    "roll": "Dice roll. 4-6 wins.\nUsage: `.roll <amount|all>`",
    "roulette": "Bet on red/black/green.\nUsage: `.roulette <color> <amount|all>`",
    "mines": "Mines game.\nUsage: `.mines <bet> [mines]` then `.mines <1-25>` or `.mines cashout`",
    "blackjack": "Blackjack.\nUsage: `.blackjack <bet>` then `.blackjack hit` or `.blackjack stand`",
    "slot": "Slot machine.\nUsage: `.slot <amount|all>`",
    "afk": "Set yourself AFK.\nUsage: `.afk [reason]`",
    "cds": "Show your cooldowns.\nUsage: `.cds`",
    "donate": "Send coins to someone.\nUsage: `.donate <amount|all> @user`",
    "help": "Show info for one command.\nUsage: `.help <command>`",
    "menu": "Show the short command list.\nUsage: `.menu`",
    "setjob": "Get randomly assigned a job that pays a salary automatically every 3 days, even offline. You can only reroll once every 2 weeks.\nUsage: `.setjob`",
    "myjob": "See your current job and salary.\nUsage: `.myjob`",
    "jobs": "List available jobs and their pay.\nUsage: `.jobs`",
    "treasury": "See the server treasury, funded by taxes.\nUsage: `.treasury`",
    "buypet": "Adopt a pet that earns passive income.\nUsage: `.buypet <type> <name>`",
    "feedpet": "Feed your pet so it keeps earning.\nUsage: `.feedpet`",
    "collectpet": "Collect the coins your pet has earned.\nUsage: `.collectpet`",
    "pet": "See your (or someone else's) pet.\nUsage: `.pet [user]`",
    "marry": "Propose marriage to another user.\nUsage: `.marry @user`",
    "marryaccept": "Accept a pending marriage proposal.\nUsage: `.marryaccept`",
    "divorce": "End your marriage.\nUsage: `.divorce`",
    "partner": "See who someone is married to.\nUsage: `.partner [user]`",
    "achievements": "See your (or someone else's) achievements.\nUsage: `.achievements [user]`",
    "sell": "List an item for sale on the player market (5% tax on sale).\nUsage: `.sell <item> <quantity> <price>`",
    "market": "Browse the player market.\nUsage: `.market`",
    "buylisting": "Buy a listing from the player market.\nUsage: `.buylisting <id>`",
    "cancellisting": "Cancel your own market listing.\nUsage: `.cancellisting <id>`",
    "syncroles": "Re-apply any level role rewards you've earned but don't have (fixes cases where auto-assignment failed, e.g. a bot permissions issue).\nUsage: `.syncroles`",
    "give": "[Admin] Give a role to a user directly.\nUsage: `.give @user @role`",
    "take": "[Admin] Strip a role from a user directly.\nUsage: `.take @user @role`",
    "setlevelrole": "[Admin] Set a role reward for reaching a level.\nUsage: `.setlevelrole <level> @role`",
    "levelroles": "See all configured level role rewards.\nUsage: `.levelroles`",
}


def build_menu_text():
    return (
        "╭━━━〔 Command Menu 〕━━━⬣\n"
        "┃\n"
        "┃ Type `.help <command>` for details\n"
        "┃\n"
        "┃ ── KiraGPT ──\n"
        "┃ • kiragpt on / off\n"
        "┃ • kiragpt wild on / ai on / normal on\n"
        "┃ • kiragpt <message>\n"
        "┃\n"
        "┃ ── Fun ──\n"
        "┃ • ping\n"
        "┃ • 8ball\n"
        "┃ • joke\n"
        "┃ • translate\n"
        "┃ • trt\n"
        "┃\n"
        "┃ ── Info ──\n"
        "┃ • avatar\n"
        "┃ • userinfo\n"
        "┃ • profile\n"
        "┃ • poll\n"
        "┃ • updateinfo\n"
        "┃ • versions\n"
        "┃\n"
        "┃ ── Economy ──\n"
        "┃ • bal\n"
        "┃ • daily\n"
        "┃ • work\n"
        "┃ • lb\n"
        "┃ • rank\n"
        "┃ • ranklb\n"
        "┃ • withdraw\n"
        "┃ • deposit\n"
        "┃ • fish\n"
        "┃ • beg\n"
        "┃ • dig\n"
        "┃ • rob\n"
        "┃\n"
        "┃ ── Jobs & Salary ──\n"
        "┃ • jobs\n"
        "┃ • setjob\n"
        "┃ • myjob\n"
        "┃ • treasury\n"
        "┃\n"
        "┃ ── Pets ──\n"
        "┃ • buypet\n"
        "┃ • feedpet\n"
        "┃ • collectpet\n"
        "┃ • pet\n"
        "┃\n"
        "┃ ── Marriage ──\n"
        "┃ • marry\n"
        "┃ • marryaccept\n"
        "┃ • divorce\n"
        "┃ • partner\n"
        "┃\n"
        "┃ ── Achievements ──\n"
        "┃ • achievements\n"
        "┃\n"
        "┃ ── Market ──\n"
        "┃ • sell\n"
        "┃ • market\n"
        "┃ • buylisting\n"
        "┃ • cancellisting\n"
        "┃ • syncroles\n"
        "┃\n"
        "┃ ── Shop ──\n"
        "┃ • shop\n"
        "┃ • buy\n"
        "┃ • use\n"
        "┃ • inventory\n"
        "┃\n"
        "┃ ── Gambling ──\n"
        "┃ • cf\n"
        "┃ • roll\n"
        "┃ • roulette\n"
        "┃ • mines\n"
        "┃ • blackjack\n"
        "┃ • slot\n"
        "┃\n"
        "┃ ── Utility ──\n"
        "┃ • afk\n"
        "┃ • cds\n"
        "┃ • donate\n"
        "┃ • help\n"
        "┃\n"
        "┃ ── Admin ──\n"
        "┃ • give\n"
        "┃ • take\n"
        "┃ • setlevelrole\n"
        "┃ • levelroles\n"
        "┃\n"
        "┃ ── Owner ──\n"
        "┃ • auth\n"
        "┃ • storage\n"
        "┃ • stats\n"
        "┃ • activity\n"
        "┃ • clearcache\n"
        "┃\n"
        "╰━━━━━━━━━━━━━━━━━━━━━━⬣"
    )


def build_help_text(name: str) -> str:
    key = name.strip().lower().lstrip("./")
    aliases = {
        "coinflip": "cf", "wd": "withdraw", "dep": "deposit",
        "inv": "inventory", "top": "leaderboard", "leaderboard": "lb",
        "cooldowns": "cds", "bj": "blackjack", "lucky": "use",
    }
    key = aliases.get(key, key)
    info = COMMAND_HELP.get(key)
    if not info:
        return f"❌ No help found for `{name}`.\nUse `.menu` to see command names."
    return f"╭━━━〔 ❓ {key} 〕━━━⬣\n┃ {info.replace(chr(10), chr(10) + '┃ ')}\n╰━━━━━━━━━━━━━━━━━━━━━━⬣"


def format_uptime(seconds: float):
    seconds = int(seconds)
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60
    return f"{h}h {m}m {s}s"


def build_storage_text():
    uptime = time.time() - BOT_START_TIME
    process = psutil.Process()
    proc_mb = process.memory_info().rss / (1024 * 1024)
    mem = psutil.virtual_memory()
    cpu = psutil.cpu_percent(interval=None)
    latency = round(bot.latency * 1000) if bot.latency else 0
    return (
        "⚙️ *Bot Storage / Status*\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        f"🕒 Uptime: {format_uptime(uptime)}\n"
        f"📡 Ping: {latency}ms\n"
        f"🏠 Servers: {len(bot.guilds)}\n"
        f"👤 Cached users: {len(bot.users)}\n"
        f"💬 Cached messages: {len(bot.cached_messages)}\n"
        f"🧠 KiraGPT sessions: {len(kiragpt_sessions)}\n"
        f"💣 Active mines games: {len(active_mines_games)}\n"
        f"🃏 Active blackjack games: {len(active_blackjack_games)}\n"
        f"💾 Bot RAM: {proc_mb:.1f} MB\n"
        f"🖥️ System RAM: {mem.percent}% used\n"
        f"⚙️ CPU: {cpu}%\n"
        f"📦 Version: {BOT_VERSION}\n"
        "━━━━━━━━━━━━━━━━━━━"
    )


def do_clearcache():
    process = psutil.Process()
    before_mb = process.memory_info().rss / (1024 * 1024)

    sessions_cleared = len(kiragpt_sessions)
    kiragpt_sessions.clear()

    mines_cleared = len(active_mines_games)
    active_mines_games.clear()

    bj_cleared = len(active_blackjack_games)
    active_blackjack_games.clear()

    afk_cleared = len(afk_users)
    afk_users.clear()

    for bucket in (
        cf_cooldowns, roulette_cooldowns, fish_cooldowns, beg_cooldowns,
        dig_cooldowns, slot_cooldowns, dice_cooldowns,
    ):
        bucket.clear()

    collected = gc.collect()
    after_mb = process.memory_info().rss / (1024 * 1024)
    freed_mb = max(0.0, before_mb - after_mb)

    return (
        "🧹 *Cache Cleared*\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        f"🧠 KiraGPT sessions wiped: {sessions_cleared}\n"
        f"💣 Mines games ended: {mines_cleared}\n"
        f"🃏 Blackjack games ended: {bj_cleared}\n"
        f"💤 AFK entries removed: {afk_cleared}\n"
        f"⏱️ Memory cooldowns reset\n"
        f"🗑️ GC objects collected: {collected}\n"
        f"💾 RAM change: {freed_mb:.2f} MB\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        "✅ Bot cache was actually cleared."
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
    if not has_global_item(user_id, "fishing_rod"):
        return "❌ You need a **Fishing Rod** first. Buy one with `.buy fishing rod` (1,000 coins)."
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
    if not has_global_item(user_id, "shovel"):
        return "❌ You need a **Shovel** first. Buy one with `.buy shovel` (1,000 coins)."
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
    remaining = check_persistent_cooldown("daily", user_id, DAILY_COOLDOWN_SECONDS)
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
    remaining = check_persistent_cooldown("work", user_id, WORK_COOLDOWN_SECONDS)
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


# ---------- Jobs & Salary ----------
# A persistent job (separate from the one-off flavor text in .work) that
# pays out automatically on a timer via the salary_payout_loop task below,
# even while you're offline. Salary is taxed; the tax feeds the treasury.

def set_job(user_id, job_key: str):
    remaining = check_persistent_cooldown("setjob", user_id, SETJOB_COOLDOWN_SECONDS)
    if remaining is not None:
        days = int(remaining // 86400)
        hours = int((remaining % 86400) // 3600)
        return f"⏳ You can only change jobs once every 2 weeks. Try again in **{days}d {hours}h**."
    conn, cur = get_db()
    cur.execute(
        "INSERT INTO jobs (user_id, job, last_salary) VALUES (%s, %s, NOW()) "
        "ON CONFLICT (user_id) DO UPDATE SET job = EXCLUDED.job, last_salary = NOW()",
        (user_id, job_key),
    )
    conn.commit()
    cur.close()
    release_db(conn)
    return f"🎲 You've been assigned a job: **{JOBS[job_key]['label']}**! Salary: **${JOBS[job_key]['pay']:,}** every {SALARY_INTERVAL_HOURS // 24} days."


def get_job(user_id):
    conn, cur = get_db()
    cur.execute("SELECT job FROM jobs WHERE user_id = %s", (user_id,))
    row = cur.fetchone()
    cur.close()
    release_db(conn)
    return row[0] if row else None


def get_all_jobholders():
    """Returns a list of (user_id, job) for everyone with a job set."""
    conn, cur = get_db()
    cur.execute("SELECT user_id, job FROM jobs")
    rows = cur.fetchall()
    cur.close()
    release_db(conn)
    return rows


def build_myjob_text(user_id) -> str:
    job_key = get_job(user_id)
    if not job_key:
        return "❌ You don't have a job yet. Get one with `.setjob` (it's randomly assigned)."
    info = JOBS[job_key]
    return (
        f"💼 You work as a **{info['label']}**\n"
        f"💰 Salary: **${info['pay']:,}** every **{SALARY_INTERVAL_HOURS // 24} days** (before tax)\n"
        f"🔁 You can reroll once every 2 weeks (`.setjob`)"
    )


def build_jobs_list_text() -> str:
    lines = ["╭━━━〔 💼 ᴀᴠᴀɪʟᴀʙʟᴇ ᴊᴏʙs 〕━━━⬣", "┃"]
    for key, info in JOBS.items():
        lines.append(f"┃ `{key}` — {info['label']} — ${info['pay']:,}/{SALARY_INTERVAL_HOURS // 24}d")
    lines.append("┃")
    lines.append("┃ Get randomly assigned one with `.setjob` (once every 2 weeks)")
    lines.append("╰━━━━━━━━━━━━━━━━━━━━━━⬣")
    return "\n".join(lines)


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

    dodged = False
    if position in game["mine_positions"]:
        dodge_chance = min(0.9, 0.5 * get_lucky_stacks(user_id))
        if random.random() < dodge_chance:
            # Lucky Potion: dodge the mine by relocating it elsewhere on the
            # board, so the total mine count (and payout math) stays the same.
            available = [
                p for p in range(1, 26)
                if p not in game["revealed"] and p != position and p not in game["mine_positions"]
            ]
            game["mine_positions"].discard(position)
            if available:
                game["mine_positions"].add(random.choice(available))
            dodged = True
        else:
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

    text = build_mines_progress_text(game)
    if dodged:
        text = "🍀 Lucky Potion saved you from a mine!\n" + text
    return text


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


# ---------- Blackjack ----------

BLACKJACK_RANKS = ["2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K", "A"]
BLACKJACK_SUITS = ["♠", "♥", "♦", "♣"]


def new_blackjack_deck():
    deck = [(rank, suit) for rank in BLACKJACK_RANKS for suit in BLACKJACK_SUITS]
    random.shuffle(deck)
    return deck


def card_value(rank: str) -> int:
    if rank in ("J", "Q", "K"):
        return 10
    if rank == "A":
        return 11
    return int(rank)


def hand_total(hand):
    total = sum(card_value(rank) for rank, _ in hand)
    aces = sum(1 for rank, _ in hand if rank == "A")
    while total > 21 and aces > 0:
        total -= 10
        aces -= 1
    return total


def format_hand(hand):
    return " ".join(f"{rank}{suit}" for rank, suit in hand)


def build_blackjack_text(game, reveal_dealer=False, result_line=None):
    player_total = hand_total(game["player"])
    lines = ["🃏 *BLACKJACK* 🃏", "──────────────────"]
    if reveal_dealer:
        dealer_total = hand_total(game["dealer"])
        lines.append(f"Dealer: {format_hand(game['dealer'])} ({dealer_total})")
    else:
        lines.append(f"Dealer: {game['dealer'][0][0]}{game['dealer'][0][1]} 🂠")
    lines.append(f"You: {format_hand(game['player'])} ({player_total})")
    lines.append("──────────────────")
    lines.append(f"Bet: ${game['bet']:,}")
    if result_line:
        lines.append("")
        lines.append(result_line)
    else:
        lines.append("")
        lines.append("👉 `.blackjack hit` to draw, `.blackjack stand` to hold.")
    return "\n".join(lines)


def start_blackjack(user_id: int, bet_str: str):
    if user_id in active_blackjack_games:
        return "❌ You already have a blackjack game running. Finish it first."

    bal = get_balance(user_id)
    try:
        bet = parse_amount(bet_str, all_value=bal["wallet"])
    except ValueError:
        return "❌ Invalid bet amount."
    if bet <= 0:
        return "❌ Enter a bet greater than $0."
    if bet > bal["wallet"]:
        return "❌ You don't have that much in your wallet."

    update_balance(user_id, wallet=bal["wallet"] - bet)

    deck = new_blackjack_deck()
    player = [deck.pop(), deck.pop()]
    dealer = [deck.pop(), deck.pop()]
    game = {"deck": deck, "player": player, "dealer": dealer, "bet": bet}

    if hand_total(player) == 21:
        return resolve_blackjack(user_id, game, natural=True)

    active_blackjack_games[user_id] = game
    return build_blackjack_text(game)


def resolve_blackjack(user_id: int, game, natural=False, player_bust=False):
    bet = game["bet"]
    if user_id in active_blackjack_games:
        del active_blackjack_games[user_id]

    if player_bust:
        return build_blackjack_text(
            game, reveal_dealer=True,
            result_line=f"💥 Bust! You lost **${bet:,}**.",
        )

    if natural:
        payout = int(bet * 2.5)
        bal = get_balance(user_id)
        update_balance(user_id, wallet=bal["wallet"] + payout)
        result_line = f"🎉 Blackjack! You won **${payout:,}**!"
        if grant_achievement(user_id, "blackjack_natural"):
            result_line += f"\n🏅 Achievement unlocked: **{ACHIEVEMENTS['blackjack_natural']['label']}**"
        return build_blackjack_text(
            game, reveal_dealer=True,
            result_line=result_line,
        )

    # Dealer draws until 17+
    while hand_total(game["dealer"]) < 17:
        game["dealer"].append(game["deck"].pop())

    player_total = hand_total(game["player"])
    dealer_total = hand_total(game["dealer"])

    if dealer_total > 21 or player_total > dealer_total:
        payout = bet * 2
        bal = get_balance(user_id)
        update_balance(user_id, wallet=bal["wallet"] + payout)
        result_line = f"🎉 You won **${payout:,}**!"
    elif player_total == dealer_total:
        bal = get_balance(user_id)
        update_balance(user_id, wallet=bal["wallet"] + bet)
        result_line = f"🤝 Push! Your **${bet:,}** bet was returned."
    else:
        if random.random() < min(0.9, 0.5 * get_lucky_stacks(user_id)):
            payout = bet * 2
            bal = get_balance(user_id)
            update_balance(user_id, wallet=bal["wallet"] + payout)
            result_line = f"🍀 Lucky save! You won **${payout:,}**!"
        else:
            result_line = f"😔 You lost **${bet:,}**."

    return build_blackjack_text(game, reveal_dealer=True, result_line=result_line)


def hit_blackjack(user_id: int):
    game = active_blackjack_games.get(user_id)
    if not game:
        return "❌ No active blackjack game. Start one with `.blackjack <bet>`."

    game["player"].append(game["deck"].pop())
    if hand_total(game["player"]) > 21:
        return resolve_blackjack(user_id, game, player_bust=True)
    return build_blackjack_text(game)


def stand_blackjack(user_id: int):
    game = active_blackjack_games.get(user_id)
    if not game:
        return "❌ No active blackjack game. Start one with `.blackjack <bet>`."
    return resolve_blackjack(user_id, game)


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

    # Lucky Potion: if it was a total loss, give a chance to upgrade it to
    # a partial win (2 matching), matching the "win-rate boost" the item promises.
    if max_count == 1 and random.random() < min(0.9, 0.5 * get_lucky_stacks(user_id)):
        symbol = random.choice(SLOT_SYMBOLS)
        spin = [symbol, symbol, random.choice([s for s in SLOT_SYMBOLS if s != symbol])]
        random.shuffle(spin)
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

    newly_earned = False
    if max_count == 3:
        newly_earned = grant_achievement(user_id, "jackpot")

    if payout > 0:
        footer = f"🎉 *YOU WON!* 🎉\nPayout: ${payout:,}\n\n💵 Wallet: ${final_bal['wallet']:,}"
    else:
        footer = f"💥 *YOU LOST!* 💥\nBetter luck next time.\n\n💵 Wallet: ${final_bal['wallet']:,}"
    if newly_earned:
        footer += f"\n🏅 Achievement unlocked: **{ACHIEVEMENTS['jackpot']['label']}**"

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
    if not won and random.random() < min(0.9, 0.5 * get_lucky_stacks(user_id)):
        won = True
        roll = random.randint(4, 6)


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


def get_remaining_persistent_cooldown(command_name: str, user_id: int, seconds: int):
    """Read-only check for a persistent cooldown, does not start/reset it."""
    uid = user_id
    conn, cur = get_db()
    cur.execute(
        "SELECT last_used FROM persistent_cooldowns WHERE user_id = %s AND command_name = %s",
        (uid, command_name),
    )
    row = cur.fetchone()
    cur.close()
    release_db(conn)
    if row is None:
        return None
    elapsed = time.time() - row[0].timestamp()
    if elapsed < seconds:
        return seconds - elapsed
    return None


COOLDOWN_REGISTRY = [
    ("Coinflip (.cf)", cf_cooldowns, CF_COOLDOWN_SECONDS),
    ("Roulette (.roulette)", roulette_cooldowns, ROULETTE_COOLDOWN_SECONDS),
    ("Fish (.fish)", fish_cooldowns, FISH_COOLDOWN_SECONDS),
    ("Beg (.beg)", beg_cooldowns, BEG_COOLDOWN_SECONDS),
    ("Dig (.dig)", dig_cooldowns, DIG_COOLDOWN_SECONDS),
    ("Slot (.slot)", slot_cooldowns, SLOT_COOLDOWN_SECONDS),
    ("Dice (.roll)", dice_cooldowns, DICE_COOLDOWN_SECONDS),
]

# Cooldowns tracked in the database rather than memory, so they survive
# restarts. Kept separate from COOLDOWN_REGISTRY since they're read differently.
PERSISTENT_COOLDOWN_REGISTRY = [
    ("Daily (.daily)", "daily", DAILY_COOLDOWN_SECONDS),
    ("Work (.work)", "work", WORK_COOLDOWN_SECONDS),
    ("Rob (.rob)", "rob", ROB_COOLDOWN_SECONDS),
]


def build_cooldowns_text(user_id: int):
    lines = []
    for label, cooldowns, seconds in COOLDOWN_REGISTRY:
        remaining = get_remaining_cooldown(cooldowns, user_id, seconds)
        if remaining is not None:
            lines.append(f"┃ ⏳ {label}: {int(remaining) + 1}s left")

    for label, command_name, seconds in PERSISTENT_COOLDOWN_REGISTRY:
        remaining = get_remaining_persistent_cooldown(command_name, user_id, seconds)
        if remaining is not None:
            hours = int(remaining // 3600)
            mins = int((remaining % 3600) // 60)
            secs = int(remaining % 60)
            if hours:
                lines.append(f"┃ ⏳ {label}: {hours}h {mins}m left")
            else:
                lines.append(f"┃ ⏳ {label}: {mins}m {secs}s left")

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


# ---------- Shop / Inventory ----------

def get_shop_items(guild_id: int):
    conn, cur = get_db()
    cur.execute(
        "SELECT item_id, name, price, description, role_id FROM shop_items "
        "WHERE guild_id = %s ORDER BY price",
        (str(guild_id),),
    )
    rows = cur.fetchall()
    cur.close()
    release_db(conn)
    return rows


def get_shop_item(guild_id: int, item_id: int):
    conn, cur = get_db()
    cur.execute(
        "SELECT item_id, name, price, description, role_id FROM shop_items "
        "WHERE guild_id = %s AND item_id = %s",
        (str(guild_id), item_id),
    )
    row = cur.fetchone()
    cur.close()
    release_db(conn)
    return row


def buy_shop_item(user_id: int, guild_id: int, item_id: int):
    """Returns (success: bool, message: str, role_id_or_None)."""
    item = get_shop_item(guild_id, item_id)
    if item is None:
        return False, "❌ That item doesn't exist in this server's shop.", None
    _, name, price, description, role_id = item

    bal = get_balance(user_id)
    if bal["wallet"] < price:
        return False, f"❌ You need **{price:,}** coins but only have **{bal['wallet']:,}** in your wallet.", None

    update_balance(user_id, wallet=bal["wallet"] - price)

    conn, cur = get_db()
    cur.execute(
        "INSERT INTO inventory (user_id, item_id, quantity) VALUES (%s, %s, 1) "
        "ON CONFLICT (user_id, item_id) DO UPDATE SET quantity = inventory.quantity + 1",
        (user_id, item_id),
    )
    conn.commit()
    cur.close()
    release_db(conn)

    return True, f"✅ You bought **{name}** for **{price:,}** coins!", int(role_id) if role_id else None


def get_inventory(user_id: int):
    """Returns a list of (name, quantity, description, role_id) for a user's items."""
    conn, cur = get_db()
    cur.execute(
        "SELECT si.name, inv.quantity, si.description, si.role_id "
        "FROM inventory inv JOIN shop_items si ON inv.item_id = si.item_id "
        "WHERE inv.user_id = %s ORDER BY si.name",
        (user_id,),
    )
    rows = cur.fetchall()
    cur.close()
    release_db(conn)
    return rows


def build_inventory_text(display_name: str, user_id: int) -> str:
    custom = get_inventory(user_id)
    global_items = get_global_inventory(user_id)
    if not custom and not global_items:
        return f"🎒 **{display_name}**'s inventory is empty."
    lines = [f"╭━━━〔 🎒 {display_name}'s ɪɴᴠᴇɴᴛᴏʀʏ 〕━━━⬣", "┃"]
    for key, qty in global_items:
        info = GLOBAL_ITEMS.get(key, {})
        lines.append(f"┃ {info.get('name', key)} x{qty}")
    for name, quantity, description, role_id in custom:
        lines.append(f"┃ {name} x{quantity}")
    stacks = get_lucky_stacks(user_id)
    until = get_cd_boost_until(user_id)
    if stacks:
        lines.append(f"┃ 🍀 Lucky stacks: {stacks} (win rate x{1 + 0.5 * stacks:.1f})")
    if until and time.time() < until:
        left = int(until - time.time())
        lines.append(f"┃ ⚡ Cooldown boost: {left // 60}m {left % 60}s left")
    lines.append("╰━━━━━━━━━━━━━━━━━━━━━━⬣")
    return "\n".join(lines)


# ---------- Global shop items / effects ----------

GLOBAL_ITEMS = {
    "vx": {
        "name": "Vx",
        "price": 100000,
        "description": "Halves all cooldowns for 5 minutes. Use with .use vx",
        "consumable": True,
        "duration": 300,
    },
    "v9": {
        "name": "V9",
        "price": 200000,
        "description": "Halves all cooldowns for 10 minutes. Use with .use v9",
        "consumable": True,
        "duration": 600,
    },
    "lucky": {
        "name": "Lucky Potion",
        "price": 500000,
        "description": "Adds +0.5 to your win-rate multiplier. Infinitely stackable. Use with .use lucky",
        "consumable": True,
    },
    "gun": {
        "name": "Gun",
        "price": 1000,
        "description": "Required to use .rob",
        "consumable": False,
    },
    "fishing_rod": {
        "name": "Fishing Rod",
        "price": 1000,
        "description": "Required to use .fish",
        "consumable": False,
    },
    "shovel": {
        "name": "Shovel",
        "price": 1000,
        "description": "Required to use .dig",
        "consumable": False,
    },
    "guard": {
        "name": "Guard",
        "price": 50000,
        "description": "Blocks the next robbery against you, then is used up",
        "consumable": False,
        "stackable": True,
    },
}

ITEM_ALIASES = {
    "vx": "vx",
    "v9": "v9",
    "lucky": "lucky",
    "lucky potion": "lucky",
    "potion": "lucky",
    "gun": "gun",
    "fishing rod": "fishing_rod",
    "rod": "fishing_rod",
    "fishrod": "fishing_rod",
    "shovel": "shovel",
    "guard": "guard",
}


def resolve_item_key(name: str):
    return ITEM_ALIASES.get(name.strip().lower())


def get_global_item_qty(user_id, item_key: str) -> int:
    conn, cur = get_db()
    cur.execute(
        "SELECT quantity FROM global_inventory WHERE user_id = %s AND item_key = %s",
        (user_id, item_key),
    )
    row = cur.fetchone()
    cur.close()
    release_db(conn)
    return row[0] if row else 0


def has_global_item(user_id, item_key: str) -> bool:
    return get_global_item_qty(user_id, item_key) > 0


def add_global_item(user_id, item_key: str, amount: int = 1):
    conn, cur = get_db()
    cur.execute(
        "INSERT INTO global_inventory (user_id, item_key, quantity) VALUES (%s, %s, %s) "
        "ON CONFLICT (user_id, item_key) DO UPDATE SET quantity = global_inventory.quantity + %s",
        (user_id, item_key, amount, amount),
    )
    conn.commit()
    cur.close()
    release_db(conn)


def remove_global_item(user_id, item_key: str, amount: int = 1) -> bool:
    qty = get_global_item_qty(user_id, item_key)
    if qty < amount:
        return False
    conn, cur = get_db()
    cur.execute(
        "UPDATE global_inventory SET quantity = quantity - %s WHERE user_id = %s AND item_key = %s",
        (amount, user_id, item_key),
    )
    conn.commit()
    cur.close()
    release_db(conn)
    return True


def get_global_inventory(user_id):
    conn, cur = get_db()
    cur.execute(
        "SELECT item_key, quantity FROM global_inventory WHERE user_id = %s AND quantity > 0 ORDER BY item_key",
        (user_id,),
    )
    rows = cur.fetchall()
    cur.close()
    release_db(conn)
    return rows


def get_user_effects(user_id):
    conn, cur = get_db()
    cur.execute(
        "SELECT lucky_stacks, cd_boost_until, kiragpt_reply_count FROM user_effects WHERE user_id = %s",
        (user_id,),
    )
    row = cur.fetchone()
    if row is None:
        cur.execute(
            "INSERT INTO user_effects (user_id, lucky_stacks, cd_boost_until, kiragpt_reply_count) VALUES (%s, 0, NULL, 0)",
            (user_id,),
        )
        conn.commit()
        cur.close()
        release_db(conn)
        return {"lucky_stacks": 0, "cd_boost_until": None, "kiragpt_reply_count": 0}
    cur.close()
    release_db(conn)
    return {"lucky_stacks": row[0] or 0, "cd_boost_until": row[1], "kiragpt_reply_count": row[2] or 0}


def set_user_effects(user_id, lucky_stacks=None, cd_boost_until=None):
    current = get_user_effects(user_id)
    stacks = current["lucky_stacks"] if lucky_stacks is None else lucky_stacks
    until = current["cd_boost_until"] if cd_boost_until is None else cd_boost_until
    conn, cur = get_db()
    cur.execute(
        "INSERT INTO user_effects (user_id, lucky_stacks, cd_boost_until, kiragpt_reply_count) VALUES (%s, %s, %s, 0) "
        "ON CONFLICT (user_id) DO UPDATE SET lucky_stacks = EXCLUDED.lucky_stacks, "
        "cd_boost_until = EXCLUDED.cd_boost_until",
        (user_id, stacks, until),
    )
    conn.commit()
    cur.close()
    release_db(conn)


def get_kiragpt_reply_count(user_id) -> int:
    return get_user_effects(user_id)["kiragpt_reply_count"]


def increment_kiragpt_reply_count(user_id):
    uid = user_id
    get_user_effects(user_id)  # ensures a row exists
    conn, cur = get_db()
    cur.execute(
        "UPDATE user_effects SET kiragpt_reply_count = kiragpt_reply_count + 1 WHERE user_id = %s",
        (uid,),
    )
    conn.commit()
    cur.close()
    release_db(conn)


def get_lucky_stacks(user_id) -> int:
    return get_user_effects(user_id)["lucky_stacks"]


def get_cd_boost_until(user_id):
    return get_user_effects(user_id)["cd_boost_until"]


def luck_chance(base: float, user_id) -> float:
    """Each lucky potion adds +0.5 to the win multiplier. Capped at 95%."""
    stacks = get_lucky_stacks(user_id)
    return min(0.95, base * (1 + 0.5 * stacks))


def buy_global_item(user_id, item_key: str):
    item = GLOBAL_ITEMS[item_key]
    if not item.get("consumable") and not item.get("stackable") and has_global_item(user_id, item_key):
        return False, f"❌ You already own a **{item['name']}** — no need to buy another."
    bal = get_balance(user_id)
    if bal["wallet"] < item["price"]:
        return False, f"❌ You need **{item['price']:,}** coins but only have **{bal['wallet']:,}** in your wallet."
    update_balance(user_id, wallet=bal["wallet"] - item["price"])
    add_global_item(user_id, item_key, 1)
    extra = ""
    if item.get("consumable"):
        extra = f"\nUse it with `.use {item_key}`"
    return True, f"✅ You bought **{item['name']}** for **{item['price']:,}** coins!{extra}"


def use_global_item(user_id, item_key: str):
    item = GLOBAL_ITEMS.get(item_key)
    if not item:
        return "❌ Unknown item."
    if not item.get("consumable"):
        return f"❌ **{item['name']}** is a tool. You just need to own it."
    if not remove_global_item(user_id, item_key, 1):
        return f"❌ You don't have a **{item['name']}**."
    if item_key in ("vx", "v9"):
        until = time.time() + item["duration"]
        set_user_effects(user_id, cd_boost_until=until)
        mins = item["duration"] // 60
        return f"⚡ **{item['name']}** activated! All cooldowns are halved for **{mins} minutes**."
    if item_key == "lucky":
        stacks = get_lucky_stacks(user_id) + 1
        set_user_effects(user_id, lucky_stacks=stacks)
        return (
            f"🍀 You drank a **Lucky Potion**!\n"
            f"Lucky stacks: **{stacks}**\n"
            f"Win-rate multiplier: **x{1 + 0.5 * stacks:.1f}**"
        )
    return "✅ Used."


def build_shop_text(guild_id: int) -> str:
    lines = ["╭━━━〔 🛒 sʜᴏᴘ 〕━━━⬣", "┃", "┃ **Global items**"]
    for key, item in GLOBAL_ITEMS.items():
        lines.append(f"┃ `{key}` {item['name']} — {item['price']:,} coins — {item['description']}")
    custom = get_shop_items(guild_id)
    if custom:
        lines.append("┃")
        lines.append("┃ **Server items**")
        for item_id, name, price, description, role_id in custom:
            desc_part = f" — {description}" if description else ""
            lines.append(f"┃ **#{item_id}** {name} — {price:,} coins{desc_part}")
    lines.append("┃")
    lines.append("┃ Buy with `.buy vx` / `.buy gun` / `.buy <id>`")
    lines.append("┃ Use potions with `.use vx` / `.use lucky`")
    lines.append("╰━━━━━━━━━━━━━━━━━━━━━━⬣")
    return "\n".join(lines)


# ---------- Achievements ----------

ACHIEVEMENTS = {
    "first_blood": {"label": "First Blood", "description": "Successfully rob someone for the first time."},
    "jackpot": {"label": "Jackpot!", "description": "Hit the 3-of-a-kind jackpot on the slot machine."},
    "blackjack_natural": {"label": "Natural 21", "description": "Draw a natural blackjack."},
    "veteran": {"label": "Veteran", "description": "Reach level 20."},
    "high_roller": {"label": "High Roller", "description": "Have 1,000,000 coins or more in total."},
    "pet_owner": {"label": "Pet Owner", "description": "Adopt your first pet."},
    "married": {"label": "Tied the Knot", "description": "Get married."},
    "entrepreneur": {"label": "Entrepreneur", "description": "Sell an item on the market."},
}


def has_achievement(user_id, key: str) -> bool:
    conn, cur = get_db()
    cur.execute(
        "SELECT 1 FROM achievements WHERE user_id = %s AND achievement_key = %s",
        (user_id, key),
    )
    row = cur.fetchone()
    cur.close()
    release_db(conn)
    return row is not None


def grant_achievement(user_id, key: str) -> bool:
    """Awards an achievement if the user doesn't already have it.
    Returns True if this call newly granted it, else False."""
    if key not in ACHIEVEMENTS:
        return False
    conn, cur = get_db()
    cur.execute(
        "INSERT INTO achievements (user_id, achievement_key) VALUES (%s, %s) "
        "ON CONFLICT (user_id, achievement_key) DO NOTHING",
        (user_id, key),
    )
    granted = cur.rowcount > 0
    conn.commit()
    cur.close()
    release_db(conn)
    return granted


def get_user_achievements(user_id):
    conn, cur = get_db()
    cur.execute(
        "SELECT achievement_key FROM achievements WHERE user_id = %s ORDER BY earned_at",
        (user_id,),
    )
    rows = [r[0] for r in cur.fetchall()]
    cur.close()
    release_db(conn)
    return rows


def build_achievements_text(display_name: str, user_id) -> str:
    earned = set(get_user_achievements(user_id))
    lines = [f"╭━━━〔 🏅 {display_name}'s ᴀᴄʜɪᴇᴠᴇᴍᴇɴᴛs 〕━━━⬣", "┃"]
    for key, info in ACHIEVEMENTS.items():
        mark = "✅" if key in earned else "⬜"
        lines.append(f"┃ {mark} **{info['label']}** — {info['description']}")
    lines.append("┃")
    lines.append(f"┃ {len(earned)}/{len(ACHIEVEMENTS)} unlocked")
    lines.append("╰━━━━━━━━━━━━━━━━━━━━━━⬣")
    return "\n".join(lines)


# ---------- Pets ----------

def get_pet(user_id):
    """Returns the pet's live state (hunger decayed for elapsed time since
    it was last fed), or None if the user has no pet."""
    conn, cur = get_db()
    cur.execute(
        "SELECT pet_type, pet_name, hunger, last_fed, last_collected FROM pets WHERE user_id = %s",
        (user_id,),
    )
    row = cur.fetchone()
    cur.close()
    release_db(conn)
    if row is None:
        return None
    pet_type, pet_name, hunger, last_fed, last_collected = row
    elapsed_hours = max(0.0, (time.time() - last_fed.timestamp()) / 3600)
    current_hunger = max(0, hunger - int(elapsed_hours * PET_HUNGER_DECAY_PER_HOUR))
    return {
        "pet_type": pet_type,
        "pet_name": pet_name,
        "hunger": current_hunger,
        "last_fed": last_fed,
        "last_collected": last_collected,
    }


def buy_pet(user_id, pet_type: str, pet_name: str):
    pet_type = pet_type.strip().lower()
    info = PET_TYPES.get(pet_type)
    if not info:
        options = ", ".join(f"`{k}`" for k in PET_TYPES)
        return False, f"❌ Unknown pet type. Choose from: {options}."
    if get_pet(user_id) is not None:
        return False, "❌ You already have a pet. You can only have one at a time."
    if not pet_name.strip():
        return False, "❌ Give your pet a name: `.buypet <type> <name>`."

    bal = get_balance(user_id)
    if bal["wallet"] < info["price"]:
        return False, f"❌ You need **{info['price']:,}** coins to adopt a **{info['name']}**."
    update_balance(user_id, wallet=bal["wallet"] - info["price"])

    conn, cur = get_db()
    cur.execute(
        "INSERT INTO pets (user_id, pet_type, pet_name, hunger, last_fed, last_collected) "
        "VALUES (%s, %s, %s, 100, NOW(), NOW())",
        (user_id, pet_type, pet_name.strip()[:32]),
    )
    conn.commit()
    cur.close()
    release_db(conn)

    newly_earned = grant_achievement(user_id, "pet_owner")
    text = f"🐾 You adopted a **{info['name']}** named **{pet_name.strip()[:32]}**!"
    if newly_earned:
        text += f"\n🏅 Achievement unlocked: **{ACHIEVEMENTS['pet_owner']['label']}**"
    return True, text


def feed_pet(user_id):
    pet = get_pet(user_id)
    if pet is None:
        return "❌ You don't have a pet yet. Adopt one with `.buypet <type> <name>`."
    bal = get_balance(user_id)
    if bal["wallet"] < PET_FEED_COST:
        return f"❌ Feeding costs **{PET_FEED_COST:,}** coins — you don't have enough."
    update_balance(user_id, wallet=bal["wallet"] - PET_FEED_COST)

    new_hunger = min(100, pet["hunger"] + PET_HUNGER_PER_FEED)
    conn, cur = get_db()
    cur.execute(
        "UPDATE pets SET hunger = %s, last_fed = NOW() WHERE user_id = %s",
        (new_hunger, user_id),
    )
    conn.commit()
    cur.close()
    release_db(conn)
    return f"🍖 You fed **{pet['pet_name']}**! Hunger is now **{new_hunger}/100**."


def collect_pet_income(user_id):
    pet = get_pet(user_id)
    if pet is None:
        return "❌ You don't have a pet yet. Adopt one with `.buypet <type> <name>`."
    if pet["hunger"] < PET_STARVING_THRESHOLD:
        return f"😿 **{pet['pet_name']}** is too hungry to work. Feed it with `.feedpet` first."

    info = PET_TYPES[pet["pet_type"]]
    elapsed_hours = max(0.0, (time.time() - pet["last_collected"].timestamp()) / 3600)
    elapsed_hours = min(elapsed_hours, 48)  # cap a single collection window
    earned = int(info["hourly_income"] * elapsed_hours)
    if earned <= 0:
        return f"⏳ **{pet['pet_name']}** hasn't earned anything new yet — check back later."

    bal = get_balance(user_id)
    update_balance(user_id, wallet=bal["wallet"] + earned)
    conn, cur = get_db()
    cur.execute("UPDATE pets SET last_collected = NOW() WHERE user_id = %s", (user_id,))
    conn.commit()
    cur.close()
    release_db(conn)
    return f"💰 **{pet['pet_name']}** earned you **{earned:,}** coins while it worked!"


def build_pet_text(display_name: str, user_id) -> str:
    pet = get_pet(user_id)
    if pet is None:
        options = ", ".join(f"`{k}` ({v['name']}, {v['price']:,} coins)" for k, v in PET_TYPES.items())
        return f"🐾 **{display_name}** doesn't have a pet.\nAdopt one with `.buypet <type> <name>`.\nTypes: {options}"
    info = PET_TYPES[pet["pet_type"]]
    status = "🟢 Well fed" if pet["hunger"] >= PET_STARVING_THRESHOLD else "🔴 Starving (not earning)"
    return (
        f"╭━━━〔 🐾 {display_name}'s ᴘᴇᴛ 〕━━━⬣\n"
        f"┃ Name: {pet['pet_name']} ({info['name']})\n"
        f"┃ Hunger: {pet['hunger']}/100 — {status}\n"
        f"┃ Income: {info['hourly_income']:,}/hour while fed\n"
        f"┃\n"
        f"┃ `.feedpet` to feed • `.collectpet` to claim earnings\n"
        "╰━━━━━━━━━━━━━━━━━━━━━━⬣"
    )


# ---------- Marriage ----------

marriage_proposals = {}  # target_id -> proposer_id (in-memory, ephemeral by design)


def get_partner(user_id):
    conn, cur = get_db()
    cur.execute("SELECT partner_id FROM marriages WHERE user_id = %s", (user_id,))
    row = cur.fetchone()
    cur.close()
    release_db(conn)
    return row[0] if row else None


def propose_marriage(proposer_id, target_id):
    if proposer_id == target_id:
        return "❌ You can't marry yourself."
    if get_partner(proposer_id) is not None:
        return "❌ You're already married. `.divorce` first if you want to remarry."
    if get_partner(target_id) is not None:
        return "❌ That person is already married."
    marriage_proposals[target_id] = proposer_id
    return "💍 Proposal sent! They can accept with `.marryaccept`."


def accept_marriage(user_id):
    proposer_id = marriage_proposals.get(user_id)
    if not proposer_id:
        return "❌ You don't have a pending proposal."
    del marriage_proposals[user_id]
    if get_partner(proposer_id) is not None or get_partner(user_id) is not None:
        return "❌ One of you got married to someone else in the meantime."

    conn, cur = get_db()
    cur.execute(
        "INSERT INTO marriages (user_id, partner_id) VALUES (%s, %s), (%s, %s)",
        (proposer_id, user_id, user_id, proposer_id),
    )
    conn.commit()
    cur.close()
    release_db(conn)

    newly_a = grant_achievement(proposer_id, "married")
    newly_b = grant_achievement(user_id, "married")
    text = "💒 Congratulations, you're now married!"
    if newly_a or newly_b:
        text += f"\n🏅 Achievement unlocked: **{ACHIEVEMENTS['married']['label']}**"
    return text


def do_divorce(user_id):
    partner_id = get_partner(user_id)
    if partner_id is None:
        return "❌ You're not married."
    conn, cur = get_db()
    cur.execute(
        "DELETE FROM marriages WHERE (user_id = %s AND partner_id = %s) OR (user_id = %s AND partner_id = %s)",
        (user_id, partner_id, partner_id, user_id),
    )
    conn.commit()
    cur.close()
    release_db(conn)
    return "💔 You're now divorced."


# ---------- Market ----------

def create_listing(seller_id, item_name_raw: str, quantity_str: str, price_str: str):
    try:
        quantity = int(quantity_str)
        price = int(price_str.replace(",", "").replace("$", ""))
    except ValueError:
        return False, "❌ Usage: `.sell <item> <quantity> <price>`"
    if quantity <= 0 or price <= 0:
        return False, "❌ Quantity and price must both be greater than 0."

    key = resolve_item_key(item_name_raw)
    if not key:
        return False, "❌ You can only list global items (vx, v9, lucky, gun, fishing rod, shovel, guard)."
    item = GLOBAL_ITEMS[key]
    if not remove_global_item(seller_id, key, quantity):
        return False, f"❌ You don't have {quantity}x **{item['name']}**."

    conn, cur = get_db()
    cur.execute(
        "INSERT INTO market_listings (seller_id, item_key, quantity, price) "
        "VALUES (%s, %s, %s, %s) RETURNING listing_id",
        (seller_id, key, quantity, price),
    )
    listing_id = cur.fetchone()[0]
    conn.commit()
    cur.close()
    release_db(conn)

    newly_earned = grant_achievement(seller_id, "entrepreneur")
    text = f"✅ Listed **{quantity}x {item['name']}** at **{price:,}** coins each. Listing ID: **#{listing_id}**"
    if newly_earned:
        text += f"\n🏅 Achievement unlocked: **{ACHIEVEMENTS['entrepreneur']['label']}**"
    return True, text


def get_listings():
    conn, cur = get_db()
    cur.execute(
        "SELECT listing_id, seller_id, item_key, quantity, price FROM market_listings ORDER BY created_at"
    )
    rows = cur.fetchall()
    cur.close()
    release_db(conn)
    return rows


def build_market_text() -> str:
    rows = get_listings()
    if not rows:
        return "📭 No active market listings. List one with `.sell <item> <quantity> <price>`."
    lines = ["╭━━━〔 🏪 ᴘʟᴀʏᴇʀ ᴍᴀʀᴋᴇᴛ 〕━━━⬣"]
    for listing_id, seller_id, item_key, quantity, price in rows:
        name = GLOBAL_ITEMS.get(item_key, {}).get("name", item_key)
        lines.append(f"┃ **#{listing_id}** {name} x{quantity} — {price:,} coins each")
    lines.append("┃")
    lines.append("┃ Buy with `.buylisting <id>` • Cancel your own with `.cancellisting <id>`")
    lines.append("╰━━━━━━━━━━━━━━━━━━━━━━⬣")
    return "\n".join(lines)


def buy_listing(buyer_id, listing_id_str: str):
    try:
        listing_id = int(listing_id_str)
    except ValueError:
        return "❌ Usage: `.buylisting <id>`"

    conn, cur = get_db()
    try:
        cur.execute(
            "SELECT seller_id, item_key, quantity, price FROM market_listings WHERE listing_id = %s FOR UPDATE",
            (listing_id,),
        )
        row = cur.fetchone()
        if row is None:
            conn.rollback()
            return "❌ That listing doesn't exist — it may already be sold or cancelled."
        seller_id, item_key, quantity, price = row
        if seller_id == buyer_id:
            conn.rollback()
            return "❌ You can't buy your own listing. Cancel it instead with `.cancellisting`."

        total = price * quantity
        cur.execute(
            "INSERT INTO balances (user_id, wallet, bank, limit_amt) VALUES (%s, %s, %s, %s) "
            "ON CONFLICT (user_id) DO NOTHING",
            (buyer_id, DEFAULT_WALLET, DEFAULT_BANK, 0),
        )
        cur.execute(
            "INSERT INTO balances (user_id, wallet, bank, limit_amt) VALUES (%s, %s, %s, %s) "
            "ON CONFLICT (user_id) DO NOTHING",
            (seller_id, DEFAULT_WALLET, DEFAULT_BANK, 0),
        )
        cur.execute("SELECT wallet FROM balances WHERE user_id = %s FOR UPDATE", (buyer_id,))
        buyer_wallet = cur.fetchone()[0]
        if buyer_wallet < total:
            conn.rollback()
            return f"❌ You need **{total:,}** coins but only have **{buyer_wallet:,}**."

        tax = int(total * MARKET_TAX_RATE) if total > 0 else 0
        net = total - tax

        cur.execute("DELETE FROM market_listings WHERE listing_id = %s", (listing_id,))
        if cur.rowcount == 0:
            conn.rollback()
            return "❌ That listing was just bought by someone else."

        cur.execute(
            "UPDATE balances SET wallet = wallet - %s WHERE user_id = %s",
            (total, buyer_id),
        )
        cur.execute(
            "UPDATE balances SET wallet = wallet + %s WHERE user_id = %s",
            (net, seller_id),
        )
        if tax > 0:
            cur.execute("SELECT value FROM bot_meta WHERE key = %s", (TREASURY_META_KEY,))
            treasury_row = cur.fetchone()
            current_treasury = int(treasury_row[0]) if treasury_row else 0
            cur.execute(
                "INSERT INTO bot_meta (key, value) VALUES (%s, %s) "
                "ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value",
                (TREASURY_META_KEY, str(current_treasury + tax)),
            )
        cur.execute(
            "INSERT INTO global_inventory (user_id, item_key, quantity) VALUES (%s, %s, %s) "
            "ON CONFLICT (user_id, item_key) DO UPDATE SET quantity = global_inventory.quantity + %s",
            (buyer_id, item_key, quantity, quantity),
        )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
        release_db(conn)

    item_name = GLOBAL_ITEMS.get(item_key, {}).get("name", item_key)
    return f"✅ Bought **{quantity}x {item_name}** for **{total:,}** coins!"


def cancel_listing(user_id, listing_id_str: str):
    try:
        listing_id = int(listing_id_str)
    except ValueError:
        return "❌ Usage: `.cancellisting <id>`"

    conn, cur = get_db()
    try:
        cur.execute(
            "SELECT seller_id, item_key, quantity FROM market_listings WHERE listing_id = %s FOR UPDATE",
            (listing_id,),
        )
        row = cur.fetchone()
        if row is None:
            conn.rollback()
            return "❌ That listing doesn't exist."
        seller_id, item_key, quantity = row
        if seller_id != user_id:
            conn.rollback()
            return "❌ That's not your listing."
        cur.execute("DELETE FROM market_listings WHERE listing_id = %s", (listing_id,))
        if cur.rowcount == 0:
            conn.rollback()
            return "❌ That listing was just bought by someone else."
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
        release_db(conn)

    add_global_item(user_id, item_key, quantity)
    return "✅ Listing cancelled. Your items were returned."


# ---------- Rob ----------

def do_rob(robber_id: int, victim_id: int):
    if robber_id == victim_id:
        return "❌ You can't rob yourself."

    if not has_global_item(robber_id, "gun"):
        return "❌ You need a **Gun** first. Buy one with `.buy gun` (1,000 coins)."

    remaining = check_persistent_cooldown("rob", robber_id, ROB_COOLDOWN_SECONDS)
    if remaining is not None:
        mins = int(remaining // 60)
        secs = int(remaining % 60)
        return f"⏳ You're laying low. Try robbing again in **{mins}m {secs}s**."

    victim_bal = get_balance(victim_id)
    robber_bal = get_balance(robber_id)

    if victim_bal["wallet"] < 100:
        return "❌ That person doesn't have enough in their wallet to be worth robbing."

    if has_global_item(victim_id, "guard"):
        remove_global_item(victim_id, "guard", 1)
        return "🛡️ They had a **Guard**. The robbery was blocked, and their Guard was used up."

    if random.random() < luck_chance(ROB_SUCCESS_CHANCE, robber_id):
        stolen = int(victim_bal["wallet"] * random.uniform(0.05, ROB_MAX_STEAL_PERCENT))
        stolen = max(stolen, 1)
        net, tax = apply_tax(stolen)
        update_balance(victim_id, wallet=victim_bal["wallet"] - stolen)
        update_balance(robber_id, wallet=robber_bal["wallet"] + net)
        newly_earned = grant_achievement(robber_id, "first_blood")
        text = f"💰 You successfully robbed **{stolen:,}** coins! (Tax: {tax:,} → treasury. You keep **{net:,}**.)"
        if newly_earned:
            text += f"\n🏅 Achievement unlocked: **{ACHIEVEMENTS['first_blood']['label']}**"
        return text
    else:
        penalty = int(robber_bal["wallet"] * ROB_FAIL_PENALTY_PERCENT)
        penalty = min(penalty, robber_bal["wallet"])
        update_balance(robber_id, wallet=robber_bal["wallet"] - penalty)
        return f"🚨 You got caught! You paid a fine of **{penalty:,}** coins."



@tasks.loop(hours=1)
async def salary_payout_loop():
    """Checks hourly; pays out each jobholder's salary once
    SALARY_INTERVAL_HOURS have passed since their last payout (or since they
    set the job, if never paid). Salary is taxed on the way in — the tax
    feeds the server treasury."""
    conn, cur = get_db()
    cur.execute("SELECT user_id, job, last_salary FROM jobs")
    rows = cur.fetchall()
    now = time.time()
    for user_id, job_key, last_salary in rows:
        info = JOBS.get(job_key)
        if info is None:
            continue
        if last_salary is None:
            cur.execute("UPDATE jobs SET last_salary = NOW() WHERE user_id = %s", (user_id,))
            continue
        last_ts = last_salary.timestamp()
        if now - last_ts < SALARY_INTERVAL_HOURS * 3600:
            continue
        net, tax = apply_tax(info["pay"])
        bal = get_balance(user_id)
        update_balance(user_id, wallet=bal["wallet"] + net)
        cur.execute("UPDATE jobs SET last_salary = NOW() WHERE user_id = %s", (user_id,))
    conn.commit()
    cur.close()
    release_db(conn)


@tasks.loop(hours=24)
async def bank_interest_loop():
    """Once a day, adds BANK_INTEREST_RATE interest to everyone's bank
    balance. Untaxed — rewards saving instead of just hoarding wallet cash."""
    conn, cur = get_db()
    cur.execute(
        "UPDATE balances SET bank = bank + FLOOR(bank * %s)::BIGINT WHERE bank > 0",
        (BANK_INTEREST_RATE,),
    )
    conn.commit()
    cur.close()
    release_db(conn)


@bot.event
async def on_ready():
    print(f"Logged in as {bot.user} (ID: {bot.user.id})")
    if not salary_payout_loop.is_running():
        salary_payout_loop.start()
    if not bank_interest_loop.is_running():
        bank_interest_loop.start()
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} slash command(s)")
        current_names = sorted(set(c.name for c in synced))
        previous_raw = get_meta("command_list")
        if previous_raw is not None:
            previous_names = previous_raw.split(",") if previous_raw else []
            new_ones = sorted(set(current_names) - set(previous_names))
            if new_ones:
                print("New slash commands: " + ", ".join(new_ones))
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


def build_profile_embed(member):
    """Everything about a player in one place: economy, leveling, job, pet,
    marriage, achievements, and inventory."""
    user_id = did(member.id)
    bal = get_balance(user_id)
    level_data = get_level_data(user_id)
    xp_needed = xp_for_level(level_data["level"])
    job_key = get_job(user_id)
    pet = get_pet(user_id)
    partner_id = get_partner(user_id)
    earned_achievements = get_user_achievements(user_id)
    inventory = get_global_inventory(user_id)

    embed = discord.Embed(title=f"📋 Profile: {member.display_name}", color=discord.Color.gold())
    embed.set_thumbnail(url=member.display_avatar.url)

    embed.add_field(
        name="💰 Economy",
        value=(
            f"Wallet: **${bal['wallet']:,}**\n"
            f"Bank: **${bal['bank']:,}**\n"
            f"Total: **${bal['wallet'] + bal['bank']:,}**"
        ),
        inline=True,
    )

    embed.add_field(
        name="🎖️ Level",
        value=(
            f"Level: **{level_data['level']}**\n"
            f"XP: **{level_data['xp']:,} / {xp_needed:,}**"
        ),
        inline=True,
    )

    if job_key:
        info = JOBS[job_key]
        job_value = f"**{info['label']}**\n${info['pay']:,} / {SALARY_INTERVAL_HOURS // 24}d"
    else:
        job_value = "None — `.setjob`"
    embed.add_field(name="💼 Job", value=job_value, inline=True)

    if pet:
        pet_info = PET_TYPES[pet["pet_type"]]
        status = "🟢 Fed" if pet["hunger"] >= PET_STARVING_THRESHOLD else "🔴 Starving"
        pet_value = f"**{pet['pet_name']}** ({pet_info['name']})\n{status} — {pet['hunger']}/100"
    else:
        pet_value = "None — `.buypet`"
    embed.add_field(name="🐾 Pet", value=pet_value, inline=True)

    if partner_id:
        raw_id = partner_id.split(":", 1)[-1]
        partner_value = f"<@{raw_id}>"
    else:
        partner_value = "Not married"
    embed.add_field(name="💍 Partner", value=partner_value, inline=True)

    embed.add_field(
        name="🏅 Achievements",
        value=f"**{len(earned_achievements)} / {len(ACHIEVEMENTS)}** unlocked",
        inline=True,
    )

    if inventory:
        inv_lines = [
            f"{GLOBAL_ITEMS.get(key, {}).get('name', key)} x{qty}" for key, qty in inventory
        ]
        inv_value = "\n".join(inv_lines)
    else:
        inv_value = "Empty"
    embed.add_field(name="🎒 Inventory", value=inv_value, inline=False)

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


@bot.tree.command(name="profile", description="See every stat for a player: economy, level, job, pet, marriage, achievements, inventory")
@app_commands.describe(member="The member to look up (defaults to you)")
async def profile(interaction: discord.Interaction, member: discord.Member = None):
    await interaction.response.defer()
    member = member or interaction.user
    try:
        embed = build_profile_embed(member)
    except Exception as e:
        print(f"profile command failed: {e}")
        await interaction.followup.send("❌ Something went wrong building that profile. Try again in a moment.")
        return
    await interaction.followup.send(embed=embed)


@bot.command(name="profile")
async def profile_prefix(ctx: commands.Context, member: discord.Member = None):
    member = member or ctx.author
    try:
        embed = build_profile_embed(member)
    except Exception as e:
        print(f"profile command failed: {e}")
        await ctx.reply("❌ Something went wrong building that profile. Try again in a moment.")
        return
    await ctx.reply(embed=embed)


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
        }
    return kiragpt_sessions[user_id]


MAX_REPLIES_FOR_NORMAL_USERS = 50


async def handle_kiragpt_message(user, prompt: str, send_func):
    user_id = did(user.id)
    session = get_kiragpt_session(user_id)
    is_creator = is_kira_creator(user)

    # Rate limit for non-admins
    if not is_creator:
        if get_kiragpt_reply_count(user_id) >= MAX_REPLIES_FOR_NORMAL_USERS:
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

    if not prompt.strip():
        await send_func(
            "❌ Usage:\n"
            "`.kiragpt <message>`\n"
            "`.kiragpt on/off` — continuous chat\n"
            "`.kiragpt wild on` / `ai on` / `normal on` — change mode"
        )
        return

    mode = session.get("mode", "normal")

    reply_text = await generate_code_response(
        prompt, mode=mode, is_creator=is_creator, history=session["history"]
    )

    session["history"].append({"role": "user", "content": prompt[:1500]})
    session["history"].append({"role": "assistant", "content": reply_text})
    if len(session["history"]) > 20:
        session["history"] = session["history"][-20:]

    if not is_creator:
        increment_kiragpt_reply_count(user_id)

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


@bot.command(name="withdraw", aliases=["wd"])
async def withdraw_prefix(ctx: commands.Context, amount: str):
    await ctx.reply(do_withdraw(did(ctx.author.id), amount))


@bot.tree.command(name="deposit", description="Deposit money from your wallet to your bank")
@app_commands.describe(amount="Amount to deposit, or 'all'")
async def deposit(interaction: discord.Interaction, amount: str):
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


def build_updateinfo_text() -> str:
    info = LATEST_UPDATE_INFO
    lines = [
        "╭━━━〔 🆕 Latest Update 〕━━━⬣",
        "┃",
        f"┃ Version: **{info['version']}**",
        f"┃ Date: {info['date']}",
        "┃",
        "┃ What's new:",
    ]
    for change in info["changes"]:
        lines.append(f"┃ • {change}")
    lines.append("┃")
    lines.append("┃ Full log: `.versions`")
    lines.append("╰━━━━━━━━━━━━━━━━━━━━━━⬣")
    return "\n".join(lines)


def build_version_history_text() -> str:
    """Discord caps a single message at 2000 characters. As VERSION_HISTORY
    grows, showing every entry eventually exceeds that and the send fails
    outright (looks like 'the application did not respond'). So this shows
    as many of the most recent entries as fit, oldest-first is not
    preserved — newest first, truncate once we're near the limit."""
    CHAR_BUDGET = 1900  # leave headroom under Discord's 2000 cap
    header = [
        "╭━━━〔 📜 Version History 〕━━━⬣",
        f"┃ Current: **{BOT_VERSION}**",
        "┃",
    ]
    footer_template = "╰━━━━━━━━━━━━━━━━━━━━━━⬣"
    used = sum(len(l) + 1 for l in header) + len(footer_template) + 1

    body_lines = []
    shown = 0
    for entry in VERSION_HISTORY:
        entry_lines = [f"┃ **v{entry['version']}** — {entry['date']}"]
        for change in entry["changes"]:
            entry_lines.append(f"┃  • {change}")
        entry_lines.append("┃")
        entry_len = sum(len(l) + 1 for l in entry_lines)
        if used + entry_len > CHAR_BUDGET:
            break
        body_lines.extend(entry_lines)
        used += entry_len
        shown += 1

    omitted = len(VERSION_HISTORY) - shown
    lines = header + body_lines
    if omitted > 0:
        lines.append(f"┃ …and {omitted} older update(s) not shown here.")
        lines.append("┃")
    lines.append(footer_template)
    return "\n".join(lines)


@bot.tree.command(name="updateinfo", description="See what changed in the latest update")
async def updateinfo(interaction: discord.Interaction):
    await interaction.response.send_message(build_updateinfo_text())


@bot.command(name="updateinfo", aliases=["changelog"])
async def updateinfo_prefix(ctx: commands.Context):
    await ctx.reply(build_updateinfo_text())


@bot.tree.command(name="versions", description="See the full version history log")
async def versions(interaction: discord.Interaction):
    await interaction.response.send_message(build_version_history_text())


@bot.command(name="versions", aliases=["versionhistory", "history"])
async def versions_prefix(ctx: commands.Context):
    await ctx.reply(build_version_history_text())


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
    if not won and random.random() < min(0.9, 0.5 * get_lucky_stacks(user_id)):
        won = True
        result = side
        result_display = "HEADS 🦅" if result == "heads" else "TAILS 🪙"


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
    if not won and random.random() < min(0.9, 0.5 * get_lucky_stacks(user_id)):
        won = True
        # Re-roll a number that actually matches the chosen color, so the
        # displayed result stays consistent with the "you won" outcome.
        for _ in range(50):
            number, color, color_display = do_roulette_spin()
            if color == color_choice:
                break
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
    await interaction.response.send_message(do_clearcache())


@bot.command(name="clearcache")
@commands.is_owner()
async def clearcache_prefix(ctx: commands.Context):
    await ctx.reply(do_clearcache())


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


@bot.tree.command(name="setjob", description="Get randomly assigned a job that pays you a salary automatically")
async def setjob(interaction: discord.Interaction):
    job_key = random.choice(list(JOBS.keys()))
    await interaction.response.send_message(set_job(did(interaction.user.id), job_key))


@bot.command(name="setjob")
async def setjob_prefix(ctx: commands.Context):
    job_key = random.choice(list(JOBS.keys()))
    await ctx.reply(set_job(did(ctx.author.id), job_key))


@bot.tree.command(name="myjob", description="See your current job and salary")
async def myjob(interaction: discord.Interaction):
    await interaction.response.send_message(build_myjob_text(did(interaction.user.id)))


@bot.command(name="myjob")
async def myjob_prefix(ctx: commands.Context):
    await ctx.reply(build_myjob_text(did(ctx.author.id)))


@bot.tree.command(name="jobs", description="See all available jobs")
async def jobs_cmd(interaction: discord.Interaction):
    await interaction.response.send_message(build_jobs_list_text())


@bot.command(name="jobs")
async def jobs_prefix(ctx: commands.Context):
    await ctx.reply(build_jobs_list_text())


@bot.tree.command(name="treasury", description="See the server treasury (funded by taxes)")
async def treasury(interaction: discord.Interaction):
    await interaction.response.send_message(f"🏛️ Server treasury: **${get_treasury():,}** (funded by salary and rob taxes)")


@bot.command(name="treasury")
async def treasury_prefix(ctx: commands.Context):
    await ctx.reply(f"🏛️ Server treasury: **${get_treasury():,}** (funded by salary and rob taxes)")


# ---------- Pet commands ----------

@bot.tree.command(name="buypet", description="Adopt a pet that earns passive income")
@app_commands.describe(pet_type="dog, cat, dragon, or hamster", name="Your pet's name")
async def buypet(interaction: discord.Interaction, pet_type: str, name: str):
    success, message = buy_pet(did(interaction.user.id), pet_type, name)
    await interaction.response.send_message(message)


@bot.command(name="buypet")
async def buypet_prefix(ctx: commands.Context, pet_type: str, *, name: str = ""):
    success, message = buy_pet(did(ctx.author.id), pet_type, name)
    await ctx.reply(message)


@bot.tree.command(name="feedpet", description="Feed your pet")
async def feedpet(interaction: discord.Interaction):
    await interaction.response.send_message(feed_pet(did(interaction.user.id)))


@bot.command(name="feedpet")
async def feedpet_prefix(ctx: commands.Context):
    await ctx.reply(feed_pet(did(ctx.author.id)))


@bot.tree.command(name="collectpet", description="Collect the coins your pet has earned")
async def collectpet(interaction: discord.Interaction):
    await interaction.response.send_message(collect_pet_income(did(interaction.user.id)))


@bot.command(name="collectpet")
async def collectpet_prefix(ctx: commands.Context):
    await ctx.reply(collect_pet_income(did(ctx.author.id)))


@bot.tree.command(name="pet", description="See your (or someone else's) pet")
@app_commands.describe(user="The user to check (leave blank for yourself)")
async def pet(interaction: discord.Interaction, user: discord.User = None):
    target = user or interaction.user
    await interaction.response.send_message(build_pet_text(target.display_name, did(target.id)))


@bot.command(name="pet")
async def pet_prefix(ctx: commands.Context, user: discord.User = None):
    target = user or ctx.author
    await ctx.reply(build_pet_text(target.display_name, did(target.id)))


# ---------- Marriage commands ----------

@bot.tree.command(name="marry", description="Propose marriage to another user")
@app_commands.describe(user="The user to propose to")
async def marry(interaction: discord.Interaction, user: discord.User):
    if user.bot:
        await interaction.response.send_message("❌ You can't marry a bot.")
        return
    await interaction.response.send_message(propose_marriage(did(interaction.user.id), did(user.id)))


@bot.command(name="marry")
async def marry_prefix(ctx: commands.Context, user: discord.Member):
    if user.bot:
        await ctx.reply("❌ You can't marry a bot.")
        return
    await ctx.reply(propose_marriage(did(ctx.author.id), did(user.id)))


@bot.tree.command(name="marryaccept", description="Accept a pending marriage proposal")
async def marryaccept(interaction: discord.Interaction):
    await interaction.response.send_message(accept_marriage(did(interaction.user.id)))


@bot.command(name="marryaccept")
async def marryaccept_prefix(ctx: commands.Context):
    await ctx.reply(accept_marriage(did(ctx.author.id)))


@bot.tree.command(name="divorce", description="End your marriage")
async def divorce(interaction: discord.Interaction):
    await interaction.response.send_message(do_divorce(did(interaction.user.id)))


@bot.command(name="divorce")
async def divorce_prefix(ctx: commands.Context):
    await ctx.reply(do_divorce(did(ctx.author.id)))


@bot.tree.command(name="partner", description="See who you're (or someone else is) married to")
@app_commands.describe(user="The user to check (leave blank for yourself)")
async def partner(interaction: discord.Interaction, user: discord.User = None):
    target = user or interaction.user
    partner_id = get_partner(did(target.id))
    if partner_id is None:
        await interaction.response.send_message(f"💔 **{target.display_name}** isn't married.")
        return
    await interaction.response.send_message(f"💍 **{target.display_name}** is married to <@{partner_id.split(':', 1)[-1]}>.")


@bot.command(name="partner")
async def partner_prefix(ctx: commands.Context, user: discord.Member = None):
    target = user or ctx.author
    partner_id = get_partner(did(target.id))
    if partner_id is None:
        await ctx.reply(f"💔 **{target.display_name}** isn't married.")
        return
    await ctx.reply(f"💍 **{target.display_name}** is married to <@{partner_id.split(':', 1)[-1]}>.")


# ---------- Achievements command ----------

@bot.tree.command(name="achievements", description="See your (or someone else's) achievements")
@app_commands.describe(user="The user to check (leave blank for yourself)")
async def achievements(interaction: discord.Interaction, user: discord.User = None):
    target = user or interaction.user
    await interaction.response.send_message(build_achievements_text(target.display_name, did(target.id)))


@bot.command(name="achievements", aliases=["badges"])
async def achievements_prefix(ctx: commands.Context, user: discord.User = None):
    target = user or ctx.author
    await ctx.reply(build_achievements_text(target.display_name, did(target.id)))


# ---------- Market commands ----------

@bot.tree.command(name="sell", description="List an item for sale on the player market")
@app_commands.describe(item="Item name (vx, gun, shovel...)", quantity="How many to sell", price="Price per item")
async def sell(interaction: discord.Interaction, item: str, quantity: str, price: str):
    success, message = create_listing(did(interaction.user.id), item, quantity, price)
    await interaction.response.send_message(message)


@bot.command(name="sell")
async def sell_prefix(ctx: commands.Context, item: str, quantity: str, price: str):
    success, message = create_listing(did(ctx.author.id), item, quantity, price)
    await ctx.reply(message)


@bot.tree.command(name="market", description="Browse the player market")
async def market(interaction: discord.Interaction):
    await interaction.response.send_message(build_market_text())


@bot.command(name="market")
async def market_prefix(ctx: commands.Context):
    await ctx.reply(build_market_text())


@bot.tree.command(name="buylisting", description="Buy a listing from the player market")
@app_commands.describe(listing_id="The listing ID (see .market)")
async def buylisting(interaction: discord.Interaction, listing_id: str):
    await interaction.response.send_message(buy_listing(did(interaction.user.id), listing_id))


@bot.command(name="buylisting")
async def buylisting_prefix(ctx: commands.Context, listing_id: str):
    await ctx.reply(buy_listing(did(ctx.author.id), listing_id))


@bot.tree.command(name="cancellisting", description="Cancel your own market listing")
@app_commands.describe(listing_id="The listing ID to cancel")
async def cancellisting(interaction: discord.Interaction, listing_id: str):
    await interaction.response.send_message(cancel_listing(did(interaction.user.id), listing_id))


@bot.command(name="cancellisting")
async def cancellisting_prefix(ctx: commands.Context, listing_id: str):
    await ctx.reply(cancel_listing(did(ctx.author.id), listing_id))


@bot.tree.command(name="lb", description="Show the richest users")
async def lb(interaction: discord.Interaction):
    await interaction.response.send_message(build_leaderboard_text())


@bot.command(name="lb", aliases=["top", "leaderboard"])
async def lb_prefix(ctx: commands.Context):
    await ctx.reply(build_leaderboard_text())


def build_rank_text(user_id: int, display_name: str) -> str:
    data = get_level_data(user_id)
    needed = xp_for_level(data["level"])
    return (
        f"📊 **{display_name}**'s Rank\n"
        f"Level: **{data['level']}**\n"
        f"XP: **{data['xp']:,} / {needed:,}**"
    )


def build_ranklb_text() -> str:
    rows = get_xp_leaderboard()
    if not rows:
        return "No one has earned XP yet."
    lines = ["🎖️ **Level Leaderboard** 🎖️\n"]
    for i, (user_id, level, xp) in enumerate(rows, start=1):
        lines.append(f"**{i}.** <@{user_id}> — Level {level} ({xp:,} XP)")
    return "\n".join(lines)


@bot.tree.command(name="rank", description="See your (or someone else's) level and XP")
@app_commands.describe(user="The user to check (leave blank for yourself)")
async def rank(interaction: discord.Interaction, user: discord.User = None):
    target = user or interaction.user
    await interaction.response.send_message(build_rank_text(did(target.id), target.display_name))


@bot.command(name="rank")
async def rank_prefix(ctx: commands.Context, user: discord.User = None):
    target = user or ctx.author
    await ctx.reply(build_rank_text(did(target.id), target.display_name))


@bot.tree.command(name="ranklb", description="See the level leaderboard")
async def ranklb(interaction: discord.Interaction):
    await interaction.response.send_message(build_ranklb_text())


@bot.command(name="ranklb", aliases=["levellb", "levels"])
async def ranklb_prefix(ctx: commands.Context):
    await ctx.reply(build_ranklb_text())


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


@bot.command(name="blackjack", aliases=["bj"])
async def blackjack_prefix(ctx: commands.Context, action: str = None):
    user_id = did(ctx.author.id)
    if action is None:
        await ctx.reply("❌ Usage: `.blackjack <bet>` to start, `.blackjack hit`, or `.blackjack stand`.")
        return
    if action.lower() == "hit":
        await ctx.reply(hit_blackjack(user_id))
        return
    if action.lower() == "stand":
        await ctx.reply(stand_blackjack(user_id))
        return
    await ctx.reply(start_blackjack(user_id, action))


@bot.tree.command(name="blackjack", description="Start a blackjack game")
@app_commands.describe(bet="Amount to bet, or 'all'")
async def blackjack_start(interaction: discord.Interaction, bet: str):
    await interaction.response.send_message(start_blackjack(did(interaction.user.id), bet))


@bot.tree.command(name="rob", description="Attempt to rob another user")
@app_commands.describe(user="The user to rob")
async def rob(interaction: discord.Interaction, user: discord.User):
    await interaction.response.send_message(do_rob(did(interaction.user.id), did(user.id)))


@bot.command(name="rob")
async def rob_prefix(ctx: commands.Context, user: discord.User):
    await ctx.reply(do_rob(did(ctx.author.id), did(user.id)))


@bot.tree.command(name="shop", description="View this server's shop")
async def shop(interaction: discord.Interaction):
    if interaction.guild is None:
        await interaction.response.send_message("❌ Use this command in a server.")
        return
    await interaction.response.send_message(build_shop_text(interaction.guild.id))


@bot.command(name="shop")
async def shop_prefix(ctx: commands.Context):
    if ctx.guild is None:
        await ctx.reply("❌ Use this command in a server.")
        return
    await ctx.reply(build_shop_text(ctx.guild.id))


def handle_buy(user_id: int, guild_id: int, item_name: str):
    key = resolve_item_key(item_name)
    if key:
        return buy_global_item(user_id, key) + (None,)
    try:
        item_id = int(item_name)
    except ValueError:
        return False, "❌ Unknown item. Use `.shop` to see names and IDs.", None
    return buy_shop_item(user_id, guild_id, item_id)


@bot.tree.command(name="buy", description="Buy an item from the shop")
@app_commands.describe(item="Item name (vx, gun, shovel...) or server item ID")
async def buy(interaction: discord.Interaction, item: str):
    if interaction.guild is None:
        await interaction.response.send_message("❌ Use this command in a server.")
        return
    success, message, role_id = handle_buy(did(interaction.user.id), interaction.guild.id, item)
    if success and role_id is not None and isinstance(interaction.user, discord.Member):
        role = interaction.guild.get_role(role_id)
        if role is not None:
            try:
                await interaction.user.add_roles(role, reason="Shop purchase")
                message += f"\n🏅 The **{role.name}** role has been added to you."
            except discord.Forbidden:
                message += "\n⚠️ Couldn't assign the role — check my role permissions."
    await interaction.response.send_message(message)


@bot.command(name="buy")
async def buy_prefix(ctx: commands.Context, *, item: str):
    if ctx.guild is None:
        await ctx.reply("❌ Use this command in a server.")
        return
    success, message, role_id = handle_buy(did(ctx.author.id), ctx.guild.id, item)
    if success and role_id is not None and isinstance(ctx.author, discord.Member):
        role = ctx.guild.get_role(role_id)
        if role is not None:
            try:
                await ctx.author.add_roles(role, reason="Shop purchase")
                message += f"\n🏅 The **{role.name}** role has been added to you."
            except discord.Forbidden:
                message += "\n⚠️ Couldn't assign the role — check my role permissions."
    await ctx.reply(message)


@bot.tree.command(name="use", description="Use a consumable item (vx, v9, lucky)")
@app_commands.describe(item="vx, v9, or lucky")
async def use_item(interaction: discord.Interaction, item: str):
    key = resolve_item_key(item)
    if not key:
        await interaction.response.send_message("❌ Use `.use vx`, `.use v9`, or `.use lucky`.")
        return
    await interaction.response.send_message(use_global_item(did(interaction.user.id), key))


@bot.command(name="use")
async def use_item_prefix(ctx: commands.Context, *, item: str):
    key = resolve_item_key(item)
    if not key:
        await ctx.reply("❌ Use `.use vx`, `.use v9`, or `.use lucky`.")
        return
    await ctx.reply(use_global_item(did(ctx.author.id), key))


@bot.tree.command(name="help", description="Show help for one command")
@app_commands.describe(command="Command name")
async def help_slash(interaction: discord.Interaction, command: str):
    await interaction.response.send_message(build_help_text(command))


@bot.command(name="help")
async def help_prefix(ctx: commands.Context, *, command: str = ""):
    if not command.strip():
        await ctx.reply("Usage: `.help <command>`\nExample: `.help fish`\nOr use `.menu` for the list.")
        return
    await ctx.reply(build_help_text(command))


@bot.tree.command(name="inventory", description="See your (or someone else's) items")
@app_commands.describe(user="The user to check (leave blank for yourself)")
async def inventory(interaction: discord.Interaction, user: discord.User = None):
    target = user or interaction.user
    await interaction.response.send_message(build_inventory_text(target.display_name, did(target.id)))


@bot.command(name="inventory", aliases=["inv"])
async def inventory_prefix(ctx: commands.Context, user: discord.User = None):
    target = user or ctx.author
    await ctx.reply(build_inventory_text(target.display_name, did(target.id)))


@bot.tree.command(name="setlevelrole", description="[Admin] Set a role reward for reaching a level")
@app_commands.describe(level="The level to reward", role="The role to grant")
async def setlevelrole(interaction: discord.Interaction, level: int, role: discord.Role):
    if not is_kira_creator(interaction.user):
        await interaction.response.send_message("❌ Only server administrators can do that.")
        return
    set_level_role(interaction.guild.id, level, role.id)
    await interaction.response.send_message(f"✅ Users will now get **{role.name}** at level **{level}**.")


@bot.command(name="setlevelrole")
async def setlevelrole_prefix(ctx: commands.Context, level: int, role: discord.Role):
    if not is_kira_creator(ctx.author):
        await ctx.reply("❌ Only server administrators can do that.")
        return
    set_level_role(ctx.guild.id, level, role.id)
    await ctx.reply(f"✅ Users will now get **{role.name}** at level **{level}**.")


@bot.tree.command(name="give", description="[Admin] Give a role to a user directly")
@app_commands.describe(user="The user to give the role to", role="The role to give")
async def give(interaction: discord.Interaction, user: discord.Member, role: discord.Role):
    if not is_kira_creator(interaction.user):
        await interaction.response.send_message("❌ Only server administrators can do that.")
        return
    if role in user.roles:
        await interaction.response.send_message(f"❌ **{user.display_name}** already has **{role.name}**.")
        return
    try:
        await user.add_roles(role, reason=f"Given by {interaction.user}")
        await interaction.response.send_message(f"✅ Gave **{role.name}** to **{user.display_name}**.")
    except discord.Forbidden:
        await interaction.response.send_message(
            f"❌ Couldn't give **{role.name}** — the bot needs **Manage Roles** and its role "
            f"must sit above **{role.name}** in Server Settings → Roles."
        )


@bot.command(name="give")
async def give_prefix(ctx: commands.Context, user: discord.Member, role: discord.Role):
    if not is_kira_creator(ctx.author):
        await ctx.reply("❌ Only server administrators can do that.")
        return
    if role in user.roles:
        await ctx.reply(f"❌ **{user.display_name}** already has **{role.name}**.")
        return
    try:
        await user.add_roles(role, reason=f"Given by {ctx.author}")
        await ctx.reply(f"✅ Gave **{role.name}** to **{user.display_name}**.")
    except discord.Forbidden:
        await ctx.reply(
            f"❌ Couldn't give **{role.name}** — the bot needs **Manage Roles** and its role "
            f"must sit above **{role.name}** in Server Settings → Roles."
        )


@bot.tree.command(name="take", description="[Admin] Strip a role from a user directly")
@app_commands.describe(user="The user to remove the role from", role="The role to remove")
async def take(interaction: discord.Interaction, user: discord.Member, role: discord.Role):
    if not is_kira_creator(interaction.user):
        await interaction.response.send_message("❌ Only server administrators can do that.")
        return
    if role not in user.roles:
        await interaction.response.send_message(f"❌ **{user.display_name}** doesn't have **{role.name}**.")
        return
    try:
        await user.remove_roles(role, reason=f"Removed by {interaction.user}")
        await interaction.response.send_message(f"✅ Removed **{role.name}** from **{user.display_name}**.")
    except discord.Forbidden:
        await interaction.response.send_message(
            f"❌ Couldn't remove **{role.name}** — the bot needs **Manage Roles** and its role "
            f"must sit above **{role.name}** in Server Settings → Roles."
        )


@bot.command(name="take")
async def take_prefix(ctx: commands.Context, user: discord.Member, role: discord.Role):
    if not is_kira_creator(ctx.author):
        await ctx.reply("❌ Only server administrators can do that.")
        return
    if role not in user.roles:
        await ctx.reply(f"❌ **{user.display_name}** doesn't have **{role.name}**.")
        return
    try:
        await user.remove_roles(role, reason=f"Removed by {ctx.author}")
        await ctx.reply(f"✅ Removed **{role.name}** from **{user.display_name}**.")
    except discord.Forbidden:
        await ctx.reply(
            f"❌ Couldn't remove **{role.name}** — the bot needs **Manage Roles** and its role "
            f"must sit above **{role.name}** in Server Settings → Roles."
        )


@bot.tree.command(name="levelroles", description="See all configured level role rewards")
async def levelroles(interaction: discord.Interaction):
    rows = list_level_roles(interaction.guild.id)
    if not rows:
        await interaction.response.send_message("No level roles configured yet.")
        return
    lines = ["🏅 **Level Role Rewards**\n"]
    for level, role_id in rows:
        lines.append(f"Level {level} → <@&{role_id}>")
    await interaction.response.send_message("\n".join(lines))


@bot.command(name="levelroles")
async def levelroles_prefix(ctx: commands.Context):
    rows = list_level_roles(ctx.guild.id)
    if not rows:
        await ctx.reply("No level roles configured yet.")
        return
    lines = ["🏅 **Level Role Rewards**\n"]
    for level, role_id in rows:
        lines.append(f"Level {level} → <@&{role_id}>")
    await ctx.reply("\n".join(lines))


async def _sync_roles_for(member: discord.Member):
    """Re-applies any level role rewards the member has earned but doesn't
    have — for cases where auto-assignment failed (e.g. a permissions fix
    happened after the level-up already occurred)."""
    data = get_level_data(did(member.id))
    current_level = data["level"]
    rows = list_level_roles(member.guild.id)
    given, blocked, gone = [], [], []
    for level, role_id in rows:
        if level > current_level:
            continue
        role = member.guild.get_role(int(role_id))
        if role is None:
            gone.append(str(level))
            continue
        if role in member.roles:
            continue
        try:
            await member.add_roles(role, reason="Level role sync")
            given.append(role.name)
        except discord.Forbidden:
            blocked.append(role.name)
    if not given and not blocked and not gone:
        return "✅ You already have every role reward you've earned."
    parts = []
    if given:
        parts.append(f"🏅 Given: {', '.join(given)}")
    if blocked:
        parts.append(f"⚠️ Couldn't give (check the bot's Manage Roles permission and role position): {', '.join(blocked)}")
    if gone:
        parts.append(f"⚠️ Configured role(s) for level(s) {', '.join(gone)} no longer exist on this server.")
    return "\n".join(parts)


@bot.tree.command(name="syncroles", description="Re-apply any level role rewards you're missing")
async def syncroles(interaction: discord.Interaction):
    if interaction.guild is None or not isinstance(interaction.user, discord.Member):
        await interaction.response.send_message("❌ This only works inside a server.")
        return
    await interaction.response.send_message(await _sync_roles_for(interaction.user))


@bot.command(name="syncroles")
async def syncroles_prefix(ctx: commands.Context):
    if ctx.guild is None:
        await ctx.reply("❌ This only works inside a server.")
        return
    await ctx.reply(await _sync_roles_for(ctx.author))


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


async def broadcast_owner_message(text: str):
    """Post @everyone + text in every server the bot can speak in."""
    sent = 0
    failed = 0
    mention = discord.AllowedMentions(everyone=True, users=False, roles=False, replied_user=False)
    for guild in bot.guilds:
        channel = None
        if guild.system_channel and guild.system_channel.permissions_for(guild.me).send_messages:
            channel = guild.system_channel
        else:
            for ch in guild.text_channels:
                perms = ch.permissions_for(guild.me)
                if perms.send_messages:
                    channel = ch
                    break
        if channel is None:
            failed += 1
            continue
        try:
            await channel.send(f"@everyone {text}", allowed_mentions=mention)
            sent += 1
        except discord.HTTPException:
            failed += 1
    return sent, failed


@bot.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return

    # Owner DM broadcast: "!hello" -> "@everyone hello" in every server
    if message.guild is None and message.content.startswith("!"):
        if await bot.is_owner(message.author):
            text = message.content[1:].strip()
            if not text:
                await message.channel.send("❌ Type something after `!`\nExample: `!nice`")
                return
            sent, failed = await broadcast_owner_message(text)
            await message.channel.send(f"✅ Sent to **{sent}** server(s). Failed: **{failed}**.")
            return

    # XP / leveling
    if message.guild is not None:
        try:
            new_level = add_message_xp(did(message.author.id))
            if new_level is not None:
                level_up_msg = (
                    f"🎉 {message.author.mention} leveled up to **level {new_level}**! "
                    f"(+{XP_LEVEL_UP_REWARD:,} coins)"
                )
                role_id = get_level_role(message.guild.id, new_level)
                if role_id is not None:
                    role = message.guild.get_role(role_id)
                    if role is None:
                        level_up_msg += (
                            f"\n⚠️ A role reward is set for level {new_level}, but that role "
                            f"no longer exists on this server."
                        )
                    elif isinstance(message.author, discord.Member):
                        try:
                            await message.author.add_roles(role, reason=f"Reached level {new_level}")
                            level_up_msg += f"\n🏅 You've earned the **{role.name}** role!"
                        except discord.Forbidden:
                            level_up_msg += (
                                f"\n⚠️ Couldn't give you the **{role.name}** role — the bot needs "
                                f"**Manage Roles** and its role must sit above **{role.name}** in "
                                f"Server Settings → Roles."
                            )
                        except discord.HTTPException as e:
                            level_up_msg += f"\n⚠️ Couldn't give you the **{role.name}** role (Discord error: {e})."
                if new_level >= 20 and grant_achievement(did(message.author.id), "veteran"):
                    level_up_msg += f"\n🏅 Achievement unlocked: **{ACHIEVEMENTS['veteran']['label']}**"
                await message.channel.send(level_up_msg)
        except Exception as e:
            print(f"XP handling failed: {e}")

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
