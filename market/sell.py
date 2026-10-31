from core import *

@bot.tree.command(name="sell", description="List an item for sale on the player market")
@app_commands.describe(item="Item name (vx, gun, shovel...)", quantity="How many to sell", price="Price per item")
async def sell(interaction: discord.Interaction, item: str, quantity: str, price: str):
    success, message = create_listing(did(interaction.user.id), item, quantity, price)
    await interaction.response.send_message(message)


@bot.command(name="sell")
async def sell_prefix(ctx: commands.Context, item: str, quantity: str, price: str):
    success, message = create_listing(did(ctx.author.id), item, quantity, price)
    await ctx.reply(message)

