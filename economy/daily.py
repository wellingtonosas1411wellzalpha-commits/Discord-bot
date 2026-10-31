from core import *

@bot.tree.command(name="daily", description="Claim your daily reward")
async def daily(interaction: discord.Interaction):
    await interaction.response.send_message(do_daily(did(interaction.user.id)))


@bot.command(name="daily")
async def daily_prefix(ctx: commands.Context):
    await ctx.reply(do_daily(did(ctx.author.id)))

