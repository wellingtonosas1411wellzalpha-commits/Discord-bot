from core import *

@bot.tree.command(name="auth", description="[Owner only] Toggle whether the bot responds in this server")
@app_commands.describe(state="on or off")
@app_commands.choices(state=[
    app_commands.Choice(name="on", value="on"),
    app_commands.Choice(name="off", value="off"),
])
async def auth(interaction: discord.Interaction, state: app_commands.Choice[str]):
    if not await interaction.client.is_owner(interaction.user):
        await interaction.response.send_message("❌ Only the bot owner can use this command.", ephemeral=True)
        return
    if interaction.guild is None:
        await interaction.response.send_message("❌ This command only works inside a server.")
        return
    set_auth_state(interaction.guild.id, state.value == "on")
    await interaction.response.send_message(f"🔐 Bot responses turned **{state.value}** for this server.")


@bot.command(name="auth")
@commands.is_owner()
async def auth_prefix(ctx: commands.Context, state: str):
    state = state.lower()
    if state not in ("on", "off"):
        await ctx.reply("❌ Use `.auth on` or `.auth off`.")
        return
    if ctx.guild is None:
        await ctx.reply("❌ This command only works inside a server.")
        return
    set_auth_state(ctx.guild.id, state == "on")
    await ctx.reply(f"🔐 Bot responses turned **{state}** for this server.")

