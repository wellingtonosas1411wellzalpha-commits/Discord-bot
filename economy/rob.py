from core import *

@bot.tree.command(name="rob", description="Attempt to rob another user")
@app_commands.describe(user="The user to rob")
async def rob(interaction: discord.Interaction, user: discord.User):
    await interaction.response.send_message(do_rob(did(interaction.user.id), did(user.id)))


@bot.command(name="rob")
async def rob_prefix(ctx: commands.Context, user: discord.User):
    await ctx.reply(do_rob(did(ctx.author.id), did(user.id)))

SHOP_ITEM_CHOICES = [
    app_commands.Choice(name="Vx — 100,000 coins", value="vx"),
    app_commands.Choice(name="V9 — 200,000 coins", value="v9"),
    app_commands.Choice(name="Lucky Potion — 500,000 coins", value="lucky"),
    app_commands.Choice(name="Gun — 1,000 coins", value="gun"),
    app_commands.Choice(name="Fishing Rod — 1,000 coins", value="fishing_rod"),
    app_commands.Choice(name="Shovel — 1,000 coins", value="shovel"),
    app_commands.Choice(name="Guard — 50,000 coins", value="guard"),
]

async def apply_shop_purchase(send_func, user, guild, item_name: str, amount: int = 1):
    success, message, role_id = handle_buy(did(user.id), guild.id, item_name, amount)
    if success and role_id is not None and isinstance(user, discord.Member):
        role = guild.get_role(role_id)
        if role is not None:
            try:
                await user.add_roles(role, reason="Shop purchase")
                message += f"\n🏅 The **{role.name}** role has been added to you."
            except discord.Forbidden:
                message += "\n⚠️ Couldn't assign the role — check my role permissions."
    await send_func(message)

