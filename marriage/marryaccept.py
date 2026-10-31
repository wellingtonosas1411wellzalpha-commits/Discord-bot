from core import *

@bot.tree.command(name="marryaccept", description="Accept a pending marriage proposal")
async def marryaccept(interaction: discord.Interaction):
    await interaction.response.send_message(accept_marriage(did(interaction.user.id)))


@bot.command(name="marryaccept")
async def marryaccept_prefix(ctx: commands.Context):
    await ctx.reply(accept_marriage(did(ctx.author.id)))

