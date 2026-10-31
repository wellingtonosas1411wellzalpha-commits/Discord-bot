from core import *

@bot.tree.command(name="buylisting", description="Buy a listing from the player market")
@app_commands.describe(listing_id="The listing ID (see .market)")
async def buylisting(interaction: discord.Interaction, listing_id: str):
    await interaction.response.send_message(buy_listing(did(interaction.user.id), listing_id))


@bot.command(name="buylisting")
async def buylisting_prefix(ctx: commands.Context, listing_id: str):
    await ctx.reply(buy_listing(did(ctx.author.id), listing_id))

