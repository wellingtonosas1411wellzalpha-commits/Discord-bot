from core import *

@bot.tree.command(name="xunban", description="[Admin] Remove a category ban")
@app_commands.describe(user="User to unban", category="Category to restore")
async def xunban_slash(interaction: discord.Interaction, user: discord.Member, category: str):
    if not is_kira_creator(interaction.user):
        await interaction.response.send_message("❌ Admins only.", ephemeral=True)
        return
    category = category.lower().strip()
    uid = did(user.id)
    banned = set(x_bans.get(uid, []))
    banned.discard(category)
    if banned:
        x_bans[uid] = sorted(banned)
    else:
        x_bans.pop(uid, None)
    save_bans()
    await interaction.response.send_message(f"✅ **{user.display_name}** can use **{category}** again.")

@bot.command(name="xunban")
async def xunban_prefix(ctx: commands.Context, user: discord.Member, category: str):
    if not is_kira_creator(ctx.author):
        await ctx.reply("❌ Admins only.", mention_author=False)
        return
    category = category.lower().strip()
    uid = did(user.id)
    banned = set(x_bans.get(uid, []))
    banned.discard(category)
    if banned:
        x_bans[uid] = sorted(banned)
    else:
        x_bans.pop(uid, None)
    save_bans()
    await ctx.reply(f"✅ **{user.display_name}** can use **{category}** again.", mention_author=False)
