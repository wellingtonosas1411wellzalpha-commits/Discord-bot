from core import *

SKIP = {
    "checkall", "reset", "restart", "give", "take", "botban", "botunban",
    "xban", "xunban", "delete", "ptag", "auth", "test", "loan", "donate",
    "pay", "withdraw", "deposit", "rob", "clearcache", "setjob",
    "setlevelrole", "marry", "divorce", "payloan", "react", "antibadword",
}

@bot.command(name="checkall")
@commands.is_owner()
async def checkall(ctx: commands.Context):
    start = discord.utils.utcnow()
    await ctx.reply("Checking commands. This can take a bit.", mention_author=False)
    failed, ok, skipped = [], [], []
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
    deleted = 0
    async for msg in ctx.channel.history(limit=300, after=start):
        if msg.author == bot.user:
            try:
                await msg.delete()
                deleted += 1
            except discord.HTTPException:
                pass
    lines = ["CHECKALL", "", f"OK        {len(ok)}", f"Failed    {len(failed)}", f"Skipped   {len(skipped)}", f"Deleted   {deleted}", ""]
    if failed:
        lines.append("FAILED")
        lines.extend(f"- {item}" for item in failed)
    else:
        lines.append("No command failed.")
    lines.append("")
    lines.append("Skipped commands can change data, so they were not run.")
    await ctx.send(f"```\n" + "\n".join(lines) + "\n```")
