from core import *

def mute_key(guild_id):
    return f"mute:{guild_id}"

def muted_ids(guild_id):
    raw = get_meta(mute_key(guild_id)) or "[]"
    try:
        return set(json.loads(raw))
    except Exception:
        return set()

def save_muted(guild_id, ids):
    set_meta(mute_key(guild_id), json.dumps(sorted(ids)))

@bot.tree.command(name="mute", description="Delete a user's new messages")
@app_commands.describe(user="User to mute")
async def mute_slash(interaction: discord.Interaction, user: discord.Member):
    if not isinstance(interaction.user, discord.Member) or not interaction.user.guild_permissions.manage_messages:
        await interaction.response.send_message("You need Manage Messages.", ephemeral=True)
        return
    ids = muted_ids(interaction.guild.id)
    ids.add(str(user.id))
    save_muted(interaction.guild.id, ids)
    await interaction.response.send_message(f"Muted {user.mention}.")

@bot.command(name="mute")
async def mute_prefix(ctx: commands.Context, user: discord.Member):
    if not isinstance(ctx.author, discord.Member) or not ctx.author.guild_permissions.manage_messages:
        await ctx.reply("You need Manage Messages.", mention_author=False)
        return
    ids = muted_ids(ctx.guild.id)
    ids.add(str(user.id))
    save_muted(ctx.guild.id, ids)
    await ctx.reply(f"Muted {user.mention}.", mention_author=False)
