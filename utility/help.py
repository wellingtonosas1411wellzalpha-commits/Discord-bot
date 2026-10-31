from core import *

@bot.tree.command(name="help", description="Show help for one command")
@app_commands.describe(command="Command name")
async def help_slash(interaction: discord.Interaction, command: str):
    await interaction.response.send_message(build_help_text(command))


@bot.command(name="help")
async def help_prefix(ctx: commands.Context, *, command: str = ""):
    if not command.strip():
        await ctx.reply("Usage: `.help <command>`\nExample: `.help fish`\nOr use `.menu` for the list.")
        return
    await ctx.reply(build_help_text(command))

