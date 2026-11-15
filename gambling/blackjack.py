from core import *

@bot.command(name="blackjack", aliases=["bj"])
async def blackjack_prefix(ctx: commands.Context, action: str = None):
    user_id = did(ctx.author.id)
    if action is None:
        await ctx.reply("Usage: `.blackjack <bet>` to start, `.blackjack hit`, or `.blackjack stand`.")
        return
    if action.lower() == "hit":
        await ctx.reply(hit_blackjack(user_id))
        return
    if action.lower() == "stand":
        await ctx.reply(stand_blackjack(user_id))
        return
    await ctx.reply(start_blackjack(user_id, action))

@bot.tree.command(name="blackjack", description="Play blackjack")
@app_commands.describe(action="start, hit, or stand", bet="Bet when starting")
@app_commands.choices(action=[
    app_commands.Choice(name="start", value="start"),
    app_commands.Choice(name="hit", value="hit"),
    app_commands.Choice(name="stand", value="stand"),
])
async def blackjack_slash(interaction: discord.Interaction, action: app_commands.Choice[str], bet: str = ""):
    user_id = did(interaction.user.id)
    if action.value == "hit":
        await interaction.response.send_message(hit_blackjack(user_id))
        return
    if action.value == "stand":
        await interaction.response.send_message(stand_blackjack(user_id))
        return
    await interaction.response.send_message(start_blackjack(user_id, bet or "0"))
