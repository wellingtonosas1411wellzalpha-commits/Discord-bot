from core import *

@bot.tree.command(name="tag", description="Mention every member")
@app_commands.describe(message="Message to send with the tags")
async def tag(interaction: discord.Interaction, message: str):
    if interaction.guild is None:
        await interaction.response.send_message("Use this in a server.", ephemeral=True)
        return
    await interaction.response.defer(ephemeral=True)
    count = await send_member_tags(interaction.channel, message)
    await interaction.followup.send(f"Tagged {count} member(s).", ephemeral=True)


@bot.command(name="tag", aliases=["ptag"])
@commands.guild_only()
async def tag_prefix(ctx: commands.Context, *, message: str):
    try:
        await ctx.message.delete()
    except Exception as e:
        print(f"tag delete failed: {e}")
    await send_member_tags(ctx.channel, message)
