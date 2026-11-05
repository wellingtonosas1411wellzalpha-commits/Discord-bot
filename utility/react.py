from core import *

REACT_EMOJIS = [
    "👍", "❤️", "😂", "🔥", "😮", "😢", "🎉", "👀", "💯", "✨",
    "😎", "🙌", "💀", "😭", "🙏", "⭐", "💥", "🧠", "👑", "✅",
]

@bot.tree.command(name="react", description="React to the replied message")
@app_commands.describe(count="How many reactions, max 20")
async def react_slash(interaction: discord.Interaction, count: app_commands.Range[int, 1, 20]):
    await interaction.response.send_message("❌ Reply to a message with `.react 15`.", ephemeral=True)

@bot.command(name="react")
async def react_prefix(ctx: commands.Context, count: int = 1):
    if ctx.message.reference is None or ctx.message.reference.message_id is None:
        await ctx.reply("❌ Reply to the message you want reactions on.", mention_author=False)
        return
    count = max(1, min(count, len(REACT_EMOJIS)))
    try:
        target = await ctx.channel.fetch_message(ctx.message.reference.message_id)
    except discord.NotFound:
        await ctx.reply("❌ I couldn't find that message.", mention_author=False)
        return
    added = 0
    for emoji in REACT_EMOJIS[:count]:
        try:
            await target.add_reaction(emoji)
            added += 1
        except discord.HTTPException:
            break
    try:
        await ctx.message.delete()
    except discord.HTTPException:
        if added == 0:
            await ctx.reply("❌ I couldn't react. Check my Add Reactions permission.", mention_author=False)
