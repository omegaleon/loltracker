"""LLM client for build analysis using Claude Haiku 4.5.

Post-game: Sends match context (all 10 players, their champions, roles,
items) to Claude and receives structured JSON build recommendations.

Pre-game (live): Sends draft context (champions, roles, ranks — no items)
and receives a recommended build path for the upcoming game.
"""

import json
import logging
import os

import anthropic

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "claude-haiku-4-5"
AVAILABLE_MODELS = {
    "claude-haiku-4-5": "Haiku (Fast)",
    "claude-sonnet-4-5": "Sonnet (Smarter)",
}
MAX_TOKENS = 1500

SYSTEM_PROMPT = """You are a League of Legends build analyst. You reason ONLY from the item data provided in each prompt. Do NOT rely on memory about items — READ the item descriptions given to you.

FORMAT RULES:
- Recommend exactly 6 items: 5 completed items + 1 pair of boots.
- Do NOT include trinkets (Farsight Alteration, Oracle Lens, Stealth Ward) — they are free and not build items.
- Do NOT include starter items (Doran's, Dark Seal, Cull, support starters).
- Do NOT include components — only finished items from the VALID ITEMS list.

MECHANICAL RULES THAT ARE NOT IN ITEM DESCRIPTIONS:
- Lord Dominik's Regards, Mortal Reminder, AND Serylda's Grudge ALL build from Last Whisper — they are MUTUALLY EXCLUSIVE. You can only build ONE of these three.
- Some champions are hybrid (Kai'Sa, Katarina, Varus, Corki, Ezreal, etc.) and can build AD or AP. Look at what they are ACTUALLY building in the game to determine their path — do not assume.

REASONING APPROACH:
1. READ the item descriptions provided — check what stats each item gives and what its passive does.
2. Look at the champion and what stats they scale with based on their actual build in this game.
3. Consider the enemy team composition and what they built.
4. Recommend items whose stats and passives address this specific game's needs.
5. Order items by purchase priority — strongest power spike first, situational items later."""

# Lazy-initialized client (only created when first needed)
_client = None


def _get_client():
    """Get or create the Anthropic client."""
    global _client
    if _client is None:
        api_key = os.environ.get("ANTHROPIC_API_KEY", "")
        if not api_key:
            # Fall back to claude.key file for local dev
            key_path = os.path.join(os.path.dirname(__file__), "claude.key")
            if os.path.exists(key_path):
                with open(key_path) as f:
                    api_key = f.read().strip()
        if not api_key:
            raise RuntimeError(
                "ANTHROPIC_API_KEY not set and no claude.key file found"
            )
        _client = anthropic.Anthropic(api_key=api_key)
    return _client


def is_available() -> bool:
    """Check if the Anthropic API key is configured."""
    try:
        _get_client()
        return True
    except RuntimeError:
        return False


def get_valid_item_names(item_map: dict) -> list[str]:
    """Extract completed item + boots names from Data Dragon item_map.

    Filters to items costing >= 2200g (completed) or boots >= 900g.
    Deduplicates by name (Ornn upgrades share names with originals).
    Returns sorted list of unique item names that the LLM may recommend.
    """
    names = set()
    for item_id, info in item_map.items():
        gold = info.get("gold", 0)
        name = info.get("name", "")
        if not name:
            continue
        # Include completed items (2200+) and boots (900-1300 range)
        if gold >= 2200 or (900 <= gold <= 1300 and (
            "boots" in name.lower() or "greaves" in name.lower()
            or "treads" in name.lower() or "shoes" in name.lower()
            or "swiftness" in name.lower() or "lucidity" in name.lower()
            or "steelcaps" in name.lower() or "swiftmarch" in name.lower()
            or "crushers" in name.lower() or "advance" in name.lower()
            or "crimson" in name.lower() or "spellslinger" in name.lower()
            or "gunmetal" in name.lower()
        )):
            names.add(name)
    return sorted(names)


def _strip_html(text: str) -> str:
    """Strip HTML tags from Data Dragon item descriptions."""
    import re
    text = re.sub(r'<br\s*/?>', ' | ', text)
    text = re.sub(r'<[^>]+>', '', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def _valid_items_block(item_map: dict) -> str:
    """Build the VALID ITEMS section with full descriptions for prompts.

    Includes item name, gold cost, stats, and passive descriptions
    so the LLM can reason from actual item data instead of guessing.
    """
    valid_names = set(get_valid_item_names(item_map))
    if not valid_names:
        return ""

    lines = []
    for item_id in sorted(item_map.keys()):
        info = item_map[item_id]
        name = info.get("name", "")
        if name not in valid_names:
            continue
        # Remove duplicates (first occurrence wins)
        valid_names.discard(name)

        gold = info.get("gold", 0)
        desc = _strip_html(info.get("full_description",
                                     info.get("description", "")))
        lines.append(f"- {name} ({gold}g): {desc}")

    return (
        "\n\nVALID ITEMS — Read these descriptions carefully. "
        "ONLY recommend items from this list:\n"
        + "\n".join(lines)
    )


def build_prompt(player, teammates, enemies, item_map, game_duration,
                 build_order=None):
    """Build the analysis prompt from match data.

    Args:
        player: dict with champion_name, position, items (list of int IDs),
                role_bound_item (int ID)
        teammates: list of dicts with champion_name, position, items, role_bound_item
        enemies: list of dicts with champion_name, position, items, role_bound_item
        item_map: dict mapping int item_id -> {name, description, gold}
        game_duration: int seconds
        build_order: optional list of {"item": str, "time": str} showing
            actual purchase order from timeline data
    """
    def format_items(items, boots_id):
        """Convert item IDs to names."""
        names = []
        for item_id in items:
            if item_id and item_id != 0:
                info = item_map.get(item_id)
                if info:
                    names.append(info["name"])
        if boots_id and boots_id != 0:
            info = item_map.get(boots_id)
            if info:
                names.append(info["name"])
        return names if names else ["(no items)"]

    def format_player_line(p):
        items = [p.get(f"item{i}", 0) for i in range(7)]
        boots = p.get("role_bound_item", 0)
        item_names = format_items(items, boots)
        pos = p.get("position", "?")
        return f"  {p['champion_name']} ({pos}): {', '.join(item_names)}"

    dur_min = game_duration // 60
    dur_sec = game_duration % 60

    # Build the player's items
    player_items = [player.get(f"item{i}", 0) for i in range(7)]
    player_boots = player.get("role_bound_item", 0)
    player_item_names = format_items(player_items, player_boots)

    # Gather all enemy items to check what they actually built
    enemy_has_armor = False
    enemy_has_mr = False
    enemy_has_healing = False
    armor_items = {"3075", "3110", "3143", "3068", "3742", "6333"}  # common armor
    mr_items = {"3065", "3211", "3194", "4401", "3190"}  # common MR
    healing_items = {"3065", "3083", "6631", "3153"}  # sustain items

    for e in enemies:
        e_items = set()
        for i in range(7):
            eid = e.get(f"item{i}", 0)
            if eid:
                e_items.add(str(eid))
        rbi = e.get("role_bound_item", 0)
        if rbi:
            e_items.add(str(rbi))
        if e_items & armor_items:
            enemy_has_armor = True
        if e_items & mr_items:
            enemy_has_mr = True
        if e_items & healing_items:
            enemy_has_healing = True

    valid_items = _valid_items_block(item_map)

    # Format actual build order if timeline data is available
    build_order_section = ""
    if build_order:
        order_lines = []
        for i, bo in enumerate(build_order, 1):
            order_lines.append(f"  {i}. {bo['item']} (completed at {bo['time']})")
        build_order_section = (
            "\n\nACTUAL BUILD ORDER (from timeline — items completed in this sequence):\n"
            + "\n".join(order_lines)
        )

    prompt = f"""Analyze this League of Legends match and recommend the optimal item build for the player.

GAME CONTEXT:
- Duration: {dur_min}:{dur_sec:02d}
- Player: {player['champion_name']} ({player.get('position', '?')})
- Player's final build: {', '.join(player_item_names)}{build_order_section}

YOUR TEAM (allies):
{chr(10).join(format_player_line(t) for t in teammates)}

ENEMY TEAM:
{chr(10).join(format_player_line(e) for e in enemies)}

ENEMY ITEMIZATION FACTS:
- Enemy team built armor items: {"Yes" if enemy_has_armor else "No"}
- Enemy team built MR items: {"Yes" if enemy_has_mr else "No"}
- Enemy team has healing/sustain items: {"Yes" if enemy_has_healing else "No"}
{valid_items}

INSTRUCTIONS:
1. READ the VALID ITEMS descriptions above. Use the actual stats and passives to reason — do NOT guess what items do.
2. Recommend exactly 6 items (5 completed items + 1 boots) for {player['champion_name']} in PURCHASE PRIORITY ORDER. Include boots at the correct position in the sequence.
3. For each item, reference its actual stats or passive from the description to explain why it fits this game.
4. If the ACTUAL BUILD ORDER is provided above, critique the player's item sequencing — did they prioritize the right items early?
5. Note any synergies with teammates that affect item choices.
6. Give a one-sentence verdict on the player's actual build quality AND ordering.
7. ONLY use item names from the VALID ITEMS list. Do NOT invent items or recommend items not on the list.

Respond with ONLY valid JSON in this exact format:
{{
  "recommended_build_order": [
    {{"item": "Item Name", "reason": "Why this item at this priority in this game"}},
    ...
  ],
  "build_order_critique": "Assessment of the player's item sequencing — what they should have bought earlier or later (omit if no timeline data)",
  "situational_notes": [
    "Note about a specific item swap based on game state"
  ],
  "synergy_notes": [
    "How a specific item choice synergizes with a teammate's kit"
  ],
  "verdict": "One sentence on the actual build quality and ordering"
}}"""

    return prompt


def analyze_match_build(player, teammates, enemies, item_map,
                        game_duration, build_order=None,
                        model=None) -> dict:
    """Call Claude to analyze the match build.

    Args:
        model: Override model to use (default: DEFAULT_MODEL).
               Must be a key in AVAILABLE_MODELS.

    Returns parsed JSON dict with recommended_build_order,
    build_order_critique, situational_notes, synergy_notes, verdict.
    """
    client = _get_client()
    use_model = model if model and model in AVAILABLE_MODELS else DEFAULT_MODEL
    prompt = build_prompt(player, teammates, enemies, item_map, game_duration,
                          build_order=build_order)

    logger.info("Requesting build analysis for %s (%s) using %s",
                player["champion_name"], player.get("position", "?"), use_model)

    response = client.messages.create(
        model=use_model,
        max_tokens=MAX_TOKENS,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
        timeout=60.0,
    )

    # Extract text content
    text = response.content[0].text.strip()

    # Parse JSON (handle potential markdown code fences)
    if text.startswith("```"):
        # Strip code fences
        lines = text.split("\n")
        # Remove first and last lines (```json and ```)
        lines = [l for l in lines if not l.strip().startswith("```")]
        text = "\n".join(lines)

    result = json.loads(text)
    result["_model"] = use_model  # Tag which model produced this
    logger.info("Build analysis complete for %s (model=%s): verdict=%s",
                player["champion_name"], use_model,
                result.get("verdict", "N/A")[:60])
    return result


def build_pregame_prompt(player_champion, player_role, teammates, enemies,
                         item_map=None, item_names=None):
    """Build the pre-game analysis prompt from draft data (no items).

    Args:
        player_champion: str champion name
        player_role: str role (Top/Jungle/Mid/Bot/Support)
        teammates: list of dicts with champion_name, role, rank (str like "Gold 1 45LP")
        enemies: list of dicts with champion_name, role, rank
        item_map: dict mapping item_id -> {name, description, gold} (preferred)
        item_names: deprecated — list of valid item names (fallback)
    """
    def format_player_line(p):
        rank_str = p.get("rank", "Unknown")
        return f"  {p['champion_name']} ({p.get('role', '?')}) — {rank_str}"

    # Use full item descriptions if item_map is provided
    if item_map:
        valid_items_section = _valid_items_block(item_map)
    elif item_names:
        valid_items_section = (
            "\n\nVALID ITEMS (current patch — ONLY recommend items from this list):\n"
            + ", ".join(item_names)
        )
    else:
        valid_items_section = ""

    prompt = f"""A game is about to start. Recommend the optimal full build path for the player based on the team compositions.

PLAYER: {player_champion} ({player_role})

YOUR TEAM (allies):
{chr(10).join(format_player_line(t) for t in teammates)}

ENEMY TEAM:
{chr(10).join(format_player_line(e) for e in enemies)}
{valid_items_section}

INSTRUCTIONS:
1. READ the VALID ITEMS descriptions above. Use the actual stats and passives to reason — do NOT guess what items do.
2. Recommend exactly 6 items (5 completed items + 1 boots) in purchase priority order for {player_champion} ({player_role}) against this specific enemy team. Include boots at the correct position.
3. For each item, reference its actual stats or passive from the description to explain why it fits this draft.
4. Specify what to prioritize on first back (components, items under 1300g).
5. Note key matchup considerations and team synergies that affect itemization.
6. Think from first principles about what {player_champion} needs against these specific enemies.
7. ONLY use item names from the VALID ITEMS list. Do NOT invent items or recommend items not on the list.

Respond with ONLY valid JSON in this exact format:
{{
  "recommended_build_order": [
    {{"item": "Item Name", "reason": "Why this item against this draft"}},
    ...
  ],
  "first_back_priority": "What to buy on first recall and why",
  "key_matchup_notes": [
    "Specific matchup consideration affecting item choices"
  ],
  "synergy_notes": [
    "How a teammate's kit affects your build choices"
  ]
}}"""

    return prompt


def analyze_live_build(player_champion, player_role, teammates,
                       enemies, item_map=None, item_names=None,
                       model=None) -> dict:
    """Call Claude to generate a pre-game build recommendation.

    Args:
        item_map: Full item data dict for descriptions (preferred).
        item_names: Deprecated fallback — list of item name strings.
        model: Override model to use (default: DEFAULT_MODEL).

    Returns parsed JSON dict with recommended_build_order,
    first_back_priority, key_matchup_notes, synergy_notes.
    """
    client = _get_client()
    use_model = model if model and model in AVAILABLE_MODELS else DEFAULT_MODEL
    prompt = build_pregame_prompt(player_champion, player_role,
                                 teammates, enemies,
                                 item_map=item_map, item_names=item_names)

    logger.info("Requesting pre-game build for %s (%s) using %s",
                player_champion, player_role, use_model)

    response = client.messages.create(
        model=use_model,
        max_tokens=MAX_TOKENS,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
        timeout=60.0,
    )

    # Extract text content
    text = response.content[0].text.strip()

    # Parse JSON (handle potential markdown code fences)
    if text.startswith("```"):
        lines = text.split("\n")
        lines = [l for l in lines if not l.strip().startswith("```")]
        text = "\n".join(lines)

    result = json.loads(text)
    result["_model"] = use_model
    logger.info("Pre-game build complete for %s (model=%s): %d items recommended",
                player_champion, use_model,
                len(result.get("recommended_build_order", [])))
    return result
