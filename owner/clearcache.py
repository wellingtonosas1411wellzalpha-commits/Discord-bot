from core import *

@bot.tree.command(name="clearcache", description="[Admin] Clear the bot's cache and free up memory")
async def clearcache(interaction: discord.Interaction):
    if not is_kira_creator(interaction.user):
        await interaction.response.send_message("❌ Admins only.", ephemeral=True)
        return
    await interaction.response.send_message(do_clearcache())


@bot.command(name="clearcache")
async def clearcache_prefix(ctx: commands.Context):
    if not is_kira_creator(ctx.author):
        await ctx.reply('❌ Admins only.', mention_author=False)
        return
    await ctx.reply(do_clearcache())
