from core import *

@bot.tree.command(name="antilink", description="Delete messages that contain links")
@app_commands.describe(state="on or off")
@app_commands.choices(state=[app_commands.Choice(name="on", value="on"), app_commands.Choice(name="off", value="off")])
async def antilink_slash(interaction: discord.Interaction, state: app_commands.Choice[str]):
    if not isinstance(interaction.user, discord.Member) or not interaction.user.guild_permissions.manage_messages:
        await interaction.response.send_message("You need Manage Messages.", ephemeral=True)
        return
    set_meta(f"antilink:{interaction.guild.id}", state.value)
    await interaction.response.send_message(f"Antilink is {state.value}.")

@bot.command(name="antilink")
async def antilink_prefix(ctx: commands.Context, state: str):
    if not isinstance(ctx.author, discord.Member) or not ctx.author.guild_permissions.manage_messages:
        await ctx.reply("You need Manage Messages.", mention_author=False)
        return
    state = state.lower()
    if state not in ("on", "off"):
        await ctx.reply("Use .antilink on or .antilink off.", mention_author=False)
        return
    set_meta(f"antilink:{ctx.guild.id}", state)
    await ctx.reply(f"Antilink is {state}.", mention_author=False)
