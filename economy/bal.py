from core import *

@bot.tree.command(name="bal", description="Check your account balance")
async def bal(interaction: discord.Interaction):
    await interaction.response.send_message(build_balance_text(did(interaction.user.id)))


@bot.command(name="bal")
async def bal_prefix(ctx: commands.Context):
    await ctx.reply(build_balance_text(did(ctx.author.id)))

