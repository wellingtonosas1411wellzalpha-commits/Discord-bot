from core import *

@bot.tree.command(name="syncroles", description="Re-apply any level role rewards you're missing")
async def syncroles(interaction: discord.Interaction):
    if interaction.guild is None or not isinstance(interaction.user, discord.Member):
        await interaction.response.send_message("❌ This only works inside a server.")
        return
    await interaction.response.send_message(await _sync_roles_for(interaction.user))


@bot.command(name="syncroles")
async def syncroles_prefix(ctx: commands.Context):
    if ctx.guild is None:
        await ctx.reply("❌ This only works inside a server.")
        return
    await ctx.reply(await _sync_roles_for(ctx.author))

