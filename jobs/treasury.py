from core import *

@bot.tree.command(name="treasury", description="See the server treasury (funded by taxes)")
async def treasury(interaction: discord.Interaction):
    await interaction.response.send_message(
        f"🏛️ Server treasury: **${get_treasury():,}** (salary tax)\n"
        f"🏦 Bot bank: **${get_bot_bank():,}** (gambling losses + loan repayments)"
    )


@bot.command(name="treasury")
async def treasury_prefix(ctx: commands.Context):
    await ctx.reply(
        f"🏛️ Server treasury: **${get_treasury():,}** (salary tax)\n"
        f"🏦 Bot bank: **${get_bot_bank():,}** (gambling losses + loan repayments)"
    )

# ---------- Pet commands ----------

