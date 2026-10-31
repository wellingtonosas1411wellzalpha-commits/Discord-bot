from core import *

@bot.tree.command(name="inventory", description="See your (or someone else's) items")
@app_commands.describe(user="The user to check (leave blank for yourself)")
async def inventory(interaction: discord.Interaction, user: discord.User = None):
    target = user or interaction.user
    await interaction.response.send_message(build_inventory_text(target.display_name, did(target.id)))


@bot.command(name="inventory", aliases=["inv"])
async def inventory_prefix(ctx: commands.Context, user: discord.User = None):
    target = user or ctx.author
    await ctx.reply(build_inventory_text(target.display_name, did(target.id)))

