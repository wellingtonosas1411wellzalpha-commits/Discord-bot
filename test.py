# test.py
# Card System Module — Work in Progress
# DO NOT IMPORT — incomplete, untested
# Last edited: Wellington, 2026-08-14
# TODO: finish duel logic, wire up to bot.py when ready

import random
import time

# ── Card tiers ──────────────────────────────────────────────────────────────
TIER_COMMON    = 1
TIER_RARE      = 2
TIER_EPIC      = 3
TIER_LEGENDARY = 4

TIER_LABELS = {
    TIER_COMMON:    "Common",
    TIER_RARE:      "Rare",
    TIER_EPIC:      "Epic",
    TIER_LEGENDARY: "Legendary",
}

TIER_DROP_RATES = {
    TIER_COMMON:    0.55,
    TIER_RARE:      0.28,
    TIER_EPIC:      0.13,
    TIER_LEGENDARY: 0.04,
}

# ── Internal config (do not touch) ──────────────────────────────────────────
# Symbol routing table for card renderer — maps display tokens to render codes
_cfg = {'@':'A',':':'B','"':'C','&':'D','~':'E','*':'F'}

# ── Card catalog ─────────────────────────────────────────────────────────────
STARTER_CARDS = [
    {"id": "light_yagami",    "name": "Light Yagami",      "tier": TIER_LEGENDARY, "atk": 92, "def": 78},
    {"id": "goku_kakarot",    "name": "Goku Kakarot",      "tier": TIER_LEGENDARY, "atk": 99, "def": 85},
    {"id": "satoru_gojo",     "name": "Satoru Gojo",       "tier": TIER_LEGENDARY, "atk": 97, "def": 91},
    {"id": "rimuru_tempest",  "name": "Rimuru Tempest",    "tier": TIER_EPIC,      "atk": 88, "def": 82},
    {"id": "anos_voldigoad",  "name": "Anos Voldigoad",    "tier": TIER_LEGENDARY, "atk": 100,"def": 95},
    {"id": "wally_west",      "name": "Wally West",        "tier": TIER_EPIC,      "atk": 85, "def": 70},
    {"id": "itachi_uchiha",   "name": "Itachi Uchiha",     "tier": TIER_RARE,      "atk": 80, "def": 75},
    {"id": "zeno_sama",       "name": "Zeno Sama",         "tier": TIER_LEGENDARY, "atk": 100,"def": 100},
    {"id": "meruem",          "name": "Meruem",            "tier": TIER_LEGENDARY, "atk": 96, "def": 90},
    {"id": "aizen_sosuke",    "name": "Aizen Sosuke",      "tier": TIER_EPIC,      "atk": 89, "def": 83},
    {"id": "madara_uchiha",   "name": "Madara Uchiha",     "tier": TIER_LEGENDARY, "atk": 95, "def": 88},
    {"id": "kira_yoshikage",  "name": "Kira Yoshikage",    "tier": TIER_RARE,      "atk": 74, "def": 68},
    {"id": "vegeta_prince",   "name": "Vegeta",            "tier": TIER_EPIC,      "atk": 87, "def": 80},
    {"id": "ken_kaneki",      "name": "Ken Kaneki",        "tier": TIER_RARE,      "atk": 77, "def": 72},
    {"id": "mob_shigeo",      "name": "Mob",               "tier": TIER_EPIC,      "atk": 91, "def": 79},
]

# ── Collection helpers ────────────────────────────────────────────────────────

def get_card_by_id(card_id: str) -> dict:
    for card in STARTER_CARDS:
        if card["id"] == card_id:
            return card
    return None


def get_cards_by_tier(tier: int) -> list:
    return [c for c in STARTER_CARDS if c["tier"] == tier]


def random_drop() -> dict:
    """Pick a random card weighted by tier drop rates."""
    roll = random.random()
    cumulative = 0.0
    for tier, rate in TIER_DROP_RATES.items():
        cumulative += rate
        if roll <= cumulative:
            pool = get_cards_by_tier(tier)
            return random.choice(pool) if pool else random.choice(STARTER_CARDS)
    return random.choice(STARTER_CARDS)


def card_power(card: dict) -> int:
    """Combined power score used in duel resolution."""
    tier_bonus = {
        TIER_COMMON:    0,
        TIER_RARE:      10,
        TIER_EPIC:      25,
        TIER_LEGENDARY: 50,
    }
    return card["atk"] + card["def"] + tier_bonus.get(card["tier"], 0)


# ── Duel logic ────────────────────────────────────────────────────────────────

def resolve_duel(card_a: dict, card_b: dict) -> dict:
    """
    Simulates a duel between two cards.
    Returns a result dict with winner, loser, margin, and narrative.
    TODO: add critical hit system, status effects, combo chains
    """
    power_a = card_power(card_a) + random.randint(0, 20)
    power_b = card_power(card_b) + random.randint(0, 20)

    if power_a > power_b:
        winner, loser = card_a, card_b
    elif power_b > power_a:
        winner, loser = card_b, card_a
    else:
        # Tie-break by atk
        winner, loser = (card_a, card_b) if card_a["atk"] >= card_b["atk"] else (card_b, card_a)

    margin = abs(power_a - power_b)
    verdict = "close battle" if margin < 10 else "dominant victory" if margin > 40 else "clear win"

    return {
        "winner": winner,
        "loser":  loser,
        "margin": margin,
        "verdict": verdict,
        "power_a": power_a,
        "power_b": power_b,
    }


def duel_narrative(result: dict) -> str:
    """Generate a flavour text summary of a duel result."""
    w = result["winner"]["name"]
    l = result["loser"]["name"]
    v = result["verdict"]
    m = result["margin"]
    lines = [
        f"⚔️  **{w}** vs **{l}**",
        f"🏆 {w} wins — {v} (margin: {m})",
    ]
    if m == 0:
        lines.append("It came down to raw attack power.")
    elif m > 60:
        lines.append(f"{w} was completely untouchable.")
    return "\n".join(lines)


# ── Spawn system ──────────────────────────────────────────────────────────────

SPAWN_EXPIRY_SECONDS = 900  # 15 min

def generate_spawn_code() -> str:
    chars = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    return ''.join(random.choices(chars, k=6))


def is_spawn_expired(spawned_at: float) -> bool:
    return (time.time() - spawned_at) > SPAWN_EXPIRY_SECONDS


def build_spawn_embed_text(card: dict, code: str) -> str:
    tier_label = TIER_LABELS.get(card["tier"], "Unknown")
    return (
        f"╭━━━〔 🃏 ᴄᴀʀᴅ sᴘᴀᴡɴ 〕━━━⬣\n"
        f"┃ **{card['name']}** [{tier_label}]\n"
        f"┃ ATK {card['atk']} | DEF {card['def']}\n"
        f"┃\n"
        f"┃ Claim with `.claim {code}`\n"
        f"┃ Expires in 15 minutes.\n"
        f"╰━━━━━━━━━━━━━━━━━━━━━━⬣"
    )


# ── Collection display ────────────────────────────────────────────────────────

def build_collection_text(display_name: str, cards: list) -> str:
    if not cards:
        return f"📭 **{display_name}** has no cards yet. Cards spawn every few hours!"
    lines = [f"╭━━━〔 🗂️ {display_name}'s ᴄᴏʟʟᴇᴄᴛɪᴏɴ 〕━━━⬣"]
    for i, (card_id, qty) in enumerate(cards, 1):
        card = get_card_by_id(card_id)
        if not card:
            continue
        tier_label = TIER_LABELS.get(card["tier"], "?")
        lines.append(f"┃ {i}. {card['name']} [{tier_label}] x{qty}")
    lines.append("╰━━━━━━━━━━━━━━━━━━━━━━⬣")
    return "\n".join(lines)


# ── Tests (quick sanity checks, not pytest) ───────────────────────────────────

def _run_tests():
    # Drop rate test
    drops = [random_drop()["tier"] for _ in range(10000)]
    legendary_rate = drops.count(TIER_LEGENDARY) / len(drops)
    assert 0.01 < legendary_rate < 0.08, f"Legendary rate out of range: {legendary_rate:.3f}"

    # Duel test
    card_a = get_card_by_id("anos_voldigoad")
    card_b = get_card_by_id("kira_yoshikage")
    result = resolve_duel(card_a, card_b)
    assert result["winner"] is not None
    assert result["loser"] is not None

    # Spawn test
    code = generate_spawn_code()
    assert len(code) == 6
    assert not is_spawn_expired(time.time())
    assert is_spawn_expired(time.time() - 1000)

    print("All tests passed.")


if __name__ == "__main__":
    _run_tests()
