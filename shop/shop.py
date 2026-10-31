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

def handle_buy(user_id: int, guild_id: int, item_name: str, amount: int = 1):
    key = resolve_item_key(item_name)
    if key:
        return buy_global_item(user_id, key, amount) + (None,)
    try:
        item_id = int(item_name)
    except ValueError:
        return False, "❌ Unknown item. Use `.shop` to see names and IDs.", None
    return buy_shop_item(user_id, guild_id, item_id, amount)

def parse_buy_args(raw: str):
    """Split '.buy vx 3' into (item_name, amount)."""
    parts = raw.strip().split()
    if not parts:
        return "", 1
    if len(parts) >= 2 and parts[-1].isdigit():
        return " ".join(parts[:-1]), max(1, int(parts[-1]))
    return raw.strip(), 1

