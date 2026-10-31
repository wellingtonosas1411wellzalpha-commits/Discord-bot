from core import *

@bot.tree.command(name="clearcache", description="[Owner only] Clear the bot's cache and free up memory")
async def clearcache(interaction: discord.Interaction):
    if not await interaction.client.is_owner(interaction.user):
        await interaction.response.send_message("❌ Only the bot owner can use this command.", ephemeral=True)
        return
    await interaction.response.send_message(do_clearcache())


@bot.command(name="clearcache")
@commands.is_owner()
async def clearcache_prefix(ctx: commands.Context):
    await ctx.reply(do_clearcache())

def do_reset(user_id, clear_xp: bool = False):
    update_balance(user_id, wallet=DEFAULT_WALLET, bank=DEFAULT_BANK)
    set_user_effects(user_id, lucky_stacks=0, cd_boost_until=None)
    conn, cur = get_db()
    cur.execute("DELETE FROM inventory WHERE user_id = %s", (user_id,))
    cur.execute("DELETE FROM global_inventory WHERE user_id = %s", (user_id,))
    cur.execute("DELETE FROM pets WHERE user_id = %s", (user_id,))
    cur.execute("DELETE FROM jobs WHERE user_id = %s", (user_id,))
    cur.execute("DELETE FROM marriages WHERE user_id = %s OR partner_id = %s", (user_id, user_id))
    cur.execute("DELETE FROM achievements WHERE user_id = %s", (user_id,))
    if clear_xp:
        cur.execute("DELETE FROM levels WHERE user_id = %s", (user_id,))
    cur.execute("DELETE FROM persistent_cooldowns WHERE user_id = %s", (user_id,))
    cur.execute("DELETE FROM loans WHERE user_id = %s", (user_id,))
    cur.execute("DELETE FROM market_listings WHERE seller_id = %s", (user_id,))
    cur.execute("DELETE FROM afk WHERE user_id = %s", (user_id,))
    cur.execute(
        "UPDATE user_effects SET kiragpt_reply_count = 0, lucky_stacks = 0, cd_boost_until = NULL WHERE user_id = %s",
        (user_id,),
    )
    conn.commit()
    cur.close()
    release_db(conn)
    set_meta(f"test_mode:{user_id}", "off")
    set_meta(f"test_snapshot:{user_id}", "")
    return (
        "🔄 Reset complete.\n"
        f"Wallet: **${DEFAULT_WALLET:,}**\n"
        f"Bank: **${DEFAULT_BANK:,}**\n"
        "Items, pet, job, marriage, cooldowns, loans, and lucky stacks were cleared.\n"
        + ("XP and level were cleared." if clear_xp else "XP was kept. Use `.reset all` to clear XP too.")
    )

TEST_WALLET = 999_999_999_999_999

def has_tester_role(member) -> bool:
    if not isinstance(member, discord.Member):
        return False
    names = {role.name.lower().strip() for role in member.roles}
    return "tester" in names

def snapshot_test_state(user_id):
    bal = get_balance(user_id)
    conn, cur = get_db()
    cur.execute("SELECT item_key, quantity FROM global_inventory WHERE user_id = %s", (user_id,))
    global_items = cur.fetchall()
    cur.execute("SELECT item_id, quantity FROM inventory WHERE user_id = %s", (user_id,))
    custom_items = cur.fetchall()
    cur.execute("SELECT pet_type, pet_name, hunger FROM pets WHERE user_id = %s", (user_id,))
    pets = cur.fetchall()
    cur.close()
    release_db(conn)
    effects = get_user_effects(user_id)
    return {
        "wallet": bal["wallet"],
        "bank": bal["bank"],
        "global_items": [[k, q] for k, q in global_items],
        "custom_items": [[i, q] for i, q in custom_items],
        "pets": [[ptype, pname, hunger] for ptype, pname, hunger in pets],
        "lucky_stacks": effects["lucky_stacks"],
        "cd_boost_until": effects["cd_boost_until"] if isinstance(effects["cd_boost_until"], (int, float)) else (
            effects["cd_boost_until"].isoformat() if effects["cd_boost_until"] else None
        ),
    }

def restore_test_state(user_id, snap):
    update_balance(user_id, wallet=snap["wallet"], bank=snap["bank"])
    conn, cur = get_db()
    cur.execute("DELETE FROM global_inventory WHERE user_id = %s", (user_id,))
    for key, qty in snap.get("global_items", []):
        cur.execute(
            "INSERT INTO global_inventory (user_id, item_key, quantity) VALUES (%s, %s, %s)",
            (user_id, key, qty),
        )
    cur.execute("DELETE FROM inventory WHERE user_id = %s", (user_id,))
    for item_id, qty in snap.get("custom_items", []):
        cur.execute(
            "INSERT INTO inventory (user_id, item_id, quantity) VALUES (%s, %s, %s)",
            (user_id, item_id, qty),
        )
    cur.execute("DELETE FROM pets WHERE user_id = %s", (user_id,))
    for pet_type, pet_name, hunger in snap.get("pets", []):
        cur.execute(
            "INSERT INTO pets (user_id, pet_type, pet_name, hunger) VALUES (%s, %s, %s, %s)",
            (user_id, pet_type, pet_name, hunger),
        )
    conn.commit()
    cur.close()
    release_db(conn)
    until = snap.get("cd_boost_until")
    set_user_effects(
        user_id,
        lucky_stacks=snap.get("lucky_stacks", 0),
        cd_boost_until=until,
    )

def do_test(user_id, turn_on: bool):
    if turn_on:
        if test_mode_on(user_id):
            return "⚠️ Test mode is already **on**."
        snap = snapshot_test_state(user_id)
        set_meta(f"test_snapshot:{user_id}", json.dumps(snap))
        set_meta(f"test_mode:{user_id}", "on")
        update_balance(user_id, wallet=TEST_WALLET)
        return (
            "🧪 Test mode is **on**.\n"
            "You now have infinite test money and no item limits.\n"
            "It cannot be donated. When you turn it off, extra money, bet winnings, "
            "and items bought with test money disappear."
        )
    if not test_mode_on(user_id):
        return "❌ Test mode is already **off**."
    raw = get_meta(f"test_snapshot:{user_id}")
    if not raw:
        set_meta(f"test_mode:{user_id}", "off")
        return "❌ Test snapshot was missing. Test mode is now off."
    restore_test_state(user_id, json.loads(raw))
    set_meta(f"test_mode:{user_id}", "off")
    set_meta(f"test_snapshot:{user_id}", "")
    return "🧪 Test mode is **off**. Extra money and items bought with test money were removed."

