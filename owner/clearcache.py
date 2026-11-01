from core import *

@bot.tree.command(name="clearcache", description="[Owner only] Clear the bot's cache and free up memory")
async def clearcache(interaction: discord.Interaction):
    if not await interaction.client.is_owner(interaction.user):
        await interaction.response.send_message("❌ Only the bot owner can use this command.", ephemeral=True)
        return
    await interaction.response.send_message(do_clearcache())


@bot.command(name="clearcache")
@commands.is_owner()
async def clearcache_prefix(ctx: commands.Context):
    await ctx.reply(do_clearcache())
