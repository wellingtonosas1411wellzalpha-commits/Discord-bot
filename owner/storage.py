from core import *

@bot.tree.command(name="storage", description="[Owner only] Show bot system status")
async def storage(interaction: discord.Interaction):
    if not await interaction.client.is_owner(interaction.user):
        await interaction.response.send_message("❌ Only the bot owner can use this command.", ephemeral=True)
        return
    await interaction.response.send_message(build_storage_text())


@bot.command(name="storage")
@commands.is_owner()
async def storage_prefix(ctx: commands.Context):
    await ctx.reply(build_storage_text())

