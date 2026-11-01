from core import *

@bot.tree.command(name="shop", description="Open the shop — pick an item and how many to buy")
@app_commands.describe(item="Item to buy", amount="How many to buy")
@app_commands.choices(item=SHOP_ITEM_CHOICES)
async def shop(
    interaction: discord.Interaction,
    item: app_commands.Choice[str] = None,
    amount: app_commands.Range[int, 1, 99] = 1,
):
    if interaction.guild is None:
        await interaction.response.send_message("❌ Use this command in a server.")
        return
    if item is None:
        await interaction.response.send_message(build_shop_text(interaction.guild.id))
        return
    await apply_shop_purchase(
        interaction.response.send_message,
        interaction.user,
        interaction.guild,
        item.value,
        amount,
    )


@bot.command(name="shop")
async def shop_prefix(ctx: commands.Context):
    if ctx.guild is None:
        await ctx.reply("❌ Use this command in a server.")
        return
    await ctx.reply(build_shop_text(ctx.guild.id))
