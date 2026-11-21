import os
from core import *

def menu_file():
    path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", "banner.png")
    return discord.File(path, filename="xephon.png")

@bot.tree.command(name="menu", description="Show all bot commands")
async def menu(interaction: discord.Interaction):
    await interaction.response.send_message(build_menu_text(), file=menu_file())


@bot.command(name="menu")
async def menu_prefix(ctx: commands.Context):
    await ctx.reply(build_menu_text(), file=menu_file())
