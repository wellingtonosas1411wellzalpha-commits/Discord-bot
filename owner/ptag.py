from core import *

@bot.tree.command(name="ptag", description="[Owner only] Mention every member")
@app_commands.describe(message="Message to send with the tags")
async def ptag(interaction: discord.Interaction, message: str):
    if interaction.guild is None:
        await interaction.response.send_message("❌ Use this in a server.", ephemeral=True)
        return
    if not await interaction.client.is_owner(interaction.user):
        await interaction.response.send_message("❌ Only the bot owner can use this.", ephemeral=True)
        return
    await interaction.response.defer(ephemeral=True)
    count = await send_member_tags(interaction.channel, message)
    await interaction.followup.send(f"Tagged {count} member(s).", ephemeral=True)


@bot.command(name="ptag")
@commands.guild_only()
async def ptag_prefix(ctx: commands.Context, *, message: str):
    if not await bot.is_owner(ctx.author):
        await ctx.reply("❌ Only the bot owner can use this.", mention_author=False)
        return
    try:
        await ctx.message.delete()
    except Exception as e:
        print(f"ptag delete failed: {e}")
    await send_member_tags(ctx.channel, message)

