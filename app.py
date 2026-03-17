"""Flask web application for LolTracker.

Multi-account League of Legends tracker with:
- Profile/account management
- Cross-account aggregated statistics
- Live game lookup with win prediction
- Prediction tracking and resolution
"""

import datetime
import json
import logging
import math
import os
import queue
import threading
import time
from collections import defaultdict
from html import escape as html_escape
from concurrent.futures import ThreadPoolExecutor, as_completed
from itertools import combinations

from flask import Flask, render_template, jsonify, request, Response
from flask_compress import Compress

from riot_api import RiotAPI, load_api_key
from champion_positions import CHAMPION_POSITIONS
from champion_role_rates import get_role_rates
from build_guides import get_build_guide, get_all_guides_for_champion, generate_client_export
from opgg_scraper import scrape_season_ranks
import llm_client
import database as db

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
Compress(app)

# Initialise the Riot API client once at startup
_api_key = load_api_key()
_api = RiotAPI(_api_key)

# Secondary API client for duo detection (separate rate limit bucket)
_api_key_secondary = os.environ.get("RIOT_API_KEY_SECONDARY", "").strip()
if _api_key_secondary:
    _api_duo = RiotAPI(_api_key_secondary)
    logger.info("Secondary Riot API key loaded for duo detection")
else:
    _api_duo = _api  # fallback to primary if no secondary key
    logger.info("No secondary API key — duo detection shares primary key")

MAX_WORKERS = 8

# ---- Live game result cache ---------------------------------------------------
# Caches the full _build_live_game() result by game_id so re-searching the same
# active game returns instantly without re-fetching names/ranks/winrates/duos.
# TTL: 10 minutes (live games last 20-40min; data doesn't change mid-game).
_live_game_cache: dict[str, dict] = {}  # game_id -> {"result": dict, "ts": float}
_LIVE_CACHE_TTL = 600  # 10 minutes


def _get_cached_live_game(game_id: str) -> dict | None:
    """Return cached live game result if fresh, else None."""
    entry = _live_game_cache.get(game_id)
    if entry and (time.time() - entry["ts"]) < _LIVE_CACHE_TTL:
        return entry["result"]
    return None


def _cache_live_game(game_id: str, result: dict):
    """Store live game result in the in-memory cache."""
    _live_game_cache[game_id] = {"result": result, "ts": time.time()}

    # Evict stale entries to prevent unbounded growth
    cutoff = time.time() - _LIVE_CACHE_TTL * 2
    stale = [k for k, v in _live_game_cache.items() if v["ts"] < cutoff]
    for k in stale:
        _live_game_cache.pop(k, None)


# ---- Task deduplication lock registry ------------------------------------------
# Prevents duplicate background work when multiple users/tabs trigger the same
# operation concurrently. Keyed by (operation, resource_id).
_task_locks: dict[tuple[str, str], threading.Lock] = {}
_task_locks_meta = threading.Lock()  # protects _task_locks dict itself


def task_lock(operation: str, resource_key: str) -> threading.Lock:
    """Get or create a lock for a specific operation + resource combination."""
    key = (operation, resource_key)
    with _task_locks_meta:
        if key not in _task_locks:
            _task_locks[key] = threading.Lock()
        return _task_locks[key]


# Ranked queue type constants
RANKED_SOLO = "RANKED_SOLO_5x5"
RANKED_FLEX = "RANKED_FLEX_SR"
DIVISION_SHORT = {"I": "1", "II": "2", "III": "3", "IV": "4"}

# Queue ID -> human-readable name
QUEUE_NAMES = {
    0: "Custom",
    400: "Normal Draft",
    420: "Ranked Solo/Duo",
    430: "Blind Pick",
    440: "Ranked Flex",
    450: "ARAM",
    480: "Swiftplay",
    490: "Quickplay",
    700: "Clash",
    720: "ARAM Clash",
    900: "ARURF",
    1020: "One for All",
    1300: "Nexus Blitz",
    1400: "Ultimate Spellbook",
    1700: "Arena",
    1900: "Pick URF",
}

# Duo detection constants
SHARED_MATCH_THRESHOLD = 2   # minimum shared match IDs to flag a duo
DUO_MATCH_HISTORY_COUNT = 10  # match IDs to fetch per player for duo detection

SPELL_SMITE = 11
POSITION_DISPLAY = {
    "TOP": "Top", "JUNGLE": "Jungle", "MIDDLE": "Mid",
    "BOTTOM": "Bot", "SUPPORT": "Support", "UTILITY": "Support",
}

# Rank tier to numeric score for prediction
TIER_SCORES = {
    "IRON": 0, "BRONZE": 4, "SILVER": 8, "GOLD": 12,
    "PLATINUM": 16, "EMERALD": 20, "DIAMOND": 24,
    "MASTER": 28, "GRANDMASTER": 30, "CHALLENGER": 32,
}
DIVISION_SCORES = {"IV": 0, "III": 1, "II": 2, "I": 3}

# Season definitions (epoch seconds). Ordered newest-first.
# Keys match Riot's naming: s2026 = Season 2026, s2024_s2 = Season 2024 Split 2.
# "filter": True means season appears in the dropdown for match filtering.
# "filter": False means season only appears in account card season history rows.
SEASONS = {
    "s2026":    {"label": "Current Season",  "start": 1767848400, "end": None,       "filter": True},
    "s2025":    {"label": "Season 2025",     "start": 1736312400, "end": 1767848400, "filter": True},
    "s2024_s3": {"label": "S2024 Split 3",   "start": 1727236800, "end": 1736312400, "filter": True},
    "s2024_s2": {"label": "S2024 Split 2",   "start": 1715644800, "end": 1727236800, "filter": True},
    "s2024_s1": {"label": "S2024 Split 1",   "start": 1704700800, "end": 1715644800, "filter": True},
    # Older seasons — display-only (no match data, just scraped rank history)
    "s2023_s2": {"label": "S2023 Split 2",   "start": 1689742800, "end": 1704700800, "filter": False},
    "s2023_s1": {"label": "S2023 Split 1",   "start": 1673326800, "end": 1689742800, "filter": False},
    "s2022":    {"label": "Season 2022",     "start": 1641535200, "end": 1673326800, "filter": False},
    "s2021":    {"label": "Season 2021",     "start": 1610082000, "end": 1641535200, "filter": False},
    "s2020":    {"label": "Season 2020",     "start": 1578628800, "end": 1610082000, "filter": False},
    "s9":       {"label": "Season 9",        "start": 1548219600, "end": 1574132400, "filter": False},
    "s8":       {"label": "Season 8",        "start": 1516078800, "end": 1542024000, "filter": False},
    "s7":       {"label": "Season 7",        "start": 1481090400, "end": 1510023600, "filter": False},
    "s6":       {"label": "Season 6",        "start": 1453269600, "end": 1478498400, "filter": False},
    "s5":       {"label": "Season 5",        "start": 1421820000, "end": 1447221600, "filter": False},
    "s4":       {"label": "Season 4",        "start": 1389330000, "end": 1415682000, "filter": False},
    "s3":       {"label": "Season 3",        "start": 1360022400, "end": 1384387200, "filter": False},
}
DEFAULT_SEASON = "s2026"


def _season_times(season_key: str | None) -> tuple:
    """Return (start_time, end_time) for a season key, or (None, None) if invalid."""
    if season_key and season_key in SEASONS:
        return SEASONS[season_key]["start"], SEASONS[season_key]["end"]
    return None, None


# Initialize database on startup
db.init_db()


# ---- Page routes -----------------------------------------------------------

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/riot.txt")
def riot_txt():
    return app.send_static_file("riot.txt")


# ---- Profile API -----------------------------------------------------------

@app.route("/api/profiles", methods=["GET"])
def list_profiles():
    profiles = db.get_profiles()
    return jsonify(profiles)


@app.route("/api/profiles", methods=["POST"])
def create_profile():
    data = request.get_json(silent=True) or {}
    name = data.get("name", "").strip()
    if not name:
        return jsonify({"error": "Profile name is required"}), 400
    profile = db.create_profile(name)
    return jsonify(profile), 201


@app.route("/api/profiles/<int:profile_id>", methods=["GET"])
def get_profile(profile_id):
    profile = db.get_profile(profile_id)
    if not profile:
        return jsonify({"error": "Profile not found"}), 404

    accounts = profile.get("accounts", [])
    puuids = [a["puuid"] for a in accounts]

    # Build season time-range map for the batch query
    season_ranges: dict[str, tuple[int | None, int | None]] = {}
    for skey, sdef in SEASONS.items():
        season_ranges[skey] = (sdef["start"], sdef["end"])

    # Single batch query: all puuids × all filterable seasons → {puuid: {season: stats}}
    batch_stats = db.get_batch_season_stats(puuids, season_ranges)

    # Selected season stats (for the main rank display W/L)
    season_key = request.args.get("season") or DEFAULT_SEASON
    if season_key == "all":
        for acct in accounts:
            acct["season_stats"] = db.get_season_stats_for_puuid(
                acct["puuid"], start_time=None, end_time=None
            )
    else:
        for acct in accounts:
            p = acct["puuid"]
            if season_key in batch_stats.get(p, {}):
                acct["season_stats"] = batch_stats[p][season_key]
            else:
                start_time, end_time = _season_times(season_key)
                acct["season_stats"] = db.get_season_stats_for_puuid(
                    acct["puuid"], start_time=start_time, end_time=end_time
                )

    # All-seasons history from batch results (already computed above)
    for acct in accounts:
        acct["all_season_stats"] = batch_stats.get(acct["puuid"], {})

    # Attach scraped season ranks (from op.gg) for each account
    for acct in accounts:
        ranks_list = db.get_season_ranks_for_account(acct["id"])
        acct["season_ranks"] = {r["season_key"]: r for r in ranks_list}

    return jsonify(profile)


@app.route("/api/profiles/<int:profile_id>", methods=["PATCH"])
def update_profile(profile_id):
    data = request.get_json(silent=True) or {}
    name = data.get("name", "").strip()
    if not name:
        return jsonify({"error": "Profile name is required"}), 400
    result = db.update_profile_name(profile_id, name)
    if not result:
        return jsonify({"error": "Profile not found"}), 404
    return jsonify(result)


@app.route("/api/profiles/<int:profile_id>", methods=["DELETE"])
def delete_profile(profile_id):
    if db.delete_profile(profile_id):
        return jsonify({"ok": True})
    return jsonify({"error": "Profile not found"}), 404


# ---- Account API -----------------------------------------------------------

@app.route("/api/profiles/<int:profile_id>/accounts", methods=["POST"])
def add_account(profile_id):
    """Add an account to a profile by Riot ID."""
    data = request.get_json(silent=True) or {}
    import re as _re
    # Strip invisible Unicode characters (directional marks, zero-width chars, etc.)
    riot_id = _re.sub(r'[\u200b-\u200f\u2028-\u202f\u2060-\u206f\ufeff]', '', data.get("riot_id", "")).strip()
    if not riot_id or "#" not in riot_id:
        return jsonify({"error": "Invalid Riot ID. Use GameName#TagLine"}), 400

    # Verify profile exists
    profile = db.get_profile(profile_id)
    if not profile:
        return jsonify({"error": "Profile not found"}), 404

    parts = riot_id.split("#", 1)
    game_name = parts[0].strip()
    tag_line = parts[1].strip()

    # Resolve via Riot API
    try:
        account = _api.get_account_by_riot_id(game_name, tag_line)
        if not account:
            return jsonify({"error": f"Player '{riot_id}' not found"}), 404

        puuid = account["puuid"]
        real_name = account.get("gameName", game_name)
        real_tag = account.get("tagLine", tag_line)

        acct = db.add_account(profile_id, puuid, real_name, real_tag)

        # Fetch initial ranks using puuid
        _refresh_account_ranks(acct["id"], puuid)

        # Scrape past season ranks from op.gg in background
        threading.Thread(
            target=_scrape_and_store_season_ranks,
            args=(acct["id"], real_name, real_tag),
            daemon=True,
        ).start()

        # Return updated account with ranks
        return jsonify(db.get_account(acct["id"])), 201

    except Exception as e:
        logger.exception("Error adding account")
        return jsonify({"error": str(e)}), 500


@app.route("/api/accounts/<int:account_id>", methods=["DELETE"])
def remove_account(account_id):
    if db.delete_account(account_id):
        return jsonify({"ok": True})
    return jsonify({"error": "Account not found"}), 404


# ---- Rank refresh ----------------------------------------------------------

def _refresh_account_ranks(account_id: int, puuid: str):
    """Fetch and store current ranks for an account using puuid.

    Also re-resolves gameName/tagLine in case the player renamed.
    """
    if not puuid:
        return
    try:
        # Re-resolve name (handles summoner name changes)
        acct_data = _api.get_account_by_puuid(puuid)
        if acct_data:
            new_name = acct_data.get("gameName")
            new_tag = acct_data.get("tagLine")
            if new_name and new_tag:
                db.update_account_name(puuid, new_name, new_tag)
    except Exception:
        logger.exception("Failed to re-resolve name for %s", puuid[:8])

    try:
        entries = _api.get_league_entries_by_puuid(puuid)
        for entry in entries:
            qt = entry.get("queueType", "")
            if qt in (RANKED_SOLO, RANKED_FLEX):
                tier = entry.get("tier", "")
                rank = entry.get("rank", "")
                lp = entry.get("leaguePoints", 0)
                wins = entry.get("wins", 0)
                losses = entry.get("losses", 0)
                db.upsert_rank(account_id, qt, tier, rank, lp, wins, losses)
                # Record rank snapshot for LP history tracking
                if tier:
                    db.insert_rank_history(
                        account_id, qt, tier, rank, lp, wins, losses
                    )
    except Exception:
        logger.exception("Failed to refresh ranks for account %d", account_id)


@app.route("/api/accounts/<int:account_id>/refresh", methods=["POST"])
def refresh_account(account_id):
    _touch_user_activity()
    acct = db.get_account(account_id)
    if not acct:
        return jsonify({"error": "Account not found"}), 404
    lock = task_lock("refresh_account", str(account_id))
    if not lock.acquire(blocking=False):
        return jsonify({"error": "Refresh already in progress"}), 409
    try:
        _refresh_account_ranks(account_id, acct.get("puuid", ""))
        return jsonify(db.get_account(account_id))
    finally:
        lock.release()


def _scrape_and_store_season_ranks(account_id: int, game_name: str,
                                   tag_line: str):
    """Scrape past season ranks from op.gg and store in season_ranks table.

    Guarded by task_lock to prevent duplicate concurrent scrapes for the same account.
    """
    lock = task_lock("scrape", str(account_id))
    if not lock.acquire(blocking=False):
        logger.debug("Skipping duplicate scrape for account %d", account_id)
        return
    try:
        ranks = scrape_season_ranks(game_name, tag_line)
        for r in ranks:
            db.upsert_season_rank(
                account_id=account_id,
                season_key=r["season_key"],
                tier=r["tier"],
                division=r["division"],
                lp=r["lp"],
                peak_tier=r.get("peak_tier", ""),
                peak_division=r.get("peak_division", ""),
                peak_lp=r.get("peak_lp", 0),
                source="opgg",
            )
        logger.info("Stored %d season ranks for account %d (%s#%s)",
                     len(ranks), account_id, game_name, tag_line)
    except Exception:
        logger.exception("Failed to scrape season ranks for %s#%s",
                         game_name, tag_line)
    finally:
        lock.release()


@app.route("/api/accounts/<int:account_id>/scrape-ranks", methods=["POST"])
def scrape_account_ranks(account_id):
    """Scrape past season ranks from op.gg for an account."""
    acct = db.get_account(account_id)
    if not acct:
        return jsonify({"error": "Account not found"}), 404

    _scrape_and_store_season_ranks(
        account_id, acct["game_name"], acct["tag_line"]
    )
    season_ranks = db.get_season_ranks_for_account(account_id)
    return jsonify({"season_ranks": season_ranks})


@app.route("/api/accounts/<int:account_id>/scrape-ranks-if-missing", methods=["POST"])
def scrape_account_ranks_if_missing(account_id):
    """Scrape ranks only if the account has no season_ranks data at all.

    Used by the frontend to auto-scrape when user switches to a past season
    and an account card is missing scraped rank data.
    Returns existing data immediately if already scraped.
    """
    acct = db.get_account(account_id)
    if not acct:
        return jsonify({"error": "Account not found"}), 404

    existing = db.get_season_ranks_for_account(account_id)
    # Only consider "real" season keys (ignore opgg_sN legacy keys)
    real = [r for r in existing if not r["season_key"].startswith("opgg_")]
    if real:
        # Already have scraped data — return it without re-scraping
        return jsonify({
            "scraped": False,
            "season_ranks": {r["season_key"]: r for r in existing},
        })

    # No data yet — scrape now (synchronous, fast single HTTP call)
    _scrape_and_store_season_ranks(
        account_id, acct["game_name"], acct["tag_line"]
    )
    updated = db.get_season_ranks_for_account(account_id)
    return jsonify({
        "scraped": True,
        "season_ranks": {r["season_key"]: r for r in updated},
    })


@app.route("/api/profiles/<int:profile_id>/scrape-ranks", methods=["POST"])
def scrape_profile_ranks(profile_id):
    """Scrape past season ranks from op.gg for all accounts in a profile."""
    profile = db.get_profile(profile_id)
    if not profile:
        return jsonify({"error": "Profile not found"}), 404

    accounts = profile.get("accounts", [])
    scraped = 0
    for acct in accounts:
        _scrape_and_store_season_ranks(
            acct["id"], acct["game_name"], acct["tag_line"]
        )
        scraped += 1

    return jsonify({"scraped": scraped, "total_accounts": len(accounts)})


@app.route("/api/profiles/<int:profile_id>/refresh", methods=["POST"])
def refresh_profile(profile_id):
    """Refresh ranks and fetch recent matches for all accounts in a profile."""
    _touch_user_activity()
    profile = db.get_profile(profile_id)
    if not profile:
        return jsonify({"error": "Profile not found"}), 404

    lock = task_lock("refresh_profile", str(profile_id))
    if not lock.acquire(blocking=False):
        return jsonify({"error": "Refresh already in progress"}), 409

    accounts = profile.get("accounts", [])

    # Snapshot old ranks for comparison
    old_ranks = {}
    for acct in accounts:
        for r in acct.get("ranks", []):
            key = f"{acct['id']}_{r['queue_type']}"
            old_ranks[key] = {
                "tier": r.get("tier", ""),
                "rank": r.get("rank", ""),
                "lp": r.get("lp", 0),
                "wins": r.get("wins", 0),
                "losses": r.get("losses", 0),
            }

    if accounts:
        workers = min(MAX_WORKERS, len(accounts))
        with ThreadPoolExecutor(max_workers=workers) as executor:
            # Refresh ranks AND fetch recent matches in parallel
            rank_futures = {
                executor.submit(
                    _refresh_account_ranks, a["id"], a.get("puuid", "")
                ): ("rank", a) for a in accounts
            }
            match_futures = {
                executor.submit(
                    _fetch_and_store_matches, a["puuid"], 20
                ): ("match", a) for a in accounts
            }
            new_matches_count = 0
            for future in as_completed({**rank_futures, **match_futures}):
                try:
                    future.result()
                except Exception:
                    pass

    # Build change summary
    updated_profile = db.get_profile(profile_id)
    changes = []
    for acct in updated_profile.get("accounts", []):
        name = acct.get("game_name", "?")
        for r in acct.get("ranks", []):
            key = f"{acct['id']}_{r['queue_type']}"
            old = old_ranks.get(key)
            if not old:
                if r.get("tier"):
                    changes.append(f"{name}: placed {r['tier']} {r.get('rank', '')} {r.get('lp', 0)} LP")
                continue
            # Compare
            lp_diff = r.get("lp", 0) - old.get("lp", 0)
            wins_diff = r.get("wins", 0) - old.get("wins", 0)
            losses_diff = r.get("losses", 0) - old.get("losses", 0)
            tier_changed = r.get("tier", "") != old.get("tier", "") or r.get("rank", "") != old.get("rank", "")

            queue_label = "Solo" if r["queue_type"] == "RANKED_SOLO_5x5" else "Flex"
            if tier_changed:
                changes.append(f"{name} ({queue_label}): {old['tier']} {old['rank']} -> {r['tier']} {r.get('rank', '')} ({r.get('lp', 0)} LP)")
            elif lp_diff != 0:
                sign = "+" if lp_diff > 0 else ""
                changes.append(f"{name} ({queue_label}): {sign}{lp_diff} LP ({r.get('lp', 0)} LP)")
            elif wins_diff > 0 or losses_diff > 0:
                changes.append(f"{name} ({queue_label}): +{wins_diff}W +{losses_diff}L")

    # Auto-scrape season ranks from op.gg for accounts that don't have any yet
    for acct in updated_profile.get("accounts", []):
        existing_ranks = db.get_season_ranks_for_account(acct["id"])
        if not existing_ranks:
            threading.Thread(
                target=_scrape_and_store_season_ranks,
                args=(acct["id"], acct["game_name"], acct["tag_line"]),
                daemon=True,
            ).start()

    lock.release()

    result = dict(updated_profile)
    result["refresh_changes"] = changes
    return jsonify(result)


# ---- Match History ---------------------------------------------------------

@app.route("/api/accounts/<int:account_id>/matches", methods=["GET"])
def account_matches(account_id):
    """Return match history from DB instantly (no Riot API calls).

    Query params:
      season  - season key (e.g. s2026) to filter by date range
      offset  - pagination offset (default 0)
      limit   - page size (default 20)
    """
    acct = db.get_account(account_id)
    if not acct:
        return jsonify({"error": "Account not found"}), 404

    puuid = acct["puuid"]
    limit = int(request.args.get("limit", 20))
    offset = int(request.args.get("offset", 0))

    # Season filtering
    season_key = request.args.get("season")
    start_time, end_time = _season_times(season_key)

    # Return from DB immediately — no Riot API calls
    matches = db.get_matches_for_puuid(
        puuid, limit=limit, offset=offset,
        start_time=start_time, end_time=end_time,
    )
    total = db.count_matches_for_puuid(puuid, start_time=start_time, end_time=end_time)
    version = _api.get_latest_version()
    formatted = _format_matches(matches, version)

    # Enrich with opponent champion names for filtering
    match_ids = [m["match_id"] for m in matches if m.get("match_id")]
    opponents = db.get_opponent_champions(match_ids, puuid)
    for fm in formatted:
        fm["vs_champions"] = opponents.get(fm["match_id"], [])

    return jsonify({
        "account": {
            "id": acct["id"],
            "game_name": acct["game_name"],
            "tag_line": acct["tag_line"],
        },
        "ddragon_version": version,
        "matches": formatted,
        "total": total,
        "offset": offset,
        "limit": limit,
        "has_more": offset + len(matches) < total,
    })


@app.route("/api/accounts/<int:account_id>/fetch-new", methods=["POST"])
def fetch_new_matches(account_id):
    """Fetch recent matches from Riot API and store new ones. Returns count of new matches."""
    _touch_user_activity()
    acct = db.get_account(account_id)
    if not acct:
        return jsonify({"error": "Account not found"}), 404

    puuid = acct["puuid"]
    lock = task_lock("fetch_matches", puuid)
    if not lock.acquire(blocking=False):
        return jsonify({"error": "Fetch already in progress", "new_matches": 0}), 409
    try:
        new_count = _fetch_and_store_matches(puuid, 20)
        return jsonify({"new_matches": new_count or 0})
    except Exception:
        logger.exception("Error fetching matches for account %d", account_id)
        return jsonify({"new_matches": 0})
    finally:
        lock.release()


@app.route("/api/profiles/<int:profile_id>/matches", methods=["GET"])
def profile_matches(profile_id):
    """Get recent matches across all accounts in a profile."""
    profile = db.get_profile(profile_id)
    if not profile:
        return jsonify({"error": "Profile not found"}), 404

    puuids = [a["puuid"] for a in profile.get("accounts", [])]
    count = int(request.args.get("count", 40))

    # Fetch new matches for all accounts in parallel
    if puuids:
        workers = min(MAX_WORKERS, len(puuids))
        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = {
                executor.submit(_fetch_and_store_matches, p, 20): p
                for p in puuids
            }
            for f in as_completed(futures):
                try:
                    f.result()
                except Exception:
                    pass

    matches = db.get_matches_for_puuids(puuids, count)
    version = _api.get_latest_version()
    formatted = _format_matches(matches, version)

    # Attach account info to each match
    puuid_to_name = {}
    for a in profile.get("accounts", []):
        puuid_to_name[a["puuid"]] = f"{a['game_name']}#{a['tag_line']}"
    for m in formatted:
        m["account_name"] = puuid_to_name.get(m.get("puuid", ""), "")

    return jsonify({
        "ddragon_version": version,
        "matches": formatted,
    })


def _fetch_and_store_matches(puuid: str, count: int = 20) -> int:
    """Fetch recent match IDs from Riot API, get details, store in DB.

    Returns the number of new matches fetched and stored.
    """
    # Get ranked match IDs
    solo_ids = _api.get_match_ids(puuid, count=count, queue=420)
    flex_ids = _api.get_match_ids(puuid, count=count, queue=440)
    all_ids = list(dict.fromkeys(solo_ids + flex_ids))[:count]

    if not all_ids:
        return 0

    # Check which we already have
    with db.get_db() as conn:
        placeholders = ",".join("?" for _ in all_ids)
        existing = conn.execute(
            f"SELECT match_id FROM matches WHERE match_id IN ({placeholders})",
            all_ids
        ).fetchall()
        existing_ids = {r["match_id"] for r in existing}

    new_ids = [mid for mid in all_ids if mid not in existing_ids]
    if not new_ids:
        return 0

    logger.info("Fetching %d new match details for %s", len(new_ids), puuid[:8])

    stored = 0
    # Fetch new match details in parallel
    workers = min(MAX_WORKERS, len(new_ids))
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {executor.submit(_api.get_match, mid): mid for mid in new_ids}
        for future in as_completed(futures):
            try:
                data = future.result()
                if data:
                    db.store_match(data)
                    stored += 1
            except Exception:
                logger.exception("Failed to fetch/store match")

    return stored


def _format_matches(matches: list, version: str) -> list:
    """Format match database rows into frontend-friendly dicts."""
    result = []
    for m in matches:
        game_start = m.get("game_start", 0)
        date_str = "Unknown"
        if game_start:
            dt = datetime.datetime.fromtimestamp(game_start / 1000)
            date_str = dt.strftime("%b %-d")

        duration = m.get("game_duration", 0)
        dur_str = f"{duration // 60}:{duration % 60:02d}"

        queue_id = m.get("queue_id") or 0
        queue_name = QUEUE_NAMES.get(queue_id, "Unknown")

        items = [m.get(f"item{i}", 0) for i in range(7)]
        role_bound_item = m.get("role_bound_item", 0)

        # Sanitize notes for safe display (HTML-escape)
        raw_notes = m.get("notes") or None
        safe_notes = html_escape(raw_notes) if raw_notes else None

        entry = {
            "match_id": m["match_id"],
            "champion_name": m.get("champion_name", "Unknown"),
            "champion_id": m.get("champion_id", 0),
            "win": bool(m.get("win")),
            "kills": m.get("kills", 0),
            "deaths": m.get("deaths", 0),
            "assists": m.get("assists", 0),
            "cs": m.get("cs", 0),
            "gold": m.get("gold", 0),
            "damage": m.get("damage", 0),
            "vision": m.get("vision_score", 0),
            "items": items,
            "role_bound_item": role_bound_item,
            "queue_id": queue_id,
            "queue_name": queue_name,
            "date_str": date_str,
            "game_duration_str": dur_str,
            "game_start": game_start,
            "position": m.get("position", ""),
            "perk_primary": m.get("perk_primary", 0),
            "perk_sub": m.get("perk_sub", 0),
            "summoner1_id": m.get("summoner1_id", 0),
            "summoner2_id": m.get("summoner2_id", 0),
            "ddragon_version": version,
            "notes": safe_notes,
            "is_remake": bool(m.get("is_remake")),
        }
        if "puuid" in m:
            entry["puuid"] = m["puuid"]
        result.append(entry)
    return result


# ---- Champion Stats --------------------------------------------------------

@app.route("/api/champion-positions", methods=["GET"])
def get_champion_positions():
    """Return champion_id -> position mapping for frontend role filtering."""
    return jsonify(CHAMPION_POSITIONS)


@app.route("/api/profiles/<int:profile_id>/stats/champions", methods=["GET"])
def champion_stats(profile_id):
    profile = db.get_profile(profile_id)
    if not profile:
        return jsonify({"error": "Profile not found"}), 404

    # Optional account_id filter
    account_id = request.args.get("account_id")
    if account_id:
        acct = next(
            (a for a in profile.get("accounts", []) if str(a["id"]) == account_id),
            None,
        )
        puuids = [acct["puuid"]] if acct else []
    else:
        puuids = [a["puuid"] for a in profile.get("accounts", [])]

    # Season filtering
    season_key = request.args.get("season")
    start_time, end_time = _season_times(season_key)

    stats = db.get_champion_stats(puuids, start_time=start_time, end_time=end_time)
    version = _api.get_latest_version()

    # Map position display names
    pos_display = {"TOP": "Top", "JUNGLE": "Jungle", "MIDDLE": "Mid",
                   "BOTTOM": "Bot", "SUPPORT": "Support", "UTILITY": "Support"}

    for s in stats:
        s["winrate"] = round(s["wins"] / s["games"] * 100) if s["games"] > 0 else 0
        # Add position from champion_positions mapping
        champ_id = s.get("champion_id")
        raw_pos = CHAMPION_POSITIONS.get(champ_id) if champ_id else None
        s["position"] = pos_display.get(raw_pos, "") if raw_pos else ""

    return jsonify({
        "ddragon_version": version,
        "champions": stats,
    })


@app.route("/api/profiles/<int:profile_id>/stats/champions/<champion_name>", methods=["GET"])
def champion_detail(profile_id, champion_name):
    """Deep stats for a specific champion across all profile accounts."""
    profile = db.get_profile(profile_id)
    if not profile:
        return jsonify({"error": "Profile not found"}), 404

    # Optional account_id filter
    account_id = request.args.get("account_id")
    if account_id:
        acct = next(
            (a for a in profile.get("accounts", []) if str(a["id"]) == account_id),
            None,
        )
        puuids = [acct["puuid"]] if acct else []
    else:
        puuids = [a["puuid"] for a in profile.get("accounts", [])]

    # Season filtering
    season_key = request.args.get("season")
    start_time, end_time = _season_times(season_key)

    builds = db.get_champion_builds(puuids, champion_name,
                                    start_time=start_time, end_time=end_time)
    version = _api.get_latest_version()

    if not builds:
        return jsonify({
            "champion_name": champion_name,
            "ddragon_version": version,
            "games": 0,
            "builds": [],
            "common_items": [],
        })

    # Analyze builds
    games = len(builds)
    wins = sum(1 for b in builds if b.get("win"))
    winrate = round(wins / games * 100) if games > 0 else 0

    # Count item frequencies (exclude trinket slot 6 and 0s)
    item_counts = defaultdict(lambda: {"count": 0, "wins": 0})
    for b in builds:
        for i in range(6):
            item_id = b.get(f"item{i}", 0)
            if item_id and item_id > 0:
                item_counts[item_id]["count"] += 1
                if b.get("win"):
                    item_counts[item_id]["wins"] += 1

    # Sort by frequency
    common_items = []
    for item_id, data in sorted(item_counts.items(),
                                 key=lambda x: x[1]["count"], reverse=True)[:12]:
        wr = round(data["wins"] / data["count"] * 100) if data["count"] > 0 else 0
        common_items.append({
            "item_id": item_id,
            "count": data["count"],
            "winrate": wr,
            "pick_rate": round(data["count"] / games * 100),
        })

    # Count rune frequencies
    rune_counts = defaultdict(lambda: {"count": 0, "wins": 0})
    for b in builds:
        pk = b.get("perk_primary", 0)
        if pk:
            rune_counts[pk]["count"] += 1
            if b.get("win"):
                rune_counts[pk]["wins"] += 1

    common_runes = []
    for rune_id, data in sorted(rune_counts.items(),
                                 key=lambda x: x[1]["count"], reverse=True)[:6]:
        wr = round(data["wins"] / data["count"] * 100) if data["count"] > 0 else 0
        common_runes.append({
            "rune_id": rune_id,
            "count": data["count"],
            "winrate": wr,
        })

    # Build the match list for display
    formatted = _format_matches(builds, version)

    return jsonify({
        "champion_name": champion_name,
        "ddragon_version": version,
        "games": games,
        "wins": wins,
        "winrate": winrate,
        "avg_kills": round(sum(b.get("kills", 0) for b in builds) / games, 1),
        "avg_deaths": round(sum(b.get("deaths", 0) for b in builds) / games, 1),
        "avg_assists": round(sum(b.get("assists", 0) for b in builds) / games, 1),
        "avg_cs": round(sum(b.get("cs", 0) for b in builds) / games),
        "avg_damage": round(sum(b.get("damage", 0) for b in builds) / games),
        "common_items": common_items,
        "common_runes": common_runes,
        "matches": formatted,
    })


# ---- Live Game + Prediction ------------------------------------------------

@app.route("/api/live/<int:account_id>", methods=["GET"])
def check_live_game(account_id):
    """Check if an account is in a live game."""
    acct = db.get_account(account_id)
    if not acct:
        return jsonify({"error": "Account not found"}), 404

    game = _api.get_active_game(acct["puuid"])
    if not game:
        return jsonify({"active": False})

    return jsonify({"active": True, "game_id": game.get("gameId")})


@app.route("/api/profiles/<int:profile_id>/live-status", methods=["GET"])
def profile_live_status(profile_id):
    """Batch check which accounts in a profile are currently in a live game."""
    profile = db.get_profile(profile_id)
    if not profile:
        return jsonify({"error": "Profile not found"}), 404

    accounts = profile.get("accounts", [])
    if not accounts:
        return jsonify({})

    result = {}

    def check_one(acct):
        try:
            game = _api.get_active_game(acct["puuid"])
            if game:
                return acct["id"], {
                    "active": True,
                    "game_id": game.get("gameId"),
                    "queue_id": game.get("gameQueueConfigId"),
                    "champion_id": None,
                }
            return acct["id"], {"active": False}
        except Exception:
            return acct["id"], {"active": False}

    workers = min(MAX_WORKERS, len(accounts))
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {executor.submit(check_one, a): a for a in accounts}
        for future in as_completed(futures):
            acct_id, status = future.result()
            result[str(acct_id)] = status

    return jsonify(result)


# Server-side cache for live status polling — one API check serves all tabs
_live_status_cache = {"data": [], "timestamp": 0.0}
_live_status_lock = threading.Lock()
_LIVE_STATUS_TTL = 60  # seconds — only re-check Riot API once per minute


@app.route("/api/all-live-status", methods=["GET"])
def all_live_status():
    """Check live game status for ALL accounts across ALL profiles.

    Returns a list of currently active players (empty list if none).
    Cached server-side so multiple browser tabs share one API check per minute.
    """
    now = time.time()

    # Return cached result if fresh enough
    if now - _live_status_cache["timestamp"] < _LIVE_STATUS_TTL:
        return jsonify(_live_status_cache["data"])

    # Only one request actually refreshes — others wait and use the result
    if not _live_status_lock.acquire(blocking=False):
        # Another request is already refreshing — return stale cache
        return jsonify(_live_status_cache["data"])

    try:
        accounts = db.get_all_accounts_unique()
        if not accounts:
            _live_status_cache["data"] = []
            _live_status_cache["timestamp"] = now
            return jsonify([])

        # Accounts are sorted by profile activity (most recent first)
        # so active players get checked first in the thread pool.
        # We check ALL accounts — no dormant cutoff — because a dormant
        # account could start playing at any time.
        active = []

        def check_one(acct):
            try:
                game = _api_duo.get_active_game(acct["puuid"])
                if game:
                    return {
                        "account_id": acct["id"],
                        "puuid": acct["puuid"],
                        "game_name": acct["game_name"],
                        "tag_line": acct["tag_line"],
                        "active": True,
                        "game_id": game.get("gameId"),
                        "queue_id": game.get("gameQueueConfigId"),
                    }
                return None
            except Exception:
                return None

        workers = min(MAX_WORKERS, len(accounts))
        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = [executor.submit(check_one, a) for a in accounts]
            for f in as_completed(futures):
                result = f.result()
                if result:
                    active.append(result)

        _live_status_cache["data"] = active
        _live_status_cache["timestamp"] = time.time()
        return jsonify(active)
    finally:
        _live_status_lock.release()


@app.route("/api/live-game/<puuid>", methods=["GET"])
def live_game_detail(puuid):
    """Get live game details with win prediction. Returns SSE stream.

    Uses an in-memory cache so re-searching the same active game returns
    instantly. When another request is already in progress, waits for it
    to finish and returns the cached result. After sending the main result,
    keeps the connection open briefly for a build_recommendation LLM event.
    """

    def _send_result_and_llm(result, puuid_inner):
        """Yield the main result event, then optionally the LLM event."""
        game_id = result.get("game_id", "")

        # Check for cached LLM analysis before sending main result
        cached_analysis = None
        if game_id and llm_client.is_available():
            cached = db.get_live_analysis(game_id, puuid_inner)
            if cached:
                try:
                    cached_analysis = json.loads(cached["analysis_json"])
                except (json.JSONDecodeError, TypeError):
                    pass

        # Include cached analysis in the main result if available
        result_to_send = dict(result)  # shallow copy to avoid mutating cache
        if cached_analysis:
            result_to_send["build_recommendation"] = cached_analysis

        yield f"event: result\ndata: {json.dumps(result_to_send)}\n\n"

        # If no cached analysis, fire LLM in background and send follow-up event
        if not cached_analysis and game_id and llm_client.is_available():
            llm_q = queue.Queue()

            def run_llm():
                try:
                    analysis = _generate_live_build_analysis(
                        game_id, puuid_inner, result
                    )
                    llm_q.put(("ok", analysis))
                except Exception as e:
                    logger.exception("Live LLM analysis failed for game %s",
                                     game_id)
                    llm_q.put(("error", str(e)))

            llm_thread = threading.Thread(target=run_llm, daemon=True)
            llm_thread.start()

            # Wait up to 35s for LLM response (30s timeout + 5s buffer)
            while llm_thread.is_alive():
                try:
                    status, payload = llm_q.get(timeout=10)
                    if status == "ok" and payload:
                        yield f"event: build_recommendation\ndata: {json.dumps({'ok': True, 'analysis': payload})}\n\n"
                    elif status == "error":
                        yield f"event: build_recommendation\ndata: {json.dumps({'ok': False, 'error': payload})}\n\n"
                    break
                except queue.Empty:
                    yield ": keepalive\n\n"
                    continue

            # Final drain in case the result arrived after thread finished
            if not llm_q.empty():
                try:
                    status, payload = llm_q.get_nowait()
                    if status == "ok" and payload:
                        yield f"event: build_recommendation\ndata: {json.dumps({'ok': True, 'analysis': payload})}\n\n"
                except queue.Empty:
                    pass

            llm_thread.join(timeout=2)

    def generate():
        # ---- Fast path: check in-memory cache for this player's active game.
        for gid, entry in list(_live_game_cache.items()):
            if (time.time() - entry["ts"]) < _LIVE_CACHE_TTL:
                cached_result = entry["result"]
                if cached_result.get("searched_puuid") == puuid:
                    yield f"event: progress\ndata: {json.dumps({'step': 'Loading cached game data...'})}\n\n"
                    yield from _send_result_and_llm(cached_result, puuid)
                    return

        # ---- Quick spectator check to get game_id early.
        # This lets us send cached LLM build recommendations BEFORE the
        # full player data (names/ranks/winrates) finishes loading.
        yield f"event: progress\ndata: {json.dumps({'step': 'Checking for active game...'})}\n\n"
        try:
            spectator_data = _api.get_active_game(puuid)
        except Exception as e:
            logger.exception("Spectator API check failed")
            yield f"event: error\ndata: {json.dumps({'error': str(e)})}\n\n"
            return

        if not spectator_data:
            yield f"event: error\ndata: {json.dumps({'error': 'Player is not currently in a game.'})}\n\n"
            return

        early_game_id = str(spectator_data.get("gameId", ""))

        # Send cached LLM build recommendation immediately if available
        early_llm_sent = False
        if early_game_id and llm_client.is_available():
            cached_llm = db.get_live_analysis(early_game_id, puuid)
            if cached_llm:
                try:
                    analysis = json.loads(cached_llm["analysis_json"])
                    yield f"event: cached_build\ndata: {json.dumps({'ok': True, 'analysis': analysis})}\n\n"
                    early_llm_sent = True
                except (json.JSONDecodeError, TypeError):
                    pass

        # If no cached LLM analysis exists, fire the LLM immediately using
        # spectator data (champion names + roles) — don't wait for the slow
        # _build_live_game() to finish fetching ranks/winrates/duos.
        early_llm_thread = None
        early_llm_q = queue.Queue()
        if not early_llm_sent and early_game_id and llm_client.is_available():
            try:
                # Build lightweight team comp from spectator data
                champion_map = _api.get_champion_data()
                participants = spectator_data.get("participants", [])
                light_teams_map = defaultdict(list)
                for p in participants:
                    team_id = p.get("teamId", 0)
                    champ_id = p.get("championId", 0)
                    p_puuid = p.get("puuid", "")
                    spell1 = p.get("spell1Id", 0)
                    spell2 = p.get("spell2Id", 0)
                    has_smite = spell1 == SPELL_SMITE or spell2 == SPELL_SMITE
                    light_teams_map[team_id].append({
                        "puuid": p_puuid,
                        "champion_id": champ_id,
                        "champion_name": champion_map.get(champ_id, "Unknown"),
                        "team_id": team_id,
                        "spell1": spell1,
                        "spell2": spell2,
                        "has_smite": has_smite,
                        "role": None,
                        "rank": None,
                    })

                # Assign roles using the same Hungarian algorithm
                _assign_team_roles(light_teams_map)

                # Build minimal live_result structure
                light_teams = []
                for tid in sorted(light_teams_map.keys()):
                    light_teams.append({
                        "team_id": tid,
                        "players": light_teams_map[tid],
                    })
                light_result = {
                    "game_id": early_game_id,
                    "teams": light_teams,
                    "searched_puuid": puuid,
                }

                def run_early_llm():
                    try:
                        analysis = _generate_live_build_analysis(
                            early_game_id, puuid, light_result
                        )
                        early_llm_q.put(("ok", analysis))
                    except Exception as e:
                        logger.exception(
                            "Early LLM fire failed for game %s",
                            early_game_id
                        )
                        early_llm_q.put(("error", str(e)))

                early_llm_thread = threading.Thread(
                    target=run_early_llm, daemon=True
                )
                early_llm_thread.start()
                yield f"event: progress\ndata: {json.dumps({'step': 'Generating build recommendation...'})}\n\n"
                logger.info(
                    "Fired early LLM from spectator data for game %s",
                    early_game_id
                )
            except Exception:
                logger.exception("Failed to build lightweight result for early LLM")

        progress_q = queue.Queue()

        def on_progress(msg):
            progress_q.put(msg)

        result_holder = [None]
        error_holder = [None]

        def run():
            # Lock on game_id (not puuid) so that multiple players in the
            # same game share a single _build_live_game() call.
            lock_key = early_game_id or puuid
            lock = task_lock("live_game", lock_key)
            acquired = lock.acquire(blocking=False)
            if not acquired:
                # Another request is already building this game — wait
                # for it to finish and use its cached result. NEVER re-run.
                on_progress("Game data loading (another request in progress)...")
                lock.acquire(blocking=True, timeout=120)
                lock.release()
                # Return cached result from the first request
                if early_game_id and early_game_id in _live_game_cache:
                    entry = _live_game_cache[early_game_id]
                    if (time.time() - entry["ts"]) < _LIVE_CACHE_TTL:
                        result_holder[0] = entry["result"]
                        progress_q.put(None)
                        return
                # Fallback: scan cache by puuid
                for gid, entry in list(_live_game_cache.items()):
                    if (time.time() - entry["ts"]) < _LIVE_CACHE_TTL:
                        if entry["result"].get("searched_puuid") == puuid:
                            result_holder[0] = entry["result"]
                            progress_q.put(None)
                            return
                # First request must have failed — don't re-run, just error
                error_holder[0] = "Game data unavailable. Try again."
                progress_q.put(None)
                return

            try:
                # Pass spectator_data to avoid duplicate API call
                result_holder[0] = _build_live_game(
                    puuid, on_progress, spectator_data=spectator_data
                )
                # Cache the result by game_id
                game_id = result_holder[0].get("game_id", "")
                if game_id:
                    _cache_live_game(game_id, result_holder[0])
            except ValueError as e:
                error_holder[0] = str(e)
            except Exception as e:
                logger.exception("Error in live game lookup")
                error_holder[0] = str(e)
            finally:
                if acquired:
                    lock.release()
                progress_q.put(None)

        thread = threading.Thread(target=run, daemon=True)
        thread.start()

        while True:
            # Check for early LLM result (non-blocking) while waiting
            # for progress from _build_live_game
            if not early_llm_sent and not early_llm_q.empty():
                try:
                    status, payload = early_llm_q.get_nowait()
                    if status == "ok" and payload:
                        yield f"event: cached_build\ndata: {json.dumps({'ok': True, 'analysis': payload})}\n\n"
                        early_llm_sent = True
                except queue.Empty:
                    pass

            try:
                step = progress_q.get(timeout=5)
            except queue.Empty:
                # Send SSE comment as keepalive to prevent proxy/Cloudflare
                # from killing the connection during long rate-limit waits
                if not thread.is_alive():
                    break
                yield ": keepalive\n\n"
                continue
            if step is None:
                break
            yield f"event: progress\ndata: {json.dumps({'step': step})}\n\n"

        # Final check for early LLM result after main loop exits
        if not early_llm_sent and early_llm_thread is not None:
            # Give the LLM thread a moment to finish if it's close
            early_llm_thread.join(timeout=2)
            if not early_llm_q.empty():
                try:
                    status, payload = early_llm_q.get_nowait()
                    if status == "ok" and payload:
                        yield f"event: cached_build\ndata: {json.dumps({'ok': True, 'analysis': payload})}\n\n"
                        early_llm_sent = True
                except queue.Empty:
                    pass

        thread.join(timeout=5)

        if error_holder[0]:
            yield f"event: error\ndata: {json.dumps({'error': error_holder[0]})}\n\n"
            return
        elif not result_holder[0]:
            yield f"event: error\ndata: {json.dumps({'error': 'No response.'})}\n\n"
            return

        yield from _send_result_and_llm(result_holder[0], puuid)

    return Response(generate(), mimetype="text/event-stream")


def _hungarian_assignment(cost_matrix):
    """Solve the assignment problem using the Hungarian (Munkres) algorithm.

    Given an NxN cost matrix, finds the assignment of rows to columns
    that minimizes total cost. Returns list of (row, col) pairs.

    This is a pure-Python implementation to avoid adding scipy as a dependency.
    """
    n = len(cost_matrix)
    if n == 0:
        return []

    # Work with a copy
    C = [row[:] for row in cost_matrix]

    # Step 1: Subtract row minimums
    for i in range(n):
        m = min(C[i])
        for j in range(n):
            C[i][j] -= m

    # Step 2: Subtract column minimums
    for j in range(n):
        m = min(C[i][j] for i in range(n))
        for i in range(n):
            C[i][j] -= m

    # State tracking
    row_covered = [False] * n
    col_covered = [False] * n
    starred = [[False] * n for _ in range(n)]
    primed = [[False] * n for _ in range(n)]

    def _clear_covers():
        for i in range(n):
            row_covered[i] = False
            col_covered[i] = False

    def _clear_primes():
        for i in range(n):
            for j in range(n):
                primed[i][j] = False

    # Step 3: Star zeros
    for i in range(n):
        for j in range(n):
            if C[i][j] == 0 and not row_covered[i] and not col_covered[j]:
                starred[i][j] = True
                row_covered[i] = True
                col_covered[j] = True
    _clear_covers()

    for _ in range(n * n * 2):  # safety limit
        # Cover columns with starred zeros
        for i in range(n):
            for j in range(n):
                if starred[i][j]:
                    col_covered[j] = True

        # Check if done
        if sum(col_covered) >= n:
            break

        # Find uncovered zero
        while True:
            found = False
            z_row, z_col = -1, -1
            for i in range(n):
                if row_covered[i]:
                    continue
                for j in range(n):
                    if col_covered[j]:
                        continue
                    if C[i][j] == 0:
                        z_row, z_col = i, j
                        found = True
                        break
                if found:
                    break

            if not found:
                # No uncovered zero — adjust matrix
                min_val = float('inf')
                for i in range(n):
                    if row_covered[i]:
                        continue
                    for j in range(n):
                        if col_covered[j]:
                            continue
                        if C[i][j] < min_val:
                            min_val = C[i][j]
                for i in range(n):
                    for j in range(n):
                        if row_covered[i]:
                            C[i][j] += min_val
                        if not col_covered[j]:
                            C[i][j] -= min_val
                continue  # retry finding uncovered zero

            # Prime the uncovered zero
            primed[z_row][z_col] = True

            # Check if there's a starred zero in this row
            star_col = -1
            for j in range(n):
                if starred[z_row][j]:
                    star_col = j
                    break

            if star_col >= 0:
                # Cover this row, uncover the starred zero's column
                row_covered[z_row] = True
                col_covered[star_col] = False
            else:
                # Augmenting path starting from this primed zero
                path = [(z_row, z_col)]
                while True:
                    # Find starred zero in column of last path entry
                    r = -1
                    for i in range(n):
                        if starred[i][path[-1][1]]:
                            r = i
                            break
                    if r < 0:
                        break
                    path.append((r, path[-1][1]))
                    # Find primed zero in row of the starred zero
                    c = -1
                    for j in range(n):
                        if primed[r][j]:
                            c = j
                            break
                    path.append((r, c))

                # Augment: unstar starred, star primed
                for r, c in path:
                    starred[r][c] = not starred[r][c]

                _clear_covers()
                _clear_primes()
                break  # go back to covering columns

    result = []
    for i in range(n):
        for j in range(n):
            if starred[i][j]:
                result.append((i, j))
    return result


def _assign_team_roles(teams_map: dict):
    """Assign roles to players per team using champion role frequency data
    and the Hungarian algorithm for optimal assignment.

    Strategy:
    1. Hard-assign Smite holder → Jungle (if exactly one)
    2. Build probability matrix from champion_role_rates.py data
    3. Apply summoner spell bonuses (Exhaust → Support, Heal/Barrier → Bot)
    4. Use Hungarian algorithm to find optimal role assignment
    5. Fall back to greedy assignment if Hungarian fails
    """
    ROLES = ["TOP", "JUNGLE", "MIDDLE", "BOTTOM", "UTILITY"]
    ROLE_TO_DISPLAY = {
        "TOP": "Top", "JUNGLE": "Jungle", "MIDDLE": "Mid",
        "BOTTOM": "Bot", "UTILITY": "Support",
    }
    SPELL_EXHAUST = 3
    SPELL_HEAL = 7
    SPELL_BARRIER = 21

    def _has_spell(p, spell_id):
        return p.get("spell1") == spell_id or p.get("spell2") == spell_id

    for team_id, players in teams_map.items():
        n = len(players)
        if n == 0:
            continue

        # Build role probability for each player
        player_probs = []
        for p in players:
            rates = get_role_rates(p["champion_id"])
            # Apply summoner spell bonuses
            if _has_spell(p, SPELL_EXHAUST):
                rates["UTILITY"] = min(1.0, rates.get("UTILITY", 0) + 0.3)
            if _has_spell(p, SPELL_HEAL) or _has_spell(p, SPELL_BARRIER):
                rates["BOTTOM"] = min(1.0, rates.get("BOTTOM", 0) + 0.2)
            player_probs.append(rates)

        # Check for Smite → hard-assign Jungle
        smite_idx = None
        smite_players = [i for i, p in enumerate(players) if p.get("has_smite")]
        if len(smite_players) == 1:
            smite_idx = smite_players[0]

        if smite_idx is not None:
            # Remove Jungle from consideration, solve remaining 4 roles
            remaining_roles = [r for r in ROLES if r != "JUNGLE"]
            remaining_players = [i for i in range(n) if i != smite_idx]

            if len(remaining_players) == len(remaining_roles):
                # Build cost matrix (cost = 1 - probability, lower is better)
                cost_matrix = []
                for pi in remaining_players:
                    row = []
                    for role in remaining_roles:
                        prob = player_probs[pi].get(role, 0.0)
                        row.append(1.0 - prob)
                    cost_matrix.append(row)

                assignments = _hungarian_assignment(cost_matrix)
                result = {smite_idx: "Jungle"}
                for row_idx, col_idx in assignments:
                    player_idx = remaining_players[row_idx]
                    role = remaining_roles[col_idx]
                    result[player_idx] = ROLE_TO_DISPLAY[role]
                # Apply
                for i, p in enumerate(players):
                    p["role"] = result.get(i, "Unknown")
            else:
                # Edge case: not exactly 4 remaining — fall through
                players[smite_idx]["role"] = "Jungle"
                _assign_remaining_greedy(
                    players, player_probs, ROLES, ROLE_TO_DISPLAY,
                    skip_indices={smite_idx}, skip_roles={"JUNGLE"}
                )
        else:
            # No Smite holder — solve full 5x5 assignment
            if n == len(ROLES):
                cost_matrix = []
                for pi in range(n):
                    row = []
                    for role in ROLES:
                        prob = player_probs[pi].get(role, 0.0)
                        row.append(1.0 - prob)
                    cost_matrix.append(row)

                assignments = _hungarian_assignment(cost_matrix)
                result = {}
                for row_idx, col_idx in assignments:
                    result[row_idx] = ROLE_TO_DISPLAY[ROLES[col_idx]]
                for i, p in enumerate(players):
                    p["role"] = result.get(i, "Unknown")
            else:
                # Non-standard team size — greedy fallback
                _assign_remaining_greedy(
                    players, player_probs, ROLES, ROLE_TO_DISPLAY,
                    skip_indices=set(), skip_roles=set()
                )


def _assign_remaining_greedy(players, player_probs, roles, role_display,
                             skip_indices, skip_roles):
    """Greedy fallback: assign each unassigned player to their highest-
    probability unassigned role."""
    available_roles = [r for r in roles if r not in skip_roles]
    unassigned = [i for i in range(len(players)) if i not in skip_indices]

    # Sort by max probability descending (assign most certain players first)
    scored = []
    for i in unassigned:
        max_prob = max(player_probs[i].get(r, 0.0) for r in available_roles)
        scored.append((max_prob, i))
    scored.sort(reverse=True)

    taken = set()
    for _, i in scored:
        best_role = None
        best_prob = -1
        for r in available_roles:
            if r in taken:
                continue
            prob = player_probs[i].get(r, 0.0)
            if prob > best_prob:
                best_prob = prob
                best_role = r
        if best_role:
            players[i]["role"] = role_display[best_role]
            taken.add(best_role)
        else:
            players[i]["role"] = "Unknown"


def _build_live_game(puuid: str, on_progress=None, spectator_data=None):
    """Build live game data with prediction.

    Args:
        puuid: Player's PUUID.
        on_progress: Callback for progress messages.
        spectator_data: Pre-fetched spectator API response (optional).
            If provided, skips the initial get_active_game() call.
    """

    def _progress(msg):
        if on_progress:
            on_progress(msg)

    if spectator_data:
        game = spectator_data
    else:
        _progress("Checking for active game...")
        game = _api.get_active_game(puuid)
    if not game:
        raise ValueError("Player is not currently in a game.")

    # Log raw spectator participant data for debugging role assignment
    raw_participants = game.get("participants", [])
    if raw_participants:
        p0 = raw_participants[0]
        logger.info("Spectator participant keys: %s", list(p0.keys()))
        for rp in raw_participants:
            logger.info(
                "  Team %s: champ=%s spell1=%s spell2=%s %s",
                rp.get("teamId"), rp.get("championId"),
                rp.get("spell1Id"), rp.get("spell2Id"),
                {k: v for k, v in rp.items() if k not in (
                    "teamId", "championId", "spell1Id", "spell2Id",
                    "puuid", "summonerId", "perks", "gameCustomizationObjects"
                )}
            )

    _progress("Loading champion data...")
    version = _api.get_latest_version()
    champion_map = _api.get_champion_data(version)

    game_id = str(game.get("gameId", ""))
    queue_id = game.get("gameQueueConfigId", -1)
    queue_name = QUEUE_NAMES.get(queue_id, game.get("gameMode", "Unknown"))

    # Check for existing prediction
    existing_pred = db.get_prediction_by_game(game_id)

    # Build participant data — roles assigned per-team after collecting all players
    participants = game.get("participants", [])
    teams_map = defaultdict(list)

    for p in participants:
        team_id = p.get("teamId", 0)
        champ_id = p.get("championId", 0)
        p_puuid = p.get("puuid", "")
        hidden = not p_puuid or p_puuid.startswith("BOT")

        spell1 = p.get("spell1Id", 0)
        spell2 = p.get("spell2Id", 0)
        has_smite = spell1 == SPELL_SMITE or spell2 == SPELL_SMITE

        teams_map[team_id].append({
            "puuid": p_puuid,
            "summoner_id": p.get("summonerId", ""),
            "champion_id": champ_id,
            "champion_name": champion_map.get(champ_id, "Unknown"),
            "team_id": team_id,
            "hidden": hidden,
            "spell1": spell1,
            "spell2": spell2,
            "has_smite": has_smite,
            "role": None,
            "game_name": None,
            "tag_line": None,
            "rank": None,
            "champion_winrate": None,
        })

    # Assign roles per team using smite detection + champion position data
    _assign_team_roles(teams_map)

    # Resolve names
    all_players = [
        pl for team in teams_map.values() for pl in team if not pl["hidden"]
    ]
    _progress(f"Resolving {len(all_players)} player names...")
    _resolve_names_parallel(all_players)

    # Fetch ranks
    _progress("Fetching ranked data...")
    _fetch_ranks_parallel(all_players, queue_id)

    # Fetch champion winrates
    _progress("Fetching champion win rates...")
    _fetch_champion_winrates(all_players)

    # Detect duos
    team_duos = _detect_duos_for_live_game(teams_map, on_progress)

    # Build prediction
    _progress("Calculating win prediction...")
    prediction = _predict_winner(teams_map, game_id, existing_pred)

    teams_result = []
    for team_id in sorted(teams_map.keys()):
        teams_result.append({
            "team_id": team_id,
            "players": teams_map[team_id],
            "duos": team_duos.get(team_id, []),
        })

    return {
        "game_id": game_id,
        "game_start_time": game.get("gameStartTime"),
        "game_length": game.get("gameLength"),
        "game_mode": game.get("gameMode", "UNKNOWN"),
        "queue_name": queue_name,
        "queue_id": queue_id,
        "teams": teams_result,
        "ddragon_version": version,
        "prediction": prediction,
        "searched_puuid": puuid,
    }


def _resolve_names_parallel(players: list):
    """Resolve gameName/tagLine for players in parallel."""
    if not players:
        return

    def _fetch(player):
        try:
            acct = _api.get_account_by_puuid(player["puuid"])
            if acct:
                player["game_name"] = acct.get("gameName")
                player["tag_line"] = acct.get("tagLine")
                if not player["game_name"]:
                    player["hidden"] = True
        except Exception:
            logger.exception("Failed to resolve name for %s", player["puuid"])
            player["hidden"] = True

    workers = min(MAX_WORKERS, len(players))
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = [executor.submit(_fetch, p) for p in players]
        for f in as_completed(futures):
            f.result()


def _fetch_ranks_parallel(players: list, queue_id: int):
    """Fetch ranked data for players in parallel."""
    if not players:
        return

    preferred_queue = RANKED_FLEX if queue_id == 440 else RANKED_SOLO

    def _fetch(player):
        puuid = player.get("puuid", "")
        if not puuid:
            return
        try:
            entries = _api.get_league_entries_by_puuid(puuid)
            chosen = None
            fallback = None
            for entry in entries:
                qt = entry.get("queueType", "")
                if qt == preferred_queue:
                    chosen = entry
                    break
                elif qt in (RANKED_SOLO, RANKED_FLEX):
                    fallback = entry
            entry = chosen or fallback
            if entry:
                tier = entry.get("tier", "").capitalize()
                div = DIVISION_SHORT.get(entry.get("rank", ""), entry.get("rank", ""))
                lp = entry.get("leaguePoints", 0)
                wins = entry.get("wins", 0)
                losses = entry.get("losses", 0)
                total = wins + losses
                wr = round(wins / total * 100) if total > 0 else 0
                is_apex = tier in ("Master", "Grandmaster", "Challenger")
                player["rank"] = {
                    "tier": tier,
                    "division": div,
                    "lp": lp,
                    "wins": wins,
                    "losses": losses,
                    "winrate": wr,
                    "full": tier if is_apex else f"{tier} {div}",
                    "queue_type": entry.get("queueType", ""),
                }
        except Exception:
            logger.exception("Failed to fetch rank for %s", puuid)

    workers = min(MAX_WORKERS, len(players))
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = [executor.submit(_fetch, p) for p in players]
        for f in as_completed(futures):
            f.result()


def _fetch_champion_winrates(players: list):
    """Fetch champion-specific winrate for each player.

    DB-only: queries local participants table. No Riot API calls.
    Champion WR is only 10% weight — not worth burning rate limit budget
    on 50+ API calls for marginal prediction improvement. Players we've
    seen before (our own accounts) will have data; unknowns get default 50%.
    """
    if not players:
        return

    for player in players:
        if player.get("hidden"):
            continue
        puuid = player.get("puuid", "")
        champ_id = player.get("champion_id", 0)
        if not puuid or not champ_id:
            continue

        try:
            with db.get_db() as conn:
                rows = conn.execute(
                    """SELECT win FROM participants
                       WHERE puuid = ? AND champion_id = ?
                       ORDER BY match_id DESC LIMIT 10""",
                    (puuid, champ_id)
                ).fetchall()

            if rows:
                games = len(rows)
                wins = sum(1 for r in rows if r["win"])
                player["champion_winrate"] = {
                    "wins": wins,
                    "games": games,
                    "winrate": round(wins / games * 100),
                }
        except Exception:
            logger.exception("Failed to fetch champion winrate")


# ---- Win Prediction --------------------------------------------------------

def _predict_winner(teams_map: dict, game_id: str,
                    existing_pred: dict | None,
                    save: bool = True) -> dict:
    """Predict the winning team based on heuristics.

    Weights derived from analysis of 61 predictions (18 live + 43 retroactive):
    - Rank alone predicts correctly ~72% of the time (Riot claims ~75%)
    - Recent form (overall ranked WR) is a solid secondary signal
    - Champion WR is noisy with small sample sizes, especially in live
    - Champion exp was useless (always 50 in live) — removed

    Factors:
    1. Rank Score (65%) - Average numeric rank per team — strongest predictor
    2. Recent Form (25%) - Average overall ranked WR per team
    3. Champion Win Rate (10%) - Average champion WR (only with 3+ games data)
    """
    team_scores = {}
    team_factors = {}  # Per-team factor breakdown for transparency
    player_factors = {}  # Per-player factor breakdown

    for team_id, players in teams_map.items():
        visible = [p for p in players if not p.get("hidden")]
        if not visible:
            team_scores[team_id] = 50.0
            team_factors[str(team_id)] = {
                "rank_score": 50, "champion_wr": 50,
                "recent_form": 50,
            }
            continue

        per_player = []

        # Factor 1: Rank Score
        rank_scores = []
        for p in visible:
            r = p.get("rank")
            if r:
                tier_upper = r["tier"].upper()
                base = TIER_SCORES.get(tier_upper, 12)
                div_val = DIVISION_SCORES.get(
                    {"1": "I", "2": "II", "3": "III", "4": "IV"}.get(
                        r["division"], r["division"]
                    ), 0
                )
                rs = base + div_val
            else:
                rs = 12  # Default to Gold-ish
            rank_scores.append(rs)

            # Champion WR for this player
            cw = p.get("champion_winrate")
            cw_val = cw["winrate"] if cw and cw.get("games", 0) >= 3 else 50
            cw_games = cw["games"] if cw else 0

            # Recent form for this player
            form_val = r["winrate"] if r and r.get("winrate") else 50

            per_player.append({
                "name": f"{p.get('game_name', '?')}#{p.get('tag_line', '?')}",
                "champion": p.get("champion_name", "?"),
                "rank_score": round(min(rs / 32 * 100, 100), 1),
                "champion_wr": round(cw_val, 1),
                "recent_form": round(form_val, 1),
                "champion_games": cw_games,
            })

        avg_rank = sum(rank_scores) / len(rank_scores) if rank_scores else 12
        rank_normalized = min(avg_rank / 32 * 100, 100)  # 0-100 scale

        # Factor 2: Champion Win Rate
        champ_wrs = []
        for p in visible:
            cw = p.get("champion_winrate")
            if cw and cw.get("games", 0) >= 3:
                champ_wrs.append(cw["winrate"])
            else:
                champ_wrs.append(50)
        avg_champ_wr = sum(champ_wrs) / len(champ_wrs) if champ_wrs else 50

        # Factor 3: Recent Form (ranked WR)
        form_wrs = []
        for p in visible:
            r = p.get("rank")
            if r and r.get("winrate"):
                form_wrs.append(r["winrate"])
            else:
                form_wrs.append(50)
        avg_form = sum(form_wrs) / len(form_wrs) if form_wrs else 50

        # Weighted score — rank-heavy based on data analysis:
        # rank alone ~72% correct, form ~72%, champWR noisy, exp useless
        score = (
            rank_normalized * 0.65 +
            avg_form * 0.25 +
            avg_champ_wr * 0.10
        )
        team_scores[team_id] = score
        team_factors[str(team_id)] = {
            "rank_score": round(rank_normalized, 1),
            "champion_wr": round(avg_champ_wr, 1),
            "recent_form": round(avg_form, 1),
        }
        player_factors[str(team_id)] = per_player

    # Determine winner
    sorted_teams = sorted(team_scores.items(), key=lambda x: x[1], reverse=True)
    predicted_team = sorted_teams[0][0]
    score_diff = abs(sorted_teams[0][1] - sorted_teams[1][1]) if len(sorted_teams) > 1 else 0
    # Confidence: scale score diff to 0.5-0.95 range
    confidence = min(0.5 + score_diff / 40, 0.95)

    factors = {
        "team_scores": {str(k): round(v, 1) for k, v in team_scores.items()},
        "team_factors": team_factors,
        "player_factors": player_factors,
        "weights": {
            "rank_score": 0.65,
            "champion_wr": 0.10,
            "recent_form": 0.25,
        },
    }

    # Store prediction if new
    if existing_pred:
        prediction_data = {
            "id": existing_pred["id"],
            "predicted_team": existing_pred["predicted_team"],
            "confidence": existing_pred["confidence"],
            "factors": json.loads(existing_pred.get("factors", "{}")) if existing_pred.get("factors") else {},
            "outcome": existing_pred["outcome"],
            "blue_score": existing_pred.get("blue_score", 0),
            "red_score": existing_pred.get("red_score", 0),
            "already_predicted": True,
        }
    else:
        blue_score = team_scores.get(100, 50)
        red_score = team_scores.get(200, 50)

        pred_id = None
        if save:
            # Re-check for existing prediction (another thread may have inserted
            # while we were computing scores).  create_prediction() also uses
            # INSERT OR IGNORE, so this is belt-and-suspenders.
            recheck = db.get_prediction_by_game(game_id)
            if recheck:
                return {
                    "id": recheck["id"],
                    "predicted_team": recheck["predicted_team"],
                    "confidence": recheck["confidence"],
                    "factors": json.loads(recheck.get("factors", "{}")) if recheck.get("factors") else {},
                    "outcome": recheck["outcome"],
                    "blue_score": recheck.get("blue_score", 0),
                    "red_score": recheck.get("red_score", 0),
                    "already_predicted": True,
                }

            # Build player summaries for storage (only for live game predictions)
            blue_players = json.dumps([
                {"name": f"{p.get('game_name', '?')}#{p.get('tag_line', '?')}",
                 "champion": p.get("champion_name", "?"),
                 "rank": p.get("rank", {}).get("full", "Unranked") if p.get("rank") else "Unranked"}
                for p in teams_map.get(100, []) if not p.get("hidden")
            ])
            red_players = json.dumps([
                {"name": f"{p.get('game_name', '?')}#{p.get('tag_line', '?')}",
                 "champion": p.get("champion_name", "?"),
                 "rank": p.get("rank", {}).get("full", "Unranked") if p.get("rank") else "Unranked"}
                for p in teams_map.get(200, []) if not p.get("hidden")
            ])

            pred = db.create_prediction(
                game_id=game_id,
                predicted_team=predicted_team,
                confidence=round(confidence, 3),
                factors=json.dumps(factors),
                blue_score=round(blue_score, 1),
                red_score=round(red_score, 1),
                blue_players=blue_players,
                red_players=red_players,
            )
            pred_id = pred["id"]

        prediction_data = {
            "id": pred_id,
            "predicted_team": predicted_team,
            "confidence": round(confidence, 3),
            "factors": factors,
            "outcome": "pending",
            "blue_score": round(blue_score, 1),
            "red_score": round(red_score, 1),
            "already_predicted": False,
        }

    return prediction_data


# ---- Predictions API -------------------------------------------------------

@app.route("/api/predictions", methods=["GET"])
def list_predictions():
    limit = request.args.get("limit", 20, type=int)
    offset = request.args.get("offset", 0, type=int)
    limit = min(limit, 100)  # cap at 100

    data = db.get_all_predictions(limit=limit, offset=offset)
    version = _api.get_latest_version()
    result = []

    for p in data["predictions"]:
        entry = dict(p)
        # Parse JSON fields
        for field in ("factors", "blue_players", "red_players"):
            val = entry.get(field)
            if val and isinstance(val, str):
                try:
                    entry[field] = json.loads(val)
                except (json.JSONDecodeError, TypeError):
                    pass

        # For match-source predictions, build blue_players/red_players from
        # the match participants so the frontend can render player names
        mid = entry.get("resolved_match_id") or entry.get("match_id")
        if mid and entry.get("outcome") != "pending":
            match = db.get_match_detail(mid)
            if match:
                duration = match.get("game_duration", 0)
                teams = {100: {"kills": 0, "deaths": 0, "assists": 0,
                               "gold": 0, "damage": 0},
                         200: {"kills": 0, "deaths": 0, "assists": 0,
                               "gold": 0, "damage": 0}}
                winner = None
                blue_players_list = []
                red_players_list = []
                for pt in match.get("participants", []):
                    tid = pt.get("team_id", 0)
                    if tid in teams:
                        teams[tid]["kills"] += pt.get("kills", 0)
                        teams[tid]["deaths"] += pt.get("deaths", 0)
                        teams[tid]["assists"] += pt.get("assists", 0)
                        teams[tid]["gold"] += pt.get("gold", 0)
                        teams[tid]["damage"] += pt.get("damage", 0)
                    if pt.get("win") and winner is None:
                        winner = tid
                    # Build player summaries for match-source predictions
                    player_summary = {
                        "name": f"{pt.get('game_name', pt.get('champion_name', '?'))}#{pt.get('tag_line', '?')}",
                        "champion": pt.get("champion_name", "?"),
                        "champion_id": pt.get("champion_id"),
                    }
                    if tid == 100:
                        blue_players_list.append(player_summary)
                    elif tid == 200:
                        red_players_list.append(player_summary)

                entry["match_teams"] = teams
                entry["match_winner"] = winner
                entry["match_duration"] = duration

                # Fill in blue/red players if missing (match-source predictions)
                if not entry.get("blue_players"):
                    entry["blue_players"] = blue_players_list
                if not entry.get("red_players"):
                    entry["red_players"] = red_players_list

        entry["ddragon_version"] = version
        result.append(entry)

    return jsonify({
        "predictions": result,
        "total": data["total"],
        "correct": data["correct"],
        "incorrect": data["incorrect"],
        "pending": data["pending"],
        "limit": limit,
        "offset": offset,
    })


@app.route("/api/predictions/<int:pred_id>/resolve", methods=["POST"])
def resolve_prediction_route(pred_id):
    """Try to resolve a prediction by checking if the game has ended.

    Searches for the match in recent history of one of the participants.
    """
    with db.get_db() as conn:
        row = conn.execute(
            "SELECT * FROM predictions WHERE id = ?", (pred_id,)
        ).fetchone()

    if not row:
        return jsonify({"error": "Prediction not found"}), 404

    pred = dict(row)
    if pred["outcome"] != "pending":
        return jsonify({"message": "Already resolved", "outcome": pred["outcome"]})

    # Try to find the match result
    # Parse blue_players to get a name to search
    try:
        blue_players = json.loads(pred.get("blue_players", "[]"))
    except (json.JSONDecodeError, TypeError):
        blue_players = []

    if not blue_players:
        return jsonify({"error": "No player data to resolve from"}), 400

    # Search for a recent match with matching game_id
    # The game_id from spectator API is different from match_id,
    # but we can search by participant names
    first_player_name = blue_players[0].get("name", "")
    if "#" not in first_player_name:
        return jsonify({"error": "Cannot resolve: invalid player data"}), 400

    parts = first_player_name.split("#", 1)
    try:
        account = _api.get_account_by_riot_id(parts[0], parts[1])
        if not account:
            return jsonify({"error": "Could not find player"}), 404

        # Get their recent matches
        match_ids = _api.get_match_ids(account["puuid"], count=5)
        for mid in match_ids:
            match_data = _api.get_match(mid)
            if not match_data:
                continue

            info = match_data.get("info", {})
            # Store this match
            db.store_match(match_data)

            # Check if this game's participants match our prediction
            match_puuids = {p.get("puuid") for p in info.get("participants", [])}

            # Find if this participant was on team 100 (blue)
            for p in info.get("participants", []):
                if p.get("puuid") == account["puuid"]:
                    # This participant was in the match
                    winning_team = 100 if any(
                        pp.get("win") for pp in info.get("participants", [])
                        if pp.get("teamId") == 100
                    ) else 200

                    outcome = "correct" if winning_team == pred["predicted_team"] else "incorrect"
                    db.resolve_prediction(pred_id, outcome, mid)
                    return jsonify({
                        "outcome": outcome,
                        "match_id": mid,
                        "winning_team": winning_team,
                    })

    except Exception as e:
        logger.exception("Error resolving prediction")
        return jsonify({"error": str(e)}), 500

    return jsonify({"message": "Game may still be in progress", "outcome": "pending"})


# ---- Quick search (for live game by Riot ID) --------------------------------

@app.route("/api/search", methods=["GET"])
def search_player():
    """Quick search: resolve Riot ID and check for live game."""
    riot_id = request.args.get("riot_id", "").strip()
    if not riot_id or "#" not in riot_id:
        return jsonify({"error": "Invalid Riot ID format. Use GameName#TagLine"}), 400

    parts = riot_id.split("#", 1)
    game_name = parts[0].strip()
    tag_line = parts[1].strip()

    try:
        account = _api.get_account_by_riot_id(game_name, tag_line)
        if not account:
            return jsonify({"error": f"Player '{riot_id}' not found"}), 404

        puuid = account["puuid"]
        game = _api.get_active_game(puuid)

        return jsonify({
            "puuid": puuid,
            "game_name": account.get("gameName", game_name),
            "tag_line": account.get("tagLine", tag_line),
            "in_game": game is not None,
            "game_id": game.get("gameId") if game else None,
        })

    except Exception as e:
        logger.exception("Error in search")
        return jsonify({"error": str(e)}), 500


# ---- Item data (Data Dragon) -----------------------------------------------

@app.route("/api/items", methods=["GET"])
def get_items():
    """Return item ID -> {name, description, gold} mapping for tooltips."""
    version = _api.get_latest_version()
    items = _api.get_item_data(version)
    return jsonify({"version": version, "items": items})


# ---- Match detail + retroactive prediction ---------------------------------

@app.route("/api/matches/<match_id>/detail", methods=["GET"])
def match_detail(match_id):
    """Get full match detail: all 10 players with extended stats + computed metrics."""
    try:
        match = db.get_match_detail(match_id)
        if not match:
            return jsonify({"error": "Match not found in database"}), 404

        # Try to get latest DDragon version; fall back to match's game_version
        try:
            version = _api.get_latest_version()
        except Exception:
            version = match.get("game_version", "14.1.1")

        duration = match.get("game_duration", 0)
        duration_min = max(duration / 60, 1)  # avoid division by zero

        # Compute team totals
        teams = {100: {"kills": 0, "damage": 0, "gold": 0},
                 200: {"kills": 0, "damage": 0, "gold": 0}}
        for p in match.get("participants", []):
            tid = p.get("team_id", 0)
            if tid in teams:
                teams[tid]["kills"] += p.get("kills", 0)
                teams[tid]["damage"] += p.get("damage", 0)
                teams[tid]["gold"] += p.get("gold", 0)

        # Add computed stats per participant
        for p in match.get("participants", []):
            p["cs_per_min"] = round(p.get("cs", 0) / duration_min, 1)
            tid = p.get("team_id", 0)
            team_kills = teams.get(tid, {}).get("kills", 1) or 1
            team_dmg = teams.get(tid, {}).get("damage", 1) or 1
            p["kill_participation"] = round(
                (p.get("kills", 0) + p.get("assists", 0)) / team_kills * 100
            )
            p["damage_share"] = round(p.get("damage", 0) / team_dmg * 100)

        # Determine actual winner
        winner = None
        for p in match.get("participants", []):
            if p.get("win"):
                winner = p.get("team_id")
                break

        queue_id = match.get("queue_id", 0)
        queue_name = QUEUE_NAMES.get(queue_id, "Unknown")

        return jsonify({
            "match_id": match_id,
            "game_start": match.get("game_start"),
            "game_duration": duration,
            "game_version": match.get("game_version"),
            "queue_id": queue_id,
            "queue_name": queue_name,
            "ddragon_version": version,
            "winning_team": winner,
            "teams": teams,
            "participants": match.get("participants", []),
        })
    except Exception as exc:
        app.logger.error("match_detail error for %s: %s", match_id, exc)
        return jsonify({"error": "Failed to load match details. Please retry."}), 500


# ---- Duo Detection ---------------------------------------------------------

@app.route("/api/matches/<match_id>/duos", methods=["GET"])
def match_duos(match_id):
    """Detect duo pairs in a historical match.

    For each team, fetches recent match IDs per player (before this game)
    and flags pairs with >= SHARED_MATCH_THRESHOLD shared matches.
    Results are cached in duo_cache table (historical matches never change).
    """
    # Check cache first (fast path, no lock needed)
    cached = db.get_duo_cache(match_id)
    if cached is not None:
        return jsonify(cached)

    # Acquire lock — second caller blocks and will hit cache after first finishes
    lock = task_lock("duos", match_id)
    with lock:
        # Re-check cache after acquiring lock (first caller may have populated it)
        cached = db.get_duo_cache(match_id)
        if cached is not None:
            return jsonify(cached)
        return _compute_duos(match_id)


def _compute_duos(match_id):
    """Compute duo detection for a match (called under lock)."""
    # Get participants from the database
    participants = db.get_match_participants_puuids(match_id)
    if not participants:
        return jsonify({"error": "Match not found or no participants"}), 404

    # Get match start time for end_time filtering
    game_start = db.get_match_start_time(match_id)
    # Convert epoch ms to epoch seconds for Riot API end_time param
    end_time_s = int(game_start / 1000) if game_start else None

    # Group participants by team
    teams = defaultdict(list)
    for p in participants:
        teams[p["team_id"]].append(p)

    # Fetch recent match IDs per player (parallel)
    puuid_to_matches = {}

    def _fetch_match_ids(puuid):
        try:
            ids = _api_duo.get_match_ids(
                puuid, count=DUO_MATCH_HISTORY_COUNT,
                end_time=end_time_s,
            )
            return puuid, set(ids) if ids else set()
        except Exception:
            logger.exception("Failed to fetch match IDs for duo detection: %s", puuid)
            return puuid, set()

    all_puuids = [p["puuid"] for p in participants if p["puuid"]]
    if all_puuids:
        workers = min(MAX_WORKERS, len(all_puuids))
        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = {executor.submit(_fetch_match_ids, pid): pid for pid in all_puuids}
            for future in as_completed(futures):
                pid, match_set = future.result()
                puuid_to_matches[pid] = match_set

    # Detect duos: set intersection per same-team pair
    all_shared_ids = set()
    team_duos_shared = {}  # (puuid1, puuid2) -> shared match IDs

    for team_id, team_players in teams.items():
        team_puuids = [p["puuid"] for p in team_players if p["puuid"]]
        for p1, p2 in combinations(team_puuids, 2):
            m1 = puuid_to_matches.get(p1, set())
            m2 = puuid_to_matches.get(p2, set())
            shared = m1 & m2
            if len(shared) >= SHARED_MATCH_THRESHOLD:
                team_duos_shared[(p1, p2)] = shared
                all_shared_ids.update(shared)

    # Fetch shared match details for duo winrate (parallel)
    shared_match_cache = {}
    if all_shared_ids:
        def _fetch_detail(mid):
            try:
                return mid, _api_duo.get_match(mid)
            except Exception:
                return mid, None

        workers = min(MAX_WORKERS, len(all_shared_ids))
        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = {executor.submit(_fetch_detail, mid): mid for mid in all_shared_ids}
            for future in as_completed(futures):
                mid, data = future.result()
                if data:
                    shared_match_cache[mid] = data

    # Compute duo winrates
    duos = []
    for (p1, p2), shared in team_duos_shared.items():
        wins = 0
        games = 0
        for mid in shared:
            match_data = shared_match_cache.get(mid)
            if not match_data:
                continue
            info = match_data.get("info", {})
            p1_data = None
            p2_data = None
            for participant in info.get("participants", []):
                if participant.get("puuid") == p1:
                    p1_data = participant
                elif participant.get("puuid") == p2:
                    p2_data = participant
            if (p1_data and p2_data
                    and p1_data.get("teamId") == p2_data.get("teamId")):
                games += 1
                if p1_data.get("win"):
                    wins += 1

        duo_winrate = None
        if games > 0:
            duo_winrate = {
                "wins": wins,
                "games": games,
                "winrate": round(wins / games * 100),
            }

        # Determine which team this duo belongs to
        duo_team = None
        for team_id, team_players in teams.items():
            team_puuids = {p["puuid"] for p in team_players}
            if p1 in team_puuids and p2 in team_puuids:
                duo_team = team_id
                break

        duos.append({
            "players": [p1, p2],
            "team_id": duo_team,
            "shared_matches": len(shared),
            "duo_winrate": duo_winrate,
        })

    result = {"duos": duos, "match_id": match_id}

    # Cache the result (historical matches never change)
    db.set_duo_cache(match_id, result)

    return jsonify(result)


def _detect_duos_for_live_game(teams_map: dict, on_progress=None) -> dict:
    """Detect duos for a live game by fetching recent match IDs per player.

    Returns a dict mapping team_id -> list of duo dicts.
    """

    def _progress(msg):
        if on_progress:
            on_progress(msg)

    _progress("Detecting duo partners...")

    # Fetch recent match IDs per player (parallel)
    puuid_to_matches = {}
    all_players = [
        pl for team in teams_map.values() for pl in team
        if not pl.get("hidden") and pl.get("puuid")
    ]

    def _fetch_match_ids(player):
        try:
            ids = _api_duo.get_match_ids(
                player["puuid"], count=DUO_MATCH_HISTORY_COUNT,
            )
            return player["puuid"], set(ids) if ids else set()
        except Exception:
            return player["puuid"], set()

    if all_players:
        workers = min(MAX_WORKERS, len(all_players))
        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = {executor.submit(_fetch_match_ids, p): p for p in all_players}
            for future in as_completed(futures):
                pid, match_set = future.result()
                puuid_to_matches[pid] = match_set

    # Detect duos per team
    all_shared_ids = set()
    team_duos_shared = {}

    for team_id, players in teams_map.items():
        team_visible = [p for p in players if not p.get("hidden") and p.get("puuid")]
        for p1, p2 in combinations(team_visible, 2):
            m1 = puuid_to_matches.get(p1["puuid"], set())
            m2 = puuid_to_matches.get(p2["puuid"], set())
            shared = m1 & m2
            if len(shared) >= SHARED_MATCH_THRESHOLD:
                team_duos_shared[(p1["puuid"], p2["puuid"])] = shared
                all_shared_ids.update(shared)

    # Fetch shared match details for duo winrate
    shared_match_cache = {}
    if all_shared_ids:
        _progress(f"Analyzing {len(all_shared_ids)} shared matches for duo winrate...")

        def _fetch_detail(mid):
            try:
                return mid, _api_duo.get_match(mid)
            except Exception:
                return mid, None

        workers = min(MAX_WORKERS, len(all_shared_ids))
        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = {executor.submit(_fetch_detail, mid): mid for mid in all_shared_ids}
            for future in as_completed(futures):
                mid, data = future.result()
                if data:
                    shared_match_cache[mid] = data

    # Build duo results per team
    team_duos = defaultdict(list)
    for (p1, p2), shared in team_duos_shared.items():
        wins = 0
        games = 0
        for mid in shared:
            match_data = shared_match_cache.get(mid)
            if not match_data:
                continue
            info = match_data.get("info", {})
            p1_data = None
            p2_data = None
            for participant in info.get("participants", []):
                if participant.get("puuid") == p1:
                    p1_data = participant
                elif participant.get("puuid") == p2:
                    p2_data = participant
            if (p1_data and p2_data
                    and p1_data.get("teamId") == p2_data.get("teamId")):
                games += 1
                if p1_data.get("win"):
                    wins += 1

        duo_winrate = None
        if games > 0:
            duo_winrate = {
                "wins": wins,
                "games": games,
                "winrate": round(wins / games * 100),
            }

        # Find team for this duo
        for team_id, players in teams_map.items():
            team_puuids = {p["puuid"] for p in players}
            if p1 in team_puuids and p2 in team_puuids:
                team_duos[team_id].append({
                    "players": [p1, p2],
                    "shared_matches": len(shared),
                    "duo_winrate": duo_winrate,
                })
                break

    return dict(team_duos)


@app.route("/api/matches/<match_id>/prediction", methods=["GET"])
def match_prediction(match_id):
    """Compute a retroactive prediction for a stored match.

    Uses current rank data for all participants (not historical).
    Caches result in match_predictions table.
    """
    # Check cache first (fast path, no lock needed)
    cached = db.get_match_prediction(match_id)
    if cached:
        result = dict(cached)
        for field in ("factors",):
            val = result.get(field)
            if val and isinstance(val, str):
                try:
                    result[field] = json.loads(val)
                except (json.JSONDecodeError, TypeError):
                    pass
        return jsonify(result)

    # Acquire lock — second caller blocks and will hit cache after first finishes
    lock = task_lock("prediction", match_id)
    with lock:
        # Re-check cache after acquiring lock
        cached = db.get_match_prediction(match_id)
        if cached:
            result = dict(cached)
            for field in ("factors",):
                val = result.get(field)
                if val and isinstance(val, str):
                    try:
                        result[field] = json.loads(val)
                    except (json.JSONDecodeError, TypeError):
                        pass
            return jsonify(result)
        return _compute_match_prediction(match_id)


def _compute_match_prediction(match_id):
    """Compute a retroactive match prediction (called under lock)."""
    # Load match from DB
    match = db.get_match_detail(match_id)
    if not match:
        return jsonify({"error": "Match not found"}), 404

    participants = match.get("participants", [])
    if not participants:
        return jsonify({"error": "No participant data"}), 400

    # Determine actual winner
    actual_winner = None
    for p in participants:
        if p.get("win"):
            actual_winner = p.get("team_id")
            break

    # Build player data structures matching the live game format
    teams_map = defaultdict(list)
    for p in participants:
        team_id = p.get("team_id", 0)
        puuid = p.get("puuid", "")
        name = p.get("game_name", "") or ""
        tag = p.get("tag_line", "") or ""
        hidden = not puuid

        teams_map[team_id].append({
            "puuid": puuid,
            "champion_id": p.get("champion_id", 0),
            "champion_name": p.get("champion_name", "Unknown"),
            "team_id": team_id,
            "hidden": hidden,
            "game_name": name,
            "tag_line": tag,
            "rank": None,
            "champion_winrate": None,
            "role": POSITION_DISPLAY.get(p.get("position", ""), None),
        })

    all_visible = [
        pl for team in teams_map.values() for pl in team if not pl["hidden"]
    ]

    # Fetch current ranks (parallel)
    queue_id = match.get("queue_id", 420)
    _fetch_ranks_parallel(all_visible, queue_id)

    # Use match stats for champion winrate instead of fetching more API data
    # (cheaper: we already have the participant's W/L in our DB)
    for pl in all_visible:
        puuid = pl["puuid"]
        champ_id = pl["champion_id"]
        champ_name = pl["champion_name"]
        # Query our local DB for this player's champion stats
        stats = db.get_champion_stats_for_puuid(puuid, champ_name)
        if stats and stats["games"] >= 1:
            pl["champion_winrate"] = {
                "wins": stats["wins"],
                "games": stats["games"],
                "winrate": round(stats["wins"] / stats["games"] * 100),
            }

    # Run prediction (save=False: don't create a live-game prediction entry)
    pred_data = _predict_winner(teams_map, match_id, None, save=False)

    predicted_team = pred_data["predicted_team"]
    outcome = "correct" if predicted_team == actual_winner else "incorrect"

    # Cache it
    db.save_match_prediction(
        match_id=match_id,
        predicted_team=predicted_team,
        confidence=pred_data["confidence"],
        factors=json.dumps(pred_data.get("factors", {})),
        blue_score=pred_data.get("blue_score", 50),
        red_score=pred_data.get("red_score", 50),
        actual_winner=actual_winner or 0,
        outcome=outcome,
    )

    return jsonify({
        "match_id": match_id,
        "predicted_team": predicted_team,
        "confidence": pred_data["confidence"],
        "factors": pred_data.get("factors", {}),
        "blue_score": pred_data.get("blue_score", 50),
        "red_score": pred_data.get("red_score", 50),
        "actual_winner": actual_winner,
        "outcome": outcome,
    })


# ---- Season definitions & match backfill -----------------------------------

@app.route("/api/seasons", methods=["GET"])
def get_seasons():
    """Return available season definitions.

    Each season has a ``filter`` flag: True means it appears in the season
    dropdown for match filtering, False means it only appears in account
    card season-history rows (older seasons with no match data).
    """
    result = []
    for key, s in SEASONS.items():
        result.append({"key": key, "label": s["label"], "filter": s.get("filter", True)})
    return jsonify(result)


@app.route("/api/accounts/<int:account_id>/rank-history", methods=["GET"])
def get_account_rank_history(account_id):
    """Return rank history snapshots for sparkline graphs.

    Query params:
      queue  - queue type (default RANKED_SOLO_5x5)
      season - season key to filter by time range (optional)
    """
    acct = db.get_account(account_id)
    if not acct:
        return jsonify({"error": "Account not found"}), 404

    queue = request.args.get("queue", "RANKED_SOLO_5x5")
    season_key = request.args.get("season")

    start_time = None
    end_time = None
    if season_key and season_key in SEASONS:
        start_time = SEASONS[season_key]["start"]
        end_time = SEASONS[season_key]["end"]

    history = db.get_rank_history(acct["id"], queue, start_time, end_time)
    return jsonify({"history": history})


# ---- Phase 23: Analytics Endpoints ----------------------------------------

@app.route("/api/profiles/<int:profile_id>/play-times", methods=["GET"])
def profile_play_times(profile_id):
    """Game time heatmap data: games per day + win rate by hour/day-of-week."""
    profile = db.get_profile(profile_id)
    if not profile:
        return jsonify({"error": "Profile not found"}), 404

    puuids = [a["puuid"] for a in profile.get("accounts", [])]
    if not puuids:
        return jsonify({"days": {}, "hours": {}})

    with db.get_db() as conn:
        placeholders = ",".join("?" * len(puuids))
        # Per-day data (last 90 days)
        rows = conn.execute(f"""
            SELECT date(m.game_start/1000, 'unixepoch', 'localtime') as day,
                   COUNT(*) as games,
                   SUM(CASE WHEN p.win THEN 1 ELSE 0 END) as wins
            FROM participants p
            JOIN matches m ON p.match_id = m.match_id
            WHERE p.puuid IN ({placeholders})
              AND m.game_start/1000 > CAST(strftime('%s','now') AS INTEGER) - 90*86400
              AND m.queue_id IN (420, 440)
            GROUP BY day
            ORDER BY day
        """, puuids).fetchall()

        days = {}
        for r in rows:
            days[r[0]] = {"games": r[1], "wins": r[2]}

        # Per hour-of-day stats
        hour_rows = conn.execute(f"""
            SELECT CAST(strftime('%H', m.game_start/1000, 'unixepoch', 'localtime') AS INTEGER) as hour,
                   CAST(strftime('%w', m.game_start/1000, 'unixepoch', 'localtime') AS INTEGER) as dow,
                   COUNT(*) as games,
                   SUM(CASE WHEN p.win THEN 1 ELSE 0 END) as wins
            FROM participants p
            JOIN matches m ON p.match_id = m.match_id
            WHERE p.puuid IN ({placeholders})
              AND m.queue_id IN (420, 440)
            GROUP BY hour, dow
        """, puuids).fetchall()

        hours = {}
        for r in hour_rows:
            key = f"{r[0]}_{r[1]}"  # "14_3" = 2pm Wednesday
            hours[key] = {"games": r[2], "wins": r[3]}

        return jsonify({"days": days, "hours": hours})


@app.route("/api/profiles/<int:profile_id>/session-stats", methods=["GET"])
def profile_session_stats(profile_id):
    """Today's session stats + streaks for each account in a profile."""
    profile = db.get_profile(profile_id)
    if not profile:
        return jsonify({"error": "Profile not found"}), 404

    accounts = profile.get("accounts", [])
    result = []
    with db.get_db() as conn:
        for acct in accounts:
            puuid = acct["puuid"]
            # Today's games
            today_rows = conn.execute("""
                SELECT p.win, p.kills, p.deaths, p.assists, p.champion_name
                FROM participants p
                JOIN matches m ON p.match_id = m.match_id
                WHERE p.puuid = ?
                  AND date(m.game_start/1000, 'unixepoch', 'localtime') = date('now', 'localtime')
                  AND m.queue_id IN (420, 440)
                  AND COALESCE(m.is_remake, 0) = 0
                ORDER BY m.game_start ASC
            """, (puuid,)).fetchall()

            today_wins = sum(1 for r in today_rows if r[0])
            today_losses = len(today_rows) - today_wins

            # Current streak (look at last 20 games in order)
            streak_rows = conn.execute("""
                SELECT p.win
                FROM participants p
                JOIN matches m ON p.match_id = m.match_id
                WHERE p.puuid = ?
                  AND m.queue_id IN (420, 440)
                  AND COALESCE(m.is_remake, 0) = 0
                ORDER BY m.game_start DESC
                LIMIT 20
            """, (puuid,)).fetchall()

            streak = 0
            streak_type = None
            for r in streak_rows:
                if streak_type is None:
                    streak_type = "W" if r[0] else "L"
                    streak = 1
                elif (r[0] and streak_type == "W") or (not r[0] and streak_type == "L"):
                    streak += 1
                else:
                    break

            # LP change today: compare earliest and latest rank_history entries today
            lp_rows = conn.execute("""
                SELECT rh.tier, rh.rank, rh.lp
                FROM rank_history rh
                WHERE rh.account_id = ?
                  AND rh.queue_type = 'RANKED_SOLO_5x5'
                  AND date(rh.recorded_at) = date('now', 'localtime')
                ORDER BY rh.recorded_at ASC
            """, (acct["id"],)).fetchall()

            lp_change = None
            if len(lp_rows) >= 2:
                first = _rank_to_score(lp_rows[0][0], lp_rows[0][1], lp_rows[0][2])
                last = _rank_to_score(lp_rows[-1][0], lp_rows[-1][1], lp_rows[-1][2])
                lp_change = last - first

            result.append({
                "account_id": acct["id"],
                "game_name": acct["game_name"],
                "today_wins": today_wins,
                "today_losses": today_losses,
                "streak": streak,
                "streak_type": streak_type,
                "lp_change": lp_change,
            })

    return jsonify({"accounts": result})


def _rank_to_score(tier, rank, lp):
    """Convert rank to numeric score for LP change calculations."""
    TIER_VAL = {
        "IRON": 0, "BRONZE": 4, "SILVER": 8, "GOLD": 12,
        "PLATINUM": 16, "EMERALD": 20, "DIAMOND": 24,
        "MASTER": 28, "GRANDMASTER": 30, "CHALLENGER": 32,
    }
    DIV_VAL = {"IV": 0, "III": 1, "II": 2, "I": 3}
    t = (tier or "").upper()
    base = TIER_VAL.get(t, 0)
    div = DIV_VAL.get((rank or "").upper(), 0)
    return (base + div) * 100 + (lp or 0)


@app.route("/api/profiles/<int:profile_id>/role-stats", methods=["GET"])
def profile_role_stats(profile_id):
    """Per-role performance breakdown across all accounts in a profile."""
    profile = db.get_profile(profile_id)
    if not profile:
        return jsonify({"error": "Profile not found"}), 404

    puuids = [a["puuid"] for a in profile.get("accounts", [])]
    if not puuids:
        return jsonify({"roles": {}})

    with db.get_db() as conn:
        placeholders = ",".join("?" * len(puuids))
        rows = conn.execute(f"""
            SELECT
                CASE p.position
                    WHEN 'TOP' THEN 'Top'
                    WHEN 'JUNGLE' THEN 'Jungle'
                    WHEN 'MIDDLE' THEN 'Mid'
                    WHEN 'BOTTOM' THEN 'Bot'
                    WHEN 'UTILITY' THEN 'Support'
                    ELSE p.position
                END as role,
                COUNT(*) as games,
                SUM(CASE WHEN p.win THEN 1 ELSE 0 END) as wins,
                ROUND(AVG(p.kills), 1) as avg_kills,
                ROUND(AVG(p.deaths), 1) as avg_deaths,
                ROUND(AVG(p.assists), 1) as avg_assists,
                ROUND(AVG(p.cs * 60.0 / NULLIF(m.game_duration, 0)), 1) as cs_per_min,
                ROUND(AVG(p.vision_score), 1) as avg_vision,
                ROUND(AVG(p.damage), 0) as avg_damage,
                ROUND(AVG(p.gold), 0) as avg_gold
            FROM participants p
            JOIN matches m ON p.match_id = m.match_id
            WHERE p.puuid IN ({placeholders})
              AND m.queue_id IN (420, 440)
              AND p.position IN ('TOP', 'JUNGLE', 'MIDDLE', 'BOTTOM', 'UTILITY')
            GROUP BY role
            ORDER BY games DESC
        """, puuids).fetchall()

        roles = {}
        for r in rows:
            role_name = r[0]
            games = r[1]
            wins = r[2]
            roles[role_name] = {
                "games": games,
                "wins": wins,
                "wr": round(wins / games * 100) if games > 0 else 0,
                "avg_kills": r[3],
                "avg_deaths": r[4],
                "avg_assists": r[5],
                "cs_per_min": r[6],
                "avg_vision": r[7],
                "avg_damage": r[8],
                "avg_gold": r[9],
            }

        return jsonify({"roles": roles})


@app.route("/api/accounts/<int:account_id>/stats-summary", methods=["GET"])
def account_stats_summary(account_id):
    """Aggregate stats for a single account (for head-to-head comparison)."""
    acct = db.get_account(account_id)
    if not acct:
        return jsonify({"error": "Account not found"}), 404

    with db.get_db() as conn:
        row = conn.execute("""
            SELECT
                COUNT(*) as games,
                SUM(CASE WHEN p.win THEN 1 ELSE 0 END) as wins,
                ROUND(AVG(p.kills), 1) as avg_kills,
                ROUND(AVG(p.deaths), 1) as avg_deaths,
                ROUND(AVG(p.assists), 1) as avg_assists,
                ROUND(AVG(p.cs * 60.0 / NULLIF(m.game_duration, 0)), 1) as cs_per_min,
                ROUND(AVG(p.vision_score), 1) as avg_vision,
                ROUND(AVG(p.damage * 60.0 / NULLIF(m.game_duration, 0)), 0) as dmg_per_min,
                ROUND(AVG(p.gold * 60.0 / NULLIF(m.game_duration, 0)), 0) as gold_per_min
            FROM participants p
            JOIN matches m ON p.match_id = m.match_id
            WHERE p.puuid = ?
              AND m.queue_id IN (420, 440)
        """, (acct["puuid"],)).fetchone()

        # Top 5 most-played champions
        champ_rows = conn.execute("""
            SELECT p.champion_name,
                   COUNT(*) as games,
                   SUM(CASE WHEN p.win THEN 1 ELSE 0 END) as wins,
                   ROUND(AVG(p.kills), 1) as avg_k,
                   ROUND(AVG(p.deaths), 1) as avg_d,
                   ROUND(AVG(p.assists), 1) as avg_a
            FROM participants p
            JOIN matches m ON p.match_id = m.match_id
            WHERE p.puuid = ?
              AND m.queue_id IN (420, 440)
            GROUP BY p.champion_name
            ORDER BY games DESC
            LIMIT 5
        """, (acct["puuid"],)).fetchall()

        # Current rank
        rank = conn.execute("""
            SELECT tier, rank, lp, wins, losses
            FROM ranks
            WHERE account_id = ? AND queue_type = 'RANKED_SOLO_5x5'
        """, (account_id,)).fetchone()

        return jsonify({
            "account_id": account_id,
            "game_name": acct["game_name"],
            "tag_line": acct["tag_line"],
            "games": row[0],
            "wins": row[1],
            "wr": round(row[1] / row[0] * 100) if row[0] > 0 else 0,
            "avg_kills": row[2],
            "avg_deaths": row[3],
            "avg_assists": row[4],
            "cs_per_min": row[5],
            "avg_vision": row[6],
            "dmg_per_min": row[7],
            "gold_per_min": row[8],
            "rank": {
                "tier": rank[0] if rank else None,
                "division": rank[1] if rank else None,
                "lp": rank[2] if rank else 0,
            } if rank else None,
            "top_champions": [{
                "name": c[0], "games": c[1], "wins": c[2],
                "wr": round(c[2] / c[1] * 100) if c[1] > 0 else 0,
                "avg_kda": f"{c[3]}/{c[4]}/{c[5]}",
            } for c in champ_rows],
        })


@app.route("/api/profiles/<int:profile_id>/dashboard-layout", methods=["GET"])
def get_dashboard_layout(profile_id):
    """Get saved dashboard layout for a profile."""
    layout = db.get_dashboard_layout(profile_id)
    if layout:
        return jsonify({"layout": json.loads(layout)})
    return jsonify({"layout": None})


@app.route("/api/profiles/<int:profile_id>/dashboard-layout", methods=["PUT"])
def save_dashboard_layout(profile_id):
    """Save dashboard layout for a profile."""
    data = request.get_json(silent=True)
    if not data or "layout" not in data:
        return jsonify({"error": "layout required"}), 400
    layout_json = json.dumps(data["layout"])
    ok = db.save_dashboard_layout(profile_id, layout_json)
    if ok:
        return jsonify({"ok": True})
    return jsonify({"error": "Failed to save layout"}), 500


@app.route("/api/accounts/<int:account_id>/performance-score", methods=["GET"])
def account_performance_score(account_id):
    """Compute GPI-style performance score vs lobby averages."""
    acct = db.get_account(account_id)
    if not acct:
        return jsonify({"error": "Account not found"}), 404

    puuid = acct["puuid"]
    with db.get_db() as conn:
        # Player's averages across recent ranked games
        player = conn.execute("""
            SELECT
                AVG(p.cs * 60.0 / NULLIF(m.game_duration, 0)) as cs_min,
                AVG(p.vision_score * 60.0 / NULLIF(m.game_duration, 0)) as vis_min,
                AVG(p.deaths * 60.0 / NULLIF(m.game_duration, 0)) as death_min,
                AVG(p.damage) as dmg,
                AVG(p.gold * 60.0 / NULLIF(m.game_duration, 0)) as gold_min,
                AVG(p.kills + p.assists) as ka,
                COUNT(*) as games
            FROM participants p
            JOIN matches m ON p.match_id = m.match_id
            WHERE p.puuid = ?
              AND m.queue_id IN (420, 440)
        """, (puuid,)).fetchone()

        if not player or player[6] < 5:
            return jsonify({"error": "Need at least 5 ranked games", "games": player[6] if player else 0}), 400

        # Get the match_ids this player was in (for lobby comparison)
        match_ids = [r[0] for r in conn.execute("""
            SELECT DISTINCT m.match_id
            FROM participants p
            JOIN matches m ON p.match_id = m.match_id
            WHERE p.puuid = ?
              AND m.queue_id IN (420, 440)
        """, (puuid,)).fetchall()]

        if not match_ids:
            return jsonify({"error": "No match data"}), 400

        placeholders = ",".join("?" * len(match_ids))

        # Lobby averages (other 9 players in same matches, excluding our player)
        # Also compute stddev for scoring
        lobby = conn.execute(f"""
            SELECT
                AVG(p.cs * 60.0 / NULLIF(m.game_duration, 0)) as cs_min,
                AVG(p.vision_score * 60.0 / NULLIF(m.game_duration, 0)) as vis_min,
                AVG(p.deaths * 60.0 / NULLIF(m.game_duration, 0)) as death_min,
                AVG(p.damage) as dmg,
                AVG(p.gold * 60.0 / NULLIF(m.game_duration, 0)) as gold_min,
                AVG(p.kills + p.assists) as ka
            FROM participants p
            JOIN matches m ON p.match_id = m.match_id
            WHERE p.match_id IN ({placeholders})
              AND p.puuid != ?
        """, match_ids + [puuid]).fetchone()

        # Compute kill participation per match for player vs lobby
        # KP = (kills + assists) / team_kills
        kp_player = conn.execute(f"""
            SELECT AVG(kp) FROM (
                SELECT CAST(p.kills + p.assists AS REAL) /
                       NULLIF((SELECT SUM(p2.kills) FROM participants p2
                               WHERE p2.match_id = p.match_id AND p2.team_id = p.team_id), 0) as kp
                FROM participants p
                WHERE p.puuid = ?
                  AND p.match_id IN ({placeholders})
            )
        """, [puuid] + match_ids).fetchone()

        kp_lobby = conn.execute(f"""
            SELECT AVG(kp) FROM (
                SELECT CAST(p.kills + p.assists AS REAL) /
                       NULLIF((SELECT SUM(p2.kills) FROM participants p2
                               WHERE p2.match_id = p.match_id AND p2.team_id = p.team_id), 0) as kp
                FROM participants p
                WHERE p.puuid != ?
                  AND p.match_id IN ({placeholders})
            )
        """, [puuid] + match_ids).fetchone()

        # Damage share per match
        ds_player = conn.execute(f"""
            SELECT AVG(ds) FROM (
                SELECT CAST(p.damage AS REAL) /
                       NULLIF((SELECT SUM(p2.damage) FROM participants p2
                               WHERE p2.match_id = p.match_id AND p2.team_id = p.team_id), 0) as ds
                FROM participants p
                WHERE p.puuid = ?
                  AND p.match_id IN ({placeholders})
            )
        """, [puuid] + match_ids).fetchone()

        ds_lobby = conn.execute(f"""
            SELECT AVG(ds) FROM (
                SELECT CAST(p.damage AS REAL) /
                       NULLIF((SELECT SUM(p2.damage) FROM participants p2
                               WHERE p2.match_id = p.match_id AND p2.team_id = p.team_id), 0) as ds
                FROM participants p
                WHERE p.puuid != ?
                  AND p.match_id IN ({placeholders})
            )
        """, [puuid] + match_ids).fetchone()

        # Score each dimension: 50 = lobby avg, scale by difference
        def score_dim(player_val, lobby_val, invert=False):
            if player_val is None or lobby_val is None or lobby_val == 0:
                return 50
            diff = (player_val - lobby_val) / max(lobby_val, 0.01)
            if invert:
                diff = -diff
            # Scale: 10% better = 65, 20% better = 80, cap 0-100
            raw = 50 + diff * 150
            return max(0, min(100, round(raw)))

        dimensions = {
            "cs_min": {
                "label": "CS/min",
                "score": score_dim(player[0], lobby[0]),
                "player": round(player[0] or 0, 1),
                "lobby": round(lobby[0] or 0, 1),
            },
            "vision": {
                "label": "Vision/min",
                "score": score_dim(player[1], lobby[1]),
                "player": round(player[1] or 0, 2),
                "lobby": round(lobby[1] or 0, 2),
            },
            "kp": {
                "label": "Kill Part.",
                "score": score_dim((kp_player[0] or 0) * 100, (kp_lobby[0] or 0) * 100),
                "player": round((kp_player[0] or 0) * 100, 1),
                "lobby": round((kp_lobby[0] or 0) * 100, 1),
            },
            "deaths": {
                "label": "Survival",
                "score": score_dim(player[2], lobby[2], invert=True),
                "player": round(player[2] or 0, 2),
                "lobby": round(lobby[2] or 0, 2),
            },
            "dmg_share": {
                "label": "Dmg Share",
                "score": score_dim((ds_player[0] or 0) * 100, (ds_lobby[0] or 0) * 100),
                "player": round((ds_player[0] or 0) * 100, 1),
                "lobby": round((ds_lobby[0] or 0) * 100, 1),
            },
            "gold": {
                "label": "Gold/min",
                "score": score_dim(player[4], lobby[4]),
                "player": round(player[4] or 0, 0),
                "lobby": round(lobby[4] or 0, 0),
            },
        }

        overall = round(sum(d["score"] for d in dimensions.values()) / len(dimensions))

        return jsonify({
            "account_id": account_id,
            "games": player[6],
            "overall": overall,
            "dimensions": dimensions,
        })


@app.route("/api/matches/<match_id>/game-analysis", methods=["GET"])
def get_game_analysis(match_id):
    """Get cached game analysis."""
    puuid = request.args.get("puuid", "")
    if not puuid:
        return jsonify({"error": "puuid required"}), 400
    cached = db.get_game_analysis(match_id, puuid)
    if cached:
        return jsonify({"analysis": cached["analysis_text"], "model": cached["model"], "cached": True})
    return jsonify({"analysis": None, "cached": False})


@app.route("/api/matches/<match_id>/game-analysis", methods=["POST"])
def generate_game_analysis(match_id):
    """Generate LLM game analysis using match data + timeline."""
    data = request.get_json(silent=True) or {}
    puuid = data.get("puuid", "")
    model = data.get("model", "claude-haiku-4-5")
    force = data.get("force", False)

    if not puuid:
        return jsonify({"error": "puuid required"}), 400

    # Check cache unless force refresh
    if not force:
        cached = db.get_game_analysis(match_id, puuid)
        if cached:
            return jsonify({"analysis": cached["analysis_text"], "model": cached["model"], "cached": True})

    # Get match detail from DB
    match = db.get_match_detail(match_id)
    if not match:
        return jsonify({"error": "Match not found"}), 404

    # Find the tracked player
    player_data = None
    for p in match.get("participants", []):
        if p.get("puuid") == puuid:
            player_data = p
            break
    if not player_data:
        return jsonify({"error": "Player not found in match"}), 404

    # Fetch timeline from Riot API (1 API call)
    timeline = None
    try:
        timeline = _api.get_match_timeline(match_id)
    except Exception as exc:
        app.logger.warning("Failed to fetch timeline for %s: %s", match_id, exc)

    # Extract timeline insights
    timeline_summary = _extract_timeline_summary(timeline, match) if timeline else None

    # Build analysis prompt
    prompt = _build_game_analysis_prompt(match, player_data, timeline_summary)

    # Call LLM
    try:
        import llm_client
        client = llm_client._get_client()
        use_model = model if model in llm_client.AVAILABLE_MODELS else llm_client.DEFAULT_MODEL

        response = client.messages.create(
            model=use_model,
            max_tokens=500,
            system="You are a League of Legends game analyst. Analyze matches from a specific player's perspective. Be specific about timing, causality, and what the player could have done differently. No generic advice. CRITICAL: Always consider the game outcome and context — if the player won, don't criticize unfinished builds (the game ended). Don't suggest building counter-items against enemies who were feeding and irrelevant. Judge decisions based on what actually happened in the game, not theorycrafting. Be concise — 4-6 sentences max.",
            messages=[{"role": "user", "content": prompt}],
            timeout=60.0,
        )

        analysis_text = response.content[0].text.strip()
        db.save_game_analysis(match_id, puuid, analysis_text, use_model)

        return jsonify({"analysis": analysis_text, "model": use_model, "cached": False})

    except Exception as exc:
        app.logger.error("Game analysis failed for %s: %s", match_id, exc)
        return jsonify({"error": f"Analysis failed: {str(exc)}"}), 500


def _extract_timeline_summary(timeline, match):
    """Extract key events from match timeline for LLM context."""
    if not timeline:
        return None

    frames = timeline.get("info", {}).get("frames", [])
    if not frames:
        return None

    participants = match.get("participants", [])
    # Map participantId -> champion name
    pid_to_champ = {}
    # Timeline uses participantId 1-10
    raw_json = db.get_match_raw_json(match.get("match_id", ""))
    if raw_json:
        import json
        try:
            raw = json.loads(raw_json)
            for p in raw.get("info", {}).get("participants", []):
                pid_to_champ[p.get("participantId")] = p.get("championName", "?")
        except Exception:
            pass

    # Also try timeline participant mapping
    if not pid_to_champ:
        tl_participants = timeline.get("info", {}).get("participants", [])
        for tp in tl_participants:
            pid = tp.get("participantId")
            puuid = tp.get("puuid", "")
            for p in participants:
                if p.get("puuid") == puuid:
                    pid_to_champ[pid] = p.get("champion_name", "?")

    def champ_name(pid):
        return pid_to_champ.get(pid, f"Player{pid}")

    summary = {
        "first_blood": None,
        "early_kills": [],      # kills before 15 min
        "dragons": [],
        "barons": [],
        "towers": [],
        "gold_diff": {},        # team gold diff at key frames
        "rift_heralds": [],
    }

    for frame in frames:
        timestamp_ms = frame.get("timestamp", 0)
        time_min = timestamp_ms / 60000

        # Gold diff at 10, 15, 20 min (pick closest frame)
        for target in [10, 15, 20]:
            if abs(time_min - target) < 0.75 and target not in summary["gold_diff"]:
                pframes = frame.get("participantFrames", {})
                team_gold = {100: 0, 200: 0}
                for pid_str, pf in pframes.items():
                    pid = int(pid_str)
                    gold = pf.get("totalGold", 0)
                    team_id = 100 if pid <= 5 else 200
                    team_gold[team_id] += gold
                summary["gold_diff"][target] = team_gold[100] - team_gold[200]

        # Events
        for event in frame.get("events", []):
            etype = event.get("type", "")
            evt_time = event.get("timestamp", 0) / 60000

            if etype == "CHAMPION_KILL" and evt_time < 15:
                killer = champ_name(event.get("killerId", 0))
                victim = champ_name(event.get("victimId", 0))
                assisters = [champ_name(a) for a in event.get("assistingParticipantIds", [])]
                kill_info = {"time": round(evt_time, 1), "killer": killer, "victim": victim}
                if assisters:
                    kill_info["assists"] = assisters
                summary["early_kills"].append(kill_info)

                if not summary["first_blood"] and event.get("killerId", 0) > 0:
                    summary["first_blood"] = kill_info

            elif etype == "ELITE_MONSTER_KILL":
                monster = event.get("monsterType", "")
                sub = event.get("monsterSubType", "")
                killer_team = 100 if event.get("killerTeamId", 0) == 100 else 200
                if monster == "DRAGON":
                    summary["dragons"].append({
                        "time": round(evt_time, 1), "type": sub.replace("_DRAGON", ""),
                        "team": "Blue" if killer_team == 100 else "Red"
                    })
                elif monster == "BARON_NASHOR":
                    summary["barons"].append({
                        "time": round(evt_time, 1),
                        "team": "Blue" if killer_team == 100 else "Red"
                    })
                elif monster == "RIFTHERALD":
                    summary["rift_heralds"].append({
                        "time": round(evt_time, 1),
                        "team": "Blue" if killer_team == 100 else "Red"
                    })

            elif etype == "BUILDING_KILL":
                building = event.get("buildingType", "")
                if "TOWER" in building:
                    killer_team = event.get("teamId", 0)
                    # teamId for buildings = team that LOST the tower
                    lost_team = "Blue" if killer_team == 100 else "Red"
                    summary["towers"].append({
                        "time": round(evt_time, 1),
                        "lost_by": lost_team,
                        "lane": event.get("laneType", ""),
                    })

    return summary


def _build_game_analysis_prompt(match, player_data, timeline_summary):
    """Build the LLM prompt for game analysis."""
    import json as _json

    participants = match.get("participants", [])
    duration = match.get("game_duration", 0)
    dur_min = duration // 60

    # Determine teams
    player_team = player_data.get("team_id", 100)
    allies = [p for p in participants if p.get("team_id") == player_team]
    enemies = [p for p in participants if p.get("team_id") != player_team]

    player_won = player_data.get("win", False)
    result = "WON" if player_won else "LOST"

    # Pull extra context from raw_json (gold earned/spent, how game ended, items)
    raw_participants = {}  # puuid -> raw participant data
    game_ended_in_surrender = False
    game_ended_in_early_surrender = False
    raw_json_str = db.get_match_raw_json(match.get("match_id", ""))
    if raw_json_str:
        try:
            raw = _json.loads(raw_json_str)
            for rp in raw.get("info", {}).get("participants", []):
                raw_participants[rp.get("puuid", "")] = rp
            # How game ended — same for all participants
            sample = raw["info"]["participants"][0] if raw["info"]["participants"] else {}
            game_ended_in_surrender = sample.get("gameEndedInSurrender", False)
            game_ended_in_early_surrender = sample.get("gameEndedInEarlySurrender", False)
        except Exception:
            pass

    def get_raw(p):
        return raw_participants.get(p.get("puuid", ""), {})

    def fmt_player(p, highlight=False):
        kda = f"{p.get('kills',0)}/{p.get('deaths',0)}/{p.get('assists',0)}"
        cs = p.get("cs", 0)
        dmg = p.get("damage", 0)
        vis = p.get("vision_score", 0)
        pos = p.get("position", "?")
        rp = get_raw(p)
        gold_earned = rp.get("goldEarned", p.get("gold", 0))
        gold_spent = rp.get("goldSpent", 0)
        unspent = gold_earned - gold_spent if gold_spent else 0
        gold_str = f"{gold_earned:,}g earned"
        if unspent > 500:
            gold_str += f" ({unspent:,}g unspent)"
        mark = " <<<" if highlight else ""
        return f"  {p.get('champion_name','?')} ({pos}): {kda} KDA, {cs} CS, {dmg:,} dmg, {vis} vision, {gold_str}{mark}"

    # How game ended
    if game_ended_in_early_surrender:
        end_str = "EARLY SURRENDER (one team ff'd before 20 min)"
    elif game_ended_in_surrender:
        end_str = "SURRENDER (one team voted to ff)"
    else:
        end_str = "NEXUS DESTROYED (played to completion)"

    prompt = f"""Analyze this ranked game from {player_data.get('champion_name','?')}'s perspective.

RESULT: {result} in {dur_min}:{duration % 60:02d} — game ended by {end_str}

{player_data.get('champion_name','?')}'s TEAM ({'Blue' if player_team == 100 else 'Red'} side):
{chr(10).join(fmt_player(p, p.get('puuid') == player_data.get('puuid')) for p in allies)}

ENEMY TEAM:
{chr(10).join(fmt_player(p) for p in enemies)}
"""

    if timeline_summary:
        tl = timeline_summary

        if tl.get("gold_diff"):
            prompt += "\nGOLD DIFFERENCE (Blue - Red):\n"
            for t in sorted(tl["gold_diff"].keys()):
                diff = tl["gold_diff"][t]
                prompt += f"  {t} min: {'+' if diff > 0 else ''}{diff:,}g\n"

        if tl.get("first_blood"):
            fb = tl["first_blood"]
            prompt += f"\nFIRST BLOOD: {fb['killer']} killed {fb['victim']} at {fb['time']}min"
            if fb.get("assists"):
                prompt += f" (assists: {', '.join(fb['assists'])})"
            prompt += "\n"

        if tl.get("dragons"):
            prompt += "\nDRAGONS:\n"
            for d in tl["dragons"]:
                prompt += f"  {d['time']}min: {d['type']} ({d['team']})\n"

        if tl.get("barons"):
            prompt += "\nBARONS:\n"
            for b in tl["barons"]:
                prompt += f"  {b['time']}min ({b['team']})\n"

        if tl.get("rift_heralds"):
            prompt += "\nRIFT HERALDS:\n"
            for h in tl["rift_heralds"]:
                prompt += f"  {h['time']}min ({h['team']})\n"

        if tl.get("early_kills"):
            prompt += f"\nEARLY KILLS (pre-15min): {len(tl['early_kills'])} total\n"
            # Show first 8 early kills for context
            for k in tl["early_kills"][:8]:
                assist_str = f" (assist: {', '.join(k['assists'])})" if k.get("assists") else ""
                prompt += f"  {k['time']}min: {k['killer']} killed {k['victim']}{assist_str}\n"

        if tl.get("towers"):
            blue_lost = sum(1 for t in tl["towers"] if t["lost_by"] == "Blue")
            red_lost = sum(1 for t in tl["towers"] if t["lost_by"] == "Red")
            prompt += f"\nTOWERS: Blue lost {blue_lost}, Red lost {red_lost}\n"

    prompt += f"""
Analyze what happened and why {player_data.get('champion_name','?')} {result.lower()}. Focus on:
- Early game impact (laning, jungle pressure, first blood context)
- Objective control and timing
- What {player_data.get('champion_name','?')} specifically did well or poorly
- The key turning point of the game

Be specific — reference actual events, timings, and gold leads. 4-6 sentences.

IMPORTANT CONTEXT RULES:
- Consider HOW the game ended. If the player won and had unspent gold, do NOT criticize their build as incomplete — the game ended before they needed to spend it.
- Do NOT recommend building specific counter-items against enemies who were irrelevant (e.g. 0/5 or 1/7 opponents). Building against a fed threat is smart; building against someone who is 0/5 is a waste of gold.
- If the game ended in surrender, the losing team likely collapsed — focus on what caused the collapse, not theoretical late-game builds.
- Judge builds and decisions in the context of what ACTUALLY happened, not what theoretically could have happened."""

    return prompt


# Active backfill tasks keyed by account_id.
# Each value is a dict with progress state that the status endpoint returns.
_backfill_tasks = {}


@app.route("/api/accounts/<int:account_id>/backfill", methods=["POST"])
def backfill_account(account_id):
    """Start a background backfill for an account's match history.

    The work runs in a daemon thread and survives client disconnects.
    Poll GET /api/accounts/<id>/backfill/status for progress.
    """
    body = request.get_json(silent=True) or {}
    season_key = body.get("season", DEFAULT_SEASON)
    season = SEASONS.get(season_key)
    if not season:
        return jsonify({"error": f"Unknown season: {season_key}"}), 400

    acct = db.get_account(account_id)
    if not acct:
        return jsonify({"error": "Account not found"}), 404

    # Prevent concurrent backfills for the same account
    backfill_lock = task_lock("backfill", str(account_id))
    if not backfill_lock.acquire(blocking=False):
        existing = _backfill_tasks.get(account_id)
        return jsonify({"error": "Backfill already running", "status": existing}), 409

    puuid = acct["puuid"]
    start_time = season["start"]
    end_time = season["end"]

    # Initialise shared state dict (read by status endpoint, written by worker)
    state = {
        "state": "running",
        "status": "Starting...",
        "total": 0,
        "total_fetch": 0,
        "fetched": 0,
        "skipped": 0,
        "errors": 0,
        "current": 0,
        "season": season_key,
        "account_id": account_id,
    }
    _backfill_tasks[account_id] = state

    def worker():
        try:
            state["status"] = "Fetching match list..."
            page_size = 100

            def fetch_all_ids_for_queue(queue_id):
                ids = []
                offset = 0
                while True:
                    page = _api.get_match_ids(
                        puuid, count=page_size, queue=queue_id,
                        start_time=start_time, end_time=end_time,
                        start=offset,
                    )
                    if not page:
                        break
                    ids.extend(page)
                    if len(page) < page_size:
                        break
                    offset += page_size
                return ids

            solo_ids = fetch_all_ids_for_queue(420)
            flex_ids = fetch_all_ids_for_queue(440)
            all_match_ids = list(dict.fromkeys(solo_ids + flex_ids))
            total = len(all_match_ids)
            state["total"] = total
            state["status"] = f"Found {total} ranked matches"

            if total == 0:
                state["state"] = "done"
                state["status"] = "No ranked matches found for this season"
                return

            # Check which we already have with raw_json
            existing_matches = db.get_existing_match_ids(all_match_ids)
            need_fetch = []
            for mid in all_match_ids:
                if mid not in existing_matches:
                    need_fetch.append(mid)
                elif not existing_matches[mid]:
                    need_fetch.append(mid)

            skipped = total - len(need_fetch)
            state["skipped"] = skipped
            state["total_fetch"] = len(need_fetch)
            state["status"] = f"Fetching {len(need_fetch)} matches ({skipped} cached)"

            # Fetch match data sequentially (rate limiter handles pacing)
            for i, mid in enumerate(need_fetch):
                try:
                    data = _api.get_match(mid)
                    if data:
                        db.store_match(data)
                        state["fetched"] += 1
                    else:
                        state["errors"] += 1
                except Exception as e:
                    logger.warning("Backfill error for %s: %s", mid, e)
                    state["errors"] += 1

                state["current"] = i + 1
                state["status"] = f"Fetching {i + 1}/{len(need_fetch)}"

            # Backfill participant names
            state["status"] = "Backfilling player names..."
            with db.get_db() as conn:
                db._backfill_participant_names(conn)

            state["state"] = "done"
            state["status"] = (
                f"Done! {total} matches — "
                f"{state['fetched']} fetched, {skipped} cached"
                + (f", {state['errors']} errors" if state["errors"] else "")
            )

        except Exception as e:
            logger.exception("Backfill failed for account %d", account_id)
            state["state"] = "error"
            state["status"] = f"Failed: {e}"
        finally:
            backfill_lock.release()

    t = threading.Thread(target=worker, daemon=True)
    t.start()
    return jsonify({"started": True, "status": state})


@app.route("/api/accounts/<int:account_id>/backfill/status", methods=["GET"])
def backfill_status(account_id):
    """Poll for backfill progress. Returns current state dict."""
    state = _backfill_tasks.get(account_id)
    if not state:
        return jsonify({"state": "idle"})
    return jsonify(state)


# ---- GDPR Data Deletion (Riot Games compliance) --------------------------------

@app.route("/api/gdpr/delete", methods=["POST"])
def gdpr_delete():
    """Delete all stored data for a player by puuid.

    Required by Riot Games API Terms — when Riot forwards a data subject
    deletion request, we must remove all personal data for the player.

    Request body: {"puuid": "..."} or {"puuids": ["...", "..."]}
    """
    data = request.get_json(silent=True) or {}

    # Support both single puuid and batch
    puuids = data.get("puuids", [])
    if not puuids and "puuid" in data:
        puuids = [data["puuid"]]

    if not puuids:
        return jsonify({"error": "puuid or puuids required"}), 400

    results = {}
    for puuid in puuids:
        if not isinstance(puuid, str) or len(puuid) < 10:
            results[puuid] = {"error": "invalid puuid"}
            continue
        try:
            summary = db.gdpr_delete_player(puuid)
            results[puuid] = summary
        except Exception as e:
            logger.error("GDPR deletion failed for puuid=%s: %s", puuid, e)
            results[puuid] = {"error": str(e)}

    logger.info("GDPR deletion request processed for %d puuids", len(puuids))
    return jsonify({"results": results})


# ---- Build Guide Endpoints ----

@app.route("/api/build-guide/<champion_name>", methods=["GET"])
def build_guide(champion_name):
    """Get build guide for a champion. Optional ?role= param."""
    role = request.args.get("role")
    guide = get_build_guide(champion_name, role)
    if not guide:
        return jsonify({"error": "No build guide available", "champion_name": champion_name}), 404
    return jsonify(guide)


@app.route("/api/build-guide/<champion_name>/export", methods=["GET"])
def build_guide_export(champion_name):
    """Generate League client item set JSON for a champion.

    Resolves champion ID dynamically from Data Dragon so we never
    hardcode IDs that could be wrong or change between patches.
    """
    role = request.args.get("role")

    # Resolve champion ID from Data Dragon (name -> id)
    champion_id = None
    try:
        version = _api.get_latest_version()
        champ_map = _api.get_champion_data(version)  # {int_id: "Name"}
        # Reverse lookup: find the numeric ID for this champion name
        for cid, cname in champ_map.items():
            if cname == champion_name:
                champion_id = cid
                break
    except Exception:
        pass  # If lookup fails, export without associatedChampions

    export = generate_client_export(champion_name, role, champion_id=champion_id)
    if not export:
        return jsonify({"error": "No build guide available for export"}), 404
    return jsonify(export)


@app.route("/api/build-guides", methods=["GET"])
def build_guides_list():
    """List all available build guides."""
    from build_guides import list_available_guides
    return jsonify({"guides": list_available_guides()})


# ---- Game Notes Endpoints (Phase 17) ----

@app.route("/api/matches/<match_id>/notes", methods=["GET"])
def get_notes(match_id):
    """Get notes for a match. Requires ?puuid= param."""
    puuid = request.args.get("puuid")
    if not puuid:
        return jsonify({"error": "puuid required"}), 400
    notes = db.get_match_notes(match_id, puuid)
    return jsonify({"match_id": match_id, "notes": notes})


@app.route("/api/matches/<match_id>/notes", methods=["PUT", "POST"])
def save_notes(match_id):
    """Save notes for a match. Body: {"notes": "text", "puuid": "..."}"""
    logger.info("save_notes called: match_id=%s method=%s", match_id, request.method)
    data = request.get_json()
    if not data:
        return jsonify({"error": "JSON body required"}), 400
    puuid = data.get("puuid")
    if not puuid:
        return jsonify({"error": "puuid required"}), 400
    notes = data.get("notes", "")
    # Enforce max length
    if len(notes) > 2000:
        return jsonify({"error": "Notes too long (max 2000 characters)"}), 400
    notes = notes.strip()
    if not notes:
        db.delete_match_notes(match_id, puuid)
        return jsonify({"ok": True, "notes": None})
    db.save_match_notes(match_id, puuid, notes)
    safe_notes = html_escape(notes)
    return jsonify({"ok": True, "notes": safe_notes})


@app.route("/api/matches/<match_id>/notes", methods=["DELETE"])
def delete_notes(match_id):
    """Clear notes for a match. Requires ?puuid= param."""
    puuid = request.args.get("puuid")
    if not puuid:
        return jsonify({"error": "puuid required"}), 400
    db.delete_match_notes(match_id, puuid)
    return jsonify({"ok": True})


def _generate_live_build_analysis(game_id: str, puuid: str,
                                   live_result: dict) -> dict | None:
    """Generate pre-game LLM build recommendation for a live game.

    Uses task_lock to prevent duplicate LLM calls for the same game+player.
    Returns the parsed analysis dict, or None on failure.
    """
    lock = task_lock("live_analysis", f"{game_id}:{puuid}")
    if not lock.acquire(blocking=False):
        # Another thread is already generating — wait for it and return cache
        lock.acquire(blocking=True, timeout=35)
        lock.release()
        cached = db.get_live_analysis(game_id, puuid)
        if cached:
            try:
                return json.loads(cached["analysis_json"])
            except (json.JSONDecodeError, TypeError):
                pass
        return None

    try:
        # Re-check cache after acquiring lock
        cached = db.get_live_analysis(game_id, puuid)
        if cached:
            try:
                return json.loads(cached["analysis_json"])
            except (json.JSONDecodeError, TypeError):
                pass

        # Find the searched player and build context for the prompt
        teams = live_result.get("teams", [])
        player_data = None
        teammates = []
        enemies = []

        for team in teams:
            for p in team.get("players", []):
                if p.get("puuid") == puuid:
                    player_data = p
                    # Teammates are same-team players (excluding self)
                    teammates = [
                        t for t in team.get("players", [])
                        if t.get("puuid") != puuid
                    ]
                    break

        if not player_data:
            logger.warning("Player %s not found in live game %s", puuid, game_id)
            return None

        # Enemies are players on the other team
        player_team_id = player_data.get("team_id")
        for team in teams:
            if team.get("team_id") != player_team_id:
                enemies = team.get("players", [])
                break

        # Format rank strings for the prompt
        def rank_str(p):
            r = p.get("rank")
            if r and r.get("full"):
                return f"{r['full']} {r.get('lp', 0)} LP"
            return "Unranked"

        tm_data = [{
            "champion_name": t.get("champion_name", "Unknown"),
            "role": t.get("role", "?"),
            "rank": rank_str(t),
        } for t in teammates]

        en_data = [{
            "champion_name": e.get("champion_name", "Unknown"),
            "role": e.get("role", "?"),
            "rank": rank_str(e),
        } for e in enemies]

        # Get item data for the current patch (full descriptions for LLM)
        item_map = _api.get_item_data()

        analysis = llm_client.analyze_live_build(
            player_data.get("champion_name", "Unknown"),
            player_data.get("role", "?"),
            tm_data,
            en_data,
            item_map=item_map,
        )

        # Cache the result
        analysis_json = json.dumps(analysis)
        db.save_live_analysis(game_id, puuid, analysis_json)

        logger.info("Live build analysis saved for game %s, player %s",
                     game_id, player_data.get("champion_name"))
        return analysis

    except json.JSONDecodeError as e:
        logger.error("LLM returned invalid JSON for live game %s: %s",
                      game_id, e)
        return None
    except Exception as e:
        logger.exception("Live LLM analysis failed for game %s", game_id)
        return None
    finally:
        lock.release()


# ---- Timeline Build Order Parsing ----

def _extract_build_order(timeline_data: dict, puuid: str,
                         item_map: dict) -> list[dict]:
    """Extract the player's completed item purchase order from match timeline.

    Parses ITEM_PURCHASED events, filters to completed items (cost >= 2000g),
    and returns them in chronological order with timestamps.

    Returns list of {"item": "Item Name", "time": "12:34", "item_id": 3031}.
    """
    if not timeline_data:
        return []

    info = timeline_data.get("info", {})
    frames = info.get("frames", [])

    # Map participantId to puuid
    tl_participants = info.get("participants", [])
    participant_id = None
    for tp in tl_participants:
        if tp.get("puuid") == puuid:
            participant_id = tp.get("participantId")
            break

    if participant_id is None:
        return []

    # Collect ITEM_PURCHASED and ITEM_UNDO events for this player
    purchases = []  # (timestamp_ms, item_id)
    undone_items = []  # item_ids that were undone

    for frame in frames:
        for event in frame.get("events", []):
            if event.get("participantId") != participant_id:
                continue
            etype = event.get("type", "")
            if etype == "ITEM_PURCHASED":
                purchases.append((event.get("timestamp", 0), event.get("itemId", 0)))
            elif etype == "ITEM_UNDO":
                # Track the item that was undone (before_id is what was removed)
                before_id = event.get("beforeId", 0)
                if before_id:
                    undone_items.append(before_id)

    # Remove undone purchases (match last undo to last matching purchase)
    for undo_id in undone_items:
        for i in range(len(purchases) - 1, -1, -1):
            if purchases[i][1] == undo_id:
                purchases.pop(i)
                break

    # Filter to completed items only (cost >= 2000g or boots >= 900g)
    build_order = []
    for ts_ms, item_id in purchases:
        info_item = item_map.get(item_id)
        if not info_item:
            continue
        gold = info_item.get("gold", 0)
        name = info_item.get("name", "")
        is_boots = any(kw in name.lower() for kw in (
            "boots", "greaves", "treads", "shoes", "swiftness",
            "lucidity", "steelcaps", "swiftmarch", "crushers",
            "advance", "crimson", "spellslinger", "gunmetal"
        ))
        if gold >= 2000 or (is_boots and gold >= 900):
            minutes = ts_ms // 60000
            seconds = (ts_ms % 60000) // 1000
            build_order.append({
                "item": name,
                "time": f"{minutes}:{seconds:02d}",
                "item_id": item_id,
            })

    return build_order


# ---- LLM Build Analysis Endpoints (Phase 19) ----

@app.route("/api/matches/<match_id>/analyze", methods=["POST"])
def analyze_match_build(match_id):
    """Generate LLM build recommendation for a match.

    Body: {"puuid": "...", "force": bool, "model": "claude-haiku-4-5"|"claude-sonnet-4-5"}.
    When force=true, bypasses cache and re-runs analysis with the specified model.
    Uses lock + cache pattern to prevent duplicate LLM calls.
    """
    data = request.get_json()
    if not data:
        return jsonify({"error": "JSON body required"}), 400
    puuid = data.get("puuid")
    if not puuid:
        return jsonify({"error": "puuid required"}), 400

    force = data.get("force", False)
    model = data.get("model")  # None means use default

    # Check if LLM is configured
    if not llm_client.is_available():
        return jsonify({"error": "AI analysis not configured (no API key)"}), 503

    # Fast path: check cache (skip if force re-analyze)
    if not force:
        cached = db.get_match_analysis(match_id, puuid)
        if cached:
            try:
                result = json.loads(cached["analysis_json"])
                return jsonify({"ok": True, "analysis": result, "cached": True})
            except (json.JSONDecodeError, TypeError):
                pass

    # Acquire lock to prevent duplicate LLM calls for the same match+player
    lock = task_lock("analysis", f"{match_id}:{puuid}")
    acquired = lock.acquire(blocking=False)
    if not acquired:
        return jsonify({"ok": False, "status": "in_progress"}), 202

    try:
        # Re-check cache after acquiring lock (skip if force re-analyze)
        if not force:
            cached = db.get_match_analysis(match_id, puuid)
            if cached:
                try:
                    result = json.loads(cached["analysis_json"])
                    return jsonify({"ok": True, "analysis": result, "cached": True})
                except (json.JSONDecodeError, TypeError):
                    pass

        # Load match data
        match = db.get_match_detail(match_id)
        if not match:
            return jsonify({"error": "Match not found"}), 404

        participants = match.get("participants", [])
        player = None
        for p in participants:
            if p.get("puuid") == puuid:
                player = p
                break

        if not player:
            return jsonify({"error": "Player not found in match"}), 404

        # Split into teammates and enemies
        player_team = player.get("team_id")
        teammates = [p for p in participants
                     if p.get("team_id") == player_team and p.get("puuid") != puuid]
        enemies = [p for p in participants
                   if p.get("team_id") != player_team]

        # Get item data for name resolution
        item_map = _api.get_item_data()
        game_duration = match.get("game_duration", 0)

        # Fetch timeline for actual build order (single API call)
        build_order = []
        try:
            timeline = _api.get_match_timeline(match_id)
            if timeline:
                build_order = _extract_build_order(timeline, puuid, item_map)
                logger.info("Extracted %d completed items from timeline for %s",
                            len(build_order), match_id)
        except Exception as e:
            logger.warning("Failed to fetch timeline for %s: %s", match_id, e)

        # Call LLM with specified model
        use_model = model if model in (llm_client.AVAILABLE_MODELS or {}) else None
        analysis = llm_client.analyze_match_build(
            player, teammates, enemies, item_map, game_duration,
            build_order=build_order, model=use_model
        )

        # Include the actual build order in the response for frontend rendering
        if build_order:
            analysis["actual_build_order"] = build_order

        # Cache the result (with model info)
        actual_model = analysis.get("_model", llm_client.DEFAULT_MODEL)
        analysis_json = json.dumps(analysis)
        db.save_match_analysis(match_id, puuid, analysis_json, model=actual_model)

        return jsonify({"ok": True, "analysis": analysis, "cached": False})

    except json.JSONDecodeError as e:
        logger.error("LLM returned invalid JSON for %s: %s", match_id, e)
        return jsonify({"error": "AI returned invalid response, try again"}), 500
    except Exception as e:
        logger.exception("LLM analysis failed for %s", match_id)
        return jsonify({"error": f"Analysis failed: {str(e)}"}), 500
    finally:
        lock.release()


@app.route("/api/matches/<match_id>/analyze", methods=["GET"])
def get_analysis(match_id):
    """Check if cached analysis exists for a match+player."""
    puuid = request.args.get("puuid")
    if not puuid:
        return jsonify({"error": "puuid required"}), 400
    cached = db.get_match_analysis(match_id, puuid)
    if cached:
        try:
            result = json.loads(cached["analysis_json"])
            return jsonify({"ok": True, "analysis": result, "cached": True})
        except (json.JSONDecodeError, TypeError):
            pass
    return jsonify({"ok": False, "analysis": None})


@app.route("/api/live-analysis/<game_id>", methods=["GET"])
def get_live_analysis(game_id):
    """Get cached pre-game LLM build analysis for a live game.

    Used for cross-referencing: when viewing post-game match detail,
    fetch the pre-game recommendation via game_id (match_id = "NA1_" + game_id).
    """
    puuid = request.args.get("puuid")
    if not puuid:
        return jsonify({"error": "puuid required"}), 400
    cached = db.get_live_analysis(game_id, puuid)
    if cached:
        try:
            result = json.loads(cached["analysis_json"])
            return jsonify({"ok": True, "analysis": result, "cached": True})
        except (json.JSONDecodeError, TypeError):
            pass
    return jsonify({"ok": False, "analysis": None})


@app.route("/api/analysis/status", methods=["GET"])
def analysis_status():
    """Check if LLM analysis is available (API key configured).

    Returns available models for model selector UI.
    """
    models = [
        {"id": mid, "label": label}
        for mid, label in llm_client.AVAILABLE_MODELS.items()
    ]
    return jsonify({
        "available": llm_client.is_available(),
        "models": models,
        "default_model": llm_client.DEFAULT_MODEL,
    })


# ---- Background Scheduler --------------------------------------------------
# Runs in a single daemon thread. Performs automatic updates so data is fresh
# without requiring the user to load pages.
#
# Schedule: every hour on the hour + guaranteed 8am EST run.
# Jobs run sequentially to avoid rate limit storms.
# Respects existing task_lock mechanics to avoid conflicts with user actions.

_scheduler_status = {
    "running": False,
    "last_run": None,
    "last_run_end": None,
    "current_step": None,
    "last_error": None,
    "accounts_refreshed": 0,
    "matches_fetched": 0,
    "predictions_resolved": 0,
}
_scheduler_lock = threading.Lock()

# Track last user-triggered API activity so scheduler can yield to the user
_last_user_api_activity = 0.0  # time.time() value


def _touch_user_activity():
    """Mark that a user-triggered action just used the Riot API."""
    global _last_user_api_activity
    _last_user_api_activity = time.time()


def _user_recently_active(window: float = 120.0) -> bool:
    """True if a user-triggered API action happened within `window` seconds."""
    return (time.time() - _last_user_api_activity) < window


def _scheduler_fetch_matches(puuid: str, count: int = 20) -> int:
    """Sequential match fetcher for scheduler — no parallel workers.

    Same logic as _fetch_and_store_matches but fetches match details
    one at a time to avoid rate limit storms during background updates.
    """
    solo_ids = _api.get_match_ids(puuid, count=count, queue=420)
    flex_ids = _api.get_match_ids(puuid, count=count, queue=440)
    all_ids = list(dict.fromkeys(solo_ids + flex_ids))[:count]

    if not all_ids:
        return 0

    with db.get_db() as conn:
        placeholders = ",".join("?" for _ in all_ids)
        existing = conn.execute(
            f"SELECT match_id FROM matches WHERE match_id IN ({placeholders})",
            all_ids
        ).fetchall()
        existing_ids = {r["match_id"] for r in existing}

    new_ids = [mid for mid in all_ids if mid not in existing_ids]
    if not new_ids:
        return 0

    logger.info("Scheduler: fetching %d new match details for %s", len(new_ids), puuid[:8])

    stored = 0
    for mid in new_ids:
        try:
            data = _api.get_match(mid)
            if data:
                db.store_match(data)
                stored += 1
        except Exception:
            logger.exception("Scheduler: failed to fetch match %s", mid)
        time.sleep(0.3)  # Pace individual match fetches

    return stored


def _scheduler_update_status(**kwargs):
    """Thread-safe update of scheduler status."""
    with _scheduler_lock:
        _scheduler_status.update(kwargs)


def _run_scheduler_cycle(include_scrape: bool = False):
    """Run one full scheduler cycle: ranks, matches, predictions, optionally scrape."""
    _scheduler_update_status(
        running=True,
        last_run=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        current_step="starting",
        last_error=None,
        accounts_refreshed=0,
        matches_fetched=0,
        predictions_resolved=0,
    )

    try:
        accounts = db.get_all_accounts_unique()
        logger.info("Scheduler: starting cycle for %d accounts (scrape=%s)",
                     len(accounts), include_scrape)

        # Step 1: Refresh ranks for all accounts
        _scheduler_update_status(current_step="refreshing ranks")
        refreshed = 0
        for acct in accounts:
            lock = task_lock("refresh_account", str(acct["id"]))
            if not lock.acquire(blocking=False):
                logger.debug("Scheduler: skipping rank refresh for %s (locked)",
                             acct["game_name"])
                continue
            try:
                _refresh_account_ranks(acct["id"], acct["puuid"])
                refreshed += 1
                _scheduler_update_status(accounts_refreshed=refreshed)
            except Exception:
                logger.exception("Scheduler: failed to refresh ranks for %s",
                                 acct["game_name"])
            finally:
                lock.release()
            time.sleep(2)  # Delay between accounts to stay within rate limits

        logger.info("Scheduler: refreshed ranks for %d/%d accounts",
                     refreshed, len(accounts))

        # Step 2: Fetch new matches for all accounts (sequential to avoid rate storms)
        _scheduler_update_status(current_step="fetching matches")
        total_new = 0
        for acct in accounts:
            puuid = acct.get("puuid", "")
            if not puuid:
                continue
            lock = task_lock("fetch_matches", puuid)
            if not lock.acquire(blocking=False):
                logger.debug("Scheduler: skipping match fetch for %s (locked)",
                             acct["game_name"])
                continue
            try:
                new_count = _scheduler_fetch_matches(puuid)
                total_new += new_count
                _scheduler_update_status(matches_fetched=total_new)
            except Exception:
                logger.exception("Scheduler: failed to fetch matches for %s",
                                 acct["game_name"])
            finally:
                lock.release()
            time.sleep(1)

        logger.info("Scheduler: fetched %d new matches", total_new)

        # Step 3: Auto-resolve pending predictions
        _scheduler_update_status(current_step="resolving predictions")
        resolved = 0
        with db.get_db() as conn:
            pending = conn.execute(
                "SELECT * FROM predictions WHERE outcome = 'pending'"
            ).fetchall()

        for row in pending:
            pred = dict(row)
            try:
                blue_players = json.loads(pred.get("blue_players", "[]"))
            except (json.JSONDecodeError, TypeError):
                continue
            if not blue_players:
                continue

            first_name = blue_players[0].get("name", "")
            if "#" not in first_name:
                continue

            parts = first_name.split("#", 1)
            try:
                account = _api.get_account_by_riot_id(parts[0], parts[1])
                if not account:
                    continue

                match_ids = _api.get_match_ids(account["puuid"], count=5)
                found = False
                for mid in match_ids:
                    match_data = _api.get_match(mid)
                    if not match_data:
                        continue
                    info = match_data.get("info", {})
                    db.store_match(match_data)

                    for p in info.get("participants", []):
                        if p.get("puuid") == account["puuid"]:
                            winning_team = 100 if any(
                                pp.get("win") for pp in info.get("participants", [])
                                if pp.get("teamId") == 100
                            ) else 200
                            outcome = ("correct" if winning_team == pred["predicted_team"]
                                       else "incorrect")
                            db.resolve_prediction(pred["id"], outcome, mid)
                            resolved += 1
                            _scheduler_update_status(predictions_resolved=resolved)
                            found = True
                            break
                    if found:
                        break
            except Exception:
                logger.exception("Scheduler: failed to resolve prediction %d",
                                 pred["id"])
            time.sleep(0.5)

        logger.info("Scheduler: resolved %d/%d pending predictions",
                     resolved, len(pending))

        # Step 4: Scrape season ranks from op.gg (only on daily 8am run)
        if include_scrape:
            _scheduler_update_status(current_step="scraping season ranks")
            for acct in accounts:
                name = acct.get("game_name", "")
                tag = acct.get("tag_line", "")
                if name and tag:
                    try:
                        _scrape_and_store_season_ranks(acct["id"], name, tag)
                    except Exception:
                        logger.exception("Scheduler: failed to scrape for %s#%s",
                                         name, tag)
                    time.sleep(2)  # op.gg is external, be gentle

            logger.info("Scheduler: season rank scrape complete")

        _scheduler_update_status(
            running=False,
            current_step=None,
            last_run_end=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        )
        logger.info("Scheduler: cycle complete")

    except Exception:
        logger.exception("Scheduler: cycle failed")
        _scheduler_update_status(
            running=False,
            current_step=None,
            last_error=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        )


def _scheduler_loop():
    """Main scheduler loop. Runs hourly + guaranteed 8am EST."""
    import zoneinfo
    est = zoneinfo.ZoneInfo("America/New_York")

    # Wait 30s after startup to let the app fully initialize
    time.sleep(30)
    logger.info("Scheduler: started (pid=%d)", os.getpid())

    last_hour_run = -1
    last_8am_date = None

    while True:
        try:
            now_est = datetime.datetime.now(est)
            current_hour = now_est.hour
            current_date = now_est.date()

            # Skip if user is actively using the site (within last 2 min)
            if _user_recently_active():
                # Don't count this as "ran" — retry next loop iteration
                time.sleep(60)
                continue

            # 8am daily run (with scrape)
            if current_hour == 8 and last_8am_date != current_date:
                logger.info("Scheduler: 8am daily run")
                last_8am_date = current_date
                last_hour_run = current_hour
                _run_scheduler_cycle(include_scrape=True)

            # Hourly run (without scrape) — skip if we already ran this hour
            elif current_hour != last_hour_run:
                logger.info("Scheduler: hourly run (hour=%d)", current_hour)
                last_hour_run = current_hour
                _run_scheduler_cycle(include_scrape=False)

        except Exception:
            logger.exception("Scheduler: loop error")

        # Check every 60 seconds
        time.sleep(60)


def _start_scheduler():
    """Start the scheduler in a daemon thread.

    Only starts in one gunicorn worker to avoid duplicate runs.
    Uses a file-based lock: first worker to create the file wins.
    """
    lock_path = "/tmp/loltracker_scheduler.lock"
    try:
        # O_CREAT | O_EXCL = atomic create-if-not-exists
        fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        os.write(fd, str(os.getpid()).encode())
        os.close(fd)
    except FileExistsError:
        # Another worker already claimed the scheduler
        logger.info("Scheduler: skipping (another worker owns it)")
        return

    # Clean up lock file on exit
    import atexit
    atexit.register(lambda: os.unlink(lock_path) if os.path.exists(lock_path) else None)

    t = threading.Thread(target=_scheduler_loop, daemon=True, name="scheduler")
    t.start()
    logger.info("Scheduler: daemon thread started (pid=%d)", os.getpid())


@app.route("/api/scheduler/status", methods=["GET"])
def scheduler_status():
    """Return current scheduler status for frontend."""
    with _scheduler_lock:
        return jsonify(dict(_scheduler_status))


# Start scheduler on import (gunicorn loads app module per worker)
_start_scheduler()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
