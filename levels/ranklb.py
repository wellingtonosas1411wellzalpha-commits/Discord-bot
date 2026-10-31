from core import *

@bot.tree.command(name="ranklb", description="See the level leaderboard")
async def ranklb(interaction: discord.Interaction):
    await interaction.response.send_message(build_ranklb_text())


@bot.command(name="ranklb", aliases=["levellb", "levels"])
async def ranklb_prefix(ctx: commands.Context):
    await ctx.reply(build_ranklb_text())

# ---------- Mines ----------

