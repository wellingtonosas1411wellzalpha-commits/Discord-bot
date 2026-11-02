from core import *

def build_bans_text() -> str:
    lines = ["🚫 **Bans**"]
    if bot_bans:
        lines.append("**Bot banned:** " + ", ".join(f"<@{uid.split(':')[-1]}>" for uid in sorted(bot_bans)))
    else:
        lines.append("**Bot banned:** none")
    if x_bans:
        lines.append("**Category bans:**")
        for uid, cats in sorted(x_bans.items()):
            lines.append(f"<@{uid.split(':')[-1]}> — {', '.join(cats)}")
    else:
        lines.append("**Category bans:** none")
    return "\n".join(lines)

@bot.tree.command(name="bans", description="[Admin] Show command bans")
async def bans_slash(interaction: discord.Interaction):
    if not is_kira_creator(interaction.user):
        await interaction.response.send_message("❌ Admins only.", ephemeral=True)
        return
    await interaction.response.send_message(build_bans_text())

@bot.command(name="bans")
async def bans_prefix(ctx: commands.Context):
    if not is_kira_creator(ctx.author):
        await ctx.reply("❌ Admins only.", mention_author=False)
        return
    await ctx.reply(build_bans_text(), mention_author=False)
