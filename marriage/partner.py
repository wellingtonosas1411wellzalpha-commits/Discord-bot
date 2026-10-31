from core import *

@bot.tree.command(name="partner", description="See who you're (or someone else is) married to")
@app_commands.describe(user="The user to check (leave blank for yourself)")
async def partner(interaction: discord.Interaction, user: discord.User = None):
    target = user or interaction.user
    partner_id = get_partner(did(target.id))
    if partner_id is None:
        await interaction.response.send_message(f"💔 **{target.display_name}** isn't married.")
        return
    await interaction.response.send_message(f"💍 **{target.display_name}** is married to <@{partner_id.split(':', 1)[-1]}>.")


@bot.command(name="partner")
async def partner_prefix(ctx: commands.Context, user: discord.Member = None):
    target = user or ctx.author
    partner_id = get_partner(did(target.id))
    if partner_id is None:
        await ctx.reply(f"💔 **{target.display_name}** isn't married.")
        return
    await ctx.reply(f"💍 **{target.display_name}** is married to <@{partner_id.split(':', 1)[-1]}>.")

# ---------- Achievements command ----------

