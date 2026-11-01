from core import *

@bot.tree.command(name="versions", description="See the full version history log")
async def versions(interaction: discord.Interaction):
    await interaction.response.send_message(build_version_history_text())


@bot.command(name="versions", aliases=["versionhistory", "history"])
async def versions_prefix(ctx: commands.Context):
    await ctx.reply(build_version_history_text())

# ---------- Gambling ----------
