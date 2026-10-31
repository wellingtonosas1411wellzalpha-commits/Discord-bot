from core import *

@bot.tree.command(name="pet", description="See your (or someone else's) pet")
@app_commands.describe(user="The user to check (leave blank for yourself)")
async def pet(interaction: discord.Interaction, user: discord.User = None):
    target = user or interaction.user
    await interaction.response.send_message(build_pet_text(target.display_name, did(target.id)))


@bot.command(name="pet")
async def pet_prefix(ctx: commands.Context, user: discord.User = None):
    target = user or ctx.author
    await ctx.reply(build_pet_text(target.display_name, did(target.id)))

# ---------- Marriage commands ----------

