from core import *

@bot.tree.command(name="myjob", description="See your current job and salary")
async def myjob(interaction: discord.Interaction):
    await interaction.response.send_message(build_myjob_text(did(interaction.user.id)))


@bot.command(name="myjob")
async def myjob_prefix(ctx: commands.Context):
    await ctx.reply(build_myjob_text(did(ctx.author.id)))

