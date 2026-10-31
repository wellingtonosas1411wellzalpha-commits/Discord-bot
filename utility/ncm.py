from core import *

@bot.tree.command(name="ncm", description="Turn No Command Mode on or off")
@app_commands.describe(state="on or off")
@app_commands.choices(state=[
    app_commands.Choice(name="on", value="on"),
    app_commands.Choice(name="off", value="off"),
])
async def ncm(interaction: discord.Interaction, state: app_commands.Choice[str]):
    set_ncm(did(interaction.user.id), state.value == "on")
    if state.value == "on":
        await interaction.response.send_message(
            "🗣️ No Command Mode is **on**. Talk normally, like `donate 7 million to @user`. "
            "Money commands will ask you to say **yes** first."
        )
    else:
        ncm_pending.pop(did(interaction.user.id), None)
        await interaction.response.send_message("🔇 No Command Mode is **off**.")


@bot.command(name="ncm")
async def ncm_prefix(ctx: commands.Context, state: str):
    state = state.lower()
    if state not in ("on", "off"):
        await ctx.reply("❌ Use `.ncm on` or `.ncm off`.", mention_author=False)
        return
    set_ncm(did(ctx.author.id), state == "on")
    if state == "on":
        await ctx.reply(
            "🗣️ No Command Mode is **on**. Talk normally, like `donate 7 million to @user`. "
            "Money commands will ask you to say **yes** first.",
            mention_author=False,
        )
    else:
        ncm_pending.pop(did(ctx.author.id), None)
        await ctx.reply("🔇 No Command Mode is **off**.", mention_author=False)

