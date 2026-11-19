from core import *

def link_text(user_id, code):
    return (
        f"Your Discord ID: `{user_id}`\n"
        f"On Telegram or WhatsApp, send `.link {code}`\n"
        "After that, Discord, Telegram, and WhatsApp share money and stats."
    )

@bot.tree.command(name="link", description="Link this Discord account to Telegram or WhatsApp")
async def link_slash(interaction: discord.Interaction):
    code = make_link_code(did(interaction.user.id))
    await interaction.response.send_message(link_text(interaction.user.id, code), ephemeral=True)

@bot.command(name="link")
async def link_prefix(ctx: commands.Context):
    code = make_link_code(did(ctx.author.id))
    await ctx.reply(link_text(ctx.author.id, code), mention_author=False)
