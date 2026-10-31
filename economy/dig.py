from core import *

@bot.tree.command(name="dig", description="Dig for buried coins")
async def dig(interaction: discord.Interaction):
    await interaction.response.send_message(do_dig(did(interaction.user.id)))


@bot.command(name="dig")
async def dig_prefix(ctx: commands.Context):
    await ctx.reply(do_dig(did(ctx.author.id)))

