from core import *

@bot.tree.command(name="collectpet", description="Collect the coins your pet has earned")
async def collectpet(interaction: discord.Interaction):
    await interaction.response.send_message(collect_pet_income(did(interaction.user.id)))


@bot.command(name="collectpet")
async def collectpet_prefix(ctx: commands.Context):
    await ctx.reply(collect_pet_income(did(ctx.author.id)))

