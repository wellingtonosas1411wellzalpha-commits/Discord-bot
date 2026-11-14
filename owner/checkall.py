from core import *

SKIP = {
    "checkall", "reset", "restart", "give", "take", "botban", "botunban",
    "xban", "xunban", "delete", "ptag", "auth", "test", "loan", "donate",
    "pay", "withdraw", "deposit", "rob", "clearcache", "setjob",
    "setlevelrole", "marry", "divorce", "payloan", "react", "antibadword",
}

def build_checkall_report() -> str:
    failed, ok, skipped = [], [], []
    for cmd in sorted(bot.commands, key=lambda c: c.name):
        if cmd.name in SKIP:
            skipped.append(cmd.name)
            continue
        try:
            if not callable(cmd.callback):
                raise TypeError("not callable")
            ok.append(cmd.name)
        except Exception as e:
            failed.append(f"{cmd.name}: {e.__class__.__name__}")
    lines = ["CHECKALL", "", f"OK        {len(ok)}", f"Failed    {len(failed)}", f"Skipped   {len(skipped)}", ""]
    if failed:
        lines.append("FAILED")
        lines.extend(f"- {item}" for item in failed)
    else:
        lines.append("No command failed.")
    lines.append("")
    lines.append("Fast check. Use .command ... to test one.")
    return "```\n" + "\n".join(lines) + "\n```"

@bot.tree.command(name="checkall", description="[Owner] Quietly test commands")
async def checkall_slash(interaction: discord.Interaction):
    if not await interaction.client.is_owner(interaction.user):
        await interaction.response.send_message("Owner only.", ephemeral=True)
        return
    await interaction.response.send_message(build_checkall_report(), ephemeral=True)

@bot.command(name="checkall")
@commands.is_owner()
async def checkall_prefix(ctx: commands.Context):
    await ctx.reply(build_checkall_report(), mention_author=False)
