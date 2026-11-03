from core import *

@bot.tree.command(name="fake", description="Test command")
async def fake_slash(interaction: discord.Interaction):
    await interaction.response.send_message("real")

@bot.command(name="fake")
async def fake_prefix(ctx: commands.Context):
    await ctx.reply("real", mention_author=False)
