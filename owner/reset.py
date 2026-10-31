from core import *

@bot.tree.command(name="reset", description="[Owner only] Reset a player. XP stays unless all is true")
@app_commands.describe(user="Player to reset. Leave empty to reset yourself.", all="Also clear XP and level")
async def reset_cmd(interaction: discord.Interaction, user: discord.User = None, all: bool = False):
    if not await interaction.client.is_owner(interaction.user):
        await interaction.response.send_message("❌ Only the bot owner can use this command.", ephemeral=True)
        return
    target = user or interaction.user
    await interaction.response.send_message(f"{target.mention}\n" + do_reset(did(target.id), clear_xp=all))


@bot.command(name="reset")
@commands.is_owner()
async def reset_prefix(ctx: commands.Context, mode: str = None, user: discord.User = None):
    clear_xp = False
    target = ctx.author
    if isinstance(mode, str) and mode.lower() == "all":
        clear_xp = True
        target = user or ctx.author
    elif mode is not None:
        # .reset @user
        try:
            target = await commands.UserConverter().convert(ctx, mode)
        except Exception:
            await ctx.reply("❌ Use `.reset`, `.reset @user`, or `.reset all`.", mention_author=False)
            return
    await ctx.reply(f"{target.mention}\n" + do_reset(did(target.id), clear_xp=clear_xp), mention_author=False)

