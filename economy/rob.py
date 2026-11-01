from core import *

@bot.tree.command(name="rob", description="Attempt to rob another user")
@app_commands.describe(user="The user to rob")
async def rob(interaction: discord.Interaction, user: discord.User):
    await interaction.response.send_message(do_rob(did(interaction.user.id), did(user.id)))


@bot.command(name="rob")
async def rob_prefix(ctx: commands.Context, user: discord.User):
    await ctx.reply(do_rob(did(ctx.author.id), did(user.id)))
