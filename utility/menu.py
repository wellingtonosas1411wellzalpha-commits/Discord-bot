from core import *

@bot.tree.command(name="menu", description="Show all bot commands")
async def menu(interaction: discord.Interaction):
    await interaction.response.send_message(build_menu_text())


@bot.command(name="menu")
async def menu_prefix(ctx: commands.Context):
    await ctx.reply(build_menu_text())

def build_updateinfo_text() -> str:
    info = LATEST_UPDATE_INFO
    lines = [
        "╭━━━〔 🆕 Latest Update 〕━━━⬣",
        "┃",
        f"┃ Version: **{info['version']}**",
        f"┃ Date: {info['date']}",
        "┃",
        "┃ What's new:",
    ]
    for change in info["changes"]:
        lines.append(f"┃ • {change}")
    lines.append("┃")
    lines.append("┃ Full log: `.versions`")
    lines.append("╰━━━━━━━━━━━━━━━━━━━━━━⬣")
    return "\n".join(lines)

def build_version_history_text() -> str:
    """Discord caps a single message at 2000 characters. As VERSION_HISTORY
    grows, showing every entry eventually exceeds that and the send fails
    outright (looks like 'the application did not respond'). So this shows
    as many of the most recent entries as fit, oldest-first is not
    preserved — newest first, truncate once we're near the limit."""
    CHAR_BUDGET = 1900  # leave headroom under Discord's 2000 cap
    header = [
        "╭━━━〔 📜 Version History 〕━━━⬣",
        f"┃ Current: **{BOT_VERSION}**",
        "┃",
    ]
    footer_template = "╰━━━━━━━━━━━━━━━━━━━━━━⬣"
    used = sum(len(l) + 1 for l in header) + len(footer_template) + 1

    body_lines = []
    shown = 0
    for entry in VERSION_HISTORY:
        entry_lines = [f"┃ **v{entry['version']}** — {entry['date']}"]
        for change in entry["changes"]:
            entry_lines.append(f"┃  • {change}")
        entry_lines.append("┃")
        entry_len = sum(len(l) + 1 for l in entry_lines)
        if used + entry_len > CHAR_BUDGET:
            break
        body_lines.extend(entry_lines)
        used += entry_len
        shown += 1

    omitted = len(VERSION_HISTORY) - shown
    lines = header + body_lines
    if omitted > 0:
        lines.append(f"┃ …and {omitted} older update(s) not shown here.")
        lines.append("┃")
    lines.append(footer_template)
    return "\n".join(lines)

