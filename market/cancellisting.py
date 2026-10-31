from core import *

@bot.tree.command(name="cancellisting", description="Cancel your own market listing")
@app_commands.describe(listing_id="The listing ID to cancel")
async def cancellisting(interaction: discord.Interaction, listing_id: str):
    await interaction.response.send_message(cancel_listing(did(interaction.user.id), listing_id))


@bot.command(name="cancellisting")
async def cancellisting_prefix(ctx: commands.Context, listing_id: str):
    await ctx.reply(cancel_listing(did(ctx.author.id), listing_id))

