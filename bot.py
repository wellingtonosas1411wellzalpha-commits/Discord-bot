import os
import random
import psycopg2

import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix=".", intents=intents)

afk_users = {}  # user_id -> reason

DEFAULT_WALLET = 50000
DEFAULT_BANK = 50000
DEFAULT_LIMIT = 50000

DATABASE_URL = os.getenv("DATABASE_URL")


def get_db():
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS balances (
            user_id BIGINT PRIMARY KEY,
            wallet BIGINT NOT NULL,
            bank BIGINT NOT NULL,
            limit_amt BIGINT NOT NULL
        )
    """)
    conn.commit()
    return conn, cur


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
    bal = get_balance(user_id)
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


def do_withdraw(user_id: int, amount: int):
    bal = get_balance(user_id)
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


def do_deposit(user_id: int, amount: int):
    bal = get_balance(user_id)
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
        "┃ • roll [dice] — roll dice, e.g. 2d6\n"
        "┃ • flip — flip a coin\n"
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
        "┃ • withdraw/wd [amount] — bank ➜ wallet\n"
        "┃ • deposit/dep [amount] — wallet ➜ bank\n"
        "┃\n"
        "┃ 𝖀𝖙𝖎𝖑𝖎𝖙𝖞\n"
        "┃ • afk [reason] — set yourself as afk\n"
        "┃\n"
        "┃ ✦ use / or . before any command\n"
        "╰━━━━━━━━━━━━━━━━━━━━━━⬣"
    )


@bot.event
async def on_ready():
    print(f"Logged in as {bot.user} (ID: {bot.user.id})")
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} slash command(s)")
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


def roll_dice(dice: str):
    count, sides = map(int, dice.lower().split("d"))
    if count < 1 or sides < 1 or count > 100:
        raise ValueError
    rolls = [random.randint(1, sides) for _ in range(count)]
    return rolls, sum(rolls)


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
    await ctx.send(f"🏓 Pong! {latency_ms}ms")


@bot.tree.command(name="roll", description="Roll a dice, e.g. 2d6")
@app_commands.describe(dice="Format: NdM (e.g. 2d6 rolls two 6-sided dice)")
async def roll(interaction: discord.Interaction, dice: str = "1d6"):
    try:
        rolls, total = roll_dice(dice)
    except ValueError:
        await interaction.response.send_message(
            "Invalid format. Use NdM, like `2d6`.", ephemeral=True
        )
        return
    rolls_str = ", ".join(map(str, rolls))
    await interaction.response.send_message(
        f"🎲 Rolled {dice}: [{rolls_str}] = **{total}**"
    )


@bot.command(name="roll")
async def roll_prefix(ctx: commands.Context, dice: str = "1d6"):
    try:
        rolls, total = roll_dice(dice)
    except ValueError:
        await ctx.send("Invalid format. Use NdM, like `2d6`.")
        return
    rolls_str = ", ".join(map(str, rolls))
    await ctx.send(f"🎲 Rolled {dice}: [{rolls_str}] = **{total}**")


@bot.tree.command(name="flip", description="Flip a coin")
async def flip(interaction: discord.Interaction):
    result = random.choice(["Heads", "Tails"])
    await interaction.response.send_message(f"🪙 {result}!")


@bot.command(name="flip")
async def flip_prefix(ctx: commands.Context):
    result = random.choice(["Heads", "Tails"])
    await ctx.send(f"🪙 {result}!")


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
    await ctx.send(f"🎱 **Q:** {question}\n**A:** {answer}")


@bot.tree.command(name="avatar", description="Get a user's avatar")
@app_commands.describe(user="The user to look up (defaults to you)")
async def avatar(interaction: discord.Interaction, user: discord.User = None):
    user = user or interaction.user
    await interaction.response.send_message(embed=build_avatar_embed(user))


@bot.command(name="avatar")
async def avatar_prefix(ctx: commands.Context, user: discord.User = None):
    user = user or ctx.author
    await ctx.send(embed=build_avatar_embed(user))


@bot.tree.command(name="userinfo", description="Get info about a server member")
@app_commands.describe(member="The member to look up (defaults to you)")
async def userinfo(interaction: discord.Interaction, member: discord.Member = None):
    member = member or interaction.user
    await interaction.response.send_message(embed=build_userinfo_embed(member))


@bot.command(name="userinfo")
async def userinfo_prefix(ctx: commands.Context, member: discord.Member = None):
    member = member or ctx.author
    await ctx.send(embed=build_userinfo_embed(member))


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
    message = await ctx.send(embed=embed)
    await message.add_reaction("👍")
    await message.add_reaction("👎")


@bot.tree.command(name="joke", description="Get a random joke")
async def joke(interaction: discord.Interaction):
    await interaction.response.send_message(f"😄 {get_joke()}")


@bot.command(name="joke")
async def joke_prefix(ctx: commands.Context):
    await ctx.send(f"😄 {get_joke()}")


@bot.tree.command(name="afk", description="Set yourself as AFK")
@app_commands.describe(reason="Why you're AFK (optional)")
async def afk(interaction: discord.Interaction, reason: str = "busy"):
    afk_users[interaction.user.id] = reason
    await interaction.response.send_message(
        f"You are now afk, reason: {reason}"
    )


@bot.command(name="afk")
async def afk_prefix(ctx: commands.Context, *, reason: str = "busy"):
    afk_users[ctx.author.id] = reason
    await ctx.send(f"You are now afk, reason: {reason}")


@bot.tree.command(name="bal", description="Check your account balance")
async def bal(interaction: discord.Interaction):
    await interaction.response.send_message(build_balance_text(interaction.user.id))


@bot.command(name="bal")
async def bal_prefix(ctx: commands.Context):
    await ctx.send(build_balance_text(ctx.author.id))


@bot.tree.command(name="withdraw", description="Withdraw money from your bank to your wallet")
@app_commands.describe(amount="Amount to withdraw")
async def withdraw(interaction: discord.Interaction, amount: int):
    await interaction.response.send_message(do_withdraw(interaction.user.id, amount))


@bot.tree.command(name="wd", description="Withdraw money from your bank to your wallet")
@app_commands.describe(amount="Amount to withdraw")
async def wd(interaction: discord.Interaction, amount: int):
    await interaction.response.send_message(do_withdraw(interaction.user.id, amount))


@bot.command(name="withdraw", aliases=["wd"])
async def withdraw_prefix(ctx: commands.Context, amount: int):
    await ctx.send(do_withdraw(ctx.author.id, amount))


@bot.tree.command(name="deposit", description="Deposit money from your wallet to your bank")
@app_commands.describe(amount="Amount to deposit")
async def deposit(interaction: discord.Interaction, amount: int):
    await interaction.response.send_message(do_deposit(interaction.user.id, amount))


@bot.tree.command(name="dep", description="Deposit money from your wallet to your bank")
@app_commands.describe(amount="Amount to deposit")
async def dep(interaction: discord.Interaction, amount: int):
    await interaction.response.send_message(do_deposit(interaction.user.id, amount))


@bot.command(name="deposit", aliases=["dep"])
async def deposit_prefix(ctx: commands.Context, amount: int):
    await ctx.send(do_deposit(ctx.author.id, amount))


@bot.tree.command(name="menu", description="Show all bot commands")
async def menu(interaction: discord.Interaction):
    await interaction.response.send_message(build_menu_text())


@bot.command(name="menu")
async def menu_prefix(ctx: commands.Context):
    await ctx.send(build_menu_text())


@bot.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return

    if message.author.id in afk_users:
        del afk_users[message.author.id]
        await message.channel.send(f"Welcome back {message.author.mention}, I removed your afk.")

    for user in message.mentions:
        if user.id in afk_users:
            await message.channel.send(
                f"{user.display_name} is afk: {afk_users[user.id]}"
            )

    await bot.process_commands(message)


if __name__ == "__main__":
    if not TOKEN:
        raise RuntimeError("DISCORD_TOKEN not found. Set it in your .env file.")
    bot.run(TOKEN)
