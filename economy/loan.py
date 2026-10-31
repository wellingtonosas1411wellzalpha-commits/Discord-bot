from core import *

@bot.tree.command(name="loan", description="Borrow coins from the bot bank")
@app_commands.describe(amount="Amount to borrow. Leave empty to see your loan.")
async def loan_cmd(interaction: discord.Interaction, amount: str = None):
    await interaction.response.send_message(take_loan(did(interaction.user.id), amount))


@bot.command(name="loan")
async def loan_prefix(ctx: commands.Context, *, amount: str = None):
    await ctx.reply(take_loan(did(ctx.author.id), amount))

