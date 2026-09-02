# card_commands.py — part of Kira bot 1.16.0 (loaded by bot.py)
@bot.command(name="col", aliases=["collection", "cards"])
async def col_prefix(ctx: commands.Context, user: discord.User = None):
    target = user or ctx.author
    await ctx.reply(build_col_text(target.display_name, did(target.id)))


@bot.tree.command(name="col", description="Show your card collection")
@app_commands.describe(user="Leave blank for yourself")
async def col_slash(interaction: discord.Interaction, user: discord.User = None):
    target = user or interaction.user
    await interaction.response.send_message(build_col_text(target.display_name, did(target.id)))


@bot.command(name="card")
async def card_prefix(ctx: commands.Context, index: str = ""):
    async def send(**kwargs):
        await ctx.reply(**kwargs)
    await send_card_view(send, did(ctx.author.id), index, ctx.author.display_name)


@bot.tree.command(name="card", description="Show one card from your collection")
@app_commands.describe(index="Collection number from .col")
async def card_slash(interaction: discord.Interaction, index: str):
    await interaction.response.defer()
    async def send(**kwargs):
        await interaction.followup.send(**kwargs)
    await send_card_view(send, did(interaction.user.id), index, interaction.user.display_name)


@bot.command(name="claim")
async def claim_prefix(ctx: commands.Context, code: str = ""):
    ok, message = claim_spawn(did(ctx.author.id), code)
    await ctx.reply(message)


@bot.tree.command(name="claim", description="Claim a spawned card")
@app_commands.describe(code="The code from the spawn message")
async def claim_slash(interaction: discord.Interaction, code: str):
    ok, message = claim_spawn(did(interaction.user.id), code)
    await interaction.response.send_message(message)


@bot.command(name="duel")
async def duel_prefix(ctx: commands.Context, user: discord.Member = None):
    if user is None:
        await ctx.reply("❌ Usage: `.duel @user`")
        return
    if user.bot or user.id == ctx.author.id:
        await ctx.reply("❌ Challenge a real player, not yourself or a bot.")
        return
    if not get_user_card_rows(did(ctx.author.id)):
        await ctx.reply("❌ You have no cards to duel with.")
        return
    if not get_user_card_rows(did(user.id)):
        await ctx.reply(f"❌ **{user.display_name}** has no cards.")
        return
    pending_duels[did(user.id)] = did(ctx.author.id)
    view = DuelView(ctx.author.id, user.id)
    await ctx.reply(f"⚔️ {user.mention}, {ctx.author.display_name} challenged you to a card duel.", view=view)


@bot.tree.command(name="duel", description="Challenge someone to a card duel")
@app_commands.describe(user="The player to challenge")
async def duel_slash(interaction: discord.Interaction, user: discord.Member):
    if user.bot or user.id == interaction.user.id:
        await interaction.response.send_message("❌ Challenge a real player, not yourself or a bot.")
        return
    if not get_user_card_rows(did(interaction.user.id)):
        await interaction.response.send_message("❌ You have no cards to duel with.")
        return
    if not get_user_card_rows(did(user.id)):
        await interaction.response.send_message(f"❌ **{user.display_name}** has no cards.")
        return
    pending_duels[did(user.id)] = did(interaction.user.id)
    view = DuelView(interaction.user.id, user.id)
    await interaction.response.send_message(
        f"⚔️ {user.mention}, {interaction.user.display_name} challenged you to a card duel.",
        view=view,
    )


@bot.command(name="spawndrop")
@commands.is_owner()
async def spawndrop_prefix(ctx: commands.Context, state: str = ""):
    state = state.lower().strip()
    if state not in ("on", "off"):
        await ctx.reply("❌ Usage: `.spawndrop on` or `.spawndrop off`")
        return
    if ctx.guild is None:
        await ctx.reply("❌ Use this in a server channel.")
        return
    set_meta(CARD_SPAWN_TOGGLE_KEY, state)
    if state == "on":
        set_meta(CARD_SPAWN_CHANNEL_KEY, str(ctx.channel.id))
        await ctx.reply(f"✅ Card drops **ON** in this channel. Max **{CARD_SPAWN_PER_DAY}** per day.")
    else:
        await ctx.reply("✅ Card drops **OFF**.")


@bot.command(name="forcedrop")
@commands.is_owner()
async def forcedrop_prefix(ctx: commands.Context):
    ok, message = await post_card_spawn(ctx.channel, force=True)
    if not ok:
        await ctx.reply(message)


@bot.command(name="addcard")
@commands.is_owner()
async def addcard_prefix(ctx: commands.Context, *, raw: str = ""):
    parts = [p.strip() for p in raw.split("|")]
    if len(parts) < 3:
        await ctx.reply("❌ Usage: `.addcard <id> | <name> | <tier> | <description>`\nYou can attach a picture too.")
        return
    card_key = parts[0].lower().replace(" ", "_")
    name = parts[1]
    try:
        tier = int(parts[2])
    except ValueError:
        await ctx.reply("❌ Tier must be a number from 1 to 5.")
        return
    if not (1 <= tier <= 5):
        await ctx.reply("❌ Tier must be 1 to 5.")
        return
    description = parts[3] if len(parts) > 3 else ""
    image_url = None
    image_path = None
    if ctx.message.attachments:
        image_url = ctx.message.attachments[0].url
    add_catalog_card(card_key, name, tier, image_path=image_path, image_url=image_url, description=description)
    extra = " Picture saved from your attachment." if image_url else " Add a picture next time by attaching one."
    await ctx.reply(f"✅ Card **{name}** (`{card_key}`) T{tier} added.{extra}")



@bot.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return

    # Owner DM broadcast
    if message.guild is None and message.content[:1] in ("!", "*"):
        if await bot.is_owner(message.author):
            ping = message.content.startswith("!")
            text = message.content[1:].strip()
            if not text:
                mark = "!" if ping else "*"
                await message.channel.send(f"❌ Type something after `{mark}`")
                return
            sent, failed = await broadcast_owner_message(text, ping_everyone=ping)
            await message.channel.send(f"✅ Sent to **{sent}** server(s). Failed: **{failed}**.")
            return

    # XP / leveling
    if message.guild is not None:
        try:
            new_level = add_message_xp(did(message.author.id))
            if new_level is not None:
                level_up_msg = (
                    f"🎉 {message.author.mention} leveled up to **level {new_level}**! "
                    f"(+{XP_LEVEL_UP_REWARD:,} coins)"
                )
                role_id = get_level_role(message.guild.id, new_level)
                if role_id is not None:
                    role = message.guild.get_role(role_id)
                    if role is None:
                        level_up_msg += (
                            f"\n⚠️ A role reward is set for level {new_level}, but that role "
                            f"no longer exists on this server."
                        )
                    elif isinstance(message.author, discord.Member):
                        try:
                            await message.author.add_roles(role, reason=f"Reached level {new_level}")
                            level_up_msg += f"\n🏅 You've earned the **{role.name}** role!"
                        except discord.Forbidden:
                            level_up_msg += (
                                f"\n⚠️ Couldn't give you the **{role.name}** role — the bot needs "
                                f"**Manage Roles** and its role must sit above **{role.name}** in "
                                f"Server Settings → Roles."
                            )
                        except discord.HTTPException as e:
                            level_up_msg += f"\n⚠️ Couldn't give you the **{role.name}** role (Discord error: {e})."
                if new_level >= 20 and grant_achievement(did(message.author.id), "veteran"):
                    level_up_msg += f"\n🏅 Achievement unlocked: **{ACHIEVEMENTS['veteran']['label']}**"
                await message.channel.send(level_up_msg)
        except Exception as e:
            print(f"XP handling failed: {e}")

    # AFK handling
    if did(message.author.id) in afk_users:
        del afk_users[did(message.author.id)]
        await message.reply(f"Welcome back {message.author.mention}, I removed your afk.", mention_author=False)

    for user in message.mentions:
        if did(user.id) in afk_users:
            await message.reply(
                f"{user.display_name} is afk: {afk_users[did(user.id)]}",
                mention_author=False,
            )

    # KiraGPT continuous chat
    user_id = did(message.author.id)
    session = kiragpt_sessions.get(user_id)
    if session and session.get("active") and message.reference and message.content and message.content.strip():
        try:
            ref = message.reference.resolved
            if ref is None:
                ref = await message.channel.fetch_message(message.reference.message_id)
            if ref and ref.author.id == bot.user.id:
                async with message.channel.typing():
                    async def send_func(text, file=None):
                        if file:
                            await message.reply(text, file=file)
                        else:
                            await message.reply(text)
                    await handle_kiragpt_message(message.author, message.content, send_func)
                return
        except Exception as e:
            print(f"KiraGPT reply handling failed: {e}")

    await bot.process_commands(message)



if __name__ == "__main__":
    if not TOKEN:
        raise RuntimeError("DISCORD_TOKEN not found. Set it in your .env file.")
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL not found. Set it in your .env file.")
    init_db()

    # --- Keep-alive web server for Render's free tier ---
    # Render's free compute is only available to web services, and free
    # services sleep after 15 minutes with no HTTP traffic. This tiny Flask
    # server gives Render something to see as \"web traffic\" when an external
    # pinger (e.g. UptimeRobot) hits it every few minutes, so the bot never
    # goes idle. It runs in a background thread; the Discord bot itself still
    # runs on the main thread via bot.run() below.
    keep_alive_app = Flask(__name__)

    @keep_alive_app.route("/")
    def keep_alive_home():
        return "Kira bot is alive."

    def run_keep_alive():
        port = int(os.environ.get("PORT", 8080))
        keep_alive_app.run(host="0.0.0.0", port=port)

    threading.Thread(target=run_keep_alive, daemon=True).start()

    bot.run(TOKEN)
