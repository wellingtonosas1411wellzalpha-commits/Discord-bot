from core import *

@bot.command(name="mines")
async def mines_prefix(ctx: commands.Context, *args):
    user_id = did(ctx.author.id)
    if len(args) == 0:
        await ctx.reply(MINES_HELP_TEXT)
        return
    if args[0].lower() == "cashout":
        await ctx.reply(cashout_mines(user_id))
        return
    if user_id in active_mines_games:
        if len(args) != 1:
            await ctx.reply("Type `.mines <1-25>` to dig or `.mines cashout` to cash out.")
            return
        await ctx.reply(dig_mines(user_id, args[0]))
        return
    bet_str = args[0]
    mines_str = args[1] if len(args) > 1 else None
    await ctx.reply(start_mines(user_id, bet_str, mines_str))

@bot.tree.command(name="mines", description="Play mines")
@app_commands.describe(
    action="start, dig, or cashout",
    bet="Bet for start, or tile number for dig",
    mines="Number of mines when starting",
)
@app_commands.choices(action=[
    app_commands.Choice(name="start", value="start"),
    app_commands.Choice(name="dig", value="dig"),
    app_commands.Choice(name="cashout", value="cashout"),
])
async def mines_slash(interaction: discord.Interaction, action: app_commands.Choice[str], bet: str = "", mines: int = 3):
    user_id = did(interaction.user.id)
    if action.value == "cashout":
        await interaction.response.send_message(cashout_mines(user_id))
        return
    if action.value == "dig":
        await interaction.response.send_message(dig_mines(user_id, bet or "0"))
        return
    await interaction.response.send_message(start_mines(user_id, bet or "0", str(mines)))
