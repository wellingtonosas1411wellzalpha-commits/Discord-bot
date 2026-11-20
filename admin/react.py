from core import *

REACT_EMOJIS = [
    "👍", "❤️", "😂", "🔥", "😮", "😢", "🎉", "👀", "💯", "✨",
    "😎", "🙌", "💀", "😭", "🙏", "⭐", "💥", "🧠", "👑", "✅",
    "😡", "🤣", "😍", "🤔", "😴", "🤝", "👏", "💪", "🚀", "🌟",
    "❤️‍🔥", "💙", "💚", "💛", "💜", "🖤", "🤍", "💖", "💝", "😘",
    "😅", "😆", "😉", "😊", "😁", "🙂", "😇", "🥳", "🤯", "😱",
    "😤", "🤬", "😳", "🥺", "😏", "😒", "🙄", "😬", "🤐", "🤢",
    "🤡", "👻", "🤖", "👾", "🎮", "⚽", "🏀", "🎯", "🎲", "🧩",
    "💎", "🏆", "🥇", "⚡", "🌈", "☀️", "🌙", "⭐", "🌠", "☄️",
    "🍀", "🌸", "🌹", "🍕", "🍔", "🍟", "🍩", "🍪", "🎂", "☕",
    "📱", "💻", "⌚", "📷", "🎬", "🎵", "🎸", "🎹", "🥁", "🎤",
]

def message_id_from(raw: str):
    digits = [part for part in raw.replace("/", " ").split() if part.isdigit()]
    return int(digits[-1]) if digits else None

def pick_emojis(raw_args, count=None):
    custom = [part for part in raw_args if not part.isdigit()]
    if custom:
        return custom[:20]
    amount = count or 1
    amount = max(1, min(amount, 20, len(REACT_EMOJIS)))
    return REACT_EMOJIS[:amount]

async def add_reactions(message, emojis) -> int:
    added = 0
    for emoji in emojis[:20]:
        try:
            await message.add_reaction(emoji)
            added += 1
        except discord.HTTPException:
            break
    return added

def fake_reaction_text(count: int) -> str:
    count = max(1, min(count, 500))
    parts = []
    for i in range(count):
        parts.append(REACT_EMOJIS[i % len(REACT_EMOJIS)])
    return " ".join(parts)

async def send_fake_reactions(channel, count: int):
    text_out = fake_reaction_text(count)
    chunk = 1800
    for i in range(0, len(text_out), chunk):
        await channel.send(text_out[i:i+chunk])

@bot.tree.command(name="react", description="[Admin] React to a message link or ID")
@app_commands.describe(message_link="Message link or message ID", count="How many reactions, max 20")
async def react_slash(interaction: discord.Interaction, message_link: str, count: app_commands.Range[int, 1, 20] = 1):
    await interaction.response.defer(ephemeral=True)
    if not is_kira_creator(interaction.user):
        await interaction.followup.send("Admins only.", ephemeral=True)
        return
    message_id = message_id_from(message_link)
    if message_id is None:
        await interaction.followup.send("Give a message link or message ID.", ephemeral=True)
        return
    try:
        target = await interaction.channel.fetch_message(message_id)
    except discord.NotFound:
        await interaction.followup.send("I couldn't find that message in this channel.", ephemeral=True)
        return
    added = await add_reactions(target, pick_emojis([], count))
    if count > 20:
        await send_fake_reactions(interaction.channel, count)
    await interaction.followup.send(f"done ({count if count > 20 else added})", ephemeral=True)

@bot.command(name="react")
async def react_prefix(ctx: commands.Context, *args):
    if not is_kira_creator(ctx.author):
        await ctx.reply("Admins only.", mention_author=False)
        return
    if ctx.message.reference is None or ctx.message.reference.message_id is None:
        await ctx.reply("Reply to the message you want reactions on.", mention_author=False)
        return
    try:
        target = await ctx.channel.fetch_message(ctx.message.reference.message_id)
    except discord.NotFound:
        await ctx.reply("I couldn't find that message.", mention_author=False)
        return
    count = next((int(part) for part in args if part.isdigit()), 1)
    added = await add_reactions(target, pick_emojis(args, count))
    if count > 20 and not any(not part.isdigit() for part in args):
        await send_fake_reactions(ctx.channel, count)
    try:
        await ctx.message.delete()
    except discord.HTTPException:
        await ctx.reply(f"done ({count if count > 20 else added})", mention_author=False)
