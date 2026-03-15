"""Op.gg scraper for past season rank data.

Fetches a summoner's op.gg profile page and extracts historical season
rank data from the embedded RSC (React Server Components) payload.
This data is not available through the Riot API.
"""

import json
import logging
import re

import requests

logger = logging.getLogger(__name__)

# Headers to mimic a real browser and avoid Cloudflare blocks
_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

# Map op.gg season labels to our internal season keys.
# Our SEASONS dict in app.py covers S4 (2014) through S2026 (current).
# Op.gg uses year-based names from 2020 onwards ("S2020", "S2021", ...)
# and numbered names for earlier seasons ("S9", "S8", ..., "S3").
# Labels often have a trailing space (e.g. "S2025 ") — we map both variants.
OPGG_TO_SEASON_KEY = {
    # Current + recent (match-filterable) seasons
    "S2026 ": "s2026",
    "S2026": "s2026",
    "S2025 ": "s2025",
    "S2025": "s2025",
    "S2024 S3": "s2024_s3",
    "S2024 S2": "s2024_s2",
    "S2024 S1": "s2024_s1",
    "S2024": "s2024",
    # Year-based seasons (2020-2023)
    "S2023 S2": "s2023_s2",
    "S2023 S1": "s2023_s1",
    "S2023 ": "s2023_s1",   # bare "S2023 " (with space) = Split 1
    "S2023": "s2023_s1",    # bare "S2023" = Split 1
    "S2022 ": "s2022",
    "S2022": "s2022",
    "S2021 ": "s2021",
    "S2021": "s2021",
    "S2020 ": "s2020",
    "S2020": "s2020",
    # Old numbered seasons (S3-S9, pre-2020)
    # Op.gg switched to year-based names at 2020, so S9 (2019) is the last numbered one.
    "S9 ": "s9",
    "S9": "s9",
    "S8 ": "s8",
    "S8": "s8",
    "S7 ": "s7",
    "S7": "s7",
    "S6 ": "s6",
    "S6": "s6",
    "S5 ": "s5",
    "S5": "s5",
    "S4 ": "s4",
    "S4": "s4",
    "S3 ": "s3",
    "S3": "s3",
}


def _parse_tier(tier_str: str) -> tuple[str, str]:
    """Parse a tier string like 'gold 1' into (GOLD, 1).

    Returns (tier_upper, division) or (tier_upper, '') for apex tiers.
    """
    if not tier_str or not tier_str.strip():
        return ("", "")

    parts = tier_str.strip().split()
    tier = parts[0].upper()
    division = parts[1] if len(parts) > 1 else ""

    # Normalise old division naming (V → 5 in old seasons)
    return (tier, division)


def scrape_season_ranks(game_name: str, tag_line: str,
                        region: str = "na") -> list[dict]:
    """Scrape past season rank data from op.gg.

    Args:
        game_name: Riot ID game name (e.g. "Leon")
        tag_line: Riot ID tag line (e.g. "NA420")
        region: Op.gg region code (default "na")

    Returns:
        List of dicts with keys:
            season_key, season_label, tier, division, lp,
            peak_tier, peak_division, peak_lp
        Empty list on failure.
    """
    # Build URL: op.gg uses {name}-{tag} format
    url_name = f"{game_name}-{tag_line}"
    url = f"https://www.op.gg/summoners/{region}/{url_name}"

    try:
        resp = requests.get(url, headers=_HEADERS, timeout=30)
        if resp.status_code != 200:
            logger.warning(
                "Op.gg returned %d for %s#%s", resp.status_code,
                game_name, tag_line
            )
            return []
    except requests.RequestException as e:
        logger.warning("Failed to fetch op.gg for %s#%s: %s",
                       game_name, tag_line, e)
        return []

    text = resp.text

    # Find the RSC data block containing season rank history.
    # The data is embedded as escaped JSON inside script tags:
    #   \\"data\\":[{\\"season\\":\\"S2025 \\",...}]
    # followed by ],\\"queueType\\":\\"TOTAL\\"
    start_marker = '\\"data\\":[{\\"season\\":\\"S20'
    idx = text.find(start_marker)
    if idx == -1:
        logger.info("No season rank data found on op.gg for %s#%s",
                     game_name, tag_line)
        return []

    # Extract from the start of the array to the closing bracket
    data_start = idx + len('\\"data\\":')
    rest = text[data_start:]
    end_marker = '],\\"queueType\\":\\"TOTAL\\"'
    end_idx = rest.find(end_marker)
    if end_idx == -1:
        logger.warning("Could not find end of season data for %s#%s",
                        game_name, tag_line)
        return []

    raw = rest[:end_idx + 1]  # Include the closing ]

    # Unescape: the RSC payload uses \\" for quotes
    unescaped = raw.replace('\\"', '"')

    try:
        seasons_data = json.loads(unescaped)
    except json.JSONDecodeError as e:
        logger.warning("Failed to parse op.gg season data for %s#%s: %s",
                        game_name, tag_line, e)
        return []

    results = []
    for item in seasons_data:
        season_label = item.get("season", "").strip()
        raw_label = item.get("season", "")  # Keep original with trailing space

        # Map to our season key
        season_key = OPGG_TO_SEASON_KEY.get(raw_label)
        if not season_key:
            # Try stripped version
            season_key = OPGG_TO_SEASON_KEY.get(season_label)
        if not season_key:
            # Store with generated key for unmapped seasons
            season_key = f"opgg_{season_label.lower().replace(' ', '_')}"

        rank_entries = item.get("rank_entries", {})

        # Ending rank
        rank_info = rank_entries.get("rank_info", {})
        tier, division = _parse_tier(rank_info.get("tier", ""))
        lp_str = rank_info.get("lp")
        lp = int(lp_str) if lp_str and str(lp_str).isdigit() else 0

        # Peak rank (only available for recent seasons)
        high_rank = rank_entries.get("high_rank_info", {})
        peak_tier, peak_division = _parse_tier(high_rank.get("tier", ""))
        peak_lp_str = high_rank.get("lp")
        peak_lp = int(peak_lp_str) if peak_lp_str and str(peak_lp_str).isdigit() else 0

        if not tier:
            # Skip seasons with no rank data (unranked)
            continue

        results.append({
            "season_key": season_key,
            "season_label": season_label,
            "tier": tier,
            "division": division,
            "lp": lp,
            "peak_tier": peak_tier,
            "peak_division": peak_division,
            "peak_lp": peak_lp,
        })

    logger.info("Scraped %d season ranks from op.gg for %s#%s",
                len(results), game_name, tag_line)
    return results
