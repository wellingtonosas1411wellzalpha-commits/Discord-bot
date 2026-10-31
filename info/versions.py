from core import *

@bot.tree.command(name="versions", description="See the full version history log")
async def versions(interaction: discord.Interaction):
    await interaction.response.send_message(build_version_history_text())


@bot.command(name="versions", aliases=["versionhistory", "history"])
async def versions_prefix(ctx: commands.Context):
    await ctx.reply(build_version_history_text())

# ---------- Gambling ----------

async def run_coinflip(user_id: int, side: str, amount_str: str):
    side = side.lower()
    if side not in ("heads", "tails"):
        return "❌ Choose `heads` or `tails`."
    bal = get_balance(user_id)
    try:
        amount = parse_amount(amount_str, all_value=bal["wallet"])
    except ValueError:
        return "❌ Invalid amount."
    if amount <= 0:
        return "❌ Enter an amount greater than $0."
    if amount > bal["wallet"]:
        return "❌ You don't have that much in your wallet."

    remaining = check_cooldown(cf_cooldowns, user_id, CF_COOLDOWN_SECONDS)
    if remaining is not None:
        return f"⏳ Slow down! Try again in {int(remaining) + 1}s."

    adjust_balance(user_id, wallet_delta=-amount)
    won = random.random() < luck_chance(0.5, user_id)
    result = side if won else ("tails" if side == "heads" else "heads")
    result_display = "HEADS 🦅" if result == "heads" else "TAILS 🪙"

    if won:
        payout = amount * 2
        new_bal = get_balance(user_id)
        adjust_balance(user_id, wallet_delta=payout)
        final_bal = get_balance(user_id)
        return (
            "🪙 *COINFLIP* 🪙\n"
            "━━━━━━━━━━━━━━\n"
            f"The coin landed on: *{result_display}*\n"
            "━━━━━━━━━━━━━━\n"
            "🎉 *YOU WON!* 🎉\n"
            f"Payout: *${payout:,}*\n\n"
            f"💵 Wallet: ${final_bal['wallet']:,}"
        )
    else:
        house_take(amount)
        final_bal = get_balance(user_id)
        return (
            "🪙 *COINFLIP* 🪙\n"
            "━━━━━━━━━━━━━━\n"
            f"The coin landed on: *{result_display}*\n"
            "━━━━━━━━━━━━━━\n"
            "💥 *YOU LOST!* 💥\n"
            "Better luck next time.\n\n"
            f"💵 Wallet: ${final_bal['wallet']:,}"
        )

