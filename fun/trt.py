from core import *

@bot.command(name="trt")
async def translate_reply(ctx: commands.Context, *, language: str = ""):
    if not language.strip():
        await ctx.reply("❌ Reply to a message with `.trt <language>` to translate it.")
        return
    if not ctx.message.reference:
        await ctx.reply("❌ You need to reply to the message you want translated.")
        return
    try:
        replied = ctx.message.reference.resolved
        if replied is None or isinstance(replied, discord.DeletedReferencedMessage):
            replied = await ctx.channel.fetch_message(ctx.message.reference.message_id)
    except (discord.NotFound, discord.HTTPException):
        await ctx.reply("❌ Couldn't find the message you replied to.")
        return
    if not replied.content:
        await ctx.reply("❌ That message has no text to translate.")
        return
    async with ctx.typing():
        translated = await translate_text(language, replied.content)
        await ctx.reply(build_translate_response(language, translated))

