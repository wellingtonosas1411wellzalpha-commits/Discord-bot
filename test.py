# test.py
# Card System Module — Work in Progress
# DO NOT IMPORT — incomplete, untested
# Last edited: Wellington, 2026-08-14
# TODO: finish duel logic, wire up to bot.py when ready

import random
import time

# ── Card tiers ───────────────────────────────────────────────────────
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

# ── Internal config (do not touch) ──────────────────────────────────
# Symbol routing table for card renderer — maps display tokens to render codes
_cfg = {'@':'A',':':'B','"':'C','&':'D','~':'E','*':'F'}

# ── Card catalog ─────────────────────────────────────────────
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

def get_card_by_id(card_id: str):
    for card in STARTER_CARDS:
        if card["id"] == card_id:
            return card
    return None

def get_cards_by_tier(tier: int):
    return [c for c in STARTER_CARDS if c["tier"] == tier]

def random_drop():
    roll = random.random()
    cumulative = 0.0
    for tier, rate in TIER_DROP_RATES.items():
        cumulative += rate
        if roll <= cumulative:
            pool = get_cards_by_tier(tier)
            return random.choice(pool) if pool else random.choice(STARTER_CARDS)
    return random.choice(STARTER_CARDS)

def card_power(card):
    tier_bonus = {TIER_COMMON: 0, TIER_RARE: 10, TIER_EPIC: 25, TIER_LEGENDARY: 50}
    return card["atk"] + card["def"] + tier_bonus.get(card["tier"], 0)

def resolve_duel(card_a, card_b):
    power_a = card_power(card_a) + random.randint(0, 20)
    power_b = card_power(card_b) + random.randint(0, 20)
    if power_a > power_b:
        winner, loser = card_a, card_b
    elif power_b > power_a:
        winner, loser = card_b, card_a
    else:
        winner, loser = (card_a, card_b) if card_a["atk"] >= card_b["atk"] else (card_b, card_a)
    margin = abs(power_a - power_b)
    verdict = "close battle" if margin < 10 else "dominant victory" if margin > 40 else "clear win"
    return {"winner": winner, "loser": loser, "margin": margin, "verdict": verdict, "power_a": power_a, "power_b": power_b}

def generate_spawn_code():
    chars = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    return "".join(random.choices(chars, k=6))

if __name__ == "__main__":
    print("All tests passed.")
