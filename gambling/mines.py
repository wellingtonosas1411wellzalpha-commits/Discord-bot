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
            await ctx.reply("❌ Type `.mines <1-25>` to dig or `.mines cashout` to cash out.")
            return
        await ctx.reply(dig_mines(user_id, args[0]))
        return
    bet_str = args[0]
    mines_str = args[1] if len(args) > 1 else None
    await ctx.reply(start_mines(user_id, bet_str, mines_str))


@bot.tree.command(name="mines", description="Start a mines game")
@app_commands.describe(bet="Amount to bet, or 'all'", mines="Number of mines (1-24, default 3)")
async def mines_start(interaction: discord.Interaction, bet: str, mines: int = 3):
    await interaction.response.send_message(start_mines(did(interaction.user.id), bet, str(mines)))

