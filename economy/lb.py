from core import *

@bot.tree.command(name="lb", description="Show the richest users")
async def lb(interaction: discord.Interaction):
    await interaction.response.send_message(build_leaderboard_text())


@bot.command(name="lb", aliases=["top", "leaderboard"])
async def lb_prefix(ctx: commands.Context):
    await ctx.reply(build_leaderboard_text())
