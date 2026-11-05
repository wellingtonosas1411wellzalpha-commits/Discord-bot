from core import *

REACT_EMOJIS = [
    "👍", "❤️", "😂", "🔥", "😮", "😢", "🎉", "👀", "💯", "✨",
    "😎", "🙌", "💀", "😭", "🙏", "⭐", "💥", "🧠", "👑", "✅",
]

def message_id_from(raw: str):
    digits = [part for part in raw.replace("/", " ").split() if part.isdigit()]
    return int(digits[-1]) if digits else None

async def add_reactions(message, count: int) -> int:
    count = max(1, min(count, len(REACT_EMOJIS)))
    added = 0
    for emoji in REACT_EMOJIS[:count]:
        try:
            await message.add_reaction(emoji)
            added += 1
        except discord.HTTPException:
            break
    return added

@bot.tree.command(name="react", description="[Admin] React to a message link or ID")
@app_commands.describe(message_link="Message link or message ID", count="How many reactions, max 20")
async def react_slash(interaction: discord.Interaction, message_link: str, count: app_commands.Range[int, 1, 20] = 1):
    if not is_kira_creator(interaction.user):
        await interaction.response.send_message("❌ Admins only.", ephemeral=True)
        return
    message_id = message_id_from(message_link)
    if message_id is None:
        await interaction.response.send_message("❌ Give a message link or message ID.", ephemeral=True)
        return
    try:
        target = await interaction.channel.fetch_message(message_id)
    except discord.NotFound:
        await interaction.response.send_message("❌ I couldn't find that message in this channel.", ephemeral=True)
        return
    added = await add_reactions(target, count)
    await interaction.response.send_message(f"✅ Added {added} reaction(s).", ephemeral=True)

@bot.command(name="react")
async def react_prefix(ctx: commands.Context, count: int = 1):
    if not is_kira_creator(ctx.author):
        await ctx.reply("❌ Admins only.", mention_author=False)
        return
    if ctx.message.reference is None or ctx.message.reference.message_id is None:
        await ctx.reply("❌ Reply to the message you want reactions on.", mention_author=False)
        return
    try:
        target = await ctx.channel.fetch_message(ctx.message.reference.message_id)
    except discord.NotFound:
        await ctx.reply("❌ I couldn't find that message.", mention_author=False)
        return
    added = await add_reactions(target, count)
    try:
        await ctx.message.delete()
    except discord.HTTPException:
        if added == 0:
            await ctx.reply("❌ I couldn't react.", mention_author=False)
