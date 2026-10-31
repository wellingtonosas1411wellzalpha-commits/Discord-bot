from core import *

@bot.tree.command(name="jobs", description="See all available jobs")
async def jobs_cmd(interaction: discord.Interaction):
    await interaction.response.send_message(build_jobs_list_text())


@bot.command(name="jobs")
async def jobs_prefix(ctx: commands.Context):
    await ctx.reply(build_jobs_list_text())

