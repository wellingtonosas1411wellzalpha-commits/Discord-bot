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

async def _sync_roles_for(member: discord.Member):
    """Re-applies any level role rewards the member has earned but doesn't
    have — for cases where auto-assignment failed (e.g. a permissions fix
    happened after the level-up already occurred)."""
    data = get_level_data(did(member.id))
    current_level = data["level"]
    rows = list_level_roles(member.guild.id)
    given, blocked, gone = [], [], []
    for level, role_id in rows:
        if level > current_level:
            continue
        role = member.guild.get_role(int(role_id))
        if role is None:
            gone.append(str(level))
            continue
        if role in member.roles:
            continue
        try:
            await member.add_roles(role, reason="Level role sync")
            given.append(role.name)
        except discord.Forbidden:
            blocked.append(role.name)
    if not given and not blocked and not gone:
        return "✅ You already have every role reward you've earned."
    parts = []
    if given:
        parts.append(f"🏅 Given: {', '.join(given)}")
    if blocked:
        parts.append(f"⚠️ Couldn't give (check the bot's Manage Roles permission and role position): {', '.join(blocked)}")
    if gone:
        parts.append(f"⚠️ Configured role(s) for level(s) {', '.join(gone)} no longer exist on this server.")
    return "\n".join(parts)

