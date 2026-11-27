from core import *

def save_wa_owner(value: str) -> str:
    digits = clean_wa(value)
    if not digits:
        return ""
    owners = list(wa_owner_numbers())
    if digits not in owners:
        owners.append(digits)
        set_meta("wa_owner_numbers", json.dumps(owners))
    return digits

@bot.command(name="waowner")
@commands.is_owner()
async def waowner_prefix(ctx: commands.Context, value: str):
    digits = save_wa_owner(value)
    if not digits:
        await ctx.reply("Send a WhatsApp ID or number. Example: `.waowner 78735894134972`", mention_author=False)
        return
    await ctx.reply(f"WhatsApp owner saved: `{digits}`", mention_author=False)

@bot.tree.command(name="waowner", description="[Owner] Allow a WhatsApp ID or number to use owner commands")
@app_commands.describe(value="WhatsApp ID or phone number")
async def waowner_slash(interaction: discord.Interaction, value: str):
    if not await interaction.client.is_owner(interaction.user):
        await interaction.response.send_message("Owner only.", ephemeral=True)
        return
    digits = save_wa_owner(value)
    if not digits:
        await interaction.response.send_message("Send a WhatsApp ID or number.", ephemeral=True)
        return
    await interaction.response.send_message(f"WhatsApp owner saved: `{digits}`", ephemeral=True)
