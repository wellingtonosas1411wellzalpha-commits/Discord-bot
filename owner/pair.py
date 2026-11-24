from core import *
from whatsapp_door import request_pair

def clean_phone(value: str) -> str:
    return "".join(ch for ch in value if ch.isdigit())

def save_owner_number(number: str):
    owners = json.loads(get_meta("wa_owner_numbers") or "[]")
    if number not in owners:
        owners.append(number)
        set_meta("wa_owner_numbers", json.dumps(owners))

@bot.tree.command(name="pair", description="[Owner] Make a WhatsApp pairing code only you can see")
@app_commands.describe(phone="Bot WhatsApp number", owner_number="Number that can use owner commands")
async def pair_slash(interaction: discord.Interaction, phone: str, owner_number: str):
    if not await interaction.client.is_owner(interaction.user):
        await interaction.response.send_message("Owner only.", ephemeral=True)
        return
    bot_number = clean_phone(phone)
    owner = clean_phone(owner_number)
    if not bot_number or not owner:
        await interaction.response.send_message("Put the bot number and the owner number.", ephemeral=True)
        return
    await interaction.response.defer(ephemeral=True)
    save_owner_number(owner)
    code, err = await asyncio.to_thread(request_pair, bot_number)
    if not code:
        await interaction.followup.send(f"Could not make a code.\n{err or 'No reply from WhatsApp door.'}", ephemeral=True)
        return
    await interaction.followup.send(
        f"Pairing code: `{code}`\n"
        f"Owner number: `{owner}`\n"
        "Enter it now with no dash. It expires in about a minute.\n"
        "WhatsApp → Linked devices → Link a device → Link with phone number.",
        ephemeral=True,
    )

@bot.command(name="pair")
@commands.is_owner()
async def pair_prefix(ctx: commands.Context, phone: str, owner_number: str):
    bot_number = clean_phone(phone)
    owner = clean_phone(owner_number)
    if not bot_number or not owner:
        await ctx.author.send("Usage: .pair <bot number> <owner number>")
        return
    save_owner_number(owner)
    code, err = await asyncio.to_thread(request_pair, bot_number)
    try:
        await ctx.message.delete()
    except Exception:
        pass
    if not code:
        await ctx.author.send(f"Could not make a code.\n{err or 'No reply from WhatsApp door.'}")
        return
    await ctx.author.send(
        f"Pairing code: `{code}`\n"
        f"Owner number: `{owner}`\n"
        "Enter it now with no dash. It expires in about a minute.\n"
        "WhatsApp → Linked devices → Link a device → Link with phone number."
    )
