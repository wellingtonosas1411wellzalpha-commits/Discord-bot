from core import *

@bot.tree.command(name="achievements", description="See your (or someone else's) achievements")
@app_commands.describe(user="The user to check (leave blank for yourself)")
async def achievements(interaction: discord.Interaction, user: discord.User = None):
    target = user or interaction.user
    await interaction.response.send_message(build_achievements_text(target.display_name, did(target.id)))


@bot.command(name="achievements", aliases=["badges"])
async def achievements_prefix(ctx: commands.Context, user: discord.User = None):
    target = user or ctx.author
    await ctx.reply(build_achievements_text(target.display_name, did(target.id)))

# ---------- Market commands ----------

