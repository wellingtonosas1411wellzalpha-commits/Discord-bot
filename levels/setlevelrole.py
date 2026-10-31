from core import *

@bot.tree.command(name="setlevelrole", description="[Admin] Set a role reward for reaching a level")
@app_commands.describe(level="The level to reward", role="The role to grant")
async def setlevelrole(interaction: discord.Interaction, level: int, role: discord.Role):
    if not is_kira_creator(interaction.user):
        await interaction.response.send_message("❌ Only server administrators can do that.")
        return
    set_level_role(interaction.guild.id, level, role.id)
    await interaction.response.send_message(f"✅ Users will now get **{role.name}** at level **{level}**.")


@bot.command(name="setlevelrole")
async def setlevelrole_prefix(ctx: commands.Context, level: int, role: discord.Role):
    if not is_kira_creator(ctx.author):
        await ctx.reply("❌ Only server administrators can do that.")
        return
    set_level_role(ctx.guild.id, level, role.id)
    await ctx.reply(f"✅ Users will now get **{role.name}** at level **{level}**.")

