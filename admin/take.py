from core import *

@bot.tree.command(name="take", description="[Admin] Strip a role from a user directly")
@app_commands.describe(user="The user to remove the role from", role="The role to remove")
async def take(interaction: discord.Interaction, user: discord.Member, role: discord.Role):
    if not is_kira_creator(interaction.user):
        await interaction.response.send_message("❌ Only server administrators can do that.")
        return
    if role not in user.roles:
        await interaction.response.send_message(f"❌ **{user.display_name}** doesn't have **{role.name}**.")
        return
    try:
        await user.remove_roles(role, reason=f"Removed by {interaction.user}")
        await interaction.response.send_message(f"✅ Removed **{role.name}** from **{user.display_name}**.")
    except discord.Forbidden:
        await interaction.response.send_message(
            f"❌ Couldn't remove **{role.name}** — the bot needs **Manage Roles** and its role "
            f"must sit above **{role.name}** in Server Settings → Roles."
        )


@bot.command(name="take")
async def take_prefix(ctx: commands.Context, user: discord.Member, role: discord.Role):
    if not is_kira_creator(ctx.author):
        await ctx.reply("❌ Only server administrators can do that.")
        return
    if role not in user.roles:
        await ctx.reply(f"❌ **{user.display_name}** doesn't have **{role.name}**.")
        return
    try:
        await user.remove_roles(role, reason=f"Removed by {ctx.author}")
        await ctx.reply(f"✅ Removed **{role.name}** from **{user.display_name}**.")
    except discord.Forbidden:
        await ctx.reply(
            f"❌ Couldn't remove **{role.name}** — the bot needs **Manage Roles** and its role "
            f"must sit above **{role.name}** in Server Settings → Roles."
        )

