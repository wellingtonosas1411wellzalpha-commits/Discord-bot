from core import *

@bot.tree.command(name="syncroles", description="Re-apply any level role rewards you're missing")
async def syncroles(interaction: discord.Interaction):
    if interaction.guild is None:
        await interaction.response.send_message("❌ This only works inside a server.")
        return
    await interaction.response.defer()
    try:
        member = interaction.user
        if not isinstance(member, discord.Member):
            member = interaction.guild.get_member(interaction.user.id) or await interaction.guild.fetch_member(interaction.user.id)
        await interaction.followup.send(await _sync_roles_for(member))
    except Exception as e:
        print(f"syncroles failed: {e}")
        await interaction.followup.send("❌ Could not sync roles. Check Manage Roles and role position.")

@bot.command(name="syncroles")
async def syncroles_prefix(ctx: commands.Context):
    if ctx.guild is None:
        await ctx.reply("❌ This only works inside a server.")
        return
    try:
        member = ctx.author
        if not isinstance(member, discord.Member):
            member = ctx.guild.get_member(ctx.author.id) or await ctx.guild.fetch_member(ctx.author.id)
        await ctx.reply(await _sync_roles_for(member))
    except Exception as e:
        print(f"syncroles failed: {e}")
        await ctx.reply("❌ Could not sync roles. Check Manage Roles and role position.")
