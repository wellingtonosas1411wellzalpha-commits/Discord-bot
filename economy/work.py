from core import *

@bot.tree.command(name="work", description="Work a job for coins")
async def work(interaction: discord.Interaction):
    await interaction.response.send_message(do_work(did(interaction.user.id)))


@bot.command(name="work")
async def work_prefix(ctx: commands.Context):
    await ctx.reply(do_work(did(ctx.author.id)))

