from core import *

@bot.tree.command(name="stats", description="[Owner only] Show how many people use the bot")
async def stats(interaction: discord.Interaction):
    if not await interaction.client.is_owner(interaction.user):
        await interaction.response.send_message("❌ Only the bot owner can use this command.", ephemeral=True)
        return
    await interaction.response.send_message(build_stats_text())


@bot.command(name="stats")
@commands.is_owner()
async def stats_prefix(ctx: commands.Context):
    await ctx.reply(build_stats_text())

