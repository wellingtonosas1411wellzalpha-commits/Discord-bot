from core import *

@bot.tree.command(name="purge", description="Delete the last 10 messages here")
async def purge_slash(interaction: discord.Interaction):
    if not isinstance(interaction.user, discord.Member) or not interaction.user.guild_permissions.manage_messages:
        await interaction.response.send_message("You need Manage Messages.", ephemeral=True)
        return
    await interaction.response.defer(ephemeral=True)
    deleted = 0
    async for message in interaction.channel.history(limit=10):
        try:
            await message.delete()
            deleted += 1
        except Exception:
            pass
    await interaction.followup.send("Done.", ephemeral=True, delete_after=1)

@bot.command(name="purge")
async def purge_prefix(ctx: commands.Context):
    if not isinstance(ctx.author, discord.Member) or not ctx.author.guild_permissions.manage_messages:
        await ctx.reply("You need Manage Messages.", mention_author=False)
        return
    deleted = 0
    async for message in ctx.channel.history(limit=10):
        try:
            await message.delete()
            deleted += 1
        except Exception:
            pass

@bot.tree.command(name="clear", description="Delete Xephon's last 10 messages here")
async def clear_slash(interaction: discord.Interaction):
    if not isinstance(interaction.user, discord.Member) or not interaction.user.guild_permissions.manage_messages:
        await interaction.response.send_message("You need Manage Messages.", ephemeral=True)
        return
    await interaction.response.defer(ephemeral=True)
    deleted = 0
    async for message in interaction.channel.history(limit=50):
        if message.author.id == interaction.client.user.id:
            try:
                await message.delete()
                deleted += 1
            except Exception:
                pass
            if deleted >= 10:
                break
    await interaction.followup.send("Done.", ephemeral=True, delete_after=1)

@bot.command(name="clear")
async def clear_prefix(ctx: commands.Context):
    if not isinstance(ctx.author, discord.Member) or not ctx.author.guild_permissions.manage_messages:
        await ctx.reply("You need Manage Messages.", mention_author=False)
        return
    deleted = 0
    async for message in ctx.channel.history(limit=50):
        if message.author.id == ctx.bot.user.id:
            try:
                await message.delete()
                deleted += 1
            except Exception:
                pass
            if deleted >= 10:
                break
    try:
        await ctx.message.delete()
    except Exception:
        pass
