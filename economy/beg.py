from core import *

@bot.tree.command(name="beg", description="Beg for some coins")
async def beg(interaction: discord.Interaction):
    await interaction.response.send_message(do_beg(did(interaction.user.id)))


@bot.command(name="beg")
async def beg_prefix(ctx: commands.Context):
    await ctx.reply(do_beg(did(ctx.author.id)))

