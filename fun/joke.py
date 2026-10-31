from core import *

@bot.tree.command(name="joke", description="Get a random joke")
async def joke(interaction: discord.Interaction):
    await interaction.response.send_message(f"😄 {get_joke()}")


@bot.command(name="joke")
async def joke_prefix(ctx: commands.Context):
    await ctx.reply(f"😄 {get_joke()}")

def is_kira_creator(user) -> bool:
    """True only if the person is a server Administrator."""
    return isinstance(user, discord.Member) and user.guild_permissions.administrator

def get_kiragpt_session(user_id: str):
    if user_id not in kiragpt_sessions:
        kiragpt_sessions[user_id] = {
            "active": False,
            "history": [],
            "mode": "normal",          # normal / wild / ai
        }
    return kiragpt_sessions[user_id]

MAX_REPLIES_FOR_NORMAL_USERS = 50

async def handle_kiragpt_message(user, prompt: str, send_func):
    user_id = did(user.id)
    session = get_kiragpt_session(user_id)
    is_creator = is_kira_creator(user)

    # Rate limit for non-admins
    if not is_creator and not test_mode_on(user_id):
        if get_kiragpt_reply_count(user_id) >= MAX_REPLIES_FOR_NORMAL_USERS:
            await send_func(
                f"🚫 You have reached the limit of **{MAX_REPLIES_FOR_NORMAL_USERS} replies** "
                f"for regular users.\nAn administrator can lift this limit."
            )
            return

    # Handle mode switching
    lower = prompt.strip().lower()
    if lower in ("wild on", "wild mode on"):
        session["mode"] = "wild"
        await send_func("🔥 **Wild mode** activated. I'm feeling cocky now.")
        return
    if lower in ("ai on", "ai mode on"):
        session["mode"] = "ai"
        await send_func("🤖 **AI mode** activated. Strict coding mode only.")
        return
    if lower in ("normal on", "nice on", "normal mode on", "nice mode on"):
        session["mode"] = "normal"
        await send_func("😊 **Normal mode** activated. I'll be nice and helpful.")
        return

    if not prompt.strip():
        await send_func(
            "❌ Usage:\n"
            "`.xephongpt <message>`\n"
            "`.xephongpt on/off` — continuous chat\n"
            "`.xephongpt wild on` / `ai on` / `normal on` — change mode"
        )
        return

    mode = session.get("mode", "normal")

    reply_text = await generate_code_response(
        prompt, mode=mode, is_creator=is_creator, history=session["history"]
    )

    session["history"].append({"role": "user", "content": prompt[:1500]})
    session["history"].append({"role": "assistant", "content": reply_text})
    if len(session["history"]) > 20:
        session["history"] = session["history"][-20:]

    if not is_creator:
        increment_kiragpt_reply_count(user_id)

    if len(reply_text) <= 1900:
        await send_func(reply_text)
    else:
        import io
        file_bytes = io.BytesIO(reply_text.encode("utf-8"))
        discord_file = discord.File(file_bytes, filename="xephongpt_response.txt")
        await send_func("📄 Response was long — sending as a file:", file=discord_file)

