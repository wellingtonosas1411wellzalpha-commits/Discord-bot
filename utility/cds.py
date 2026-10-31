from core import *

@bot.command(name="cds", aliases=["cooldowns"])
async def cds_prefix(ctx: commands.Context):
    await ctx.reply(build_cooldowns_text(did(ctx.author.id)))

