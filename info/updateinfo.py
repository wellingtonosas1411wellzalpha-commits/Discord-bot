from core import *

@bot.tree.command(name="updateinfo", description="See what changed in the latest update")
async def updateinfo(interaction: discord.Interaction):
    await interaction.response.send_message(build_updateinfo_text())


@bot.command(name="updateinfo", aliases=["changelog"])
async def updateinfo_prefix(ctx: commands.Context):
    await ctx.reply(build_updateinfo_text())

