from core import *

def update_channel_text(guild, current_channel=None) -> str:
    if guild is None:
        return build_updateinfo_text()
    channel = discord.utils.get(guild.text_channels, name="update-info")
    if channel is None or current_channel and current_channel.id == channel.id:
        return build_updateinfo_text()
    return f"Click {channel.mention} for update"

@bot.tree.command(name="updateinfo", description="See what changed in the latest update")
async def updateinfo(interaction: discord.Interaction):
    await interaction.response.send_message(
        update_channel_text(interaction.guild, interaction.channel)
    )

@bot.command(name="updateinfo", aliases=["changelog"])
async def updateinfo_prefix(ctx: commands.Context):
    await ctx.reply(update_channel_text(ctx.guild, ctx.channel), mention_author=False)
