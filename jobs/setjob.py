from core import *

@bot.tree.command(name="setjob", description="Get randomly assigned a job that pays you a salary automatically")
async def setjob(interaction: discord.Interaction):
    job_key = random.choice(list(JOBS.keys()))
    await interaction.response.send_message(set_job(did(interaction.user.id), job_key))


@bot.command(name="setjob")
async def setjob_prefix(ctx: commands.Context):
    job_key = random.choice(list(JOBS.keys()))
    await ctx.reply(set_job(did(ctx.author.id), job_key))

