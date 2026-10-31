from core import *

@bot.tree.command(name="deposit", description="Deposit money from your wallet to your bank")
@app_commands.describe(amount="Amount to deposit, or 'all'")
async def deposit(interaction: discord.Interaction, amount: str):
    await interaction.response.send_message(do_deposit(did(interaction.user.id), amount))


@bot.command(name="deposit", aliases=["dep"])
async def deposit_prefix(ctx: commands.Context, amount: str):
    await ctx.reply(do_deposit(did(ctx.author.id), amount))

