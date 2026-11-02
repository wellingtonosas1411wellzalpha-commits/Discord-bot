from core import *

@bot.tree.command(name="botunban", description="[Admin] Remove a full command ban")
@app_commands.describe(user="User to unban")
async def botunban_slash(interaction: discord.Interaction, user: discord.Member):
    if not is_kira_creator(interaction.user):
        await interaction.response.send_message("❌ Admins only.", ephemeral=True)
        return
    uid = did(user.id)
    bot_bans.discard(uid)
    save_bans()
    await interaction.response.send_message(f"✅ **{user.display_name}** can use commands again.")

@bot.command(name="botunban")
async def botunban_prefix(ctx: commands.Context, user: discord.Member):
    if not is_kira_creator(ctx.author):
        await ctx.reply("❌ Admins only.", mention_author=False)
        return
    uid = did(user.id)
    bot_bans.discard(uid)
    save_bans()
    await ctx.reply(f"✅ **{user.display_name}** can use commands again.", mention_author=False)
