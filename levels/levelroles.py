from core import *

@bot.tree.command(name="levelroles", description="See all configured level role rewards")
async def levelroles(interaction: discord.Interaction):
    rows = list_level_roles(interaction.guild.id)
    if not rows:
        await interaction.response.send_message("No level roles configured yet.")
        return
    lines = ["🏅 **Level Role Rewards**\n"]
    for level, role_id in rows:
        lines.append(f"Level {level} → <@&{role_id}>")
    await interaction.response.send_message("\n".join(lines))


@bot.command(name="levelroles")
async def levelroles_prefix(ctx: commands.Context):
    rows = list_level_roles(ctx.guild.id)
    if not rows:
        await ctx.reply("No level roles configured yet.")
        return
    lines = ["🏅 **Level Role Rewards**\n"]
    for level, role_id in rows:
        lines.append(f"Level {level} → <@&{role_id}>")
    await ctx.reply("\n".join(lines))
