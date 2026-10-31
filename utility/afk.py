from core import *

@bot.tree.command(name="afk", description="Set yourself as AFK")
@app_commands.describe(reason="Why you're AFK (optional)")
async def afk(interaction: discord.Interaction, reason: str = "busy"):
    set_afk(did(interaction.user.id), reason)
    await interaction.response.send_message(
        f"You are now afk, reason: {reason}"
    )


@bot.command(name="afk")
async def afk_prefix(ctx: commands.Context, *, reason: str = "busy"):
    set_afk(did(ctx.author.id), reason)
    await ctx.reply(f"You are now afk, reason: {reason}")

