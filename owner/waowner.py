from core import *

@bot.command(name="waowner")
@commands.is_owner()
async def waowner_prefix(ctx: commands.Context, number: str):
    digits = clean_wa(number)
    owners = list(wa_owner_numbers())
    if digits not in owners:
        owners.append(digits)
        set_meta("wa_owner_numbers", json.dumps(owners))
    await ctx.reply(f"WhatsApp owner saved: `{digits}`", mention_author=False)

@bot.tree.command(name="waowner", description="[Owner] Allow a WhatsApp number to use owner commands")
@app_commands.describe(number="WhatsApp number with country code")
async def waowner_slash(interaction: discord.Interaction, number: str):
    if not await interaction.client.is_owner(interaction.user):
        await interaction.response.send_message("Owner only.", ephemeral=True)
        return
    digits = clean_wa(number)
    owners = list(wa_owner_numbers())
    if digits not in owners:
        owners.append(digits)
        set_meta("wa_owner_numbers", json.dumps(owners))
    await interaction.response.send_message(f"WhatsApp owner saved: `{digits}`", ephemeral=True)
