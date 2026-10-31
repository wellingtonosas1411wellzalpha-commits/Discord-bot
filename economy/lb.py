from core import *

@bot.tree.command(name="lb", description="Show the richest users")
async def lb(interaction: discord.Interaction):
    await interaction.response.send_message(build_leaderboard_text())


@bot.command(name="lb", aliases=["top", "leaderboard"])
async def lb_prefix(ctx: commands.Context):
    await ctx.reply(build_leaderboard_text())

def build_rank_text(user_id: int, display_name: str) -> str:
    data = get_level_data(user_id)
    needed = xp_for_level(data["level"])
    return (
        f"📊 **{display_name}**'s Rank\n"
        f"Level: **{data['level']}**\n"
        f"XP: **{data['xp']:,} / {needed:,}**"
    )

def build_ranklb_text() -> str:
    rows = get_xp_leaderboard()
    if not rows:
        return "No one has earned XP yet."
    lines = ["🎖️ **Level Leaderboard** 🎖️\n"]
    for i, (user_id, level, xp) in enumerate(rows, start=1):
        lines.append(f"**{i}.** <@{user_id}> — Level {level} ({xp:,} XP)")
    return "\n".join(lines)

