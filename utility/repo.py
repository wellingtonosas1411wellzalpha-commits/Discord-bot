from core import *

REPO_URL = "https://github.com/wellingtonosas1411wellzalpha-commits/Discord-bot"

@bot.tree.command(name="repo", description="Show the GitHub repository")
async def repo(interaction: discord.Interaction):
    await interaction.response.send_message(f"🔗 {REPO_URL}")

@bot.command(name="repo")
async def repo_prefix(ctx: commands.Context):
    await ctx.reply(f"🔗 {REPO_URL}", mention_author=False)
