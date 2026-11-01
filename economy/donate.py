from core import *

@bot.tree.command(name="donate", description="Donate money to another user")
@app_commands.describe(amount="Amount to donate, or 'all'", user="The user to donate to")
async def donate(interaction: discord.Interaction, amount: str, user: discord.User):
    if user.bot:
        await interaction.response.send_message("❌ You can't donate to a bot.")
        return
    donated, error = do_donate(did(interaction.user.id), did(user.id), amount)
    if error:
        await interaction.response.send_message(error)
        return
    await interaction.response.send_message(f"✅ Successfully donated ${donated:,} to {user.mention}")


@bot.command(name="donate")
async def donate_prefix(ctx: commands.Context, amount: str, user: discord.Member):
    if user.bot:
        await ctx.reply("❌ You can't donate to a bot.")
        return
    donated, error = do_donate(did(ctx.author.id), did(user.id), amount)
    if error:
        await ctx.reply(error)
        return
    await ctx.reply(f"✅ Successfully donated ${donated:,} to {user.mention}")
