from core import *

@bot.tree.command(name="xephongpt", description="Talk to XephonGPT")
@app_commands.describe(
    state="Mode: wild, Ai, or normal",
    toggle="Turn continuous chat on or off",
    prompt="Optional message to send",
)
@app_commands.choices(state=[
    app_commands.Choice(name="wild", value="wild"),
    app_commands.Choice(name="Ai", value="ai"),
    app_commands.Choice(name="normal", value="normal"),
])
@app_commands.choices(toggle=[
    app_commands.Choice(name="on", value="on"),
    app_commands.Choice(name="off", value="off"),
])
async def kiragpt(
    interaction: discord.Interaction,
    state: app_commands.Choice[str] = None,
    toggle: app_commands.Choice[str] = None,
    prompt: str = None,
):
    await interaction.response.defer()
    user_id = did(interaction.user.id)
    session = get_kiragpt_session(user_id)
    notes = []

    if state is not None:
        session["mode"] = state.value
        labels = {"wild": "Wild", "ai": "Ai", "normal": "Normal"}
        notes.append(f"Mode set to **{labels.get(state.value, state.value)}**.")

    if toggle is not None:
        session["active"] = toggle.value == "on"
        if toggle.value == "off":
            session["history"] = []
        notes.append(f"Continuous chat **{toggle.value.upper()}**.")

    if prompt and prompt.strip():
        async def send_func(text, file=None):
            if file:
                await interaction.followup.send(text, file=file)
            else:
                await interaction.followup.send(text)
        if notes:
            await interaction.followup.send("✅ " + " ".join(notes))
        await handle_kiragpt_message(interaction.user, prompt.strip(), send_func)
        return

    if notes:
        await interaction.followup.send("✅ " + " ".join(notes))
        return

    await interaction.followup.send(
        "Pick a **state** (`wild`, `Ai`, `normal`) and **on/off**, or add a message.",
        ephemeral=True,
    )


@bot.command(name="xephongpt")
async def kiragpt_prefix(ctx: commands.Context, *, prompt: str = ""):
    user_id = did(ctx.author.id)
    session = get_kiragpt_session(user_id)
    prompt = prompt.strip()
    lower = prompt.lower()

    if lower == "on":
        session["active"] = True
        session["history"] = []
        await ctx.reply("✅ XephonGPT continuous chat **ON**. Reply to my messages to continue!")
        return
    if lower == "off":
        session["active"] = False
        session["history"] = []
        await ctx.reply("✅ XephonGPT continuous chat **OFF**. History cleared.")
        return

    async with ctx.typing():
        async def send_func(text, file=None):
            if file:
                await ctx.reply(text, file=file)
            else:
                await ctx.reply(text)
        images = await media_parts_from_message(ctx.message)
        if ctx.message.reference and ctx.message.reference.message_id:
            try:
                replied = await ctx.channel.fetch_message(ctx.message.reference.message_id)
                images += await media_parts_from_message(replied)
            except Exception:
                pass
        await handle_kiragpt_message(ctx.author, prompt, send_func, images=images)

