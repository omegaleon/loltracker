"""
Build guide data for champion-specific optimal builds.
Each guide is keyed by "ChampionName:Role" (e.g., "Yunara:Bot", "Teemo:Jungle").
Data is structured for both UI rendering and League client item set export.
"""

# Data Dragon version for item icon URLs
DDRAGON_VERSION = "16.5.1"

# Item name lookup for display (id -> name)
ITEM_NAMES = {
    # Components / Starters
    "1001": "Boots",
    "1036": "Long Sword",
    "1038": "B.F. Sword",
    "1042": "Dagger",
    "1055": "Doran's Blade",
    "1056": "Doran's Ring",
    "1082": "Dark Seal",
    "2003": "Health Potion",
    "2031": "Refillable Potion",
    "3144": "Scout's Slingshot",
    "6690": "Rectrix",
    # Jungle Pets
    "1101": "Scorchclaw Pup",
    "1102": "Gustwalker Hatchling",
    "1103": "Mosstomper Seedling",
    # Boots
    "3006": "Berserker's Greaves",
    "3009": "Boots of Swiftness",
    "3020": "Sorcerer's Shoes",
    "3047": "Plated Steelcaps",
    "3111": "Mercury's Treads",
    "3158": "Ionian Boots of Lucidity",
    # Crit / ADC
    "2512": "Fiendhunter Bolts",
    "3031": "Infinity Edge",
    "3032": "Yun Tal Wildarrows",
    "3033": "Mortal Reminder",
    "3036": "Lord Dominik's Regards",
    "3046": "Phantom Dancer",
    "3072": "Bloodthirster",
    "3085": "Runaan's Hurricane",
    "3087": "Statikk Shiv",
    "3094": "Rapid Firecannon",
    "3097": "Stormrazor",
    "3508": "Essence Reaver",
    "6672": "Kraken Slayer",
    "6673": "Immortal Shieldbow",
    "6675": "Navori Flickerblade",
    "6676": "The Collector",
    # Lethality
    "3142": "Youmuu's Ghostblade",
    "6692": "Eclipse",
    "6694": "Serylda's Grudge",
    "6697": "Hubris",
    "6698": "Profane Hydra",
    "6699": "Voltaic Cyclosword",
    "6701": "Opportunity",
    "4004": "Spectral Cutlass",
    "3814": "Edge of Night",
    # AD Bruiser
    "3071": "Black Cleaver",
    "3073": "Experimental Hexplate",
    "3074": "Ravenous Hydra",
    "3078": "Trinity Force",
    "3153": "Blade of The Ruined King",
    "3161": "Spear of Shojin",
    "3181": "Hullbreaker",
    "3748": "Titanic Hydra",
    "2501": "Overlord's Bloodmail",
    "3053": "Sterak's Gage",
    "6333": "Death's Dance",
    "6609": "Chempunk Chainsword",
    "6610": "Sundered Sky",
    # AP
    "2503": "Blackfire Torch",
    "3003": "Archangel's Staff",
    "3089": "Rabadon's Deathcap",
    "3100": "Lich Bane",
    "3102": "Banshee's Veil",
    "3115": "Nashor's Tooth",
    "3116": "Rylai's Crystal Scepter",
    "3118": "Malignance",
    "3135": "Void Staff",
    "3137": "Cryptbloom",
    "3146": "Hextech Gunblade",
    "3152": "Hextech Rocketbelt",
    "3157": "Zhonya's Hourglass",
    "3165": "Morellonomicon",
    "4628": "Horizon Focus",
    "4629": "Cosmic Drive",
    "4633": "Riftmaker",
    "4645": "Shadowflame",
    "4646": "Stormsurge",
    "6653": "Liandry's Torment",
    "6655": "Luden's Echo",
    # On-Hit
    "3091": "Wit's End",
    "3124": "Guinsoo's Rageblade",
    "3302": "Terminus",
    # Tank
    "2502": "Unending Despair",
    "2504": "Kaenic Rookern",
    "3065": "Spirit Visage",
    "3068": "Sunfire Aegis",
    "3075": "Thornmail",
    "3083": "Warmog's Armor",
    "3084": "Heartsteel",
    "3110": "Frozen Heart",
    "3143": "Randuin's Omen",
    "3742": "Dead Man's Plate",
    "4401": "Force of Nature",
    "6665": "Jak'Sho, The Protean",
    # Support
    "2065": "Shurelya's Battlesong",
    "3107": "Redemption",
    "3190": "Locket of the Iron Solari",
    "3222": "Mikael's Blessing",
    "3504": "Ardent Censer",
    "4005": "Imperial Mandate",
    "6616": "Staff of Flowing Water",
    "6617": "Moonstone Renewer",
    "6620": "Echoes of Helia",
    "6621": "Dawncore",
    # Defense
    "3026": "Guardian Angel",
    "3139": "Mercurial Scimitar",
    "3156": "Maw of Malmortius",
}

# Champion IDs resolved dynamically from Data Dragon at export time.
# No hardcoded IDs — avoids mismatches between patches.

BUILD_GUIDES = {
    # ================================================================
    # YUNARA ADC
    # ================================================================
    "Yunara:Bot": {
        "champion_name": "Yunara",
        "role": "Bot",
        "title": "Yunara ADC — First Principles Build",
        "patch": "16.5.1",
        "skill_order": {
            "priority": "R > Q > E > W",
            "first_three": ["Q", "E", "W"],
            "reasoning": "Q max for on-hit damage (10-50 + 40% AP) and AS bonus (20-60%). "
                         "E second for MS (30-50%, or 45-75% during R) + dash during R. "
                         "W last — 99% slow is the same at all ranks, so ranks only add damage.",
        },
        "core_build": {
            "label": "Core Build",
            "items": ["6672", "3006", "2512", "3031"],
            "names": ["Kraken Slayer", "Berserker's Greaves", "Fiendhunter Bolts", "Infinity Edge"],
            "notes": [
                "Kraken default — smooth build path, Hearthbound Axe (1200g) is a realistic first-back spike. "
                "You can always buy a component (Rectrix 775g, Recurve Bow 700g, Long Sword 350g).",
                "Berserker's Greaves — 25% AS + MS. Standard ADC boot.",
                "Fiendhunter Bolts — 30 Ult Haste (R every fight), Opening Barrage (15% bonus true damage "
                "on guaranteed crits from R). 45% AS + 25% crit. This is the key synergy item.",
                "Infinity Edge — 75 AD + 25% crit + 30% crit damage. At 3 items you have 50-75% crit. "
                "Every crit triggers passive bonus magic damage at amplified multiplier.",
            ],
        },
        "first_back_variant": {
            "label": "BF Sword First Back (1300g+)",
            "items": ["3032", "3006", "2512", "3031"],
            "names": ["Yun Tal Wildarrows", "Berserker's Greaves", "Fiendhunter Bolts", "Infinity Edge"],
            "notes": [
                "If you back with 1300g+, buy B.F. Sword and go Yun Tal. Better finished item — "
                "crit ramp to 25% + Flurry (30% AS burst on champion combat). "
                "But the build path DEMANDS that big first buy.",
            ],
        },
        "fourth_item_options": {
            "label": "4th Item (game state dependent)",
            "options": [
                {
                    "item_id": "3085",
                    "name": "Runaan's Hurricane",
                    "when": "Teamfight-heavy games, enemies group up",
                    "why": "Each bolt triggers Q spread independently. 3 targets = 3 spread attacks "
                           "(each 30% AD AoE that can crit). Brings crit to 100%.",
                },
                {
                    "item_id": "3036",
                    "name": "Lord Dominik's Regards",
                    "when": "2+ enemies stacking armor, tanky frontline",
                    "why": "35% armor pen + Giant Slayer (15% bonus vs high HP). Essential to cut through.",
                },
                {
                    "item_id": "3046",
                    "name": "Phantom Dancer",
                    "when": "Need to kite dive-heavy comps",
                    "why": "65% AS (highest in game), 10% MS, Ghosted. Maximum kiting power.",
                },
            ],
        },
        "fifth_item_options": {
            "label": "5th Item",
            "options": [
                {
                    "item_id": "3036",
                    "name": "Lord Dominik's Regards",
                    "when": "Didn't buy 4th — you need armor pen eventually",
                    "why": "35% armor pen + Giant Slayer.",
                },
                {
                    "item_id": "3085",
                    "name": "Runaan's Hurricane",
                    "when": "Didn't buy 4th, teamfights happening",
                    "why": "AoE from bolts + Q spread interaction.",
                },
                {
                    "item_id": "3033",
                    "name": "Mortal Reminder",
                    "when": "Heavy healing on enemy team (Soraka, Aatrox, etc.)",
                    "why": "30% armor pen + 40% Grievous Wounds.",
                },
            ],
        },
        "defensive_options": {
            "label": "Defensive Options",
            "items": [
                {
                    "item_id": "3157",
                    "name": "Zhonya's Hourglass",
                    "when": "vs AD assassins (Zed, Rengar, Talon, Kha'Zix)",
                    "why": "Press BEFORE you die. Zed R → stasis → Death Mark pops for 0. "
                           "Rengar leaps → stasis → he's in your team with no target. "
                           "50 Armor (more than GA). 105 AP gives Q on-hit +42, passive 20.5% crit bonus. "
                           "Active stasis > passive revive against commit assassins.",
                },
                {
                    "item_id": "6333",
                    "name": "Death's Dance",
                    "when": "vs bruisers/fighters (Jax, Irelia, Riven, Darius)",
                    "why": "30% damage delayed as bleed over 3s. Defy cleanses bleed + heals on takedown. "
                           "60 AD (highest of any defensive item) + 50 Armor + 15 AH. "
                           "Bruisers don't one-shot — DD gives time to kite with E/W while DPSing them.",
                },
                {
                    "item_id": "6673",
                    "name": "Immortal Shieldbow",
                    "when": "vs instant stealth burst (Rengar from fog, Evelynn)",
                    "why": "Auto-shield at 30% HP. 55 AD + 25% crit — still scales. "
                           "Can buy 1st item in extreme cases.",
                },
                {
                    "item_id": "3156",
                    "name": "Maw of Malmortius",
                    "when": "vs AP assassins (Evelynn, LeBlanc, Fizz, Katarina)",
                    "why": "60 AD + 40 MR + magic damage shield. Shares Lifeline with Shieldbow.",
                },
                {
                    "item_id": "3026",
                    "name": "Guardian Angel",
                    "when": "General teamfight safety, no specific assassin threat",
                    "why": "55 AD + 45 Armor + revive. Better as insurance than a counter-tool.",
                },
                {
                    "item_id": "3139",
                    "name": "Mercurial Scimitar",
                    "when": "Must cleanse specific CC (Malzahar R, Skarner R, Morde R)",
                    "why": "QSS active removes CC. Only if CC is the kill setup.",
                },
            ],
        },
        "boots_options": {
            "label": "Boots",
            "items": [
                {
                    "item_id": "3006",
                    "name": "Berserker's Greaves",
                    "when": "Default — 90% of games",
                    "why": "25% AS + MS. Standard ADC boot.",
                },
                {
                    "item_id": "3047",
                    "name": "Plated Steelcaps",
                    "when": "vs AD Shaco, fed AD assassins",
                    "why": "25 Armor + 10% auto damage reduction. Shaco is almost ALL auto-attacks "
                           "(backstab, clone autos). Steelcaps negs a % of every hit.",
                },
            ],
        },
        "power_spikes": [
            {
                "items": 1,
                "description": "Kraken Slayer completed — on-hit pressure in lane, start trading aggressively.",
            },
            {
                "items": 2,
                "description": "Fiendhunter Bolts — R comes up every fight. Opening Barrage + R = guaranteed "
                               "crits deal 15% bonus true damage. This is your first major spike.",
            },
            {
                "items": 3,
                "description": "Infinity Edge — 75% crit, 30% crit damage amp. 3 out of 4 autos crit with "
                               "passive magic damage. Q spreads crit. You melt people now.",
            },
            {
                "items": 4,
                "description": "Runaan's/LDR — 100% crit with Runaan's = every auto + bolt triggers passive + spread. "
                               "Teamfight AoE is obscene. Or LDR to cut through armor.",
            },
        ],
        # For League client export
        "client_export": {
            "title": "Yunara ADC - LolTracker",
            "associated_maps": [11],
            "blocks": [
                {
                    "type": "Core Build (Kraken Default)",
                    "items": [
                        {"id": "6672", "count": 1},
                        {"id": "3006", "count": 1},
                        {"id": "2512", "count": 1},
                        {"id": "3031", "count": 1},
                        {"id": "3085", "count": 1},
                        {"id": "3036", "count": 1},
                    ],
                },
                {
                    "type": "BF Sword First Back (1300g+)",
                    "items": [
                        {"id": "3032", "count": 1},
                        {"id": "3006", "count": 1},
                        {"id": "2512", "count": 1},
                        {"id": "3031", "count": 1},
                        {"id": "3085", "count": 1},
                        {"id": "3036", "count": 1},
                    ],
                },
                {
                    "type": "4th Item Options",
                    "items": [
                        {"id": "3085", "count": 1},
                        {"id": "3036", "count": 1},
                        {"id": "3046", "count": 1},
                    ],
                },
                {
                    "type": "vs AD Assassins (Zed/Rengar/Shaco)",
                    "items": [
                        {"id": "3157", "count": 1},
                        {"id": "3047", "count": 1},
                    ],
                },
                {
                    "type": "vs Bruisers (Jax/Irelia/Riven)",
                    "items": [
                        {"id": "6333", "count": 1},
                    ],
                },
                {
                    "type": "vs AP Assassins",
                    "items": [
                        {"id": "3156", "count": 1},
                    ],
                },
                {
                    "type": "Other Defense",
                    "items": [
                        {"id": "6673", "count": 1},
                        {"id": "3026", "count": 1},
                        {"id": "3139", "count": 1},
                    ],
                },
                {
                    "type": "Boots",
                    "items": [
                        {"id": "3006", "count": 1},
                        {"id": "3047", "count": 1},
                    ],
                },
            ],
        },
    },

    # ================================================================
    # TEEMO JUNGLE
    # ================================================================
    "Teemo:Jungle": {
        "champion_name": "Teemo",
        "role": "Jungle",
        "title": "Teemo Jungle — First Principles Build",
        "patch": "16.5.1",
        "skill_order": {
            "priority": "R > E > Q > W",
            "first_three": ["E", "Q", "E"],
            "reasoning": "E max — 160% monster damage modifier. Each rank adds 38 total damage per auto "
                         "(60.8 vs monsters). Q second for 70% AP burst + blind. W last — 8% MS at rank 1 is enough.",
        },
        "core_build": {
            "label": "Core Build",
            "items": ["1101", "3020", "2503", "4645", "3089", "3135"],
            "names": ["Scorchclaw Pup", "Sorcerer's Shoes", "Blackfire Torch",
                      "Shadowflame", "Rabadon's Deathcap", "Void Staff"],
            "notes": [
                "Scorchclaw — burn + slow on abilities/autos. Best for gank-focused play.",
                "Sorcerer's Shoes — 12 flat MPen. Every damage source is magic. Non-negotiable.",
                "Blackfire Torch — Lost Chapter solves mana (shrooms cost 75 at R1). 20 AH (highest of any first item). "
                "+4% AP per target affected by burn — shrooms across the map stack this passively.",
                "Shadowflame — 110 AP + 15 MPen. With Sorcs = 27 flat MPen = near-true damage vs squishies. "
                "Cinderbloom (20% more damage below 40% HP) synergizes with DoT nature.",
                "Rabadon's Deathcap — 30% total AP multiplier. 190 + 130 = 320 base AP x 1.30 = 416 total. "
                "Shrooms hit for 658 each.",
                "Void Staff — 40% MPen. By now enemies have MR from levels + items. "
                "With 27 flat + 40% pen, a target with 80 MR has 21 effective MR.",
            ],
        },
        "first_back_variant": None,
        "fourth_item_options": None,
        "fifth_item_options": {
            "label": "6th Item (replace boots or last slot)",
            "options": [
                {
                    "item_id": "3100",
                    "name": "Lich Bane",
                    "when": "Default — with 500+ AP, Spellblade on Q → auto is massive burst",
                    "why": "100 AP + 4% MS + 10 AH. Spellblade proc with high AP is devastating.",
                },
                {
                    "item_id": "3157",
                    "name": "Zhonya's Hourglass",
                    "when": "vs AD assassins diving you",
                    "why": "105 AP + 50 Armor + 2.5s stasis. Press before death.",
                },
            ],
        },
        "defensive_options": {
            "label": "Defensive Options",
            "items": [
                {
                    "item_id": "3157",
                    "name": "Zhonya's Hourglass",
                    "when": "vs AD assassins",
                    "why": "105 AP + 50 Armor + stasis. AP isn't wasted.",
                },
                {
                    "item_id": "3102",
                    "name": "Banshee's Veil",
                    "when": "vs AP assassins or key engage abilities",
                    "why": "105 AP + 40 MR + spell shield.",
                },
            ],
        },
        "boots_options": {
            "label": "Boots",
            "items": [
                {
                    "item_id": "3020",
                    "name": "Sorcerer's Shoes",
                    "when": "Always — every damage source is magic",
                    "why": "12 flat MPen. Non-negotiable.",
                },
            ],
        },
        "power_spikes": [
            {
                "items": 1,
                "description": "Blackfire Torch — mana solved, 20 AH, burn passive stacks off shrooms. "
                               "First back Lost Chapter (1200g) is the key early spike.",
            },
            {
                "items": 2,
                "description": "Shadowflame — 190 AP, 27 flat MPen. Near-true damage vs squishies. "
                               "Cinderbloom execute on DoT ticks below 40% HP.",
            },
            {
                "items": 3,
                "description": "Rabadon's Deathcap — 416 total AP. Shrooms deal 658 damage each. "
                               "Q deals 551. 20 shrooms on the map = 13,160 potential zone damage.",
            },
        ],
        "client_export": {
            "title": "Teemo JG - LolTracker",
            "associated_maps": [11],
            "blocks": [
                {
                    "type": "Core Build",
                    "items": [
                        {"id": "1101", "count": 1},
                        {"id": "1082", "count": 1},
                        {"id": "3020", "count": 1},
                        {"id": "2503", "count": 1},
                        {"id": "4645", "count": 1},
                        {"id": "3089", "count": 1},
                        {"id": "3135", "count": 1},
                    ],
                },
                {
                    "type": "Last Item Options",
                    "items": [
                        {"id": "3100", "count": 1},
                        {"id": "3157", "count": 1},
                    ],
                },
                {
                    "type": "Defense",
                    "items": [
                        {"id": "3157", "count": 1},
                        {"id": "3102", "count": 1},
                    ],
                },
            ],
        },
    },

    # ================================================================
    # SAMIRA ADC
    # ================================================================
    "Samira:Bot": {
        "champion_name": "Samira",
        "role": "Bot",
        "title": "Samira ADC — First Principles Build",
        "patch": "16.5.1",
        "skill_order": {
            "priority": "R > Q > E > W",
            "first_three": ["Q", "E", "Q"],
            "reasoning": "Q max — primary poke and combo starter. Gun form applies on-hit, melee form is an AoE "
                         "cleave. E second for lower dash CD (20→12s) and more damage per rank. "
                         "W last — wind wall duration/damage rank scaling is least impactful.",
        },
        "core_build": {
            "label": "Core Build",
            "items": ["6673", "3006", "3031", "3072"],
            "names": ["Immortal Shieldbow", "Berserker's Greaves", "Infinity Edge", "Bloodthirster"],
            "notes": [
                "Shieldbow — Samira's defining first item. Lifeline shield at 30% HP keeps you alive during R. "
                "55 AD + 25% crit + lifesteal. Samira R fires 10 shots at full crit multiplier — each applies "
                "100% lifesteal. Shieldbow's lifesteal + shield = you survive to drain-tank through R.",
                "Berserker's Greaves — 25% AS for faster Style grade stacking. Samira needs 6 unique hits "
                "(S rank) to unlock R. Faster autos = faster S rank.",
                "Infinity Edge — 75 AD + 25% crit + 30% crit damage. At 2 items you have 50% crit. "
                "R fires 10 shots that can each crit — 30% bonus crit damage on 10 shots is massive.",
                "Bloodthirster — 80 AD + 15% lifesteal + overshield. R applies 100% lifesteal per shot. "
                "With BT + Shieldbow lifesteal, each R shot heals for a huge amount. "
                "Overshield gives even more survivability going into fights.",
            ],
        },
        "first_back_variant": None,
        "fourth_item_options": {
            "label": "4th Item (game state dependent)",
            "options": [
                {
                    "item_id": "3036",
                    "name": "Lord Dominik's Regards",
                    "when": "2+ enemies stacking armor (tanks/bruisers frontline)",
                    "why": "35% armor pen + Giant Slayer. R's 10 shots need to cut through armor to lifesteal effectively.",
                },
                {
                    "item_id": "3033",
                    "name": "Mortal Reminder",
                    "when": "Heavy healing on enemy team (Soraka, Aatrox, Vladimir, Sylas)",
                    "why": "30% armor pen + 40% Grievous Wounds. R hits all nearby enemies — applies GW to entire team.",
                },
                {
                    "item_id": "3046",
                    "name": "Phantom Dancer",
                    "when": "Need faster Style stacking and more kiting ability",
                    "why": "65% AS + 10% MS + Ghosted. Fastest way to reach S rank in teamfights.",
                },
                {
                    "item_id": "6675",
                    "name": "Navori Flickerblade",
                    "when": "Snowballing — want more E resets and Q spam",
                    "why": "60 AD + 25% crit + 20 AH. Crit autos reduce basic ability CDs. "
                           "E dash CD gets reset on kills, Navori further reduces it mid-combo.",
                },
            ],
        },
        "fifth_item_options": {
            "label": "5th Item",
            "options": [
                {
                    "item_id": "3036",
                    "name": "Lord Dominik's Regards",
                    "when": "Didn't buy 4th — armor pen is eventually mandatory",
                    "why": "35% armor pen + Giant Slayer.",
                },
                {
                    "item_id": "3139",
                    "name": "Mercurial Scimitar",
                    "when": "Must cleanse specific CC (Malzahar R, Morde R, Skarner R)",
                    "why": "QSS active. Samira MUST channel R uninterrupted — hard CC = death.",
                },
                {
                    "item_id": "3026",
                    "name": "Guardian Angel",
                    "when": "General teamfight insurance",
                    "why": "55 AD + 45 Armor + revive. Second chance after diving in with E → R.",
                },
            ],
        },
        "defensive_options": {
            "label": "Defensive Options",
            "items": [
                {
                    "item_id": "3026",
                    "name": "Guardian Angel",
                    "when": "vs mixed threats / general safety",
                    "why": "55 AD + 45 Armor + revive. Samira dives into melee range — revive gives a second chance. "
                           "Team can clean up while enemies wait for your revive.",
                },
                {
                    "item_id": "6333",
                    "name": "Death's Dance",
                    "when": "vs AD-heavy comps (3+ physical damage dealers)",
                    "why": "30% damage delayed as bleed. Defy cleanses bleed + heals on takedown. "
                           "Samira gets resets (E reset on kill) — each kill cleanses bleed and heals.",
                },
                {
                    "item_id": "3156",
                    "name": "Maw of Malmortius",
                    "when": "vs AP assassins (Evelynn, LeBlanc, Fizz, Katarina)",
                    "why": "60 AD + 40 MR + magic damage shield. Shares Lifeline with Shieldbow — "
                           "DO NOT BUILD BOTH. Replace Shieldbow with a different first item if going Maw.",
                },
                {
                    "item_id": "3139",
                    "name": "Mercurial Scimitar",
                    "when": "vs suppression or CC that interrupts R (Malzahar, Morde, Skarner)",
                    "why": "QSS active removes CC. Samira R is her entire teamfight contribution — "
                           "being CC'd out of it is a death sentence.",
                },
            ],
        },
        "boots_options": {
            "label": "Boots",
            "items": [
                {
                    "item_id": "3006",
                    "name": "Berserker's Greaves",
                    "when": "Default — 90% of games",
                    "why": "25% AS + MS. Faster autos for Style grade stacking.",
                },
                {
                    "item_id": "3047",
                    "name": "Plated Steelcaps",
                    "when": "vs heavy auto-attackers (Draven, Kog'Maw, Kalista lane + AD jungler)",
                    "why": "25 Armor + 10% auto damage reduction.",
                },
                {
                    "item_id": "3111",
                    "name": "Mercury's Treads",
                    "when": "vs heavy CC comps (3+ CC abilities that can interrupt R)",
                    "why": "25 MR + 30% tenacity. Getting CC'd during R is the worst case.",
                },
            ],
        },
        "power_spikes": [
            {
                "items": 1,
                "description": "Immortal Shieldbow — lifesteal + shield lets you survive all-ins. Start looking "
                               "for E-in opportunities when Style grade is high.",
            },
            {
                "items": 2,
                "description": "Infinity Edge — 50% crit, 30% crit damage amp. R's 10 shots now crit for massive "
                               "damage + massive lifesteal. This is your first real teamfight spike.",
            },
            {
                "items": 3,
                "description": "Bloodthirster — triple lifesteal source (Shieldbow + BT + R). You drain-tank through "
                               "entire teams during R. Overshield adds pre-fight durability.",
            },
            {
                "items": 4,
                "description": "LDR/Mortal Reminder — armor pen lets R cut through frontline. Full build Samira with "
                               "S rank is one of the highest teamfight DPS in the game.",
            },
        ],
        "client_export": {
            "title": "Samira ADC - LolTracker",
            "associated_maps": [11],
            "blocks": [
                {
                    "type": "Core Build",
                    "items": [
                        {"id": "6673", "count": 1},
                        {"id": "3006", "count": 1},
                        {"id": "3031", "count": 1},
                        {"id": "3072", "count": 1},
                    ],
                },
                {
                    "type": "4th/5th Item Options",
                    "items": [
                        {"id": "3036", "count": 1},
                        {"id": "3033", "count": 1},
                        {"id": "3046", "count": 1},
                        {"id": "6675", "count": 1},
                    ],
                },
                {
                    "type": "vs AD Threats",
                    "items": [
                        {"id": "3026", "count": 1},
                        {"id": "6333", "count": 1},
                        {"id": "3047", "count": 1},
                    ],
                },
                {
                    "type": "vs AP / CC Threats",
                    "items": [
                        {"id": "3156", "count": 1},
                        {"id": "3139", "count": 1},
                        {"id": "3111", "count": 1},
                    ],
                },
                {
                    "type": "Boots",
                    "items": [
                        {"id": "3006", "count": 1},
                        {"id": "3047", "count": 1},
                        {"id": "3111", "count": 1},
                    ],
                },
            ],
        },
    },

    # ================================================================
    # DARIUS TOP
    # ================================================================
    "Darius:Top": {
        "champion_name": "Darius",
        "role": "Top",
        "title": "Darius Top — First Principles Build",
        "patch": "16.5.1",
        "skill_order": {
            "priority": "R > Q > E > W",
            "first_three": ["Q", "W", "E"],
            "reasoning": "Q max — primary trading/sustain tool. Blade heals 15% missing HP per champion hit "
                         "(up to 45% on 3+). 100-140% tAD scaling at blade edge. E second for armor pen "
                         "passive (20-40%). W last — auto reset + slow, but scaling is just +20% tAD per rank.",
        },
        "core_build": {
            "label": "Core Build",
            "items": ["3078", "3111", "3053"],
            "names": ["Trinity Force", "Mercury's Treads", "Sterak's Gage"],
            "notes": [
                "Trinity Force — Spellblade proc + Threefold Strike AS stacking. W auto reset guarantees "
                "Spellblade. 33 AD + 25% AS + 20 AH + 300 HP. Threefold ramps AS on hit, perfect for "
                "stacking Hemorrhage to 5 (Noxian Might). Build path: Hearthbound Axe (1200g) or Sheen (1050g).",
                "Mercury's Treads — 25 MR + 30% tenacity. Darius MUST reach enemies — tenacity counters "
                "the CC that keeps him kited. Take Steelcaps only vs pure auto-attack lanes (Tryndamere).",
                "Sterak's Gage — 50 AD + 400 HP. Lifeline shield (75% bonus HP) at 30% HP. "
                "Darius at Noxian Might has +30-230 bonus AD — Sterak's amplifies his already-massive "
                "AD pool. Shield lets him survive burst to get 5 stacks.",
            ],
        },
        "first_back_variant": None,
        "fourth_item_options": {
            "label": "4th Item (game state dependent)",
            "options": [
                {
                    "item_id": "6333",
                    "name": "Death's Dance",
                    "when": "vs AD-heavy teams or extended fights",
                    "why": "30% damage delayed as bleed. Defy cleanses on takedown + heals. "
                           "Darius R resets on kill — each Dunk cleanses DD bleed. In a teamfight where "
                           "you chain 2-3 Dunks, you're unkillable. 60 AD + 50 Armor + 15 AH.",
                },
                {
                    "item_id": "6610",
                    "name": "Sundered Sky",
                    "when": "vs tanky frontlines you need to sustain through",
                    "why": "55 AD + 300 HP + 15 AH. First hit on each champion is a guaranteed crit "
                           "that heals based on missing HP. Combined with Q heal, Darius sustains "
                           "through extended fights.",
                },
                {
                    "item_id": "3742",
                    "name": "Dead Man's Plate",
                    "when": "Need to reach backline / vs kiting comps",
                    "why": "300 HP + 45 Armor + MS ramp-up. Momentum charge gives up to 60 bonus MS. "
                           "Darius's biggest weakness is getting kited — DMP closes the gap.",
                },
                {
                    "item_id": "3143",
                    "name": "Randuin's Omen",
                    "when": "vs 2+ crit ADCs or heavy crit comp",
                    "why": "400 HP + 60 Armor. Reduces crit damage taken. Active slows nearby enemies — "
                           "keeps them in Q blade range.",
                },
            ],
        },
        "fifth_item_options": {
            "label": "5th Item",
            "options": [
                {
                    "item_id": "6333",
                    "name": "Death's Dance",
                    "when": "Didn't buy 4th — always strong on Darius",
                    "why": "DD bleed cleanse on R resets makes teamfights winnable.",
                },
                {
                    "item_id": "3065",
                    "name": "Spirit Visage",
                    "when": "vs AP threats + amplifies Q heal",
                    "why": "60 MR + 450 HP + 25% heal/shield power boost. Q heal (15% missing HP × 3 champs) "
                           "is amplified by 25%. Massive sustain in teamfights.",
                },
                {
                    "item_id": "4401",
                    "name": "Force of Nature",
                    "when": "vs sustained AP damage (DoT mages, DPS mages)",
                    "why": "60 MR + 350 HP + 10% MS. Dissipate passive stacks MR as you take magic damage. "
                           "Better than Spirit Visage vs sustained AP damage, worse vs burst.",
                },
            ],
        },
        "defensive_options": {
            "label": "Defensive Options",
            "items": [
                {
                    "item_id": "3065",
                    "name": "Spirit Visage",
                    "when": "vs AP threats + want to amplify Q healing",
                    "why": "60 MR + 450 HP. 25% bonus healing amplifies Q heal (15% missing HP per champ hit).",
                },
                {
                    "item_id": "4401",
                    "name": "Force of Nature",
                    "when": "vs sustained AP damage (Brand, Cassio, Teemo)",
                    "why": "60 MR + 350 HP + 10% MS + stacking MR passive.",
                },
                {
                    "item_id": "3143",
                    "name": "Randuin's Omen",
                    "when": "vs heavy crit (2+ crit ADCs)",
                    "why": "400 HP + 60 Armor + crit damage reduction + AoE slow active.",
                },
                {
                    "item_id": "3075",
                    "name": "Thornmail",
                    "when": "vs heavy healing + auto-attackers you can't avoid",
                    "why": "350 HP + 75 Armor + Grievous Wounds on being hit by autos. Passive since "
                           "enemies are forced to auto you when you pull them with E.",
                },
                {
                    "item_id": "3083",
                    "name": "Warmog's Armor",
                    "when": "Siege/poke comps where you take chip damage before fights",
                    "why": "800 HP + out-of-combat regen. Reset between skirmishes without recalling.",
                },
            ],
        },
        "boots_options": {
            "label": "Boots",
            "items": [
                {
                    "item_id": "3111",
                    "name": "Mercury's Treads",
                    "when": "Default — 80% of games (enemy team always has CC)",
                    "why": "25 MR + 30% tenacity. Darius must reach enemies to fight.",
                },
                {
                    "item_id": "3047",
                    "name": "Plated Steelcaps",
                    "when": "vs pure auto-attack lane (Tryndamere, Vayne top) AND low CC enemy team",
                    "why": "25 Armor + 10% auto damage reduction. Only if enemy CC is minimal.",
                },
            ],
        },
        "power_spikes": [
            {
                "items": 1,
                "description": "Trinity Force — Spellblade + Threefold Strike. W auto-reset procs Spellblade "
                               "for huge burst. Start forcing all-ins at 5 Hemorrhage stacks.",
            },
            {
                "items": 2,
                "description": "Sterak's — massive AD + Lifeline shield. At Noxian Might (5 stacks), Darius has "
                               "200+ bonus AD at lvl 13. R does true damage = (base + 75% bAD) × 2 at 5 stacks. "
                               "You win almost every 1v1 and most 1v2s.",
            },
            {
                "items": 3,
                "description": "Death's Dance / 3rd tank item — teamfight monster. Q blade heals, DD cleanses on "
                               "R kills. Darius with E armor pen (30-40%), R true damage, and 3 items melts everyone.",
            },
        ],
        "client_export": {
            "title": "Darius Top - LolTracker",
            "associated_maps": [11],
            "blocks": [
                {
                    "type": "Core Build",
                    "items": [
                        {"id": "3078", "count": 1},
                        {"id": "3111", "count": 1},
                        {"id": "3053", "count": 1},
                    ],
                },
                {
                    "type": "4th/5th Item Options",
                    "items": [
                        {"id": "6333", "count": 1},
                        {"id": "6610", "count": 1},
                        {"id": "3742", "count": 1},
                        {"id": "3143", "count": 1},
                    ],
                },
                {
                    "type": "vs AP",
                    "items": [
                        {"id": "3065", "count": 1},
                        {"id": "4401", "count": 1},
                    ],
                },
                {
                    "type": "vs AD / Other Defense",
                    "items": [
                        {"id": "3143", "count": 1},
                        {"id": "3075", "count": 1},
                        {"id": "3083", "count": 1},
                    ],
                },
                {
                    "type": "Boots",
                    "items": [
                        {"id": "3111", "count": 1},
                        {"id": "3047", "count": 1},
                    ],
                },
            ],
        },
    },

    # ================================================================
    # MISS FORTUNE ADC
    # ================================================================
    "MissFortune:Bot": {
        "champion_name": "MissFortune",
        "role": "Bot",
        "title": "Miss Fortune ADC — First Principles Build",
        "patch": "16.5.1",
        "skill_order": {
            "priority": "R > Q > W > E",
            "first_three": ["Q", "W", "E"],
            "reasoning": "Q max — primary poke. Bounce crit on kill does massive damage. 100% tAD ratio on first "
                         "hit, 150% tAD on bounce (or guaranteed crit on kill). W second for AS steroid (40-80%) + "
                         "Love Tap MS. E last — slow field, damage is negligible.",
        },
        "core_build": {
            "label": "Core Build",
            "items": ["6701", "3158", "3142", "6694"],
            "names": ["Opportunity", "Ionian Boots of Lucidity", "Youmuu's Ghostblade", "Serylda's Grudge"],
            "notes": [
                "Opportunity — 55 AD + 18 lethality. Preparation passive (out-of-combat lethality bonus = up to "
                "additional 8 lethality). MF's R is often fired from fog/brush — full Preparation value. "
                "Smooth build path: Serrated Dirk (1100g) is a strong first back.",
                "Ionian Boots of Lucidity — 10 AH + 12 Summoner Spell Haste. MF wants AH to lower R CD. "
                "Every R in a teamfight is a potential ace. Lucidity is cheapest CDR path.",
                "Youmuu's Ghostblade — 55 AD + 18 lethality + 10 AH + MS active. Ghostblade active "
                "gives 20% MS for repositioning R. R channels for 3s — positioning is everything.",
                "Serylda's Grudge — 45 AD + 18 lethality + 30% armor pen. R fires 12-16 waves × 60% tAD each. "
                "Serylda's passive: abilities slow by 30% for 1s. Every R wave slows the entire enemy team. "
                "They can't walk out of R. This is MF's highest-value item.",
            ],
        },
        "first_back_variant": {
            "label": "Crit Variant (if team needs DPS)",
            "items": ["6672", "3006", "3031", "3085"],
            "names": ["Kraken Slayer", "Berserker's Greaves", "Infinity Edge", "Runaan's Hurricane"],
            "notes": [
                "If your team already has burst damage and needs sustained DPS instead, go crit. "
                "Kraken → Berserker's → IE → Runaan's. R still crits (at 30% efficiency), but your "
                "auto-attack DPS is much higher. This path is weaker for R-centric teamfights but "
                "better for extended skirmishes.",
            ],
        },
        "fourth_item_options": {
            "label": "4th Item (Lethality path)",
            "options": [
                {
                    "item_id": "6697",
                    "name": "Hubris",
                    "when": "Snowballing — you're getting kills",
                    "why": "55 AD + 18 lethality. On champion kill/assist: gain stacking AD bonus. "
                           "If ahead, Hubris snowballs MF's R damage even further.",
                },
                {
                    "item_id": "3814",
                    "name": "Edge of Night",
                    "when": "vs engage that interrupts R (Nautilus hook, Malphite R, Blitz grab)",
                    "why": "50 AD + 18 lethality + spell shield. Shield absorbs one ability — "
                           "protects R channel from the first CC that would interrupt it.",
                },
                {
                    "item_id": "3036",
                    "name": "Lord Dominik's Regards",
                    "when": "Enemy team has 2+ heavy armor stackers",
                    "why": "35% armor pen + Giant Slayer. Stacks with Serylda's 30% for 65% total armor pen. "
                           "R waves melt even full-armor tanks.",
                },
            ],
        },
        "fifth_item_options": {
            "label": "5th Item",
            "options": [
                {
                    "item_id": "3036",
                    "name": "Lord Dominik's Regards",
                    "when": "Didn't buy 4th — armor pen is essential late game",
                    "why": "35% armor pen + Giant Slayer.",
                },
                {
                    "item_id": "3026",
                    "name": "Guardian Angel",
                    "when": "Getting dove before you can R",
                    "why": "55 AD + 45 Armor + revive. MF is immobile (no dash) — GA insurance.",
                },
                {
                    "item_id": "6692",
                    "name": "Eclipse",
                    "when": "Need sustain + shield in extended fights",
                    "why": "55 AD + 18 lethality + omnivamp. Shield proc on 2 abilities vs champion.",
                },
            ],
        },
        "defensive_options": {
            "label": "Defensive Options",
            "items": [
                {
                    "item_id": "3814",
                    "name": "Edge of Night",
                    "when": "vs one key engage ability that interrupts R",
                    "why": "Spell shield protects R channel. Still gives lethality. Best defensive option for MF.",
                },
                {
                    "item_id": "3026",
                    "name": "Guardian Angel",
                    "when": "vs assassins that dive backline",
                    "why": "55 AD + 45 Armor + revive. MF has no mobility — can't dodge or dash.",
                },
                {
                    "item_id": "3156",
                    "name": "Maw of Malmortius",
                    "when": "vs AP assassins (Evelynn, Fizz, LeBlanc)",
                    "why": "60 AD + 40 MR + magic damage shield.",
                },
                {
                    "item_id": "3139",
                    "name": "Mercurial Scimitar",
                    "when": "vs suppression (Malzahar R, Skarner R)",
                    "why": "QSS active. Can't R if suppressed.",
                },
            ],
        },
        "boots_options": {
            "label": "Boots",
            "items": [
                {
                    "item_id": "3158",
                    "name": "Ionian Boots of Lucidity",
                    "when": "Default (Lethality build) — AH for more R uptime",
                    "why": "10 AH + 12 Summoner Spell Haste. Cheapest AH option.",
                },
                {
                    "item_id": "3006",
                    "name": "Berserker's Greaves",
                    "when": "Crit build — need AS for auto DPS",
                    "why": "25% AS + MS. Standard for crit path.",
                },
                {
                    "item_id": "3047",
                    "name": "Plated Steelcaps",
                    "when": "vs heavy AD auto-attackers in lane + AD assassin jungler",
                    "why": "25 Armor + 10% auto damage reduction.",
                },
            ],
        },
        "power_spikes": [
            {
                "items": 1,
                "description": "Opportunity — Serrated Dirk (1100g) first back is huge. Lethality makes Q bounce "
                               "kill-crit nearly one-shot squishies through minions. Start playing for Q bounces off "
                               "dying minions.",
            },
            {
                "items": 2,
                "description": "Youmuu's Ghostblade — 36 lethality (with Preparation). R with 2 lethality items "
                               "chunks any non-tank to 20% HP. Use Ghostblade MS to reposition for R angle.",
            },
            {
                "items": 3,
                "description": "Serylda's Grudge — THE power spike. R now slows the entire enemy team by 30% "
                               "per wave. They physically cannot walk out of R. 30% armor pen stacks with lethality "
                               "for near-true damage vs squishies. A well-aimed 3-item R wins teamfights alone.",
            },
            {
                "items": 4,
                "description": "Full lethality + armor pen. R does 720-960% total AD in waves that slow and shred. "
                               "Play for R angles. MF wins teamfights from positioning, not mechanics.",
            },
        ],
        "client_export": {
            "title": "MF ADC Lethality - LolTracker",
            "associated_maps": [11],
            "blocks": [
                {
                    "type": "Core Build (Lethality)",
                    "items": [
                        {"id": "6701", "count": 1},
                        {"id": "3158", "count": 1},
                        {"id": "3142", "count": 1},
                        {"id": "6694", "count": 1},
                    ],
                },
                {
                    "type": "Core Build (Crit Variant)",
                    "items": [
                        {"id": "6672", "count": 1},
                        {"id": "3006", "count": 1},
                        {"id": "3031", "count": 1},
                        {"id": "3085", "count": 1},
                    ],
                },
                {
                    "type": "4th/5th Options (Lethality)",
                    "items": [
                        {"id": "6697", "count": 1},
                        {"id": "3814", "count": 1},
                        {"id": "3036", "count": 1},
                        {"id": "6692", "count": 1},
                    ],
                },
                {
                    "type": "Defense",
                    "items": [
                        {"id": "3814", "count": 1},
                        {"id": "3026", "count": 1},
                        {"id": "3156", "count": 1},
                        {"id": "3139", "count": 1},
                    ],
                },
                {
                    "type": "Boots",
                    "items": [
                        {"id": "3158", "count": 1},
                        {"id": "3006", "count": 1},
                        {"id": "3047", "count": 1},
                    ],
                },
            ],
        },
    },

    # ================================================================
    # LUX MID
    # ================================================================
    "Lux:Mid": {
        "champion_name": "Lux",
        "role": "Mid",
        "title": "Lux Mid — First Principles Build",
        "patch": "16.5.1",
        "skill_order": {
            "priority": "R > E > Q > W",
            "first_three": ["E", "Q", "W"],
            "reasoning": "E max — primary poke and waveclear. 240 + 80% AP at max rank, AoE zone. "
                         "Q second for root duration (1→2s) and 70+15/rank base damage. "
                         "W last — shield is nice but Mid Lux is a burst mage, not a shielder.",
        },
        "core_build": {
            "label": "Core Build",
            "items": ["6655", "3020", "4645", "3089"],
            "names": ["Luden's Echo", "Sorcerer's Shoes", "Shadowflame", "Rabadon's Deathcap"],
            "notes": [
                "Luden's Echo — 90 AP + 10 AH + 600 mana. Echo passive deals bonus magic damage on ability hit "
                "and reduces target's MR by 4 per stack (up to 6 stacks = 24 MR shred). Lost Chapter (1200g) "
                "on first back solves mana and gives AP + AH. Lux E spam burns mana fast — she needs this.",
                "Sorcerer's Shoes — 12 flat MPen. Every damage source is magic. Combined with Luden's MR shred, "
                "squishies take near-true damage.",
                "Shadowflame — 110 AP + 15 MPen. With Sorcs = 27 flat MPen. Cinderbloom (20% more damage "
                "below 40% HP) synergizes with Lux combo — E + Q puts them below 40%, then R executes.",
                "Rabadon's Deathcap — 30% total AP. Full combo = E (80%) + Q (75%) + R (120%) + 2 passive procs "
                "(20% each) = 315% AP ratio minimum. Deathcap amplifies all of it by 30%.",
            ],
        },
        "first_back_variant": None,
        "fourth_item_options": {
            "label": "4th Item (game state dependent)",
            "options": [
                {
                    "item_id": "3135",
                    "name": "Void Staff",
                    "when": "Enemies building MR (60+ MR on 2+ targets)",
                    "why": "40% magic pen. With 27 flat pen + 40% pen, even MR stackers take heavy damage.",
                },
                {
                    "item_id": "4628",
                    "name": "Horizon Focus",
                    "when": "Default if enemies not stacking MR — max burst damage",
                    "why": "80 AP + 15 AH. Damaging a champion at 700+ range reveals them and you deal 10% "
                           "more damage. Lux E/Q/R all outrange 700 — you always get the 10% amp.",
                },
                {
                    "item_id": "3165",
                    "name": "Morellonomicon",
                    "when": "Enemy team has heavy healing (Soraka, Yuumi, Vladimir, Aatrox)",
                    "why": "80 AP + 300 HP + 40% Grievous Wounds on ability damage. E hits AoE — "
                           "applies GW to multiple enemies.",
                },
            ],
        },
        "fifth_item_options": {
            "label": "5th Item",
            "options": [
                {
                    "item_id": "3135",
                    "name": "Void Staff",
                    "when": "Didn't buy 4th — magic pen is mandatory late game",
                    "why": "40% magic pen. Enemy MR from levels alone hits 40+ by now.",
                },
                {
                    "item_id": "4628",
                    "name": "Horizon Focus",
                    "when": "Didn't buy 4th — max burst on squishies",
                    "why": "10% damage amp from range + 80 AP + AH.",
                },
                {
                    "item_id": "3157",
                    "name": "Zhonya's Hourglass",
                    "when": "Getting dove by assassins or divers",
                    "why": "105 AP + 50 Armor + stasis active. Lux is immobile — stasis buys time for E+Q.",
                },
            ],
        },
        "defensive_options": {
            "label": "Defensive Options",
            "items": [
                {
                    "item_id": "3157",
                    "name": "Zhonya's Hourglass",
                    "when": "vs AD assassins (Zed, Talon, Rengar) — THE defensive item",
                    "why": "105 AP + 50 Armor + 2.5s stasis. Lux has no mobility — stasis is her only escape. "
                           "AP isn't wasted.",
                },
                {
                    "item_id": "3102",
                    "name": "Banshee's Veil",
                    "when": "vs AP assassins or one key engage (Malphite R, Blitz Q)",
                    "why": "105 AP + 40 MR + spell shield. Blocks the first ability that would start the kill combo.",
                },
            ],
        },
        "boots_options": {
            "label": "Boots",
            "items": [
                {
                    "item_id": "3020",
                    "name": "Sorcerer's Shoes",
                    "when": "Default — every game as mid Lux",
                    "why": "12 flat MPen. Every damage source is magic. Non-negotiable.",
                },
            ],
        },
        "power_spikes": [
            {
                "items": 1,
                "description": "Luden's Echo — mana solved, MR shred passive. Lost Chapter (1200g) first back "
                               "is the key spike. Start perma-shoving with E and roaming for R snipes.",
            },
            {
                "items": 2,
                "description": "Shadowflame — 27 flat MPen total (Sorcs + Shadowflame). Squishies have ~30-40 MR. "
                               "You're dealing near-true damage. Full combo (E + Q + passive + R + passive) "
                               "one-shots any squishy who isn't building MR.",
            },
            {
                "items": 3,
                "description": "Rabadon's Deathcap — AP skyrockets. R cooldown is 30-20s (with ult haste). "
                               "R snipes across the map become kill-range on anyone below 60% HP. Full combo "
                               "kills even bruisers if they haven't built MR.",
            },
            {
                "items": 4,
                "description": "Void Staff / Horizon Focus — kill range extends to MR-building targets. "
                               "At this point, Lux's combo kills anyone who gets hit by Q.",
            },
        ],
        "client_export": {
            "title": "Lux Mid - LolTracker",
            "associated_maps": [11],
            "blocks": [
                {
                    "type": "Core Build",
                    "items": [
                        {"id": "6655", "count": 1},
                        {"id": "3020", "count": 1},
                        {"id": "4645", "count": 1},
                        {"id": "3089", "count": 1},
                    ],
                },
                {
                    "type": "4th/5th Options",
                    "items": [
                        {"id": "3135", "count": 1},
                        {"id": "4628", "count": 1},
                        {"id": "3165", "count": 1},
                    ],
                },
                {
                    "type": "Defense",
                    "items": [
                        {"id": "3157", "count": 1},
                        {"id": "3102", "count": 1},
                    ],
                },
                {
                    "type": "Boots",
                    "items": [
                        {"id": "3020", "count": 1},
                    ],
                },
            ],
        },
    },

    # ================================================================
    # LUX SUPPORT
    # ================================================================
    "Lux:Support": {
        "champion_name": "Lux",
        "role": "Support",
        "title": "Lux Support — First Principles Build",
        "patch": "16.5.1",
        "skill_order": {
            "priority": "R > E > W > Q",
            "first_three": ["E", "Q", "W"],
            "reasoning": "E max — poke and bush control in lane. W second — shield scales with AP "
                         "(40% AP per pass × 2 passes = 80% AP ratio), amplified by Heal/Shield Power. "
                         "Support Lux can't safely auto at 550 range to proc passive, so raw damage from "
                         "Q ranks is less valuable than shield strength from W ranks.",
        },
        "core_build": {
            "label": "Core Build",
            "items": ["6617", "3158", "3504", "6621"],
            "names": ["Moonstone Renewer", "Ionian Boots of Lucidity", "Ardent Censer", "Dawncore"],
            "notes": [
                "Moonstone Renewer — heals/shields an ally, then chains to nearby allies. "
                "W is a team shield (hits all allies it passes through) — Moonstone chains off each shield "
                "application. In a teamfight, W through your team + Moonstone = massive team healing.",
                "Ionian Boots of Lucidity — 10 AH + 12 Summoner Spell Haste. Support income is low — "
                "Lucidity is cheapest. More AH = more W shields and E poke.",
                "Ardent Censer — 60 AP + 100% base mana regen + 10% Heal/Shield Power. "
                "On shield/heal, gives target 25% AS + magic damage on-hit for 6s. "
                "W hits all allies — Ardent buff on your entire team in one W cast.",
                "Dawncore — 40 AP + 100% base mana regen + 10% Heal/Shield Power + 10 AH. "
                "Shields/heals based on HP% of the target. Stacks with Ardent's H/S Power "
                "for massive W shields.",
            ],
        },
        "first_back_variant": {
            "label": "Damage/Poke Variant (lane dominant)",
            "items": ["6655", "3020", "4645", "3089"],
            "names": ["Luden's Echo", "Sorcerer's Shoes", "Shadowflame", "Rabadon's Deathcap"],
            "notes": [
                "If your ADC is self-sufficient and you want to play as a second mage, go full AP. "
                "Same build as Mid Lux. Only do this if you're confident in landing Q consistently — "
                "otherwise you're a squishy damage support with no utility.",
            ],
        },
        "fourth_item_options": {
            "label": "4th Item (Enchanter path)",
            "options": [
                {
                    "item_id": "6616",
                    "name": "Staff of Flowing Water",
                    "when": "Team has 2+ AP damage dealers",
                    "why": "60 AP + 100% base mana regen + 10% H/S Power. On shield/heal: gives target "
                           "25 AP + 20 AH for 6s. W through AP-heavy team = team-wide AP/AH buff.",
                },
                {
                    "item_id": "3107",
                    "name": "Redemption",
                    "when": "Default 4th — team healing in fights",
                    "why": "200 HP + 100% base mana regen + 15% H/S Power. Active: AoE heal zone. "
                           "Cast during teamfight — heals landing after 2.5s covers the extended fight.",
                },
                {
                    "item_id": "3222",
                    "name": "Mikael's Blessing",
                    "when": "Enemy team has one critical CC you need to cleanse (Ashe R, Morg Q, Thresh hook)",
                    "why": "Active: removes CC from an ally. Also gives H/S Power. Niche but game-saving.",
                },
            ],
        },
        "fifth_item_options": None,
        "defensive_options": {
            "label": "Defensive Options",
            "items": [
                {
                    "item_id": "3157",
                    "name": "Zhonya's Hourglass",
                    "when": "vs AD assassins diving you",
                    "why": "105 AP + 50 Armor + stasis. Lux support is squishy and has no mobility. "
                           "Stasis buys time for team to peel.",
                },
                {
                    "item_id": "3190",
                    "name": "Locket of the Iron Solari",
                    "when": "vs AoE burst (Orianna R, Diana R, MF R)",
                    "why": "Active: shield all nearby allies. Against AoE burst, Locket can be more "
                           "impactful than enchanter items.",
                },
            ],
        },
        "boots_options": {
            "label": "Boots",
            "items": [
                {
                    "item_id": "3158",
                    "name": "Ionian Boots of Lucidity",
                    "when": "Default — every game as support Lux",
                    "why": "10 AH + 12 Summoner Spell Haste. Cheapest, most efficient for support income.",
                },
                {
                    "item_id": "3009",
                    "name": "Boots of Swiftness",
                    "when": "vs heavy slow-based comps (Ashe, Zilean, Nasus)",
                    "why": "60 MS + 25% slow resist. Better roaming speed.",
                },
            ],
        },
        "power_spikes": [
            {
                "items": 1,
                "description": "Moonstone Renewer — W shields now chain-heal in teamfights. Play for team "
                               "shielding, not for picks.",
            },
            {
                "items": 2,
                "description": "Ardent Censer — W applies Ardent to your entire team. One W through 3+ allies "
                               "gives everyone 25% AS + magic damage on-hit. Massive for team DPS.",
            },
            {
                "items": 3,
                "description": "Dawncore — H/S Power stacking. W shields are now substantial — each pass "
                               "shields for 80% AP × H/S Power multiplier. W is your primary teamfight tool.",
            },
        ],
        "client_export": {
            "title": "Lux Support - LolTracker",
            "associated_maps": [11],
            "blocks": [
                {
                    "type": "Core Build (Enchanter)",
                    "items": [
                        {"id": "6617", "count": 1},
                        {"id": "3158", "count": 1},
                        {"id": "3504", "count": 1},
                        {"id": "6621", "count": 1},
                    ],
                },
                {
                    "type": "Damage Variant",
                    "items": [
                        {"id": "6655", "count": 1},
                        {"id": "3020", "count": 1},
                        {"id": "4645", "count": 1},
                        {"id": "3089", "count": 1},
                    ],
                },
                {
                    "type": "4th Item Options",
                    "items": [
                        {"id": "6616", "count": 1},
                        {"id": "3107", "count": 1},
                        {"id": "3222", "count": 1},
                    ],
                },
                {
                    "type": "Defense",
                    "items": [
                        {"id": "3157", "count": 1},
                        {"id": "3190", "count": 1},
                    ],
                },
                {
                    "type": "Boots",
                    "items": [
                        {"id": "3158", "count": 1},
                        {"id": "3009", "count": 1},
                    ],
                },
            ],
        },
    },

    # ================================================================
    # NIDALEE JUNGLE
    # ================================================================
    "Nidalee:Jungle": {
        "champion_name": "Nidalee",
        "role": "Jungle",
        "title": "Nidalee Jungle — First Principles Build",
        "patch": "16.5.1",
        "skill_order": {
            "priority": "R > Q > W > E",
            "first_three": ["Q", "W", "E"],
            "reasoning": "Q max — Javelin Toss damage scales 70-250 base + 50% AP at min range, up to "
                         "200% damage at max range (= 487.5 + 1.625 AP). Cougar Q (Takedown) executes "
                         "based on target's missing HP. W second for Bushwhack (trap) reduced CD + cougar "
                         "W (Pounce) reduced CD. E last — heal is useful but ranks add less combat impact.",
        },
        "core_build": {
            "label": "Core Build",
            "items": ["1101", "3020", "6653", "3157"],
            "names": ["Scorchclaw Pup", "Sorcerer's Shoes", "Liandry's Torment", "Zhonya's Hourglass"],
            "notes": [
                "Scorchclaw — burn + slow. Gank-focused pet. Slow from Scorchclaw helps land max-range Q.",
                "Sorcerer's Shoes — 12 flat MPen. All damage is magic (0 AD scaling on Nidalee). Non-negotiable.",
                "Liandry's Torment — 80 AP + 300 HP + 20 AH. 2% max HP burn per second (4s). Javelin Toss "
                "applies the burn at long range — target takes spear damage THEN burns for 8% max HP over 4s. "
                "In jungle, burn adds substantial damage to camp clears. AP + HP is ideal for Nidalee's "
                "dive-and-execute playstyle (cougar form is melee).",
                "Zhonya's Hourglass — 105 AP + 50 Armor + stasis. Nidalee dives into melee range in cougar "
                "form. After landing W (Pounce) + Q (Takedown) + E (Swipe), stasis lets you survive while "
                "human form CDs come back up. Not optional — she's too squishy without it.",
            ],
        },
        "first_back_variant": None,
        "fourth_item_options": {
            "label": "4th Item (game state dependent)",
            "options": [
                {
                    "item_id": "3089",
                    "name": "Rabadon's Deathcap",
                    "when": "Ahead — want to maximize spear damage",
                    "why": "30% total AP multiplier. Max range spear with Deathcap AP is a death sentence. "
                           "Cougar Q execute damage also scales with AP. Snowball item.",
                },
                {
                    "item_id": "3135",
                    "name": "Void Staff",
                    "when": "Enemies building MR (60+ MR on 2+ targets)",
                    "why": "40% magic pen. With Sorcs (12 flat), you cut through MR stacking effectively.",
                },
                {
                    "item_id": "3116",
                    "name": "Rylai's Crystal Scepter",
                    "when": "Need utility — team lacks CC/slows",
                    "why": "75 AP + 350 HP. All abilities slow by 30% for 1s. Spear at max range = "
                           "slow at max range. Helps team collapse on hit targets.",
                },
            ],
        },
        "fifth_item_options": {
            "label": "5th Item",
            "options": [
                {
                    "item_id": "3089",
                    "name": "Rabadon's Deathcap",
                    "when": "Didn't buy 4th — always want this eventually",
                    "why": "30% AP multiplier. Late game spears become one-shots.",
                },
                {
                    "item_id": "3135",
                    "name": "Void Staff",
                    "when": "Didn't buy 4th — need magic pen late",
                    "why": "40% magic pen. Mandatory if enemies have MR items.",
                },
                {
                    "item_id": "4629",
                    "name": "Cosmic Drive",
                    "when": "Need MS for kiting/repositioning",
                    "why": "90 AP + 30 AH + 4% MS. Spelldance passive: combat MS boost. "
                           "More AH = more spear attempts.",
                },
            ],
        },
        "defensive_options": {
            "label": "Defensive Options",
            "items": [
                {
                    "item_id": "3157",
                    "name": "Zhonya's Hourglass",
                    "when": "Core item (already in core build) — vs any AD threat",
                    "why": "105 AP + 50 Armor + stasis. Mandatory for cougar-form dives.",
                },
                {
                    "item_id": "3102",
                    "name": "Banshee's Veil",
                    "when": "vs AP threats or key engage (replace Zhonya's if enemies are all AP)",
                    "why": "105 AP + 40 MR + spell shield. Blocks one ability.",
                },
            ],
        },
        "boots_options": {
            "label": "Boots",
            "items": [
                {
                    "item_id": "3020",
                    "name": "Sorcerer's Shoes",
                    "when": "Default — every game as Nidalee",
                    "why": "12 flat MPen. All damage is magic. Non-negotiable.",
                },
            ],
        },
        "power_spikes": [
            {
                "items": 1,
                "description": "Liandry's Torment — max range spears deal base damage + 8% max HP burn. "
                               "Clear speed improves significantly. Start invading enemy jungle.",
            },
            {
                "items": 2,
                "description": "Zhonya's — can dive into cougar form, execute, then stasis out. "
                               "This is when Nidalee becomes a real assassin. Gank with spear → cougar combo → stasis.",
            },
            {
                "items": 3,
                "description": "Deathcap/Void Staff — spears at max range with 400+ AP delete squishies. "
                               "Nidalee's mid-game is her strongest point — press your lead NOW.",
            },
        ],
        "client_export": {
            "title": "Nidalee JG - LolTracker",
            "associated_maps": [11],
            "blocks": [
                {
                    "type": "Core Build",
                    "items": [
                        {"id": "1101", "count": 1},
                        {"id": "3020", "count": 1},
                        {"id": "6653", "count": 1},
                        {"id": "3157", "count": 1},
                    ],
                },
                {
                    "type": "4th/5th Item Options",
                    "items": [
                        {"id": "3089", "count": 1},
                        {"id": "3135", "count": 1},
                        {"id": "3116", "count": 1},
                        {"id": "4629", "count": 1},
                    ],
                },
                {
                    "type": "Defense",
                    "items": [
                        {"id": "3157", "count": 1},
                        {"id": "3102", "count": 1},
                    ],
                },
                {
                    "type": "Boots",
                    "items": [
                        {"id": "3020", "count": 1},
                    ],
                },
            ],
        },
    },

    # ================================================================
    # NIDALEE SUPPORT
    # ================================================================
    "Nidalee:Support": {
        "champion_name": "Nidalee",
        "role": "Support",
        "title": "Nidalee Support — First Principles Build",
        "patch": "16.5.1",
        "skill_order": {
            "priority": "R > E > Q > W",
            "first_three": ["E", "Q", "W"],
            "reasoning": "E max — Primal Surge heal scales 150 + 35% AP at base, up to 300 + 70% AP on "
                         "low HP targets. ALSO gives 70% AS steroid to the target for 7s. Maxing E first "
                         "gives your ADC a massive AS buff in lane fights. Q second for poke damage. "
                         "W last — trap vision is useful at rank 1.",
        },
        "core_build": {
            "label": "Core Build",
            "items": ["6617", "3158", "3504", "6621"],
            "names": ["Moonstone Renewer", "Ionian Boots of Lucidity", "Ardent Censer", "Dawncore"],
            "notes": [
                "Moonstone Renewer — E heal triggers Moonstone chain heal to nearby allies. "
                "Nidalee E has one of the highest single-target heal ratios in the game (up to 70% AP "
                "on low targets). Moonstone amplifies the healing spread.",
                "Ionian Boots of Lucidity — 10 AH. Support income = cheap boots. More E heals per minute.",
                "Ardent Censer — 60 AP + 10% H/S Power. E already gives 70% AS for 7s. Ardent adds "
                "another 25% AS + magic damage on-hit. Your ADC gets 95% bonus AS for 7 seconds from "
                "one E cast. This is absurdly strong on attack-speed ADCs (Kog'Maw, Jinx, Vayne).",
                "Dawncore — 40 AP + 10% H/S Power. HP%-based bonus shields/heals. Stacks H/S Power "
                "with Ardent for massive E heals. Low HP targets get up to 300 + 70% AP × H/S multiplier.",
            ],
        },
        "first_back_variant": None,
        "fourth_item_options": {
            "label": "4th Item (game state dependent)",
            "options": [
                {
                    "item_id": "6616",
                    "name": "Staff of Flowing Water",
                    "when": "Team has 2+ AP damage dealers",
                    "why": "60 AP + 10% H/S Power. On heal: gives target 25 AP + 20 AH for 6s. "
                           "E heal triggers this — your ADC gets AS from Ardent AND your AP mid gets AP from Staff.",
                },
                {
                    "item_id": "3107",
                    "name": "Redemption",
                    "when": "Default — team healing in fights",
                    "why": "200 HP + 15% H/S Power. Active: AoE heal zone. Nidalee E is single-target only — "
                           "Redemption covers the team-wide healing gap.",
                },
                {
                    "item_id": "3065",
                    "name": "Spirit Visage",
                    "when": "vs AP threats AND you need to be tankier (surprisingly effective)",
                    "why": "60 MR + 450 HP + 25% heal amp. Amplifies your OWN E heal on yourself. "
                           "Nidalee support is squishy — Spirit Visage adds durability + self-heal.",
                },
            ],
        },
        "fifth_item_options": None,
        "defensive_options": {
            "label": "Defensive Options",
            "items": [
                {
                    "item_id": "3190",
                    "name": "Locket of the Iron Solari",
                    "when": "vs AoE burst (Orianna R, Diana R, MF R)",
                    "why": "Active: shield all nearby allies. Protects team from burst Nidalee E can't out-heal.",
                },
                {
                    "item_id": "3157",
                    "name": "Zhonya's Hourglass",
                    "when": "vs AD assassins diving backline",
                    "why": "105 AP + 50 Armor + stasis. AP still benefits E heal ratio.",
                },
            ],
        },
        "boots_options": {
            "label": "Boots",
            "items": [
                {
                    "item_id": "3158",
                    "name": "Ionian Boots of Lucidity",
                    "when": "Default — every game",
                    "why": "10 AH + 12 Summoner Spell Haste. More E heals, more Q poke.",
                },
                {
                    "item_id": "3009",
                    "name": "Boots of Swiftness",
                    "when": "Roaming-heavy games, need to ward deep",
                    "why": "60 MS + 25% slow resist. Cougar W (Pounce) + Swifties = fastest roaming support.",
                },
            ],
        },
        "power_spikes": [
            {
                "items": 1,
                "description": "Moonstone Renewer — E heal now chain-heals. Start prioritizing E on ADC in trades "
                               "for the 70% AS steroid + heal + Moonstone chain.",
            },
            {
                "items": 2,
                "description": "Ardent Censer — E gives ADC 70% + 25% = 95% bonus AS for 7 seconds. One E press "
                               "turns your ADC into a machine gun. Time E for all-ins and dragon fights.",
            },
            {
                "items": 3,
                "description": "Dawncore — H/S Power stacking makes E heals massive. Low HP ADC gets "
                               "healed for 300 + 70% AP × H/S multiplier. You're a heal bot that also "
                               "throws dangerous spears.",
            },
        ],
        "client_export": {
            "title": "Nidalee Support - LolTracker",
            "associated_maps": [11],
            "blocks": [
                {
                    "type": "Core Build (Enchanter)",
                    "items": [
                        {"id": "6617", "count": 1},
                        {"id": "3158", "count": 1},
                        {"id": "3504", "count": 1},
                        {"id": "6621", "count": 1},
                    ],
                },
                {
                    "type": "4th Item Options",
                    "items": [
                        {"id": "6616", "count": 1},
                        {"id": "3107", "count": 1},
                        {"id": "3065", "count": 1},
                    ],
                },
                {
                    "type": "Defense",
                    "items": [
                        {"id": "3190", "count": 1},
                        {"id": "3157", "count": 1},
                    ],
                },
                {
                    "type": "Boots",
                    "items": [
                        {"id": "3158", "count": 1},
                        {"id": "3009", "count": 1},
                    ],
                },
            ],
        },
    },

    # ================================================================
    # GAREN TOP
    # ================================================================
    "Garen:Top": {
        "champion_name": "Garen",
        "role": "Top",
        "title": "Garen Top — First Principles Build",
        "patch": "16.5.1",
        "skill_order": {
            "priority": "R > E > Q > W",
            "first_three": ["Q", "E", "W"],
            "reasoning": "E max — Judgment is Garen's primary damage. Each tick scales with total AD and can "
                         "crit at 30% efficiency. More ranks = more base damage per tick. E gains +1 tick per "
                         "25% bonus AS (from items/runes). Q second for silence duration (1.5→2.5s) + burst. "
                         "W one early for shield (18% bonus HP), then max last.",
        },
        "core_build": {
            "label": "Core Build",
            "items": ["3078", "3006", "3742"],
            "names": ["Trinity Force", "Berserker's Greaves", "Dead Man's Plate"],
            "notes": [
                "Trinity Force — Spellblade + Threefold Strike AS. Q auto-reset procs Spellblade. "
                "The AS from Threefold Strike adds E ticks (+1 tick per 25% bonus AS). 33 AD + 25% AS "
                "+ 20 AH + 300 HP. Best 1-item spike for Garen because it amplifies both Q burst and E DPS.",
                "Berserker's Greaves — 25% AS = +1 extra E tick. Garen's E ticks scale with bonus AS. "
                "Berserker's is 1100g for an extra tick on every E — extremely gold efficient. "
                "Yes, Berserker's on Garen. The math checks out.",
                "Dead Man's Plate — 300 HP + 45 Armor + MS ramping passive. Momentum charges "
                "give up to 60 bonus MS. Garen's biggest problem is getting to targets — DMP "
                "closes the gap. Q already gives MS + silences, DMP stacks with that.",
            ],
        },
        "first_back_variant": {
            "label": "Tank-First Variant (losing lane)",
            "items": ["3068", "3047", "3071"],
            "names": ["Sunfire Aegis", "Plated Steelcaps", "Black Cleaver"],
            "notes": [
                "If behind in lane, go tanky first. Sunfire gives waveclear + combat DPS from Immolate "
                "burn. Steelcaps for armor. Black Cleaver 2nd — E ticks apply Cleaver stacks rapidly "
                "(each tick = 1 stack, 6 stacks in ~2s for 30% armor shred). This path is lower burst "
                "but higher sustained damage vs armor stackers.",
            ],
        },
        "fourth_item_options": {
            "label": "4th Item (game state dependent)",
            "options": [
                {
                    "item_id": "3071",
                    "name": "Black Cleaver",
                    "when": "Enemy team has 2+ armor stackers",
                    "why": "55 AD + 300 HP + 20 AH. E ticks apply Carve stacks (5% armor reduction per stack, "
                           "up to 30%). Each E tick is a separate instance — 6 stacks in ~2 seconds. Enemy tank "
                           "with 200 armor loses 60 armor from E alone.",
                },
                {
                    "item_id": "3181",
                    "name": "Hullbreaker",
                    "when": "Split-push focused game, enemy can't 1v1 you",
                    "why": "60 AD + 400 HP. Boarding Party: enhanced damage to towers when solo. "
                           "Garen + Hullbreaker splits are extremely threatening — Q silences the defender, "
                           "E + Hullbreaker melts towers.",
                },
                {
                    "item_id": "6333",
                    "name": "Death's Dance",
                    "when": "vs AD-heavy teams, teamfight-focused",
                    "why": "30% damage delayed as bleed. Defy cleanses on takedown. R execute on villain "
                           "grants the takedown — DD bleed cleanse + heal after ulting.",
                },
                {
                    "item_id": "3065",
                    "name": "Spirit Visage",
                    "when": "vs AP threats + amplifies passive regen",
                    "why": "60 MR + 450 HP + 25% heal boost. Garen passive (Perseverance) heals 2-8% max HP/s "
                           "out of combat. Spirit Visage amplifies this by 25%. Also boosts W shield.",
                },
            ],
        },
        "fifth_item_options": {
            "label": "5th Item",
            "options": [
                {
                    "item_id": "3143",
                    "name": "Randuin's Omen",
                    "when": "vs crit ADCs",
                    "why": "400 HP + 60 Armor + crit damage reduction + AoE slow active.",
                },
                {
                    "item_id": "4401",
                    "name": "Force of Nature",
                    "when": "vs sustained AP damage",
                    "why": "60 MR + 350 HP + 10% MS + stacking MR passive.",
                },
                {
                    "item_id": "2501",
                    "name": "Overlord's Bloodmail",
                    "when": "Ahead and want raw stats + bulk",
                    "why": "60 AD + 800 HP. Colossal Consumption: gain max HP when taking down champions. "
                           "W shield = 18% bonus HP — 800 HP item means +144 shield value alone.",
                },
            ],
        },
        "defensive_options": {
            "label": "Defensive Options",
            "items": [
                {
                    "item_id": "3065",
                    "name": "Spirit Visage",
                    "when": "vs AP + amplifies passive regen and W shield",
                    "why": "60 MR + 450 HP + 25% heal/shield amp. Core MR item for Garen.",
                },
                {
                    "item_id": "4401",
                    "name": "Force of Nature",
                    "when": "vs sustained AP (Brand, Cassio, Teemo, Lillia)",
                    "why": "60 MR + 350 HP + 10% MS + stacking MR. Better than SV vs DoT mages.",
                },
                {
                    "item_id": "3143",
                    "name": "Randuin's Omen",
                    "when": "vs heavy crit (2+ crit ADCs)",
                    "why": "400 HP + 60 Armor + crit damage reduction.",
                },
                {
                    "item_id": "3083",
                    "name": "Warmog's Armor",
                    "when": "Siege/poke — need to reset between fights",
                    "why": "800 HP + regen passive. Stacks with Garen passive for infinite sustain between fights.",
                },
            ],
        },
        "boots_options": {
            "label": "Boots",
            "items": [
                {
                    "item_id": "3006",
                    "name": "Berserker's Greaves",
                    "when": "Default — extra E tick is too good to pass up",
                    "why": "25% AS = +1 E tick. Gold efficient damage increase for Garen specifically.",
                },
                {
                    "item_id": "3047",
                    "name": "Plated Steelcaps",
                    "when": "vs heavy auto-attackers AND you went tank build",
                    "why": "25 Armor + 10% auto damage reduction. Take when not building Trinity.",
                },
                {
                    "item_id": "3111",
                    "name": "Mercury's Treads",
                    "when": "vs heavy CC (3+ hard CC abilities targeting you)",
                    "why": "25 MR + 30% tenacity. Garen needs to stick to targets — CC = kited = useless.",
                },
            ],
        },
        "power_spikes": [
            {
                "items": 1,
                "description": "Trinity Force — Q Spellblade burst + E ticks with Threefold AS. Start forcing "
                               "trades: Q → E → back off. Sheen component (1050g) is a strong early spike.",
            },
            {
                "items": 2,
                "description": "Dead Man's Plate — MS to reach targets + armor. Q silence → run at them with DMP "
                               "momentum → E spin → R execute. Garen hits his stride at 2 items.",
            },
            {
                "items": 3,
                "description": "Black Cleaver / Death's Dance — full teamfight presence. E shreds armor for your "
                               "team, Q silences key targets, R true damage executes the villain. "
                               "W shield (18% bonus HP with ~1000 bonus HP) tanks a full ability rotation.",
            },
        ],
        "client_export": {
            "title": "Garen Top - LolTracker",
            "associated_maps": [11],
            "blocks": [
                {
                    "type": "Core Build (Trinity)",
                    "items": [
                        {"id": "3078", "count": 1},
                        {"id": "3006", "count": 1},
                        {"id": "3742", "count": 1},
                    ],
                },
                {
                    "type": "Tank Variant (Behind)",
                    "items": [
                        {"id": "3068", "count": 1},
                        {"id": "3047", "count": 1},
                        {"id": "3071", "count": 1},
                    ],
                },
                {
                    "type": "4th/5th Options",
                    "items": [
                        {"id": "3071", "count": 1},
                        {"id": "3181", "count": 1},
                        {"id": "6333", "count": 1},
                        {"id": "2501", "count": 1},
                    ],
                },
                {
                    "type": "vs AP",
                    "items": [
                        {"id": "3065", "count": 1},
                        {"id": "4401", "count": 1},
                    ],
                },
                {
                    "type": "vs AD / Tank",
                    "items": [
                        {"id": "3143", "count": 1},
                        {"id": "3083", "count": 1},
                    ],
                },
                {
                    "type": "Boots",
                    "items": [
                        {"id": "3006", "count": 1},
                        {"id": "3047", "count": 1},
                        {"id": "3111", "count": 1},
                    ],
                },
            ],
        },
    },

    # ================================================================
    # MASTER YI JUNGLE
    # ================================================================
    "MasterYi:Jungle": {
        "champion_name": "MasterYi",
        "role": "Jungle",
        "title": "Master Yi Jungle — First Principles Build",
        "patch": "16.5.1",
        "skill_order": {
            "priority": "R > Q > E > W",
            "first_three": ["Q", "E", "W"],
            "reasoning": "Q max — Alpha Strike. Each rank adds 35 base damage + reduces CD. Q applies on-hit "
                         "at 75% effectiveness and can crit. It's his gap closer, damage, and untargetability. "
                         "E second — Wuju Style adds 20-40 + 35% bAD true damage on-hit. Each rank adds "
                         "5 true damage. W one point early for damage reduction + auto-reset.",
        },
        "core_build": {
            "label": "Core Build",
            "items": ["1102", "3006", "3153", "3124"],
            "names": ["Gustwalker Hatchling", "Berserker's Greaves", "Blade of The Ruined King",
                      "Guinsoo's Rageblade"],
            "notes": [
                "Gustwalker — movement speed in brush. Yi needs to reach targets from jungle paths. "
                "Gustwalker gives MS for ganking and invading.",
                "Berserker's Greaves — 25% AS. Yi's damage is entirely auto-attack based. More AS = "
                "more on-hit procs (E true damage, BOTRK %HP, Guinsoo's phantom hit). Rush early.",
                "Blade of The Ruined King — 40 AD + 25% AS + 10% current HP on-hit. Yi E already "
                "adds true damage per auto. BOTRK adds %HP physical damage per auto. Together, "
                "each auto deals: base AD + BOTRK %HP + E true damage. The %HP on-hit is especially "
                "valuable because Q applies on-hit at 75%, so Q → auto is a burst combo vs tanks.",
                "Guinsoo's Rageblade — 30% AS + Seething Strike passive: on-hit effects trigger a "
                "phantom hit every 3rd auto. This means every 3rd auto procs BOTRK, Wuju Style, "
                "and any other on-hit TWICE. With R active (25-65% bonus AS), Yi attacks fast enough "
                "that phantom hits happen constantly. This is Yi's highest DPS spike.",
            ],
        },
        "first_back_variant": None,
        "fourth_item_options": {
            "label": "4th Item (game state dependent)",
            "options": [
                {
                    "item_id": "3302",
                    "name": "Terminus",
                    "when": "Default — best on-hit DPS item after Guinsoo's",
                    "why": "30 AD + 30% AS. Alternates between Light (armor/MR shred) and Dark (armor/MR gain) "
                           "stacks on-hit. With Guinsoo's phantom hits, stacks build fast. Yi deals mixed damage "
                           "(physical autos + E true damage + BOTRK physical) — Terminus shreds both resists.",
                },
                {
                    "item_id": "3091",
                    "name": "Wit's End",
                    "when": "vs AP-heavy enemy team (2+ AP threats)",
                    "why": "40 AD + 40% AS + 40 MR + magic damage on-hit. Defensive AND offensive vs AP. "
                           "On-hit procs with Guinsoo's. 40 MR is enough to survive AP burst.",
                },
                {
                    "item_id": "6333",
                    "name": "Death's Dance",
                    "when": "vs AD burst (assassins diving you in fights)",
                    "why": "30% damage delayed as bleed. Defy cleanses on takedown. Yi R resets on kills — "
                           "every kill in R cleanses DD bleed. Multi-kill Yi with DD is unkillable.",
                },
            ],
        },
        "fifth_item_options": {
            "label": "5th Item",
            "options": [
                {
                    "item_id": "3302",
                    "name": "Terminus",
                    "when": "Didn't buy 4th — resistance shred + damage",
                    "why": "Shreds armor + MR for your mixed damage profile.",
                },
                {
                    "item_id": "3156",
                    "name": "Maw of Malmortius",
                    "when": "vs AP burst that one-shots you",
                    "why": "60 AD + 40 MR + magic damage shield. Shield gives you time to Q + lifesteal back.",
                },
                {
                    "item_id": "3026",
                    "name": "Guardian Angel",
                    "when": "General teamfight insurance",
                    "why": "55 AD + 45 Armor + revive. Yi dives deep — revive gives second chance to clean up.",
                },
            ],
        },
        "defensive_options": {
            "label": "Defensive Options",
            "items": [
                {
                    "item_id": "6333",
                    "name": "Death's Dance",
                    "when": "vs AD threats — best defensive item for Yi",
                    "why": "30% damage delay + cleanse on kill. Yi gets resets (R + Q CD reduction on kill). "
                           "Each kill cleanses DD bleed + heals. Chain kills = invincible.",
                },
                {
                    "item_id": "3156",
                    "name": "Maw of Malmortius",
                    "when": "vs AP assassins or high AP burst",
                    "why": "60 AD + 40 MR + magic damage shield at 30% HP.",
                },
                {
                    "item_id": "3091",
                    "name": "Wit's End",
                    "when": "vs AP threats where you want DPS + defense",
                    "why": "40 AD + 40% AS + 40 MR + on-hit. Offensive AND defensive. Guinsoo's synergy.",
                },
                {
                    "item_id": "3026",
                    "name": "Guardian Angel",
                    "when": "General — revive after diving in with Q",
                    "why": "55 AD + 45 Armor + revive.",
                },
            ],
        },
        "boots_options": {
            "label": "Boots",
            "items": [
                {
                    "item_id": "3006",
                    "name": "Berserker's Greaves",
                    "when": "Default — 95% of games",
                    "why": "25% AS. Yi is an auto-attack champion. Non-negotiable.",
                },
                {
                    "item_id": "3047",
                    "name": "Plated Steelcaps",
                    "when": "vs full AD comp with heavy auto-attackers",
                    "why": "25 Armor + 10% auto damage reduction. Only if enemy is 4-5 AD.",
                },
                {
                    "item_id": "3111",
                    "name": "Mercury's Treads",
                    "when": "vs heavy CC (point-and-click CC that Q can't dodge)",
                    "why": "25 MR + 30% tenacity. Yi can dodge skillshot CC with Q, but can't dodge "
                           "point-and-click (Pantheon W, Twisted Fate gold card, Malzahar R).",
                },
            ],
        },
        "power_spikes": [
            {
                "items": 1,
                "description": "BOTRK — %HP on-hit makes Yi dangerous vs all HP levels. First back Recurve Bow "
                               "(700g) or Vampiric Scepter (900g). Start looking for ganks on overextended lanes.",
            },
            {
                "items": 2,
                "description": "Guinsoo's Rageblade — phantom hit every 3rd auto doubles all on-hit effects. "
                               "BOTRK + E true damage proc twice every 3 autos. This is Yi's biggest power spike. "
                               "With R active, you shred anything. Force objectives (Dragon, Rift Herald).",
            },
            {
                "items": 3,
                "description": "Terminus / Wit's End — resistance shred or MR. Yi at 3 items with R active "
                               "kills squishies in 2-3 autos and tanks in 5-6. Play for resets in teamfights — "
                               "R duration extends on kills, Q CD resets on kills.",
            },
            {
                "items": 4,
                "description": "Full build Yi is the premier 1v9 carry. Every auto procs 4+ on-hit effects. "
                               "Q applies all on-hit at 75% + can crit. With DD, kills cleanse damage. "
                               "Play patient — wait for key CC to be used, then Q in.",
            },
        ],
        "client_export": {
            "title": "Master Yi JG - LolTracker",
            "associated_maps": [11],
            "blocks": [
                {
                    "type": "Core Build",
                    "items": [
                        {"id": "1102", "count": 1},
                        {"id": "3006", "count": 1},
                        {"id": "3153", "count": 1},
                        {"id": "3124", "count": 1},
                    ],
                },
                {
                    "type": "4th/5th Item Options",
                    "items": [
                        {"id": "3302", "count": 1},
                        {"id": "3091", "count": 1},
                        {"id": "6333", "count": 1},
                    ],
                },
                {
                    "type": "Defense",
                    "items": [
                        {"id": "6333", "count": 1},
                        {"id": "3156", "count": 1},
                        {"id": "3091", "count": 1},
                        {"id": "3026", "count": 1},
                    ],
                },
                {
                    "type": "Boots",
                    "items": [
                        {"id": "3006", "count": 1},
                        {"id": "3047", "count": 1},
                        {"id": "3111", "count": 1},
                    ],
                },
            ],
        },
    },

    # ================================================================
    # URGOT TOP
    # ================================================================
    "Urgot:Top": {
        "champion_name": "Urgot",
        "role": "Top",
        "title": "Urgot Top — First Principles Build",
        "patch": "16.5.1",
        "skill_order": {
            "priority": "R > W > Q > E",
            "first_three": ["Q", "E", "W"],
            "reasoning": "W max — Purge. At rank 5 (level 9), W becomes a free toggle with no mana cost. "
                         "This is Urgot's biggest power spike. W locks on to the nearest enemy and fires at "
                         "3.0 fixed AS, applying on-hit at 50%. Before rank 5, W costs mana and has a duration. "
                         "Q second for poke + slow (65-85%). E last — flip is powerful but ranks only add damage.",
        },
        "core_build": {
            "label": "Core Build",
            "items": ["3071", "3047", "3748"],
            "names": ["Black Cleaver", "Plated Steelcaps", "Titanic Hydra"],
            "notes": [
                "Black Cleaver — THE Urgot item. W fires at 3.0 AS = 6 Cleaver stacks (30% armor shred) "
                "in 2 seconds. No other champion in the game stacks Cleaver this fast. 55 AD + 300 HP + 20 AH. "
                "Passive legs also apply Cleaver stacks. Q slow → W → 2 seconds = full armor shred.",
                "Plated Steelcaps — 25 Armor + 10% auto damage reduction. Urgot is a juggernaut — Steelcaps "
                "reduces incoming auto damage. Urgot does NOT scale with AS (W is fixed at 3.0), so "
                "Berserker's is completely wasted. Steelcaps are strictly better.",
                "Titanic Hydra — 50 AD + 500 HP + Cleave passive. Auto attacks deal bonus damage based on "
                "max HP. W fires 3 autos/sec — each one cleaves. With Titanic, W becomes an AoE shredder. "
                "500 HP also powers passive legs (2-6% max HP + 40-100% tAD per leg).",
            ],
        },
        "first_back_variant": None,
        "fourth_item_options": {
            "label": "4th Item (game state dependent)",
            "options": [
                {
                    "item_id": "6665",
                    "name": "Jak'Sho, The Protean",
                    "when": "Default — need mixed resists + durability",
                    "why": "300 HP + 30 Armor + 30 MR. Voidborn Resilience: ramp Armor/MR in combat. "
                           "Urgot W keeps you in combat constantly — Jak'Sho stacks are always full. "
                           "At max stacks, drain 3% max HP from nearby enemies (free damage while W-ing).",
                },
                {
                    "item_id": "3065",
                    "name": "Spirit Visage",
                    "when": "vs AP threats + want to amplify any healing (lifesteal from runes/items)",
                    "why": "60 MR + 450 HP + 25% heal amp. If running Conqueror, the healing at full stacks "
                           "is amplified. Also good with Triumph rune.",
                },
                {
                    "item_id": "6333",
                    "name": "Death's Dance",
                    "when": "vs AD-heavy teams, teamfight focused",
                    "why": "30% damage delayed as bleed. Defy cleanses on takedown. Urgot R execute = guaranteed "
                           "takedown on the feared target. DD bleed cleanse + heal after R execute.",
                },
                {
                    "item_id": "3181",
                    "name": "Hullbreaker",
                    "when": "Split-push focused, enemy can't 1v1 you",
                    "why": "60 AD + 400 HP. Urgot is already a strong duelist — Hullbreaker makes towers "
                           "melt under W + Titanic + Hullbreaker enhanced autos.",
                },
            ],
        },
        "fifth_item_options": {
            "label": "5th Item",
            "options": [
                {
                    "item_id": "3143",
                    "name": "Randuin's Omen",
                    "when": "vs heavy crit ADCs",
                    "why": "400 HP + 60 Armor + crit damage reduction + AoE slow.",
                },
                {
                    "item_id": "4401",
                    "name": "Force of Nature",
                    "when": "vs sustained AP damage (DoT mages, DPS mages)",
                    "why": "60 MR + 350 HP + 10% MS + stacking MR passive.",
                },
                {
                    "item_id": "3083",
                    "name": "Warmog's Armor",
                    "when": "Poke comps — need out-of-combat regen",
                    "why": "800 HP + regen passive. 800 HP also boosts passive leg damage and Titanic Cleave.",
                },
                {
                    "item_id": "2501",
                    "name": "Overlord's Bloodmail",
                    "when": "Ahead — want raw HP + AD for maximum leg damage",
                    "why": "60 AD + 800 HP. Passive legs scale with max HP (2-6% max HP). "
                           "800 HP = each leg does 16-48 extra damage. Colossal Consumption stacks "
                           "more HP on takedowns.",
                },
            ],
        },
        "defensive_options": {
            "label": "Defensive Options",
            "items": [
                {
                    "item_id": "6665",
                    "name": "Jak'Sho, The Protean",
                    "when": "Default mixed-resist tank item",
                    "why": "30 Armor + 30 MR + 300 HP. Ramps both resists in combat. W keeps it stacked.",
                },
                {
                    "item_id": "3065",
                    "name": "Spirit Visage",
                    "when": "vs AP threats",
                    "why": "60 MR + 450 HP + 25% heal amp.",
                },
                {
                    "item_id": "4401",
                    "name": "Force of Nature",
                    "when": "vs sustained AP (Brand, Lillia, Cassio)",
                    "why": "60 MR + 350 HP + 10% MS + stacking MR passive.",
                },
                {
                    "item_id": "3143",
                    "name": "Randuin's Omen",
                    "when": "vs crit ADCs",
                    "why": "400 HP + 60 Armor + crit damage reduction.",
                },
                {
                    "item_id": "3075",
                    "name": "Thornmail",
                    "when": "vs healing + auto-attack threats",
                    "why": "350 HP + 75 Armor + GW on being hit. E flip puts them in melee range — "
                           "they auto you while you W them, both taking and dealing damage.",
                },
            ],
        },
        "boots_options": {
            "label": "Boots",
            "items": [
                {
                    "item_id": "3047",
                    "name": "Plated Steelcaps",
                    "when": "Default — most games (most top laners are AD)",
                    "why": "25 Armor + 10% auto damage reduction. Urgot doesn't scale with AS — "
                           "Steelcaps are always the right choice vs AD.",
                },
                {
                    "item_id": "3111",
                    "name": "Mercury's Treads",
                    "when": "vs heavy CC + AP lane opponent (Kennen, Teemo, Rumble)",
                    "why": "25 MR + 30% tenacity. Take when enemy team has 3+ hard CC abilities.",
                },
            ],
        },
        "power_spikes": [
            {
                "items": 0,
                "description": "Level 9 (W rank 5) — W becomes a free toggle with no mana cost. This is Urgot's "
                               "biggest spike, even bigger than any item. Before 9, W costs mana and has a duration. "
                               "After 9, you can perma-W in every fight. Play around this power spike.",
            },
            {
                "items": 1,
                "description": "Black Cleaver — 30% armor shred in 2 seconds via W. Q slow into W with Cleaver "
                               "shreds any target. Start forcing extended trades — you win every trade with Cleaver stacks.",
            },
            {
                "items": 2,
                "description": "Titanic Hydra — W fires at 3.0 AS, each auto cleaves (bonus max HP damage). "
                               "AoE DPS is massive. You melt waves and jungle camps. In teamfights, stand near "
                               "the frontline and W — Titanic cleaves hit everyone around your target.",
            },
            {
                "items": 3,
                "description": "Jak'Sho / Death's Dance — now properly tanky. Urgot at 3 items is a raid boss. "
                               "W + passive legs (every 30s per leg, 6 legs total) + Titanic cleave + Cleaver shred "
                               "= massive sustained DPS while being nearly unkillable.",
            },
        ],
        "client_export": {
            "title": "Urgot Top - LolTracker",
            "associated_maps": [11],
            "blocks": [
                {
                    "type": "Core Build",
                    "items": [
                        {"id": "3071", "count": 1},
                        {"id": "3047", "count": 1},
                        {"id": "3748", "count": 1},
                    ],
                },
                {
                    "type": "4th/5th Options",
                    "items": [
                        {"id": "6665", "count": 1},
                        {"id": "6333", "count": 1},
                        {"id": "3181", "count": 1},
                        {"id": "2501", "count": 1},
                    ],
                },
                {
                    "type": "vs AP",
                    "items": [
                        {"id": "3065", "count": 1},
                        {"id": "4401", "count": 1},
                    ],
                },
                {
                    "type": "vs AD / Tank",
                    "items": [
                        {"id": "3143", "count": 1},
                        {"id": "3075", "count": 1},
                        {"id": "3083", "count": 1},
                    ],
                },
                {
                    "type": "Boots",
                    "items": [
                        {"id": "3047", "count": 1},
                        {"id": "3111", "count": 1},
                    ],
                },
            ],
        },
    },
}


def get_build_guide(champion_name, role=None):
    """Get build guide for a champion, optionally filtered by role.
    Returns the guide dict or None if not found."""
    if role:
        key = f"{champion_name}:{role}"
        return BUILD_GUIDES.get(key)

    # Search for any role
    for key, guide in BUILD_GUIDES.items():
        if key.startswith(f"{champion_name}:"):
            return guide
    return None


def get_all_guides_for_champion(champion_name):
    """Get all build guides for a champion (may have multiple roles)."""
    guides = []
    for key, guide in BUILD_GUIDES.items():
        if key.startswith(f"{champion_name}:"):
            guides.append(guide)
    return guides


def generate_client_export(champion_name, role=None, champion_id=None):
    """Generate League client item set JSON for clipboard export.

    champion_id is resolved from Data Dragon by the caller (app.py).
    If not provided, associatedChampions is left empty (shows for all champs).
    """
    guide = get_build_guide(champion_name, role)
    if not guide or "client_export" not in guide:
        return None

    export = guide["client_export"]
    assoc_champs = [champion_id] if champion_id else []
    return {
        "title": export["title"],
        "associatedMaps": export["associated_maps"],
        "associatedChampions": assoc_champs,
        "blocks": export["blocks"],
    }


def list_available_guides():
    """Return a list of available build guides with champion name and role."""
    return [
        {"champion_name": g["champion_name"], "role": g["role"], "key": k}
        for k, g in BUILD_GUIDES.items()
    ]
