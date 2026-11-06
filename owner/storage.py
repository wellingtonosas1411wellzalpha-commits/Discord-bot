from core import *

@bot.tree.command(name="storage", description="[Admin] Show bot system status")
async def storage(interaction: discord.Interaction):
    if not is_kira_creator(interaction.user):
        await interaction.response.send_message("❌ Admins only.", ephemeral=True)
        return
    await interaction.response.send_message(build_storage_text())


@bot.command(name="storage")
async def storage_prefix(ctx: commands.Context):
    if not is_kira_creator(ctx.author):
        await ctx.reply('❌ Admins only.', mention_author=False)
        return
    await ctx.reply(build_storage_text())

