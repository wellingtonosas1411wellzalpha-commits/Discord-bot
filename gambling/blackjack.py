from core import *

@bot.command(name="blackjack", aliases=["bj"])
async def blackjack_prefix(ctx: commands.Context, action: str = None):
    user_id = did(ctx.author.id)
    if action is None:
        await ctx.reply("❌ Usage: `.blackjack <bet>` to start, `.blackjack hit`, or `.blackjack stand`.")
        return
    if action.lower() == "hit":
        await ctx.reply(hit_blackjack(user_id))
        return
    if action.lower() == "stand":
        await ctx.reply(stand_blackjack(user_id))
        return
    await ctx.reply(start_blackjack(user_id, action))


@bot.tree.command(name="blackjack", description="Start a blackjack game")
@app_commands.describe(bet="Amount to bet, or 'all'")
async def blackjack_start(interaction: discord.Interaction, bet: str):
    await interaction.response.send_message(start_blackjack(did(interaction.user.id), bet))

