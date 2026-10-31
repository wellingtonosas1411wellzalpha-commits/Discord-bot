from core import *

@bot.tree.command(name="roulette", description="Bet on roulette (red, black, or green)")
@app_commands.describe(color="red, black, or green", amount="Amount to bet")
async def roulette(interaction: discord.Interaction, color: str, amount: str):
    async def send_func(text):
        await interaction.response.send_message(text)
        return await interaction.original_response()

    async def edit_func(message, text):
        await interaction.edit_original_response(content=text)

    await run_roulette(did(interaction.user.id), color, amount, send_func, edit_func)


@bot.command(name="roulette")
async def roulette_prefix(ctx: commands.Context, color: str, amount: str):
    async def send_func(text):
        return await ctx.reply(text)

    async def edit_func(message, text):
        await message.edit(content=text)

    await run_roulette(did(ctx.author.id), color, amount, send_func, edit_func)

