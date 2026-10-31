from core import *

@bot.tree.command(name="buy", description="Buy an item from the shop")
@app_commands.describe(item="Pick an item or type a server item ID", amount="How many to buy")
@app_commands.choices(item=SHOP_ITEM_CHOICES)
async def buy(
    interaction: discord.Interaction,
    item: app_commands.Choice[str],
    amount: app_commands.Range[int, 1, 99] = 1,
):
    if interaction.guild is None:
        await interaction.response.send_message("❌ Use this command in a server.")
        return
    await apply_shop_purchase(
        interaction.response.send_message,
        interaction.user,
        interaction.guild,
        item.value,
        amount,
    )


@bot.command(name="buy")
async def buy_prefix(ctx: commands.Context, *, item: str):
    if ctx.guild is None:
        await ctx.reply("❌ Use this command in a server.")
        return
    item_name, amount = parse_buy_args(item)
    await apply_shop_purchase(ctx.reply, ctx.author, ctx.guild, item_name, amount)

