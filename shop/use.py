from core import *

@bot.tree.command(name="use", description="Use a consumable item (vx, v9, lucky)")
@app_commands.describe(item="vx, v9, or lucky")
async def use_item(interaction: discord.Interaction, item: str):
    key = resolve_item_key(item)
    if not key:
        await interaction.response.send_message("❌ Use `.use vx`, `.use v9`, or `.use lucky`.")
        return
    await interaction.response.send_message(use_global_item(did(interaction.user.id), key))


@bot.command(name="use")
async def use_item_prefix(ctx: commands.Context, *, item: str):
    key = resolve_item_key(item)
    if not key:
        await ctx.reply("❌ Use `.use vx`, `.use v9`, or `.use lucky`.")
        return
    await ctx.reply(use_global_item(did(ctx.author.id), key))

