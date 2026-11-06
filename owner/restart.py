from core import *

@bot.tree.command(name="restart", description="[Admin] Deploy the latest commit and restart Xephon")
async def restart(interaction: discord.Interaction):
    if not is_kira_creator(interaction.user):
        await interaction.response.send_message("❌ Admins only.", ephemeral=True)
        return
    set_meta("restart_announce_channel", str(interaction.channel_id))
    set_meta("restart_announce_pending", "1")
    ok, msg = await asyncio.to_thread(trigger_render_deploy)
    if not ok:
        set_meta("restart_announce_pending", "0")
        await interaction.response.send_message(f"❌ Could not start the deploy.\n{msg}")
        return
    global bot_restarting
    bot_restarting = True
    try:
        await bot.change_presence(status=discord.Status.offline)
    except Exception as e:
        print(f"Could not set offline presence: {e}")
    await interaction.response.send_message("🔄 Xephon is going offline to apply the latest commit.")


@bot.command(name="restart")
async def restart_prefix(ctx: commands.Context):
    if not is_kira_creator(ctx.author):
        await ctx.reply('❌ Admins only.', mention_author=False)
        return
    set_meta("restart_announce_channel", str(ctx.channel.id))
    set_meta("restart_announce_pending", "1")
    ok, msg = await asyncio.to_thread(trigger_render_deploy)
    if not ok:
        set_meta("restart_announce_pending", "0")
        await ctx.reply(f"❌ Could not start the deploy.\n{msg}")
        return
    global bot_restarting
    bot_restarting = True
    try:
        await bot.change_presence(status=discord.Status.offline)
    except Exception as e:
        print(f"Could not set offline presence: {e}")
    await ctx.reply("🔄 Xephon is going offline to apply the latest commit.")

