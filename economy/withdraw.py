from core import *

@bot.tree.command(name="withdraw", description="Withdraw money from your bank to your wallet")
@app_commands.describe(amount="Amount to withdraw, or 'all'")
async def withdraw(interaction: discord.Interaction, amount: str):
    await interaction.response.send_message(do_withdraw(did(interaction.user.id), amount))


@bot.command(name="withdraw", aliases=["wd"])
async def withdraw_prefix(ctx: commands.Context, amount: str):
    await ctx.reply(do_withdraw(did(ctx.author.id), amount))

