from core import *

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

