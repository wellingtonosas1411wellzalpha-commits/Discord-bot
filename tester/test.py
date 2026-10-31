from core import *

@bot.tree.command(name="test", description="[VIP/tester] Turn infinite test money on or off")
@app_commands.describe(state="on or off")
@app_commands.choices(state=[
    app_commands.Choice(name="on", value="on"),
    app_commands.Choice(name="off", value="off"),
])
async def test_cmd(interaction: discord.Interaction, state: app_commands.Choice[str]):
    if not has_tester_role(interaction.user):
        await interaction.response.send_message("❌ You need the **tester** role.", ephemeral=True)
        return
    try:
        await interaction.response.send_message(do_test(did(interaction.user.id), state.value == "on"))
    except Exception as e:
        print(f"test failed: {e}")
        await interaction.response.send_message(f"❌ Test failed: {e}", ephemeral=True)


@bot.command(name="test")
async def test_prefix(ctx: commands.Context, state: str):
    if not has_tester_role(ctx.author):
        await ctx.reply("❌ You need the **tester** role.", mention_author=False)
        return
    state = state.lower()
    if state not in ("on", "off"):
        await ctx.reply("❌ Use `.test on` or `.test off`.", mention_author=False)
        return
    try:
        await ctx.reply(do_test(did(ctx.author.id), state == "on"), mention_author=False)
    except Exception as e:
        print(f"test failed: {e}")
        await ctx.reply(f"❌ Test failed: {e}", mention_author=False)

