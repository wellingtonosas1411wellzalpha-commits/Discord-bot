from core import *

@bot.tree.command(name="activity", description="[Owner only] See which commands people have been using")
async def activity(interaction: discord.Interaction):
    if not await interaction.client.is_owner(interaction.user):
        await interaction.response.send_message("❌ Only the bot owner can use this command.", ephemeral=True)
        return
    await interaction.response.send_message(build_activity_text())


@bot.command(name="activity")
@commands.is_owner()
async def activity_prefix(ctx: commands.Context):
    await ctx.reply(build_activity_text())

