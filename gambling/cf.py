from core import *

@bot.tree.command(name="cf", description="Bet on a coinflip")
@app_commands.describe(side="heads or tails", amount="Amount to bet")
async def cf(interaction: discord.Interaction, side: str, amount: str):
    await interaction.response.send_message(await run_coinflip(did(interaction.user.id), side, amount))


@bot.command(name="cf", aliases=["coinflip"])
async def cf_prefix(ctx: commands.Context, side: str, amount: str):
    await ctx.reply(await run_coinflip(did(ctx.author.id), side, amount))
