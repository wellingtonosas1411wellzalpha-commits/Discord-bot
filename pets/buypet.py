from core import *

@bot.tree.command(name="buypet", description="Adopt a pet that earns passive income")
@app_commands.describe(pet_type="dog, cat, dragon, or hamster", name="Your pet's name")
async def buypet(interaction: discord.Interaction, pet_type: str, name: str):
    success, message = buy_pet(did(interaction.user.id), pet_type, name)
    await interaction.response.send_message(message)


@bot.command(name="buypet")
async def buypet_prefix(ctx: commands.Context, pet_type: str, *, name: str = ""):
    success, message = buy_pet(did(ctx.author.id), pet_type, name)
    await ctx.reply(message)

