from core import *

@bot.tree.command(name="botban", description="[Admin] Ban a user from all commands")
@app_commands.describe(user="User to ban")
async def botban_slash(interaction: discord.Interaction, user: discord.Member):
    if not is_kira_creator(interaction.user):
        await interaction.response.send_message("❌ Admins only.", ephemeral=True)
        return
    uid = did(user.id)
    bot_bans.add(uid)
    save_bans()
    await interaction.response.send_message(f"🚫 **{user.display_name}** is bot-banned.")

@bot.command(name="botban")
async def botban_prefix(ctx: commands.Context, user: discord.Member):
    if not is_kira_creator(ctx.author):
        await ctx.reply("❌ Admins only.", mention_author=False)
        return
    uid = did(user.id)
    bot_bans.add(uid)
    save_bans()
    await ctx.reply(f"🚫 **{user.display_name}** is bot-banned.", mention_author=False)
