from core import *

def antidelete_key(guild_id) -> str:
    return f"antidelete:{guild_id}"

def antidelete_on(guild_id) -> bool:
    return get_meta(antidelete_key(guild_id)) == "on"

@bot.tree.command(name="antidelete", description="[Admin] Repost deleted messages")
@app_commands.describe(state="on or off")
@app_commands.choices(state=[
    app_commands.Choice(name="on", value="on"),
    app_commands.Choice(name="off", value="off"),
])
async def antidelete_slash(interaction: discord.Interaction, state: app_commands.Choice[str]):
    if not isinstance(interaction.user, discord.Member) or not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ Only an administrator can use this.", ephemeral=True)
        return
    set_meta(antidelete_key(interaction.guild.id), state.value)
    await interaction.response.send_message(f"🛡️ Antidelete is **{state.value}**.")

@bot.command(name="antidelete")
async def antidelete_prefix(ctx: commands.Context, state: str = None):
    if not isinstance(ctx.author, discord.Member) or not ctx.author.guild_permissions.administrator:
        await ctx.reply("❌ Only an administrator can use this.", mention_author=False)
        return
    if ctx.guild is None:
        await ctx.reply("❌ Use this in a server.", mention_author=False)
        return
    if state is None:
        current = "on" if antidelete_on(ctx.guild.id) else "off"
        await ctx.reply(f"🛡️ Antidelete is **{current}**.", mention_author=False)
        return
    state = state.lower()
    if state not in ("on", "off"):
        await ctx.reply("❌ Use `.antidelete on` or `.antidelete off`.", mention_author=False)
        return
    set_meta(antidelete_key(ctx.guild.id), state)
    await ctx.reply(f"🛡️ Antidelete is **{state}**.", mention_author=False)

@bot.listen("on_message_delete")
async def antidelete_repost(message: discord.Message):
    if message.guild is None or message.author.bot:
        return
    if not antidelete_on(message.guild.id):
        return
    content = message.content.strip() if message.content else ""
    if len(content) > 1500:
        content = content[:1500] + "…"
    if not content:
        content = "*no text*"
    if message.attachments:
        names = ", ".join(a.filename for a in message.attachments)
        content += f"\nAttachments: {names}"
    try:
        await message.channel.send(f"{message.author.mention} tried to delete [{content}]")
    except discord.HTTPException:
        pass
