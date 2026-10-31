from core import *

@bot.tree.command(name="divorce", description="End your marriage")
async def divorce(interaction: discord.Interaction):
    await interaction.response.send_message(do_divorce(did(interaction.user.id)))


@bot.command(name="divorce")
async def divorce_prefix(ctx: commands.Context):
    await ctx.reply(do_divorce(did(ctx.author.id)))

