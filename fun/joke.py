from core import *

@bot.tree.command(name="joke", description="Get a random joke")
async def joke(interaction: discord.Interaction):
    await interaction.response.send_message(f"😄 {get_joke()}")


@bot.command(name="joke")
async def joke_prefix(ctx: commands.Context):
    await ctx.reply(f"😄 {get_joke()}")
