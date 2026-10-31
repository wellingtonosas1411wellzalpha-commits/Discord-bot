from core import *

@bot.tree.command(name="avatar", description="Get a user's avatar")
@app_commands.describe(user="The user to look up (defaults to you)")
async def avatar(interaction: discord.Interaction, user: discord.User = None):
    user = user or interaction.user
    await interaction.response.send_message(embed=build_avatar_embed(user))


@bot.command(name="avatar")
async def avatar_prefix(ctx: commands.Context, user: discord.User = None):
    user = user or ctx.author
    await ctx.reply(embed=build_avatar_embed(user))

