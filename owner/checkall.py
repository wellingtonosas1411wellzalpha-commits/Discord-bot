from core import *

SKIP = {
    "checkall", "reset", "restart", "give", "take", "botban", "botunban",
    "xban", "xunban", "delete", "ptag", "auth", "test", "loan", "donate",
    "pay", "withdraw", "deposit", "rob", "clearcache", "setjob",
    "setlevelrole", "marry", "divorce", "payloan", "react", "antibadword",
}

async def silent(*args, **kwargs):
    return None

async def run_checkall(ctx: commands.Context) -> str:
    failed, ok, skipped = [], [], []
    old_reply, old_send, old_channel_send = ctx.reply, ctx.send, ctx.channel.send
    ctx.reply = silent
    ctx.send = silent
    ctx.channel.send = silent
    try:
        for cmd in sorted(bot.commands, key=lambda c: c.name):
            if cmd.name in SKIP:
                skipped.append(cmd.name)
                continue
            try:
                await ctx.invoke(cmd)
                ok.append(cmd.name)
            except (commands.MissingRequiredArgument, commands.BadArgument, commands.UserInputError):
                ok.append(cmd.name)
            except Exception as e:
                failed.append(f"{cmd.name}: {e.__class__.__name__}")
                print(f"checkall failed on {cmd.name}: {e}")
    finally:
        ctx.reply = old_reply
        ctx.send = old_send
        ctx.channel.send = old_channel_send
    lines = ["CHECKALL", "", f"OK        {len(ok)}", f"Failed    {len(failed)}", f"Skipped   {len(skipped)}", ""]
    if failed:
        lines.append("FAILED")
        lines.extend(f"- {item}" for item in failed)
    else:
        lines.append("No command failed.")
    lines.append("")
    lines.append("Test was silent. Skipped commands can change data.")
    return "```\n" + "\n".join(lines) + "\n```"

@bot.tree.command(name="checkall", description="[Owner] Quietly test commands")
async def checkall_slash(interaction: discord.Interaction):
    if not await interaction.client.is_owner(interaction.user):
        await interaction.response.send_message("Owner only.", ephemeral=True)
        return
    await interaction.response.defer(ephemeral=True)
    ctx = await bot.get_context(interaction)
    # prefix invoke needs a message context; build one from the interaction message if present
    if interaction.channel is None:
        await interaction.followup.send("Use this in a server.", ephemeral=True)
        return
    msg = await interaction.original_response()
    prefix_ctx = await bot.get_context(msg)
    prefix_ctx.author = interaction.user if isinstance(interaction.user, discord.Member) else prefix_ctx.author
    report = await run_checkall(prefix_ctx)
    await interaction.followup.send(report, ephemeral=True)

@bot.command(name="checkall")
@commands.is_owner()
async def checkall_prefix(ctx: commands.Context):
    report = await run_checkall(ctx)
    await ctx.reply(report, mention_author=False)
