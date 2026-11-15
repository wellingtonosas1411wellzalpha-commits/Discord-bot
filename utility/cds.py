from core import *

@bot.tree.command(name="cds", description="See your cooldowns")
async def cds_slash(interaction: discord.Interaction):
    await interaction.response.send_message(build_cooldowns_text(did(interaction.user.id)))

@bot.command(name="cds", aliases=["cooldowns"])
async def cds_prefix(ctx: commands.Context):
    await ctx.reply(build_cooldowns_text(did(ctx.author.id)))
