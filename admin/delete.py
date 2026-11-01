from core import *

def _can_delete(member) -> bool:
    return isinstance(member, discord.Member) and member.guild_permissions.manage_messages

async def _delete_target(channel, message_id: int):
    target = await channel.fetch_message(message_id)
    await target.delete()

@bot.tree.command(name="delete", description="Delete a message you reply to or paste as a link")
@app_commands.describe(message_link="Optional message link or message ID")
async def delete_slash(interaction: discord.Interaction, message_link: str = None):
    if not _can_delete(interaction.user):
        await interaction.response.send_message("❌ You need **Manage Messages**.", ephemeral=True)
        return
    message_id = None
    if message_link:
        digits = "".join(ch if ch.isdigit() else " " for ch in message_link).split()
        if digits:
            message_id = int(digits[-1])
    if message_id is None and interaction.message is not None:
        message_id = interaction.message.id
    if message_id is None:
        await interaction.response.send_message(
            "❌ Reply to a message with `/delete`, or paste a message link.",
            ephemeral=True,
        )
        return
    try:
        await _delete_target(interaction.channel, message_id)
        await interaction.response.send_message("✅ Message deleted.", ephemeral=True)
    except discord.NotFound:
        await interaction.response.send_message("❌ I couldn't find that message.", ephemeral=True)
    except discord.Forbidden:
        await interaction.response.send_message("❌ I don't have permission to delete that.", ephemeral=True)

@bot.command(name="delete")
async def delete_prefix(ctx: commands.Context):
    if not _can_delete(ctx.author):
        await ctx.reply("❌ You need **Manage Messages**.", mention_author=False)
        return
    if ctx.message.reference is None or ctx.message.reference.message_id is None:
        await ctx.reply("❌ Reply to the message you want to delete.", mention_author=False)
        return
    try:
        await _delete_target(ctx.channel, ctx.message.reference.message_id)
        await ctx.message.delete()
    except discord.NotFound:
        await ctx.reply("❌ I couldn't find that message.", mention_author=False)
    except discord.Forbidden:
        await ctx.reply("❌ I don't have permission to delete that.", mention_author=False)
