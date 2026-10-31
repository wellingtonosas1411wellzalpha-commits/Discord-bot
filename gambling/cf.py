from core import *

@bot.tree.command(name="cf", description="Bet on a coinflip")
@app_commands.describe(side="heads or tails", amount="Amount to bet")
async def cf(interaction: discord.Interaction, side: str, amount: str):
    await interaction.response.send_message(await run_coinflip(did(interaction.user.id), side, amount))


@bot.command(name="cf", aliases=["coinflip"])
async def cf_prefix(ctx: commands.Context, side: str, amount: str):
    await ctx.reply(await run_coinflip(did(ctx.author.id), side, amount))

def build_roulette_spinning_text(bet_display: str, color_choice: str):
    return (
        "🎡 *ROULETTE WHEEL* 🎡\n"
        "━━━━━━━━━━━━━━\n"
        f"Bet: *{bet_display}* on *{color_choice.upper()}*\n\n"
        "🔄 Spinning the wheel..."
    )

def build_roulette_result_text(number, color_display, won, payout, wallet):
    header = (
        "🎡 *ROULETTE WHEEL* 🎡\n"
        "━━━━━━━━━━━━━━\n"
        f"The ball landed on: *{number} {color_display}*\n"
        "━━━━━━━━━━━━━━\n"
    )
    if won:
        return header + (
            "🎉 *YOU WON!* 🎉\n"
            f"Payout: *${payout:,}*\n\n"
            f"💵 Wallet: ${wallet:,}"
        )
    else:
        return header + (
            "💥 *YOU LOST!* 💥\n"
            "Better luck next time.\n\n"
            f"💵 Wallet: ${wallet:,}"
        )

ROULETTE_MULTIPLIER = {"red": 3, "black": 3, "green": 14}

async def run_roulette(user_id: int, color_choice: str, amount_str: str, send_func, edit_func):
    color_choice = color_choice.lower()
    if color_choice not in ("red", "black", "green"):
        return await send_func("❌ Choose `red`, `black`, or `green`.")
    bal = get_balance(user_id)
    try:
        amount = parse_amount(amount_str, all_value=bal["wallet"])
    except ValueError:
        return await send_func("❌ Invalid amount.")
    if amount <= 0:
        return await send_func("❌ Enter an amount greater than $0.")
    if amount > bal["wallet"]:
        return await send_func("❌ You don't have that much in your wallet.")

    remaining = check_cooldown(roulette_cooldowns, user_id, ROULETTE_COOLDOWN_SECONDS)
    if remaining is not None:
        return await send_func(f"⏳ Slow down! Try again in {int(remaining) + 1}s.")

    adjust_balance(user_id, wallet_delta=-amount)
    sent = await send_func(build_roulette_spinning_text(f"${amount:,}", color_choice))

    await asyncio.sleep(5)

    base = (1 / 37) if color_choice == "green" else (18 / 37)
    won = random.random() < luck_chance(base, user_id)
    number, color, color_display = do_roulette_spin()
    if won and color != color_choice:
        for _ in range(50):
            number, color, color_display = do_roulette_spin()
            if color == color_choice:
                break
    if not won and color == color_choice:
        for _ in range(50):
            number, color, color_display = do_roulette_spin()
            if color != color_choice:
                break
    if won:
        payout = amount * ROULETTE_MULTIPLIER[color_choice]
        new_bal = get_balance(user_id)
        adjust_balance(user_id, wallet_delta=payout)
    else:
        payout = 0
        house_take(amount)
    final_bal = get_balance(user_id)

    result_text = build_roulette_result_text(number, color_display, won, payout, final_bal["wallet"])
    await edit_func(sent, result_text)

