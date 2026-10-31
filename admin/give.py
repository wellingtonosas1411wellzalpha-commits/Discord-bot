from core import *

@bot.tree.command(name="give", description="[Admin] Give a role to a user directly")
@app_commands.describe(user="The user to give the role to", role="The role to give")
async def give(interaction: discord.Interaction, user: discord.Member, role: discord.Role):
    if not is_kira_creator(interaction.user):
        await interaction.response.send_message("❌ Only server administrators can do that.")
        return
    if role in user.roles:
        await interaction.response.send_message(f"❌ **{user.display_name}** already has **{role.name}**.")
        return
    try:
        await user.add_roles(role, reason=f"Given by {interaction.user}")
        await interaction.response.send_message(f"✅ Gave **{role.name}** to **{user.display_name}**.")
    except discord.Forbidden:
        await interaction.response.send_message(
            f"❌ Couldn't give **{role.name}** — the bot needs **Manage Roles** and its role "
            f"must sit above **{role.name}** in Server Settings → Roles."
        )


@bot.command(name="give")
async def give_prefix(ctx: commands.Context, user: discord.Member, role: discord.Role):
    if not is_kira_creator(ctx.author):
        await ctx.reply("❌ Only server administrators can do that.")
        return
    if role in user.roles:
        await ctx.reply(f"❌ **{user.display_name}** already has **{role.name}**.")
        return
    try:
        await user.add_roles(role, reason=f"Given by {ctx.author}")
        await ctx.reply(f"✅ Gave **{role.name}** to **{user.display_name}**.")
    except discord.Forbidden:
        await ctx.reply(
            f"❌ Couldn't give **{role.name}** — the bot needs **Manage Roles** and its role "
            f"must sit above **{role.name}** in Server Settings → Roles."
        )

