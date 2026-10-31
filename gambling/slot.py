from core import *

@bot.tree.command(name="slot", description="Play the slot machine")
@app_commands.describe(amount="Amount to bet, or 'all'")
async def slot(interaction: discord.Interaction, amount: str):
    async def send_func(text):
        await interaction.response.send_message(text)
        return await interaction.original_response()

    async def edit_func(message, text):
        await interaction.edit_original_response(content=text)

    await run_slot(did(interaction.user.id), amount, send_func, edit_func)


@bot.command(name="slot")
async def slot_prefix(ctx: commands.Context, amount: str):
    async def send_func(text):
        return await ctx.reply(text)

    async def edit_func(message, text):
        await message.edit(content=text)

    await run_slot(did(ctx.author.id), amount, send_func, edit_func)

