from core import *

@bot.tree.command(name="translate", description="Translate text into another language")
@app_commands.describe(language="Target language (e.g. Spanish, French, Yoruba)", text="Text to translate")
async def translate(interaction: discord.Interaction, language: str, text: str):
    await interaction.response.defer()
    translated = await translate_text(language, text)
    await interaction.followup.send(build_translate_response(language, translated))


@bot.command(name="translate")
async def translate_prefix(ctx: commands.Context, language: str, *, text: str = ""):
    if not text.strip():
        await ctx.reply("❌ Usage: `.translate <language> <text>`")
        return
    async with ctx.typing():
        translated = await translate_text(language, text)
        await ctx.reply(build_translate_response(language, translated))


@bot.tree.context_menu(name="Translate to English")
async def translate_context_menu(interaction: discord.Interaction, message: discord.Message):
    if not message.content:
        await interaction.response.send_message("❌ That message has no text to translate.", ephemeral=True)
        return
    await interaction.response.defer(ephemeral=True)
    translated = await translate_text("English", message.content)
    await interaction.followup.send(build_translate_response("English", translated), ephemeral=True)

