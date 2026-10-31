from core import *

@bot.tree.command(name="marry", description="Propose marriage to another user")
@app_commands.describe(user="The user to propose to")
async def marry(interaction: discord.Interaction, user: discord.User):
    if user.bot:
        await interaction.response.send_message("❌ You can't marry a bot.")
        return
    await interaction.response.send_message(propose_marriage(did(interaction.user.id), did(user.id)))


@bot.command(name="marry")
async def marry_prefix(ctx: commands.Context, user: discord.Member):
    if user.bot:
        await ctx.reply("❌ You can't marry a bot.")
        return
    await ctx.reply(propose_marriage(did(ctx.author.id), did(user.id)))

