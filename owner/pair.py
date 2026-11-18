from core import *
from whatsapp_door import request_pair

@bot.tree.command(name="pair", description="[Owner] Make a fresh WhatsApp pairing code")
@app_commands.describe(phone="Phone number with country code, no plus")
async def pair_slash(interaction: discord.Interaction, phone: str):
    if not await interaction.client.is_owner(interaction.user):
        await interaction.response.send_message("Owner only.", ephemeral=True)
        return
    digits = "".join(ch for ch in phone if ch.isdigit())
    await interaction.response.defer()
    code = await asyncio.to_thread(request_pair, digits)
    if not code:
        await interaction.followup.send("Could not make a code. Wait a few seconds and try again.")
        return
    await interaction.followup.send(
        f"{interaction.user.mention} Pairing code: `{code}`\n"
        "Enter it now. It expires in about a minute.\n"
        "WhatsApp → Linked devices → Link with phone number."
    )

@bot.command(name="pair")
@commands.is_owner()
async def pair_prefix(ctx: commands.Context, phone: str):
    digits = "".join(ch for ch in phone if ch.isdigit())
    await ctx.reply("Making a fresh code...", mention_author=False)
    code = await asyncio.to_thread(request_pair, digits)
    if not code:
        await ctx.reply("Could not make a code. Wait a few seconds and try again.")
        return
    await ctx.reply(
        f"{ctx.author.mention} Pairing code: `{code}`\n"
        "Enter it now. It expires in about a minute.\n"
        "WhatsApp → Linked devices → Link with phone number.",
        mention_author=True,
    )
