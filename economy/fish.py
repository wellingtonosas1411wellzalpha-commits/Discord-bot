from core import *

@bot.tree.command(name="fish", description="Go fishing for coins")
async def fish(interaction: discord.Interaction):
    await interaction.response.send_message(do_fish(did(interaction.user.id)))


@bot.command(name="fish")
async def fish_prefix(ctx: commands.Context):
    await ctx.reply(do_fish(did(ctx.author.id)))

