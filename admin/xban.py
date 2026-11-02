from core import *

@bot.tree.command(name="xban", description="[Admin] Ban a user from one command category")
@app_commands.describe(user="User to ban", category="Category, like gambling or economy")
async def xban_slash(interaction: discord.Interaction, user: discord.Member, category: str):
    if not is_kira_creator(interaction.user):
        await interaction.response.send_message("❌ Admins only.", ephemeral=True)
        return
    category = category.lower().strip()
    if category not in BAN_CATEGORIES:
        await interaction.response.send_message(
            "❌ Category must be one of: " + ", ".join(sorted(BAN_CATEGORIES)),
            ephemeral=True,
        )
        return
    uid = did(user.id)
    banned = set(x_bans.get(uid, []))
    banned.add(category)
    x_bans[uid] = sorted(banned)
    save_bans()
    await interaction.response.send_message(f"🚫 **{user.display_name}** is banned from **{category}**.")

@bot.command(name="xban")
async def xban_prefix(ctx: commands.Context, user: discord.Member, category: str):
    if not is_kira_creator(ctx.author):
        await ctx.reply("❌ Admins only.", mention_author=False)
        return
    category = category.lower().strip()
    if category not in BAN_CATEGORIES:
        await ctx.reply("❌ Category must be one of: " + ", ".join(sorted(BAN_CATEGORIES)), mention_author=False)
        return
    uid = did(user.id)
    banned = set(x_bans.get(uid, []))
    banned.add(category)
    x_bans[uid] = sorted(banned)
    save_bans()
    await ctx.reply(f"🚫 **{user.display_name}** is banned from **{category}**.", mention_author=False)
