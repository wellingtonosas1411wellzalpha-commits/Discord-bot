import os
import re
import json
import sys
import urllib.request
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
BOT_VERSION = "1.19.9"

# Newest version first. Update this on every change.
VERSION_HISTORY = [
    {
        "version": "1.19.9",
        "date": "2026-11-03",
        "changes": [
            "Added .fake — test command, the bot says real",
        ],
    },
    {
        "version": "1.19.8",
        "date": "2026-11-03",
        "changes": [
            "New updates are posted in #moderator-only",
        ],
    },
    {
        "version": "1.19.7",
        "date": "2026-11-02",
        "changes": [
            "Removed duplicate slash commands",
        ],
    },
    {
        "version": "1.19.6",
        "date": "2026-11-02",
        "changes": [
            "Added .botban and .xban so bans survive restarts",
            "Added .botunban, .xunban, and .bans",
        ],
    },
    {
        "version": "1.19.5",
        "date": "2026-11-01",
        "changes": [
            "XephonGPT now knows the real bot structure, database, and command style",
        ],
    },
    {
        "version": "1.19.4",
        "date": "2026-11-01",
        "changes": [
            "Added .antidelete on/off to repost deleted messages",
        ],
    },
    {
        "version": "1.19.3",
        "date": "2026-11-01",
        "changes": [
            "Added .delete for replied messages",
            "XephonGPT now knows how the bot code is structured",
        ],
    },
    {
        "version": "1.19.2",
        "date": "2026-11-01",
        "changes": [
            "Fixed split crash: shop choices and shared helpers were in the wrong files",
        ],
    },
    {
        "version": "1.19.1",
        "date": "2026-11-01",
        "changes": [
            "Added .repo back — shows the GitHub repository",
        ],
    },
    {
        "version": "1.19.0",
        "date": "2026-10-31",
        "changes": [
            "Split every command into its own file inside category folders",
        ],
    },
    {
        "version": "1.18.9",
        "date": "2026-10-31",
        "changes": [
            "Removed leftover recharge code and extra blank lines",
        ],
    },
    {
        "version": "1.18.8",
        "date": "2026-10-31",
        "changes": [
            "/xephongpt now shows wild, Ai, normal and on/off choices",
        ],
    },
    {
        "version": "1.18.7",
        "date": "2026-10-31",
        "changes": [
            "Fixed NCM crash: re was not imported",
        ],
    },
    {
        "version": "1.18.6",
        "date": "2026-10-31",
        "changes": [
            "NCM runs each line in a message and no longer fails silently",
        ],
    },
    {
        "version": "1.18.5",
        "date": "2026-10-31",
        "changes": [
            ".reset keeps XP unless you use .reset all",
        ],
    },
    {
        "version": "1.18.4",
        "date": "2026-10-31",
        "changes": [
            ".reset now clears everything back to defaults",
            "Test mode lifts item and reply limits",
            "Menu credits: Developed by Kira",
        ],
    },
    {
        "version": "1.18.3",
        "date": "2026-10-31",
        "changes": [
            "Test mode balance shows infinity total only",
            ".test now requires the tester role only",
            "Spaced out the command menu",
        ],
    },
    {
        "version": "1.18.2",
        "date": "2026-10-31",
        "changes": [
            "Fixed .test crash when saving cooldown time",
        ],
    },
    {
        "version": "1.18.1",
        "date": "2026-10-31",
        "changes": [
            "Moved .ptag to the Owner menu",
            "Fixed .test on/off and accepted vip/tester role names",
            "NCM now runs a command when its name is in the sentence",
            "Cleaner command menu",
        ],
    },
    {
        "version": "1.18.0",
        "date": "2026-10-31",
        "changes": [
            ".ptag is now owner-only",
            "Removed .recharge",
            "Added .test on/off for VIP and tester roles",
        ],
    },
    {
        "version": "1.17.1",
        "date": "2026-10-30",
        "changes": [
            "Fixed No Command Mode so normal sentences are actually handled",
            "NCM now replies when it does not understand",
            "Command errors now reply instead of failing silently",
        ],
    },
    {
        "version": "1.17.0",
        "date": "2026-10-30",
        "changes": [
            "Added No Command Mode — talk normally and Xephon runs the matching command",
        ],
    },
    {
        "version": "1.16.8",
        "date": "2026-10-30",
        "changes": [
            ".ptag now mentions every member one by one",
            "XephonGPT knows the creator is Kira",
        ],
    },
    {
        "version": "1.16.7",
        "date": "2026-10-30",
        "changes": [
            "Removed the owner DM ! and * broadcast feature",
        ],
    },
    {
        "version": "1.16.6",
        "date": "2026-10-30",
        "changes": [
            "Added .ptag — deletes your message, then posts it and tags everyone",
        ],
    },
    {
        "version": "1.16.5",
        "date": "2026-10-24",
        "changes": [
            "Discord login retry now restarts the process instead of reusing a closed session",
        ],
    },
    {
        "version": "1.16.4",
        "date": "2026-10-24",
        "changes": [
            "Slash commands now sync to every server so / works immediately",
        ],
    },
    {
        "version": "1.16.3",
        "date": "2026-10-20",
        "changes": [
            "Retry Discord login if Cloudflare rate-limits the host",
        ],
    },
    {
        "version": "1.16.2",
        "date": "2026-10-20",
        "changes": [
            "Xephon sets itself online when it connects to Discord",
        ],
    },
    {
        "version": "1.16.1",
        "date": "2026-10-20",
        "changes": [
            "Removed cipher. Bot now runs as plain bot.py",
        ],
    },
    {
        "version": "1.16.0",
        "date": "2026-10-20",
        "changes": [
            "Clearer startup errors for Render deploys",
        ],
    },
    {
        "version": "1.15.9",
        "date": "2026-10-20",
        "changes": [
            "Removed .repo for now",
        ],
    },
    {
        "version": "1.15.8",
        "date": "2026-10-20",
        "changes": [
            "Fixed .repo so it sends a plain GitHub link",
        ],
    },
    {
        "version": "1.15.7",
        "date": "2026-10-20",
        "changes": [
            "Added .repo — shows the Xephon GitHub repository",
        ],
    },
    {
        "version": "1.15.6",
        "date": "2026-10-18",
        "changes": [
            ".restart now takes Xephon offline until the new deploy is back",
        ],
    },
    {
        "version": "1.15.5",
        "date": "2026-10-18",
        "changes": [
            "Added .restart — owner only, deploys the latest commit and confirms the version when Xephon is back",
        ],
    },
    {
        "version": "1.15.4",
        "date": "2026-10-18",
        "changes": [
            ".storage now shows real bot, disk, RAM, CPU, and database info",
        ],
    },
    {
        "version": "1.15.3",
        "date": "2026-10-10",
        "changes": [
            "Bot name changed from Kira to Xephon",
            ".kiragpt is now .xephongpt",
        ],
    },
    {
        "version": "1.15.2",
        "date": "2026-10-06",
        "changes": [
            "Wallet and bank moves are now atomic, so two commands at once cannot overwrite each other",
            "Loan payout and payback happen in one database transaction",
            "Mines games are saved, so a restart no longer eats the bet",
            ".auth and AFK now survive restarts",
            "Lucky Potion uses one win formula instead of a second secret reroll",
        ],
    },
    {
        "version": "1.15.1",
        "date": "2026-08-31",
        "changes": [
            "Fixed a money-integrity bug: the treasury and bot bank were read-then-written in two separate steps, so two things happening close together (two gambling losses, a rob fine landing during a loan payout, etc.) could silently overwrite each other and lose tracked money. Both are now atomic single SQL operations",
            "Fixed a stale docstring claiming rob is taxed (it isn't, since 1.11.5)",
        ],
    },
    {
        "version": "1.15.0",
        "date": "2026-08-31",
        "changes": [
            "Gambling losses and rob fines now go to the bot's bank",
            "Added .loan / .payloan — borrow from the bot bank, with a time limit and payback based on the amount",
            "In the bot's DMs, start a message with * to announce it in every server with no pings",
        ],
    },
    {
        "version": "1.14.0",
        "date": "2026-08-31",
        "changes": [
            "No items are infinitely stackable anymore — Lucky Potion maxes at 1 stack, other stackable items max at 5",
            "Added .reset [user] — owner only, sets wallet/bank back to default and clears lucky stacks",
            ".recharge is now 50,000,000 coins and can only be used 3 times per day",
        ],
    },
    {
        "version": "1.13.0",
        "date": "2026-08-31",
        "changes": [
            "/shop now lets you pick an item from a list and set how many to buy",
            "/buy also has an amount option",
            ".buy <item> <amount> works the same way",
        ],
    },
    {
        "version": "1.12.0",
        "date": "2026-08-30",
        "changes": [
            "Added .recharge — bot owner only, adds 100,000,000 coins to your wallet",
        ],
    },
    {
        "version": "1.11.5",
        "date": "2026-08-30",
        "changes": [
            "Rob no longer gets taxed — robbers keep 100% of what they steal. Only salary is taxed into the treasury now",
        ],
    },
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
            "XephonGPT's 50-reply limit now persists across restarts",
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
intents.members = True

class AuthCheckedTree(app_commands.CommandTree):
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if bot_restarting:
            if not interaction.response.is_done():
                await interaction.response.send_message("🔄 Xephon is restarting. I'll be back in a moment.", ephemeral=True)
            return False
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
        if interaction.command:
            reason = ban_reason(did(interaction.user.id), interaction.command.name)
            if reason:
                if not interaction.response.is_done():
                    await interaction.response.send_message(reason, ephemeral=True)
                return False
        if not auth_enabled.get(interaction.guild.id, True):
            await interaction.response.send_message(
                "🔒 The bot is currently disabled in this server. An admin can turn it back on with `/auth on`.",
                ephemeral=True,
            )
            return False
        return True

bot_restarting = False

bot_bans = set()
x_bans = {}
BAN_CATEGORIES = {
    "fun", "info", "economy", "jobs", "pets", "marriage", "achievements",
    "market", "shop", "gambling", "utility", "levels", "admin", "owner",
    "xephongpt", "tester",
}
COMMAND_CATEGORY = {
    "ping": "fun", "8ball": "fun", "joke": "fun", "translate": "fun", "trt": "fun", "poll": "fun",
    "avatar": "info", "userinfo": "info", "profile": "info", "updateinfo": "info", "versions": "info",
    "bal": "economy", "withdraw": "economy", "deposit": "economy", "fish": "economy", "beg": "economy",
    "dig": "economy", "rob": "economy", "loan": "economy", "payloan": "economy", "daily": "economy",
    "work": "economy", "donate": "economy", "lb": "economy",
    "setjob": "jobs", "myjob": "jobs", "jobs": "jobs", "treasury": "jobs",
    "buypet": "pets", "feedpet": "pets", "collectpet": "pets", "pet": "pets",
    "marry": "marriage", "marryaccept": "marriage", "divorce": "marriage", "partner": "marriage",
    "achievements": "achievements",
    "sell": "market", "market": "market", "buylisting": "market", "cancellisting": "market",
    "shop": "shop", "buy": "shop", "use": "shop", "inventory": "shop",
    "cf": "gambling", "roulette": "gambling", "mines": "gambling", "blackjack": "gambling",
    "slot": "gambling", "roll": "gambling",
    "afk": "utility", "cds": "utility", "help": "utility", "ncm": "utility", "menu": "utility",
    "repo": "utility", "antidelete": "utility",
    "rank": "levels", "ranklb": "levels", "setlevelrole": "levels", "levelroles": "levels", "syncroles": "levels",
    "give": "admin", "take": "admin", "delete": "admin",
    "botban": "admin", "botunban": "admin", "xban": "admin", "xunban": "admin", "bans": "admin",
    "storage": "owner", "restart": "owner", "stats": "owner", "activity": "owner",
    "clearcache": "owner", "reset": "owner", "ptag": "owner", "auth": "owner",
    "xephongpt": "xephongpt", "test": "tester",
}

class BotBanFailure(commands.CheckFailure):
    pass

def load_bans():
    global bot_bans, x_bans
    raw = get_meta("bot_bans")
    bot_bans = set(json.loads(raw)) if raw else set()
    raw = get_meta("x_bans")
    x_bans = json.loads(raw) if raw else {}

def save_bans():
    set_meta("bot_bans", json.dumps(sorted(bot_bans)))
    set_meta("x_bans", json.dumps(x_bans))

def ban_reason(user_id: str, command_name: str):
    if user_id in bot_bans:
        return "🚫 You are bot-banned. You cannot use commands."
    category = COMMAND_CATEGORY.get(command_name)
    banned = x_bans.get(user_id, [])
    if category and category in banned:
        return f"🚫 You are banned from **{category}** commands."
    return None


bot = commands.Bot(
    command_prefix=".",
    intents=intents,
    tree_cls=AuthCheckedTree,
    allowed_mentions=discord.AllowedMentions(replied_user=False),
    help_command=None,
)

@bot.check
async def global_auth_check(ctx: commands.Context) -> bool:
    if bot_restarting:
        return False
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
    if ctx.command:
        reason = ban_reason(did(ctx.author.id), ctx.command.name)
        if reason:
            raise BotBanFailure(reason)
    return auth_enabled.get(ctx.guild.id, True)

@bot.event
async def on_command_error(ctx: commands.Context, error: commands.CommandError):
    if isinstance(error, commands.NotOwner):
        await ctx.reply("❌ Only the bot owner can use this command.", mention_author=False)
        return
    if bot_restarting:
        return
    if isinstance(error, BotBanFailure):
        await ctx.reply(str(error), mention_author=False)
        return
    if isinstance(error, commands.CheckFailure):
        await ctx.reply(
            "🔒 The bot is currently disabled in this server. An admin can turn it back on with `.auth on`.",
            mention_author=False,
        )
        return
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.reply(f"❌ Missing `{error.param.name}`. Try `.help {ctx.command}`.", mention_author=False)
        return
    if isinstance(error, commands.CommandNotFound):
        return
    if isinstance(error, commands.BadArgument):
        await ctx.reply("❌ I couldn't read one of those arguments.", mention_author=False)
        return
    print(f"Command error in {getattr(ctx.command, 'name', '?')}: {error}")
    await ctx.reply("❌ That command failed. Try again.", mention_author=False)

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

TAX_RATE = 0.10  # skimmed off salary only (rob is untaxed), feeds the server treasury
TREASURY_META_KEY = "treasury_balance"
BOT_BANK_KEY = "bot_bank"

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
RENDER_DEPLOY_HOOK = os.getenv("RENDER_DEPLOY_HOOK", "")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
groq_client = groq.Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None

try:
    db_pool = psycopg2.pool.SimpleConnectionPool(1, 10, DATABASE_URL) if DATABASE_URL else None
except Exception as e:
    print(f"Database connection failed: {e}")
    db_pool = None

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
    cur.execute("""
        CREATE TABLE IF NOT EXISTS loans (
            user_id TEXT PRIMARY KEY,
            principal BIGINT NOT NULL,
            repay_amount BIGINT NOT NULL,
            remaining BIGINT NOT NULL,
            due_at DOUBLE PRECISION NOT NULL
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS afk (
            user_id TEXT PRIMARY KEY,
            reason TEXT NOT NULL
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS mines_games (
            user_id TEXT PRIMARY KEY,
            bet BIGINT NOT NULL,
            mines_count INTEGER NOT NULL,
            mine_positions TEXT NOT NULL,
            revealed TEXT NOT NULL
        )
    """)
    conn.commit()
    load_persistent_state(cur)
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
    """Set absolute wallet/bank under a row lock. Prefer adjust_balance for transfers."""
    get_balance(user_id)
    conn, cur = get_db()
    cur.execute("SELECT wallet, bank FROM balances WHERE user_id = %s FOR UPDATE", (user_id,))
    row = cur.fetchone()
    current_wallet, current_bank = row
    new_wallet = current_wallet if wallet is None else wallet
    new_bank = current_bank if bank is None else bank
    if new_wallet < 0 or new_bank < 0:
        conn.rollback()
        cur.close()
        release_db(conn)
        return False
    cur.execute(
        "UPDATE balances SET wallet = %s, bank = %s WHERE user_id = %s",
        (new_wallet, new_bank, user_id),
    )
    conn.commit()
    cur.close()
    release_db(conn)
    return True

def adjust_balance(user_id, wallet_delta: int = 0, bank_delta: int = 0):
    """Atomically add deltas. Returns new balances, or None if it would go negative."""
    get_balance(user_id)
    conn, cur = get_db()
    cur.execute(
        "UPDATE balances SET wallet = wallet + %s, bank = bank + %s "
        "WHERE user_id = %s AND wallet + %s >= 0 AND bank + %s >= 0 "
        "RETURNING wallet, bank",
        (wallet_delta, bank_delta, user_id, wallet_delta, bank_delta),
    )
    row = cur.fetchone()
    conn.commit()
    cur.close()
    release_db(conn)
    if row is None:
        return None
    return {"wallet": row[0], "bank": row[1]}

def load_persistent_state(cur):
    cur.execute("SELECT key, value FROM bot_meta WHERE key LIKE 'auth:%'")
    for key, value in cur.fetchall():
        try:
            auth_enabled[int(key.split(":", 1)[1])] = (value != "off")
        except (ValueError, IndexError):
            continue
    cur.execute("SELECT user_id, reason FROM afk")
    for user_id, reason in cur.fetchall():
        afk_users[user_id] = reason
    cur.execute("SELECT user_id, bet, mines_count, mine_positions, revealed FROM mines_games")
    for user_id, bet, mines_count, mines_raw, revealed_raw in cur.fetchall():
        active_mines_games[user_id] = {
            "bet": bet,
            "mines_count": mines_count,
            "mine_positions": set(int(x) for x in mines_raw.split(",") if x),
            "revealed": set(int(x) for x in revealed_raw.split(",") if x),
        }

def set_auth_state(guild_id: int, enabled: bool):
    auth_enabled[guild_id] = enabled
    set_meta(f"auth:{guild_id}", "on" if enabled else "off")

def set_afk(user_id, reason: str):
    afk_users[user_id] = reason
    conn, cur = get_db()
    cur.execute(
        "INSERT INTO afk (user_id, reason) VALUES (%s, %s) "
        "ON CONFLICT (user_id) DO UPDATE SET reason = EXCLUDED.reason",
        (user_id, reason),
    )
    conn.commit()
    cur.close()
    release_db(conn)

def clear_afk(user_id):
    afk_users.pop(user_id, None)
    conn, cur = get_db()
    cur.execute("DELETE FROM afk WHERE user_id = %s", (user_id,))
    conn.commit()
    cur.close()
    release_db(conn)

def save_mines_game(user_id):
    game = active_mines_games.get(user_id)
    conn, cur = get_db()
    if not game:
        cur.execute("DELETE FROM mines_games WHERE user_id = %s", (user_id,))
    else:
        mines = ",".join(str(x) for x in sorted(game["mine_positions"]))
        revealed = ",".join(str(x) for x in sorted(game["revealed"]))
        cur.execute(
            "INSERT INTO mines_games (user_id, bet, mines_count, mine_positions, revealed) "
            "VALUES (%s, %s, %s, %s, %s) "
            "ON CONFLICT (user_id) DO UPDATE SET bet = EXCLUDED.bet, mines_count = EXCLUDED.mines_count, "
            "mine_positions = EXCLUDED.mine_positions, revealed = EXCLUDED.revealed",
            (user_id, game["bet"], game["mines_count"], mines, revealed),
        )
    conn.commit()
    cur.close()
    release_db(conn)

def delete_mines_game(user_id):
    active_mines_games.pop(user_id, None)
    save_mines_game(user_id)

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
        adjust_balance(user_id, wallet_delta=XP_LEVEL_UP_REWARD)
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

def _adjust_meta_int(key: str, delta: int) -> int:
    """Atomically adds delta to a numeric bot_meta value in a single SQL
    statement (creating the row at 0 first if needed) and returns the new
    total. A separate get_meta()+set_meta() pair is NOT safe here — two
    concurrent callers (e.g. two gambling losses landing at the same
    moment) can race and one write silently clobbers the other."""
    conn, cur = get_db()
    cur.execute(
        "INSERT INTO bot_meta (key, value) VALUES (%s, %s) "
        "ON CONFLICT (key) DO UPDATE SET value = "
        "  (GREATEST(0, COALESCE(bot_meta.value, '0')::bigint + %s))::text "
        "RETURNING value",
        (key, str(max(delta, 0)), delta),
    )
    new_value = int(cur.fetchone()[0])
    conn.commit()
    cur.close()
    release_db(conn)
    return new_value

def get_treasury() -> int:
    value = get_meta(TREASURY_META_KEY)
    return int(value) if value else 0

def add_to_treasury(amount: int):
    if amount <= 0:
        return
    _adjust_meta_int(TREASURY_META_KEY, amount)

def get_bot_bank() -> int:
    value = get_meta(BOT_BANK_KEY)
    return int(value) if value else 0

def add_to_bot_bank(amount: int):
    if amount <= 0:
        return
    _adjust_meta_int(BOT_BANK_KEY, amount)

def take_from_bot_bank(amount: int) -> bool:
    """Atomically checks-and-subtracts in one statement so two people
    can't both pass the 'is there enough' check against the same stale
    balance and over-draw the bot bank (e.g. two loans taken at once)."""
    if amount <= 0:
        return True
    conn, cur = get_db()
    cur.execute(
        "UPDATE bot_meta SET value = (bot_meta.value::bigint - %s)::text "
        "WHERE key = %s AND COALESCE(bot_meta.value, '0')::bigint >= %s "
        "RETURNING value",
        (amount, BOT_BANK_KEY, amount),
    )
    row = cur.fetchone()
    conn.commit()
    cur.close()
    release_db(conn)
    return row is not None

def house_take(amount: int):
    """Send lost coins to the bot's lending bank."""
    add_to_bot_bank(amount)

def loan_terms(amount: int):
    """Return (hours, repay_amount) based on how big the loan is."""
    if amount <= 10_000:
        hours, rate = 2, 1.10
    elif amount <= 100_000:
        hours, rate = 6, 1.15
    elif amount <= 1_000_000:
        hours, rate = 12, 1.20
    elif amount <= 10_000_000:
        hours, rate = 24, 1.30
    else:
        hours, rate = 48, 1.40
    return hours, int(amount * rate)

def get_loan(user_id):
    conn, cur = get_db()
    cur.execute(
        "SELECT principal, repay_amount, remaining, due_at FROM loans WHERE user_id = %s",
        (user_id,),
    )
    row = cur.fetchone()
    cur.close()
    release_db(conn)
    if not row:
        return None
    return {
        "principal": row[0],
        "repay_amount": row[1],
        "remaining": row[2],
        "due_at": row[3],
    }

def format_loan_status(user_id) -> str:
    loan = get_loan(user_id)
    if not loan:
        return (
            f"🏦 Bot bank: **${get_bot_bank():,}**\n"
            "You have no active loan.\n"
            "Usage: `.loan <amount>`"
        )
    left = int(loan["due_at"] - time.time())
    if left <= 0:
        timer = "⚠️ OVERDUE"
    else:
        hours = left // 3600
        mins = (left % 3600) // 60
        timer = f"{hours}h {mins}m left"
    return (
        "╭━━━〔 🏦 ʟᴏᴀɴ 〕━━━⬣\n"
        f"┃ Borrowed: **${loan['principal']:,}**\n"
        f"┃ Pay back: **${loan['remaining']:,}** / ${loan['repay_amount']:,}\n"
        f"┃ Time: {timer}\n"
        "┃ Pay with `.payloan <amount|all>`\n"
        "╰━━━━━━━━━━━━━━━━━━━━━━⬣"
    )

def take_loan(user_id, amount_str: str) -> str:
    if not amount_str:
        return format_loan_status(user_id)
    if get_loan(user_id):
        return "❌ Pay off your current loan first.\n" + format_loan_status(user_id)
    try:
        amount = parse_amount(amount_str, all_value=get_bot_bank())
    except ValueError:
        return "❌ Usage: `.loan <amount>`"
    if amount < 1000:
        return "❌ Minimum loan is **$1,000**."
    if amount > 20_000_000:
        return "❌ Maximum loan is **$20,000,000**."
    bank = get_bot_bank()
    max_allowed = bank // 2
    if amount > bank:
        return f"❌ The bot bank only has **${bank:,}**."
    if amount > max_allowed:
        return f"❌ You can borrow up to half the bot bank (**${max_allowed:,}**)."
    hours, repay = loan_terms(amount)
    if not take_from_bot_bank(amount):
        return "❌ The bot bank doesn't have enough right now."
    due_at = time.time() + hours * 3600
    conn, cur = get_db()
    cur.execute(
        "INSERT INTO loans (user_id, principal, repay_amount, remaining, due_at) "
        "VALUES (%s, %s, %s, %s, %s)",
        (user_id, amount, repay, repay, due_at),
    )
    conn.commit()
    cur.close()
    release_db(conn)
    bal = get_balance(user_id)
    adjust_balance(user_id, wallet_delta=amount)
    return (
        f"✅ Loan approved: **${amount:,}**\n"
        f"Pay back **${repay:,}** within **{hours} hours**.\n"
        f"Use `.payloan <amount|all>`"
    )

def pay_loan(user_id, amount_str: str) -> str:
    loan = get_loan(user_id)
    if not loan:
        return "❌ You don't have a loan to pay."
    bal = get_balance(user_id)
    try:
        amount = parse_amount(amount_str or "all", all_value=min(bal["wallet"], loan["remaining"]))
    except ValueError:
        return "❌ Usage: `.payloan <amount|all>`"
    if amount <= 0:
        return "❌ Enter an amount greater than $0."
    if amount > bal["wallet"]:
        return f"❌ You only have **${bal['wallet']:,}** in your wallet."
    pay = min(amount, loan["remaining"])
    adjust_balance(user_id, wallet_delta=-pay)
    add_to_bot_bank(pay)
    leftover = loan["remaining"] - pay
    conn, cur = get_db()
    if leftover <= 0:
        cur.execute("DELETE FROM loans WHERE user_id = %s", (user_id,))
        conn.commit()
        cur.close()
        release_db(conn)
        return f"✅ Loan paid off! **${pay:,}** returned to the bot bank."
    cur.execute("UPDATE loans SET remaining = %s WHERE user_id = %s", (leftover, user_id))
    conn.commit()
    cur.close()
    release_db(conn)
    return f"✅ Paid **${pay:,}**. Still owed: **${leftover:,}**."

def collect_overdue_loans():
    conn, cur = get_db()
    cur.execute("SELECT user_id, remaining FROM loans WHERE due_at <= %s", (time.time(),))
    rows = cur.fetchall()
    cur.close()
    release_db(conn)
    for user_id, remaining in rows:
        bal = get_balance(user_id)
        take = min(remaining, bal["wallet"] + bal["bank"])
        from_wallet = min(take, bal["wallet"])
        from_bank = take - from_wallet
        adjust_balance(user_id, wallet_delta=-from_wallet, bank_delta=-from_bank)
        add_to_bot_bank(take)
        leftover = remaining - take
        conn, cur = get_db()
        if leftover <= 0:
            cur.execute("DELETE FROM loans WHERE user_id = %s", (user_id,))
        else:
            cur.execute("UPDATE loans SET remaining = %s WHERE user_id = %s", (leftover, user_id))
        conn.commit()
        cur.close()
        release_db(conn)

def apply_tax(amount: int, rate: float = TAX_RATE):
    """Splits an amount into (net, tax). The tax portion is added to the
    server treasury. Use this on salary (rob is untaxed as of 1.11.5)."""
    if amount <= 0:
        return amount, 0
    tax = int(amount * rate)
    net = amount - tax
    add_to_treasury(tax)
    return net, tax

def build_balance_text(user_id: int):
    if test_mode_on(user_id):
        return (
            "╭━━━〔 💳 ACCOUNT BALANCE 〕━━━⬣\n"
            "┃\n"
            "┃ 💠 TOTAL : [ ♾️ ]\n"
            "┃\n"
            "╰━━━━━━━━━━━━━━━━━━━━━━⬣"
        )
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
    adjust_balance(user_id, wallet_delta=amount, bank_delta=-amount)
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
    adjust_balance(user_id, wallet_delta=-amount, bank_delta=amount)
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
    "xephongpt": "Talk to XephonGPT.\n`.xephongpt on/off` continuous chat\n`.xephongpt wild on` / `ai on` / `normal on`\n`.xephongpt <message>`",
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
    "loan": "Borrow coins from the bot bank. Time limit and payback depend on the amount.\nUsage: `.loan [amount]`",
    "payloan": "Pay back your loan.\nUsage: `.payloan <amount|all>`",
    "shop": "View shop items. Slash command lets you pick an item and amount.\nUsage: `.shop` or `/shop`",
    "buy": "Buy an item. Add a number for quantity.\nUsage: `.buy vx` / `.buy gun 3` / `/shop`",
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
    "ncm": "No Command Mode. Talk normally and Xephon runs the matching command.\nUsage: `.ncm on` / `.ncm off`",
    "repo": "Show the GitHub repository.\nUsage: `.repo`",
    "fake": "Test command. The bot says real.\nUsage: `.fake`",
    "delete": "[Manage Messages] Delete the message you replied to.\nUsage: reply with `.delete`",
    "botban": "[Admin] Ban a user from all commands.\nUsage: `.botban @user`",
    "botunban": "[Admin] Remove a full command ban.\nUsage: `.botunban @user`",
    "xban": "[Admin] Ban a user from one category.\nUsage: `.xban @user gambling`",
    "xunban": "[Admin] Remove a category ban.\nUsage: `.xunban @user gambling`",
    "bans": "[Admin] Show bot bans and category bans.\nUsage: `.bans`",
    "antidelete": "[Admin] Repost deleted messages.\nUsage: `.antidelete on` / `.antidelete off`",
    "ptag": "[Owner] Delete your message, then mention every member with it.\nUsage: `.ptag <message>`",
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
    "test": "[VIP/tester] Turn test money on or off.\nUsage: `.test on` / `.test off`",
    "reset": "[Owner] Reset a player to defaults. XP stays unless you use `.reset all`.\nUsage: `.reset` / `.reset @user` / `.reset all`",
    "restart": "[Owner] Deploy the latest commit and restart Xephon.\nUsage: `.restart`",
}

def build_menu_text():
    return (
        '✦  ━━━━━   X E P H O N   ━━━━━  ✦\n'
        '\n'
        'Developed by Kira\n'
        '`.help <command>` for details\n'
        '\n'
        '◈  XEPHONGPT\n'
        '   xephongpt on / off\n'
        '   xephongpt wild / ai / normal\n'
        '\n'
        '◈  FUN\n'
        '   ping  ·  8ball  ·  joke\n'
        '   translate  ·  trt\n'
        '\n'
        '◈  INFO\n'
        '   avatar  ·  userinfo  ·  profile\n'
        '   poll  ·  updateinfo  ·  versions\n'
        '\n'
        '◈  ECONOMY\n'
        '   bal  ·  daily  ·  work  ·  lb\n'
        '   rank  ·  ranklb  ·  withdraw  ·  deposit\n'
        '   fish  ·  beg  ·  dig  ·  rob\n'
        '   loan  ·  payloan\n'
        '\n'
        '◈  JOBS\n'
        '   jobs  ·  setjob  ·  myjob  ·  treasury\n'
        '\n'
        '◈  PETS\n'
        '   buypet  ·  feedpet  ·  collectpet  ·  pet\n'
        '\n'
        '◈  MARRIAGE\n'
        '   marry  ·  marryaccept  ·  divorce  ·  partner\n'
        '\n'
        '◈  SHOP\n'
        '   shop  ·  buy  ·  use  ·  inventory\n'
        '\n'
        '◈  GAMBLING\n'
        '   cf  ·  roll  ·  roulette\n'
        '   mines  ·  blackjack  ·  slot\n'
        '\n'
        '◈  UTILITY\n'
        '   afk  ·  cds  ·  donate  ·  help  ·  ncm  ·  repo  ·  fake\n'
        '\n'
        '◈  ADMIN\n'
        '   give  ·  take  ·  delete  ·  botban  ·  xban\n'
        '\n'
        '◈  OWNER\n'
        '   auth  ·  storage  ·  restart  ·  stats\n'
        '   activity  ·  clearcache  ·  reset  ·  ptag\n'
        '\n'
        '◈  TESTER\n'
        '   test on  /  test off\n'
        '\n'
        '✦  Developed by Kira  ✦\n'
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
    cpu = psutil.cpu_percent(interval=0.3)
    latency = getattr(bot, "latency", None)
    ping = round(latency * 1000) if isinstance(latency, (int, float)) and latency == latency else 0
    try:
        disk = psutil.disk_usage("/")
        disk_line = f"💿 Disk: {disk.used / (1024 ** 3):.2f} / {disk.total / (1024 ** 3):.2f} GB ({disk.percent}%)"
    except Exception:
        disk_line = "💿 Disk: unavailable"
    try:
        members = sum((g.member_count or 0) for g in bot.guilds)
    except Exception:
        members = 0
    db_status = "connected"
    economy_users = 0
    treasury = 0
    bot_bank = 0
    try:
        conn, cur = get_db()
        cur.execute("SELECT COUNT(*) FROM balances")
        economy_users = cur.fetchone()[0] or 0
        cur.close()
        release_db(conn)
        treasury = get_treasury()
        bot_bank = get_bot_bank()
    except Exception as e:
        db_status = f"error ({e.__class__.__name__})"
    return (
        "⚙️ *Bot Storage / Status*\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        f"📦 Version: {BOT_VERSION}\n"
        f"🕒 Uptime: {format_uptime(uptime)}\n"
        f"📡 Ping: {ping}ms\n"
        f"🏠 Servers: {len(bot.guilds)}\n"
        f"👥 Members: {members:,}\n"
        f"👤 Cached users: {len(bot.users):,}\n"
        f"💬 Cached messages: {len(bot.cached_messages):,}\n"
        f"🗄️ Database: {db_status}\n"
        f"👛 Economy users: {economy_users:,}\n"
        f"🏦 Treasury: ${treasury:,}\n"
        f"🤖 Bot bank: ${bot_bank:,}\n"
        f"🧠 XephonGPT sessions: {len(kiragpt_sessions)}\n"
        f"💣 Active mines games: {len(active_mines_games)}\n"
        f"🃏 Active blackjack games: {len(active_blackjack_games)}\n"
        f"💾 Bot RAM: {proc_mb:.1f} MB\n"
        f"🖥️ System RAM: {mem.used / (1024 ** 2):.0f} / {mem.total / (1024 ** 2):.0f} MB ({mem.percent}%)\n"
        f"{disk_line}\n"
        f"⚙️ CPU: {cpu}%\n"
        f"🧵 Threads: {process.num_threads()}\n"
        "━━━━━━━━━━━━━━━━━━━"
    )

def do_clearcache():
    process = psutil.Process()
    before_mb = process.memory_info().rss / (1024 * 1024)

    sessions_cleared = len(kiragpt_sessions)
    kiragpt_sessions.clear()

    mines_cleared = 0

    bj_cleared = len(active_blackjack_games)
    active_blackjack_games.clear()

    afk_cleared = 0

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
        f"🧠 XephonGPT sessions wiped: {sessions_cleared}\n"
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
    adjust_balance(user_id, wallet_delta=amount)

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
    adjust_balance(user_id, wallet_delta=amount)

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
        adjust_balance(user_id, wallet_delta=amount)

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
    adjust_balance(user_id, wallet_delta=amount)
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
    adjust_balance(user_id, wallet_delta=amount)
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

    if adjust_balance(user_id, wallet_delta=-bet) is None:
        return "❌ You don't have that much in your wallet."
    mine_positions = set(random.sample(range(1, 26), mines_count))
    active_mines_games[user_id] = {
        "bet": bet,
        "mines_count": mines_count,
        "mine_positions": mine_positions,
        "revealed": set(),
    }
    save_mines_game(user_id)
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
        dodge_chance = max(0.0, luck_chance(0.5, user_id) - 0.5)
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
            house_take(game["bet"])
            text = build_mines_exploded_text(game, position)
            delete_mines_game(user_id)
            return text

    game["revealed"].add(position)
    safe_total = 25 - game["mines_count"]
    if len(game["revealed"]) == safe_total:
        multiplier = mines_multiplier(game["mines_count"], len(game["revealed"])) * MINES_HOUSE_EDGE
        payout = int(game["bet"] * multiplier)
        bal = get_balance(user_id)
        adjust_balance(user_id, wallet_delta=payout)
        grid = build_mines_grid(game)
        delete_mines_game(user_id)
        return (
            "💣 *MINES GAME* 💣\n"
            "──────────────────\n"
            f"{grid}\n"
            "──────────────────\n\n"
            f"🎉 ALL GEMS FOUND! Payout: ${payout:,}"
        )

    save_mines_game(user_id)
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
    adjust_balance(user_id, wallet_delta=payout)
    grid = build_mines_grid(game)
    delete_mines_game(user_id)
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

    adjust_balance(user_id, wallet_delta=-bet)

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
        house_take(bet)
        return build_blackjack_text(
            game, reveal_dealer=True,
            result_line=f"💥 Bust! You lost **${bet:,}**.",
        )

    if natural:
        payout = int(bet * 2.5)
        bal = get_balance(user_id)
        adjust_balance(user_id, wallet_delta=payout)
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
        adjust_balance(user_id, wallet_delta=payout)
        result_line = f"🎉 You won **${payout:,}**!"
    elif player_total == dealer_total:
        bal = get_balance(user_id)
        adjust_balance(user_id, wallet_delta=bet)
        result_line = f"🤝 Push! Your **${bet:,}** bet was returned."
    else:
        if random.random() < max(0.0, luck_chance(0.5, user_id) - 0.5):
            payout = bet * 2
            bal = get_balance(user_id)
            adjust_balance(user_id, wallet_delta=payout)
            result_line = f"🍀 Lucky save! You won **${payout:,}**!"
        else:
            house_take(bet)
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

    adjust_balance(user_id, wallet_delta=-amount)

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

    # Lucky Potion: one extra chance, same formula as other games, not a second system.
    if max_count == 1 and random.random() < max(0.0, luck_chance(0.25, user_id) - 0.25):
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
        adjust_balance(user_id, wallet_delta=payout)
    else:
        house_take(amount)
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

    adjust_balance(user_id, wallet_delta=-amount)
    roll = random.randint(1, 6)
    won = roll >= 4
    if not won and random.random() < max(0.0, luck_chance(0.5, user_id) - 0.5):
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
        adjust_balance(user_id, wallet_delta=payout)
        final_bal = get_balance(user_id)
        return header + (
            "🎉 *YOU WON!* 🎉\n"
            f"Payout: ${payout:,}\n\n"
            f"💵 Wallet: ${final_bal['wallet']:,}"
        )
    else:
        house_take(amount)
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

def test_mode_on(user_id) -> bool:
    return get_meta(f"test_mode:{user_id}") == "on"

def do_donate(sender_id: int, receiver_id: int, amount_str: str):
    if test_mode_on(sender_id):
        return "❌ Test money cannot be donated."
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

    adjust_balance(sender_id, wallet_delta=-amount)
    receiver_bal = get_balance(receiver_id)
    adjust_balance(receiver_id, wallet_delta=amount)
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

def buy_shop_item(user_id: int, guild_id: int, item_id: int, amount: int = 1):
    """Returns (success: bool, message: str, role_id_or_None)."""
    item = get_shop_item(guild_id, item_id)
    if item is None:
        return False, "❌ That item doesn't exist in this server's shop.", None
    _, name, price, description, role_id = item
    amount = max(1, int(amount))
    total = price * amount

    bal = get_balance(user_id)
    if bal["wallet"] < total:
        return False, f"❌ You need **{total:,}** coins but only have **{bal['wallet']:,}** in your wallet.", None

    adjust_balance(user_id, wallet_delta=-total)

    conn, cur = get_db()
    cur.execute(
        "INSERT INTO inventory (user_id, item_id, quantity) VALUES (%s, %s, %s) "
        "ON CONFLICT (user_id, item_id) DO UPDATE SET quantity = inventory.quantity + %s",
        (user_id, item_id, amount, amount),
    )
    conn.commit()
    cur.close()
    release_db(conn)

    bought = f"{amount}x **{name}**" if amount > 1 else f"**{name}**"
    return True, f"✅ You bought {bought} for **{total:,}** coins!", int(role_id) if role_id else None

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
        "description": "Adds +0.5 to your win-rate multiplier. Max 1 stack. Use with .use lucky",
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
        "description": "Blocks the next robbery against you, then is used up. Max 5 held",
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

MAX_LUCKY_STACKS = 1
MAX_ITEM_STACK = 5

def get_lucky_stacks(user_id) -> int:
    return min(MAX_LUCKY_STACKS, get_user_effects(user_id)["lucky_stacks"])

def get_cd_boost_until(user_id):
    return get_user_effects(user_id)["cd_boost_until"]

def luck_chance(base: float, user_id) -> float:
    """Each lucky potion adds +0.5 to the win multiplier. Capped at 95%."""
    stacks = get_lucky_stacks(user_id)
    return min(0.95, base * (1 + 0.5 * stacks))

def buy_global_item(user_id, item_key: str, amount: int = 1):
    item = GLOBAL_ITEMS[item_key]
    amount = max(1, int(amount))
    testing = test_mode_on(user_id)
    if not testing and not item.get("consumable") and not item.get("stackable"):
        if has_global_item(user_id, item_key):
            return False, f"❌ You already own a **{item['name']}** — no need to buy another."
        amount = 1
    elif not testing:
        owned = get_global_item_qty(user_id, item_key)
        if owned + amount > MAX_ITEM_STACK:
            return False, f"❌ You can only hold **{MAX_ITEM_STACK}** of **{item['name']}** (you have {owned})."
    bal = get_balance(user_id)
    total = item["price"] * amount
    if bal["wallet"] < total:
        return False, f"❌ You need **{total:,}** coins but only have **{bal['wallet']:,}** in your wallet."
    adjust_balance(user_id, wallet_delta=-total)
    add_global_item(user_id, item_key, amount)
    extra = ""
    if item.get("consumable"):
        extra = f"\nUse it with `.use {item_key}`"
    bought = f"{amount}x **{item['name']}**" if amount > 1 else f"**{item['name']}**"
    return True, f"✅ You bought {bought} for **{total:,}** coins!{extra}"

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
        current = get_lucky_stacks(user_id)
        if current >= MAX_LUCKY_STACKS:
            add_global_item(user_id, item_key, 1)
            return f"❌ Lucky Potion is already maxed at **{MAX_LUCKY_STACKS}** stack. Potion was not used."
        stacks = current + 1
        set_user_effects(user_id, lucky_stacks=stacks)
        return (
            f"🍀 You drank a **Lucky Potion**!\n"
            f"Lucky stacks: **{stacks}/{MAX_LUCKY_STACKS}**\n"
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
    lines.append("┃ Buy with `.buy vx 2` or `/shop` (pick item + amount)")
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
    adjust_balance(user_id, wallet_delta=-info["price"])

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
    adjust_balance(user_id, wallet_delta=-PET_FEED_COST)

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
    adjust_balance(user_id, wallet_delta=earned)
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
        adjust_balance(victim_id, wallet_delta=-stolen)
        adjust_balance(robber_id, wallet_delta=stolen)
        newly_earned = grant_achievement(robber_id, "first_blood")
        text = f"💰 You successfully robbed **{stolen:,}** coins! No tax on rob — it's all yours."
        if newly_earned:
            text += f"\n🏅 Achievement unlocked: **{ACHIEVEMENTS['first_blood']['label']}**"
        return text
    else:
        penalty = int(robber_bal["wallet"] * ROB_FAIL_PENALTY_PERCENT)
        penalty = min(penalty, robber_bal["wallet"])
        adjust_balance(robber_id, wallet_delta=-penalty)
        house_take(penalty)
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
        adjust_balance(user_id, wallet_delta=net)
        cur.execute("UPDATE jobs SET last_salary = NOW() WHERE user_id = %s", (user_id,))
    conn.commit()
    cur.close()
    release_db(conn)

@tasks.loop(minutes=15)
async def loan_collect_loop():
    collect_overdue_loans()

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
    load_bans()
    try:
        await bot.change_presence(
            status=discord.Status.online,
            activity=discord.Game(name="Xephon"),
        )
        print("Xephon presence set to online")
    except Exception as e:
        print(f"Could not set online presence: {e}")
    if not salary_payout_loop.is_running():
        salary_payout_loop.start()
    if not bank_interest_loop.is_running():
        bank_interest_loop.start()
    if not loan_collect_loop.is_running():
        loan_collect_loop.start()
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} global slash command(s)")
        for guild in bot.guilds:
            try:
                bot.tree.clear_commands(guild=guild)
                await bot.tree.sync(guild=guild)
                print(f"Cleared duplicate slash commands in {guild.name}")
            except Exception as e:
                print(f"Guild slash cleanup failed for {guild.name}: {e}")
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
    await announce_restart_if_pending()
    await announce_update_if_new()


async def announce_update_if_new():
    if get_meta("last_announced_version") == BOT_VERSION:
        return
    text_out = build_updateinfo_text()
    sent = 0
    for guild in bot.guilds:
        channel = discord.utils.get(guild.text_channels, name="moderator-only")
        if channel is None:
            continue
        try:
            await channel.send(text_out)
            sent += 1
        except Exception as e:
            print(f"Update announce failed in {guild.name}: {e}")
    set_meta("last_announced_version", BOT_VERSION)
    print(f"Update announce sent to {sent} moderator-only channel(s)")

async def announce_restart_if_pending():
    if get_meta("restart_announce_pending") != "1":
        return
    channel_id = get_meta("restart_announce_channel")
    set_meta("restart_announce_pending", "0")
    if not channel_id:
        return
    try:
        channel = bot.get_channel(int(channel_id)) or await bot.fetch_channel(int(channel_id))
    except Exception as e:
        print(f"Restart announce channel missing: {e}")
        return
    try:
        await channel.send(f"✅ All updates applied. Xephon is at **v{BOT_VERSION}**.")
    except Exception as e:
        print(f"Restart announce failed: {e}")

def trigger_render_deploy():
    if not RENDER_DEPLOY_HOOK:
        return False, "RENDER_DEPLOY_HOOK is not set in Render."
    req = urllib.request.Request(RENDER_DEPLOY_HOOK, data=b"{}", method="POST")
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            if 200 <= resp.status < 300:
                return True, "ok"
            return False, f"Render returned {resp.status}."
    except Exception as e:
        return False, str(e)

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
        "You are XephonGPT, a coding assistant built into the Xephon Discord bot. "
        "You were created by Kira. If anyone asks who made you or who your creator is, "
        "answer that Kira created you. Never mention Meta, Llama, or any other company/model name. "
        "Use markdown code blocks for code. Keep explanations clear. "
        "BOT STRUCTURE: bot.py only loads folders. core.py holds the bot object, PostgreSQL helpers, "
        "economy logic, and shared functions. Commands are one file each inside folders: "
        "fun, info, economy, jobs, pets, marriage, achievements, market, shop, gambling, utility, "
        "levels, admin, owner, Xephongpt, tester. Examples: utility/antidelete.py, admin/delete.py, "
        "economy/bal.py, shop/buy.py. "
        "COMMAND STYLE: every command file starts with `from core import *`. Register both "
        "`@bot.command(name=...)` and `@bot.tree.command(name=...)`. Prefix is `.`. "
        "There are no cogs, no Cog classes, no setup(), and no load_extension. "
        "DATABASE: PostgreSQL through psycopg2. Use get_db() which returns conn, cur. "
        "SQL placeholders are %s, never ?. Commit with conn.commit(), then cur.close() and release_db(conn). "
        "For simple on/off settings use get_meta(key) and set_meta(key, value). There is no settings table, "
        "no db.fetchrow, no db.execute, and no log object. User ids are stored with did(user.id). "
        "EVENTS: use @bot.listen('event_name'), never @bot.event, so you do not replace existing events. "
        "When asked to add a command, write one file in that exact style and say which folder it belongs in. "
        "Do not invent libraries, tables, or helpers that are not listed here."
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
            " Important: the person you are talking to right now is Kira, your creator. "
            "If they ask who they are, tell them they are Kira. If they ask who created you, say Kira."
        )
    return prompt

async def generate_code_response(prompt: str, mode: str = "normal", is_creator: bool = False, history: list = None) -> str:
    if not groq_client:
        return "❌ XephonGPT isn't set up yet — the owner needs to add a `GROQ_API_KEY`."
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
        return text if text else "❌ XephonGPT didn't return anything — try rephrasing."
    except Exception as e:
        return f"❌ XephonGPT error: {e}"

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


@bot.event
async def on_message(message: discord.Message):
    if message.author.bot or bot_restarting:
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
        clear_afk(did(message.author.id))
        await message.reply(f"Welcome back {message.author.mention}, I removed your afk.", mention_author=False)

    for user in message.mentions:
        if did(user.id) in afk_users:
            await message.reply(
                f"{user.display_name} is afk: {afk_users[did(user.id)]}",
                mention_author=False,
            )

    # XephonGPT continuous chat
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
            print(f"XephonGPT reply handling failed: {e}")

    # No Command Mode
    if message.guild is not None and message.content and not message.content.startswith("."):
        user_id = did(message.author.id)
        lowered = message.content.strip().lower()
        if user_id in ncm_pending:
            pending = ncm_pending.pop(user_id)
            if lowered in ("yes", "y", "confirm", "yeah", "ok", "okay"):
                await run_ncm_command(message, pending["command"], pending["args"])
            else:
                await message.reply("❌ Cancelled.", mention_author=False)
            return
        if ncm_is_on(user_id) and message.content.strip() and len(message.content) <= 500:
            lines = [ln.strip() for ln in message.content.splitlines() if ln.strip()]
            try:
                if len(lines) > 1:
                    ran = 0
                    for line in lines[:6]:
                        command, args = match_command_in_sentence(line)
                        if not command:
                            await message.reply(f"❌ No command in `{line}`.", mention_author=False)
                            continue
                        await run_ncm_command(message, command, args)
                        ran += 1
                    if ran == 0:
                        await message.reply("❌ None of those lines matched a command.", mention_author=False)
                    return
                async with message.channel.typing():
                    command, args = await parse_ncm_request(message.content)
                if not command:
                    await message.reply(
                        "❌ I couldn't match that to a command. Try again, or use `.menu`.",
                        mention_author=False,
                    )
                    return
                if command in NCM_CONFIRM:
                    ncm_pending[user_id] = {"command": command, "args": args}
                    shown = f".{command}" + (f" {args}" if args else "")
                    await message.reply(
                        f"Run `{shown}`? Say **yes** to confirm or anything else to cancel.",
                        mention_author=False,
                    )
                else:
                    await run_ncm_command(message, command, args)
            except Exception as e:
                print(f"NCM failed: {e}")
                await message.reply(f"❌ NCM failed: {e}", mention_author=False)
            return

    await bot.process_commands(message)

def start():
        print("Xephon bot starting")
        if not TOKEN:
            raise RuntimeError("DISCORD_TOKEN not found. Set it in your .env file.")
        if not DATABASE_URL:
            raise RuntimeError("DATABASE_URL not found. Set it in your .env file.")
        if db_pool is None:
            raise RuntimeError("Database pool is not ready. Check DATABASE_URL.")
        try:
            init_db()
            print("Database ready")
        except Exception as e:
            print(f"Database setup failed: {e}")
            raise

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
            return "Xephon bot is alive."

        def run_keep_alive():
            port = int(os.environ.get("PORT", 8080))
            keep_alive_app.run(host="0.0.0.0", port=port)

        threading.Thread(target=run_keep_alive, daemon=True).start()

        for attempt in range(1, 9):
            try:
                bot.run(TOKEN)
                break
            except Exception as e:
                text_err = str(e)
                rate_limited = (
                    isinstance(e, discord.HTTPException)
                    and (getattr(e, "status", None) == 429 or "1015" in text_err or "rate" in text_err.lower())
                ) or "Session is closed" in text_err or "1015" in text_err
                if not rate_limited:
                    raise
                wait = min(300, 30 * attempt)
                print(f"Discord login failed. Fresh restart in {wait}s. ({e.__class__.__name__})")
                time.sleep(wait)
                os.execv(sys.executable, [sys.executable, os.path.abspath(__file__)])
        else:
            raise RuntimeError("Discord kept rate-limiting this host. Wait and deploy once.")


# moved from economy/rob.py
SHOP_ITEM_CHOICES = [
    app_commands.Choice(name="Vx — 100,000 coins", value="vx"),
    app_commands.Choice(name="V9 — 200,000 coins", value="v9"),
    app_commands.Choice(name="Lucky Potion — 500,000 coins", value="lucky"),
    app_commands.Choice(name="Gun — 1,000 coins", value="gun"),
    app_commands.Choice(name="Fishing Rod — 1,000 coins", value="fishing_rod"),
    app_commands.Choice(name="Shovel — 1,000 coins", value="shovel"),
    app_commands.Choice(name="Guard — 50,000 coins", value="guard"),
]

async def apply_shop_purchase(send_func, user, guild, item_name: str, amount: int = 1):
    success, message, role_id = handle_buy(did(user.id), guild.id, item_name, amount)
    if success and role_id is not None and isinstance(user, discord.Member):
        role = guild.get_role(role_id)
        if role is not None:
            try:
                await user.add_roles(role, reason="Shop purchase")
                message += f"\n🏅 The **{role.name}** role has been added to you."
            except discord.Forbidden:
                message += "\n⚠️ Couldn't assign the role — check my role permissions."
    await send_func(message)



# moved from shop/shop.py
def handle_buy(user_id: int, guild_id: int, item_name: str, amount: int = 1):
    key = resolve_item_key(item_name)
    if key:
        return buy_global_item(user_id, key, amount) + (None,)
    try:
        item_id = int(item_name)
    except ValueError:
        return False, "❌ Unknown item. Use `.shop` to see names and IDs.", None
    return buy_shop_item(user_id, guild_id, item_id, amount)

def parse_buy_args(raw: str):
    """Split '.buy vx 3' into (item_name, amount)."""
    parts = raw.strip().split()
    if not parts:
        return "", 1
    if len(parts) >= 2 and parts[-1].isdigit():
        return " ".join(parts[:-1]), max(1, int(parts[-1]))
    return raw.strip(), 1



# moved from economy/donate.py
async def send_member_tags(channel, text: str):
    guild = channel.guild
    if not guild.chunked:
        await guild.chunk()
    members = [m for m in guild.members if not m.bot]
    if not members:
        await channel.send(text)
        return 0
    mentions = [m.mention for m in members]
    chunks = []
    current = text.strip()
    for mention in mentions:
        piece = f"{current} {mention}".strip()
        if len(piece) > 1900:
            chunks.append(current)
            current = mention
        else:
            current = piece
    if current:
        chunks.append(current)
    allow = discord.AllowedMentions(everyone=False, users=True, roles=False)
    for chunk in chunks:
        await channel.send(chunk, allowed_mentions=allow)
    return len(members)

NCM_ALLOWED = {
    "ping", "8ball", "avatar", "userinfo", "profile", "joke", "translate", "trt",
    "afk", "bal", "withdraw", "deposit", "cf", "roulette", "fish", "beg", "dig",
    "loan", "payloan", "daily", "work", "myjob", "jobs", "buypet", "feedpet",
    "collectpet", "pet", "marry", "marryaccept", "divorce", "partner",
    "achievements", "sell", "market", "lb", "rank", "ranklb", "mines",
    "blackjack", "rob", "shop", "buy", "use", "help", "inventory", "slot",
    "roll", "cds", "donate",
}
NCM_CONFIRM = {
    "donate", "withdraw", "deposit", "buy", "rob", "loan", "payloan", "sell",
    "use", "cf", "roulette", "mines", "blackjack", "slot", "roll", "marry",
    "divorce", "buypet", "feedpet",
}
ncm_enabled = {}
ncm_pending = {}

def ncm_is_on(user_id: str) -> bool:
    if user_id in ncm_enabled:
        return ncm_enabled[user_id]
    return get_meta(f"ncm:{user_id}") == "on"

def set_ncm(user_id: str, enabled: bool):
    ncm_enabled[user_id] = enabled
    set_meta(f"ncm:{user_id}", "on" if enabled else "off")

def normalize_amount_words(text: str) -> str:
    import re
    def repl(match):
        raw = match.group(1).replace(",", "")
        word = match.group(2).lower()
        value = float(raw)
        mult = {"k": 1_000, "m": 1_000_000, "b": 1_000_000_000, "t": 1_000_000_000_000,
                "thousand": 1_000, "million": 1_000_000, "billion": 1_000_000_000,
                "trillion": 1_000_000_000_000}.get(word, 1)
        return str(int(value * mult))
    return re.sub(r"(\d+(?:\.\d+)?)\s*(k|m|b|t|thousand|million|billion|trillion)\b", repl, text, flags=re.I)

NCM_ALIASES = {
    "balance": "bal", "money": "bal", "wallet": "bal",
    "coinflip": "cf", "coin": "cf", "inv": "inventory",
    "leaderboard": "lb", "top": "lb",
}

def match_command_in_sentence(text: str):
    lowered = text.lower()
    names = sorted(NCM_ALLOWED, key=len, reverse=True)
    found = None
    for name in names:
        if re.search(rf"\b{re.escape(name)}\b", lowered):
            found = name
            break
    if found is None:
        for alias, name in sorted(NCM_ALIASES.items(), key=lambda item: len(item[0]), reverse=True):
            if re.search(rf"\b{re.escape(alias)}\b", lowered):
                found = name
                break
    if found is None:
        return None, ""
    args = re.sub(rf"\b{re.escape(found)}\b", " ", text, count=1, flags=re.I)
    for alias, name in NCM_ALIASES.items():
        if name == found:
            args = re.sub(rf"\b{re.escape(alias)}\b", " ", args, count=1, flags=re.I)
    args = re.sub(r"\b(show|check|me|my|the|please|to)\b", " ", args, flags=re.I)
    args = normalize_amount_words(args)
    return found, " ".join(args.split())

async def parse_ncm_request(text: str) -> tuple:
    matched, args = match_command_in_sentence(text)
    if matched:
        return matched, args
    cleaned = normalize_amount_words(text)
    if not groq_client:
        return None, ""
    allowed = ", ".join(sorted(NCM_ALLOWED))
    system = (
        "Convert one Discord sentence into one existing bot command. "
        "Return only JSON like {\"command\":\"donate\",\"args\":\"7000000 <@123>\"}. "
        "If it is not a command request, return {\"command\":null}. "
        f"Allowed commands: {allowed}. "
        "args is only the arguments, never the command name or a dot. "
        "Keep Discord mentions exactly as written. "
        "7 million means 7000000. Do not invent commands."
    )
    try:
        response = await asyncio.to_thread(
            groq_client.chat.completions.create,
            model="openai/gpt-oss-120b",
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": cleaned},
            ],
            temperature=0,
        )
        raw = response.choices[0].message.content.strip()
        raw = raw.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        data = json.loads(raw)
        command = data.get("command")
        args = str(data.get("args") or "").strip()
        if command not in NCM_ALLOWED:
            return None, ""
        return command, args
    except Exception as e:
        print(f"NCM parse failed: {e}")
        return None, ""

async def run_ncm_command(message, command: str, args: str):
    cmd = bot.get_command(command)
    if cmd is None:
        await message.reply(f"❌ Unknown command `{command}`.", mention_author=False)
        return
    ctx = await bot.get_context(message)
    ctx.command = cmd
    ctx.invoked_with = command
    ctx.prefix = "."
    ctx.view = commands.view.StringView(args or "")
    ctx.view.skip_ws()
    await bot.invoke(ctx)



# moved from fun/joke.py
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
    if not is_creator and not test_mode_on(user_id):
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
            "`.xephongpt <message>`\n"
            "`.xephongpt on/off` — continuous chat\n"
            "`.xephongpt wild on` / `ai on` / `normal on` — change mode"
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
        discord_file = discord.File(file_bytes, filename="xephongpt_response.txt")
        await send_func("📄 Response was long — sending as a file:", file=discord_file)



# moved from owner/clearcache.py
def do_reset(user_id, clear_xp: bool = False):
    update_balance(user_id, wallet=DEFAULT_WALLET, bank=DEFAULT_BANK)
    set_user_effects(user_id, lucky_stacks=0, cd_boost_until=None)
    conn, cur = get_db()
    cur.execute("DELETE FROM inventory WHERE user_id = %s", (user_id,))
    cur.execute("DELETE FROM global_inventory WHERE user_id = %s", (user_id,))
    cur.execute("DELETE FROM pets WHERE user_id = %s", (user_id,))
    cur.execute("DELETE FROM jobs WHERE user_id = %s", (user_id,))
    cur.execute("DELETE FROM marriages WHERE user_id = %s OR partner_id = %s", (user_id, user_id))
    cur.execute("DELETE FROM achievements WHERE user_id = %s", (user_id,))
    if clear_xp:
        cur.execute("DELETE FROM levels WHERE user_id = %s", (user_id,))
    cur.execute("DELETE FROM persistent_cooldowns WHERE user_id = %s", (user_id,))
    cur.execute("DELETE FROM loans WHERE user_id = %s", (user_id,))
    cur.execute("DELETE FROM market_listings WHERE seller_id = %s", (user_id,))
    cur.execute("DELETE FROM afk WHERE user_id = %s", (user_id,))
    cur.execute(
        "UPDATE user_effects SET kiragpt_reply_count = 0, lucky_stacks = 0, cd_boost_until = NULL WHERE user_id = %s",
        (user_id,),
    )
    conn.commit()
    cur.close()
    release_db(conn)
    set_meta(f"test_mode:{user_id}", "off")
    set_meta(f"test_snapshot:{user_id}", "")
    return (
        "🔄 Reset complete.\n"
        f"Wallet: **${DEFAULT_WALLET:,}**\n"
        f"Bank: **${DEFAULT_BANK:,}**\n"
        "Items, pet, job, marriage, cooldowns, loans, and lucky stacks were cleared.\n"
        + ("XP and level were cleared." if clear_xp else "XP was kept. Use `.reset all` to clear XP too.")
    )

TEST_WALLET = 999_999_999_999_999

def has_tester_role(member) -> bool:
    if not isinstance(member, discord.Member):
        return False
    names = {role.name.lower().strip() for role in member.roles}
    return "tester" in names

def snapshot_test_state(user_id):
    bal = get_balance(user_id)
    conn, cur = get_db()
    cur.execute("SELECT item_key, quantity FROM global_inventory WHERE user_id = %s", (user_id,))
    global_items = cur.fetchall()
    cur.execute("SELECT item_id, quantity FROM inventory WHERE user_id = %s", (user_id,))
    custom_items = cur.fetchall()
    cur.execute("SELECT pet_type, pet_name, hunger FROM pets WHERE user_id = %s", (user_id,))
    pets = cur.fetchall()
    cur.close()
    release_db(conn)
    effects = get_user_effects(user_id)
    return {
        "wallet": bal["wallet"],
        "bank": bal["bank"],
        "global_items": [[k, q] for k, q in global_items],
        "custom_items": [[i, q] for i, q in custom_items],
        "pets": [[ptype, pname, hunger] for ptype, pname, hunger in pets],
        "lucky_stacks": effects["lucky_stacks"],
        "cd_boost_until": effects["cd_boost_until"] if isinstance(effects["cd_boost_until"], (int, float)) else (
            effects["cd_boost_until"].isoformat() if effects["cd_boost_until"] else None
        ),
    }

def restore_test_state(user_id, snap):
    update_balance(user_id, wallet=snap["wallet"], bank=snap["bank"])
    conn, cur = get_db()
    cur.execute("DELETE FROM global_inventory WHERE user_id = %s", (user_id,))
    for key, qty in snap.get("global_items", []):
        cur.execute(
            "INSERT INTO global_inventory (user_id, item_key, quantity) VALUES (%s, %s, %s)",
            (user_id, key, qty),
        )
    cur.execute("DELETE FROM inventory WHERE user_id = %s", (user_id,))
    for item_id, qty in snap.get("custom_items", []):
        cur.execute(
            "INSERT INTO inventory (user_id, item_id, quantity) VALUES (%s, %s, %s)",
            (user_id, item_id, qty),
        )
    cur.execute("DELETE FROM pets WHERE user_id = %s", (user_id,))
    for pet_type, pet_name, hunger in snap.get("pets", []):
        cur.execute(
            "INSERT INTO pets (user_id, pet_type, pet_name, hunger) VALUES (%s, %s, %s, %s)",
            (user_id, pet_type, pet_name, hunger),
        )
    conn.commit()
    cur.close()
    release_db(conn)
    until = snap.get("cd_boost_until")
    set_user_effects(
        user_id,
        lucky_stacks=snap.get("lucky_stacks", 0),
        cd_boost_until=until,
    )

def do_test(user_id, turn_on: bool):
    if turn_on:
        if test_mode_on(user_id):
            return "⚠️ Test mode is already **on**."
        snap = snapshot_test_state(user_id)
        set_meta(f"test_snapshot:{user_id}", json.dumps(snap))
        set_meta(f"test_mode:{user_id}", "on")
        update_balance(user_id, wallet=TEST_WALLET)
        return (
            "🧪 Test mode is **on**.\n"
            "You now have infinite test money and no item limits.\n"
            "It cannot be donated. When you turn it off, extra money, bet winnings, "
            "and items bought with test money disappear."
        )
    if not test_mode_on(user_id):
        return "❌ Test mode is already **off**."
    raw = get_meta(f"test_snapshot:{user_id}")
    if not raw:
        set_meta(f"test_mode:{user_id}", "off")
        return "❌ Test snapshot was missing. Test mode is now off."
    restore_test_state(user_id, json.loads(raw))
    set_meta(f"test_mode:{user_id}", "off")
    set_meta(f"test_snapshot:{user_id}", "")
    return "🧪 Test mode is **off**. Extra money and items bought with test money were removed."



# moved from utility/menu.py
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



# moved from gambling/cf.py
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

    adjust_balance(user_id, wallet_delta=-amount)
    sent = await send_func(build_roulette_spinning_text(f"${amount:,}", color_choice))

    await asyncio.sleep(5)

    base = (1 / 37) if color_choice == "green" else (18 / 37)
    won = random.random() < luck_chance(base, user_id)
    number, color, color_display = do_roulette_spin()
    if won and color != color_choice:
        for _ in range(50):
            number, color, color_display = do_roulette_spin()
            if color == color_choice:
                break
    if not won and color == color_choice:
        for _ in range(50):
            number, color, color_display = do_roulette_spin()
            if color != color_choice:
                break
    if won:
        payout = amount * ROULETTE_MULTIPLIER[color_choice]
        new_bal = get_balance(user_id)
        adjust_balance(user_id, wallet_delta=payout)
    else:
        payout = 0
        house_take(amount)
    final_bal = get_balance(user_id)

    result_text = build_roulette_result_text(number, color_display, won, payout, final_bal["wallet"])
    await edit_func(sent, result_text)



# moved from info/versions.py
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

    adjust_balance(user_id, wallet_delta=-amount)
    won = random.random() < luck_chance(0.5, user_id)
    result = side if won else ("tails" if side == "heads" else "heads")
    result_display = "HEADS 🦅" if result == "heads" else "TAILS 🪙"

    if won:
        payout = amount * 2
        new_bal = get_balance(user_id)
        adjust_balance(user_id, wallet_delta=payout)
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
        house_take(amount)
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



# moved from economy/lb.py
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



# moved from levels/levelroles.py
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


