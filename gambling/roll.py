from core import *

@bot.tree.command(name="roll", description="Roll a dice and bet on 4-6 to win")
@app_commands.describe(amount="Amount to bet, or 'all'")
async def roll(interaction: discord.Interaction, amount: str):
    await interaction.response.send_message(do_dice(did(interaction.user.id), amount))


@bot.command(name="roll")
async def roll_prefix(ctx: commands.Context, amount: str):
    await ctx.reply(do_dice(did(ctx.author.id), amount))

