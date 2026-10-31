from core import *

@bot.tree.command(name="userinfo", description="Get info about a server member")
@app_commands.describe(member="The member to look up (defaults to you)")
async def userinfo(interaction: discord.Interaction, member: discord.Member = None):
    member = member or interaction.user
    await interaction.response.send_message(embed=build_userinfo_embed(member))


@bot.command(name="userinfo")
async def userinfo_prefix(ctx: commands.Context, member: discord.Member = None):
    member = member or ctx.author
    await ctx.reply(embed=build_userinfo_embed(member))

