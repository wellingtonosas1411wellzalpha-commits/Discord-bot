from core import *

@bot.tree.command(name="feedpet", description="Feed your pet")
async def feedpet(interaction: discord.Interaction):
    await interaction.response.send_message(feed_pet(did(interaction.user.id)))


@bot.command(name="feedpet")
async def feedpet_prefix(ctx: commands.Context):
    await ctx.reply(feed_pet(did(ctx.author.id)))

