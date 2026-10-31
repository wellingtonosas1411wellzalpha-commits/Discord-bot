from core import *

@bot.tree.command(name="payloan", description="Pay back your loan")
@app_commands.describe(amount="Amount to pay, or all")
async def payloan_cmd(interaction: discord.Interaction, amount: str = "all"):
    await interaction.response.send_message(pay_loan(did(interaction.user.id), amount))


@bot.command(name="payloan")
async def payloan_prefix(ctx: commands.Context, *, amount: str = "all"):
    await ctx.reply(pay_loan(did(ctx.author.id), amount))

