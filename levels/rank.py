from core import *

@bot.tree.command(name="rank", description="See your (or someone else's) level and XP")
@app_commands.describe(user="The user to check (leave blank for yourself)")
async def rank(interaction: discord.Interaction, user: discord.User = None):
    target = user or interaction.user
    await interaction.response.send_message(build_rank_text(did(target.id), target.display_name))


@bot.command(name="rank")
async def rank_prefix(ctx: commands.Context, user: discord.User = None):
    target = user or ctx.author
    await ctx.reply(build_rank_text(did(target.id), target.display_name))

