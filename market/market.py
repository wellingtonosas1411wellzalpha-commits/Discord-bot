from core import *

@bot.tree.command(name="market", description="Browse the player market")
async def market(interaction: discord.Interaction):
    await interaction.response.send_message(build_market_text())


@bot.command(name="market")
async def market_prefix(ctx: commands.Context):
    await ctx.reply(build_market_text())

