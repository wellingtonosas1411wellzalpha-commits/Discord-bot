from core import *
import re

def abw_key(guild_id) -> str:
    return f"abw:{guild_id}"

def load_abw(guild_id) -> dict:
    raw = get_meta(abw_key(guild_id))
    if not raw:
        return {"on": False, "mode": "delete", "words": [], "warns": {}}
    try:
        data = json.loads(raw)
    except Exception:
        data = {}
    data.setdefault("on", False)
    data.setdefault("mode", "delete")
    data.setdefault("words", [])
    data.setdefault("warns", {})
    return data

def save_abw(guild_id, data):
    set_meta(abw_key(guild_id), json.dumps(data))

def find_bad_word(content: str, words: list) -> str | None:
    lowered = content.lower()
    for word in words:
        if re.search(rf"\b{re.escape(word.lower())}\b", lowered):
            return word
    return None

async def run_antibadword(send, guild, user, action: str, extra: str = ""):
    if not is_kira_creator(user):
        await send("❌ Admins only.")
        return
    data = load_abw(guild.id)
    action = (action or "").lower().strip()
    extra = (extra or "").strip()

    if action in ("on", "off"):
        data["on"] = action == "on"
        save_abw(guild.id, data)
        await send(f"Antibadword is **{action}**.")
        return
    if action == "mode":
        mode = extra.lower()
        if mode not in ("delete", "warn", "kick"):
            await send("❌ Mode must be `delete`, `warn`, or `kick`.")
            return
        data["mode"] = mode
        save_abw(guild.id, data)
        await send(f"Antibadword mode is **{mode}**.")
        return
    if action == "add":
        word = extra.lower()
        if not word:
            await send("❌ Add a word. `.antibadword add word`")
            return
        if word not in data["words"]:
            data["words"].append(word)
        save_abw(guild.id, data)
        await send(f"Added `{word}`.")
        return
    if action == "remove":
        word = extra.lower()
        data["words"] = [w for w in data["words"] if w != word]
        save_abw(guild.id, data)
        await send(f"Removed `{word}`.")
        return
    if action == "list":
        words = ", ".join(data["words"]) or "none"
        state = "on" if data["on"] else "off"
        await send(f"State: **{state}**\nMode: **{data['mode']}**\nWords: {words}")
        return
    await send(
        "Usage:\n"
        "`.antibadword on/off`\n"
        "`.antibadword add word`\n"
        "`.antibadword remove word`\n"
        "`.antibadword mode delete/warn/kick`\n"
        "`.antibadword list`"
    )

@bot.tree.command(name="antibadword", description="[Admin] Filter bad words")
@app_commands.describe(
    action="on, off, add, remove, mode, or list",
    extra="Word, or delete/warn/kick when using mode",
)
async def antibadword_slash(interaction: discord.Interaction, action: str, extra: str = ""):
    if interaction.guild is None:
        await interaction.response.send_message("❌ Use this in a server.", ephemeral=True)
        return
    await run_antibadword(interaction.response.send_message, interaction.guild, interaction.user, action, extra)

@bot.command(name="antibadword")
async def antibadword_prefix(ctx: commands.Context, action: str = "", *, extra: str = ""):
    if ctx.guild is None:
        await ctx.reply("❌ Use this in a server.", mention_author=False)
        return
    await run_antibadword(lambda text: ctx.reply(text, mention_author=False), ctx.guild, ctx.author, action, extra)

@bot.listen("on_message")
async def antibadword_listener(message: discord.Message):
    if message.author.bot or message.guild is None:
        return
    if is_kira_creator(message.author):
        return
    data = load_abw(message.guild.id)
    if not data["on"] or not data["words"]:
        return
    hit = find_bad_word(message.content or "", data["words"])
    if not hit:
        return
    try:
        await message.delete()
    except discord.HTTPException:
        return
    mode = data.get("mode", "delete")
    if mode == "delete":
        return
    uid = did(message.author.id)
    if mode == "warn":
        count = int(data["warns"].get(uid, 0)) + 1
        data["warns"][uid] = count
        save_abw(message.guild.id, data)
        if count >= 5:
            data["warns"][uid] = 0
            save_abw(message.guild.id, data)
            try:
                await message.author.kick(reason="5 antibadword warnings")
                await message.channel.send(f"{message.author.mention} was kicked after 5 warnings.")
            except discord.HTTPException:
                await message.channel.send(f"{message.author.mention} hit 5 warnings, but I could not kick them.")
            return
        await message.channel.send(f"{message.author.mention} warning **{count}/5**.")
        return
    if mode == "kick":
        try:
            await message.author.kick(reason="Antibadword kick mode")
            await message.channel.send(f"{message.author.mention} was kicked.")
        except discord.HTTPException:
            await message.channel.send(f"{message.author.mention} used a blocked word, but I could not kick them.")
