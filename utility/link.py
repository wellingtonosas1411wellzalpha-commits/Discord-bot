from core import *

@bot.tree.command(name="link", description="Link this Discord account to Telegram")
async def link_slash(interaction: discord.Interaction):
    code = make_link_code(did(interaction.user.id))
    await interaction.response.send_message(
        f"Your Discord ID: `{interaction.user.id}`\n"
        f"On Telegram, send `.link {code}`\n"
        "After that, Discord and Telegram share money and stats.",
        ephemeral=True,
    )

@bot.command(name="link")
async def link_prefix(ctx: commands.Context):
    code = make_link_code(did(ctx.author.id))
    await ctx.reply(
        f"Your Discord ID: `{ctx.author.id}`\n"
        f"On Telegram, send `.link {code}`\n"
        "After that, Discord and Telegram share money and stats.",
        mention_author=False,
    )
