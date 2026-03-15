# Champion Build Analysis Methodology

How to produce a first-principles optimal build analysis for LolTracker.
This document describes the exact process used for Yunara ADC and Teemo JG
so that future champion analyses are consistent and reproducible.

## Philosophy

- NO copying from op.gg, u.gg, or any community site
- Every item choice must be justified from ability ratios, base stats, and
  item stat cross-referencing
- The user plays high elo and will push back on lazy reasoning — the analysis
  must hold up under scrutiny
- Builds are situational, not one-size-fits-all: document the decision tree

## Step-by-Step Process

### 1. Gather Champion Data

Source: CommunityDragon (raw game data), NOT the wiki

For the target champion, extract:
- **Base stats**: AD, AS, HP, mana, armor, MR, range, MS
- **Growth stats**: Per-level scaling for each stat
- **Every ability ratio**: Base damage, AD ratios, AP ratios, bonus vs total,
  on-hit effects, DoT ticks, special interactions
- **Passive**: Often the most build-defining mechanic
- **Special mechanics**: Crit interactions, on-hit modifiers, monster damage
  modifiers, empowered auto resets, AoE spread mechanics

Document all of this in a raw data section before making any build decisions.

### 2. Identify the Core Scaling Mechanic

Ask: "What stat makes this champion's kit deal the most damage per gold spent?"

Examples:
- Yunara: Crit + AS + on-hit. Passive adds magic damage on crits. Q adds
  on-hit damage. Spread autos can crit and apply 30% on-hit. Answer: crit
  chance × attack speed × on-hit value
- Teemo JG: AP. Every damage source (E on-hit, E DoT, Q, R) scales with AP.
  160% monster damage on E. Answer: raw AP stacking with magic pen

This determines the item class (crit/AS items, AP items, lethality, etc).

### 3. Evaluate Every Candidate Item

For the champion's primary stat class, evaluate EVERY completed item:
- Read the ACTUAL current patch stats (items change every patch)
- Calculate effective DPS/burst contribution with the champion's specific ratios
- Note build path accessibility (can you buy components on realistic back timings?)
- Note special passives and how they interact with the champion's kit

CRITICAL: Verify item stats against the current patch. Common mistakes:
- Items that used to have crit may not anymore (Kraken Slayer, Bloodthirster)
- AP values, AH values, and passives change frequently
- New items may exist that weren't in training data

### 4. Determine Item Order (Build Path)

First item: What gives the biggest 1-item power spike for this champion?
- Consider build path — smooth (many cheap components) vs demanding (needs
  B.F. Sword or other big-ticket component)
- Consider the role's economy — ADC gets farm gold, JG gets camp gold
- First back timing matters: 1200g is reliable, 1300g+ is greedy

Each subsequent item: What's the marginal DPS increase per gold?
- Account for stat interactions (crit × IE passive, pen × AP, etc.)
- Account for power spike timings (2-item, 3-item breakpoints)

### 5. Map the Situational Decision Tree

At each item slot past core (usually 4th/5th item), document:
- **What**: The item
- **When**: The game state that makes this the right choice
- **Why**: The mechanical reasoning (not just "it's good")

Categories to cover:
- 4th/5th item options (offensive choices based on game state)
- Defensive options (mapped to specific threat types):
  - vs AD assassins (burst physical)
  - vs AP assassins (burst magic)
  - vs bruisers/fighters (sustained physical)
  - vs heavy healing (anti-heal)
  - vs heavy armor (armor pen)
  - vs CC-dependent comps (QSS/cleanse)
- Boots options (when to deviate from default)

### 6. Identify Power Spikes

For each completed item (1-item, 2-item, 3-item, 4-item), write:
- What changes about the champion's combat pattern at this breakpoint
- What the player should DO differently once they hit this spike
- Specific damage numbers if meaningful (e.g., "shrooms deal 658 each")

### 7. Structure for build_guides.py

Once the analysis is complete, encode it into the BUILD_GUIDES dict format:

```python
"ChampionName:Role": {
    "champion_name": "ChampionName",
    "role": "Role",            # Bot, Jungle, Mid, Top, Support
    "title": "ChampionName Role — First Principles Build",
    "patch": "XX.X.X",
    "skill_order": {
        "priority": "R > X > Y > Z",
        "first_three": ["X", "Y", "Z"],
        "reasoning": "...",
    },
    "core_build": {
        "label": "Core Build",
        "items": ["item_id", ...],       # Order matters
        "names": ["Item Name", ...],
        "notes": ["Per-item explanation", ...],
    },
    "first_back_variant": { ... } or None,
    "fourth_item_options": {
        "label": "4th Item",
        "options": [
            {"item_id": "XXXX", "name": "...", "when": "...", "why": "..."},
        ],
    },
    "fifth_item_options": { ... } or None,
    "defensive_options": {
        "label": "Defensive Options",
        "items": [
            {"item_id": "XXXX", "name": "...", "when": "...", "why": "..."},
        ],
    },
    "boots_options": { ... },
    "power_spikes": [
        {"items": 1, "description": "..."},
        {"items": 2, "description": "..."},
    ],
    "client_export": {
        "title": "ChampName Role - LolTracker",
        "associated_maps": [11],    # SR only
        "blocks": [
            {"type": "Section Name", "items": [{"id": "XXXX", "count": 1}]},
        ],
    },
}
```

Champion ID is resolved dynamically from Data Dragon at export time — do NOT
hardcode it.

### 8. Verify

- Check that every item_id in the guide is a valid current-patch item
- Check that all item names match their IDs
- Confirm the skill order matches the ability analysis
- Run the export endpoint and verify the JSON is valid for League client import

## Data Sources

- **CommunityDragon**: Raw ability data (ratios, base values, scaling)
  `https://raw.communitydragon.org/latest/game/data/characters/{champion}/`
- **Data Dragon**: Item data, champion IDs, icons
  `https://ddragon.leagueoflegends.com/cdn/{version}/data/en_US/item.json`
- **In-game testing**: Verify interactions that aren't clear from data
  (e.g., does Runaan's bolt trigger this passive?)

## Common Pitfalls

1. **Trusting outdated item data**: Always verify current patch stats
2. **Ignoring build path**: A theoretically perfect item is useless if you
   can't buy its components on realistic back timings
3. **One build for all games**: Every game has a different enemy comp.
   The decision tree IS the build guide, not a single item list
4. **Copying pro builds**: Pros play in coordinated 5v5 with voice comms.
   Solo queue requires different defensive itemization
5. **Ignoring AP ratios on AD champions**: Yunara's passive and Q both
   scale with AP — Zhonya's (105 AP) isn't just a defensive item for her
