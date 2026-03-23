"""Riot Games API client with dual-window rate limiting.

Ported from duodetector with additions for LolTracker:
- Item data from Data Dragon
- Rune/perk data from Data Dragon
"""

import os
import time
import threading
import logging
import requests

logger = logging.getLogger(__name__)

PLATFORM_HOST = "na1.api.riotgames.com"
REGIONAL_HOST = "americas.api.riotgames.com"


def _parse_rate_limits() -> list[dict]:
    """Parse rate limit windows from env vars or use dev key defaults.

    Env var format: "requests:seconds" e.g. "500:10"
    - RIOT_RATE_LIMIT_1: First window (default "20:1" for dev key)
    - RIOT_RATE_LIMIT_2: Second window (default "100:120" for dev key)

    Production key defaults: 500:10 and 30000:600
    """
    windows = []
    for i, default in enumerate(["20:1", "100:120"], start=1):
        raw = os.environ.get(f"RIOT_RATE_LIMIT_{i}", default).strip()
        try:
            parts = raw.split(":")
            max_req = int(parts[0])
            period = float(parts[1])
            windows.append({"max": max_req, "period": period, "timestamps": []})
        except (ValueError, IndexError):
            logger.warning("Invalid RIOT_RATE_LIMIT_%d='%s', using default '%s'", i, raw, default)
            parts = default.split(":")
            windows.append({"max": int(parts[0]), "period": float(parts[1]), "timestamps": []})
    return windows


class RateLimiter:
    """Token-bucket rate limiter supporting multiple time windows.

    Windows are configurable via env vars:
      RIOT_RATE_LIMIT_1 = "requests:seconds"  (default "20:1")
      RIOT_RATE_LIMIT_2 = "requests:seconds"  (default "100:120")

    Dev key:        20 req/1s,  100 req/120s
    Production key: 500 req/10s, 30000 req/600s
    """

    def __init__(self, windows: list[dict] | None = None):
        self._lock = threading.Lock()
        self._windows = windows if windows is not None else _parse_rate_limits()
        limits_str = ", ".join(f"{w['max']}/{w['period']}s" for w in self._windows)
        logger.info("Rate limiter initialized: %s", limits_str)

    def acquire(self):
        """Block until a request slot is available, then consume it."""
        while True:
            with self._lock:
                now = time.monotonic()
                can_proceed = True
                max_wait = 0.0

                for window in self._windows:
                    cutoff = now - window["period"]
                    window["timestamps"] = [
                        t for t in window["timestamps"] if t > cutoff
                    ]
                    if len(window["timestamps"]) >= window["max"]:
                        wait = window["timestamps"][0] - cutoff
                        max_wait = max(max_wait, wait)
                        can_proceed = False

                if can_proceed:
                    for window in self._windows:
                        window["timestamps"].append(now)
                    return

            time.sleep(max_wait + 0.05)


class RiotAPI:
    """Wrapper around Riot Games REST API for League of Legends."""

    def __init__(self, api_key: str):
        self._api_key = api_key
        self._rate_limiter = RateLimiter()
        self._session = requests.Session()
        self._session.headers.update({"X-Riot-Token": self._api_key})
        # Cached static data
        self._version_cache = None
        self._champion_cache = None
        self._item_cache = None

    # ---- low-level request ------------------------------------------------

    MAX_429_RETRIES = 10  # cap to prevent infinite recursion on persistent 429s

    def _get(self, url: str, timeout: int = 30, _retries: int = 0, _rate_retries: int = 0):
        """Rate-limited GET request. Returns parsed JSON or None on 404."""
        self._rate_limiter.acquire()
        logger.debug("GET %s", url)
        resp = self._session.get(url, timeout=timeout)
        if resp.status_code == 404:
            return None
        if resp.status_code == 429:
            if _rate_retries >= self.MAX_429_RETRIES:
                raise RuntimeError(
                    f"Rate limited {self.MAX_429_RETRIES} times in a row for {url}. "
                    "API key may be invalid or rate limits have changed."
                )
            retry_after = int(resp.headers.get("Retry-After", 5))
            logger.warning(
                "Rate limited (attempt %d/%d), retrying after %ds",
                _rate_retries + 1, self.MAX_429_RETRIES, retry_after,
            )
            time.sleep(retry_after)
            return self._get(url, timeout, _retries, _rate_retries + 1)
        _retry_delays = [1, 15, 30]
        if resp.status_code in (500, 502, 503, 504) and _retries < len(_retry_delays):
            wait = _retry_delays[_retries]
            logger.warning(
                "Server error %d, retry %d/%d after %ds: %s",
                resp.status_code, _retries + 1, len(_retry_delays), wait, url,
            )
            time.sleep(wait)
            return self._get(url, timeout, _retries + 1, _rate_retries)
        resp.raise_for_status()
        return resp.json()

    # ---- Account-v1 (regional) -------------------------------------------

    def get_account_by_riot_id(self, game_name: str, tag_line: str):
        """Resolve a Riot ID to an account (contains puuid)."""
        url = (
            f"https://{REGIONAL_HOST}/riot/account/v1/accounts"
            f"/by-riot-id/{game_name}/{tag_line}"
        )
        return self._get(url)

    def get_account_by_puuid(self, puuid: str):
        """Get gameName + tagLine for a puuid."""
        url = (
            f"https://{REGIONAL_HOST}/riot/account/v1/accounts"
            f"/by-puuid/{puuid}"
        )
        return self._get(url)

    # ---- Summoner-v4 (platform) ------------------------------------------

    def get_summoner_by_puuid(self, puuid: str):
        """Get summoner data (id, accountId, profileIconId, etc.)."""
        url = (
            f"https://{PLATFORM_HOST}/lol/summoner/v4/summoners"
            f"/by-puuid/{puuid}"
        )
        return self._get(url)

    # ---- Spectator-v5 (platform) -----------------------------------------

    def get_active_game(self, puuid: str):
        """Get the active game for a summoner. Returns None if not in game."""
        url = (
            f"https://{PLATFORM_HOST}/lol/spectator/v5/active-games"
            f"/by-summoner/{puuid}"
        )
        return self._get(url)

    # ---- Match-v5 (regional) ---------------------------------------------

    def get_match_ids(self, puuid: str, count: int = 20,
                      champion_id: int | None = None,
                      queue: int | None = None,
                      start_time: int | None = None,
                      end_time: int | None = None,
                      start: int = 0):
        """Get recent match IDs for a player."""
        url = (
            f"https://{REGIONAL_HOST}/lol/match/v5/matches"
            f"/by-puuid/{puuid}/ids?count={count}"
        )
        if start > 0:
            url += f"&start={start}"
        if champion_id is not None:
            url += f"&champion={champion_id}"
        if queue is not None:
            url += f"&queue={queue}"
        if start_time is not None:
            url += f"&startTime={start_time}"
        if end_time is not None:
            url += f"&endTime={end_time}"
        return self._get(url) or []

    def get_match(self, match_id: str):
        """Get full match details."""
        url = f"https://{REGIONAL_HOST}/lol/match/v5/matches/{match_id}"
        return self._get(url)

    def get_match_timeline(self, match_id: str):
        """Get match timeline (item events, kills, etc.). Single API call."""
        url = f"https://{REGIONAL_HOST}/lol/match/v5/matches/{match_id}/timeline"
        return self._get(url)

    # ---- League-v4 (platform) --------------------------------------------

    def get_league_entries_by_puuid(self, puuid: str):
        """Get ranked league entries by puuid (preferred, newer endpoint)."""
        url = (
            f"https://{PLATFORM_HOST}/lol/league/v4/entries"
            f"/by-puuid/{puuid}"
        )
        return self._get(url) or []

    def get_league_entries(self, summoner_id: str):
        """Get ranked league entries by summoner ID (legacy)."""
        url = (
            f"https://{PLATFORM_HOST}/lol/league/v4/entries"
            f"/by-summoner/{summoner_id}"
        )
        return self._get(url) or []

    def get_league_entries_by_tier(self, queue: str, tier: str, division: str, page: int = 1):
        """Get league entries for a specific tier/division via league-exp-v4.

        Returns list of entries with summonerId, wins, losses, etc.
        """
        url = (
            f"https://{PLATFORM_HOST}/lol/league-exp/v4/entries"
            f"/{queue}/{tier}/{division}?page={page}"
        )
        return self._get(url) or []

    def get_summoner_by_id(self, summoner_id: str):
        """Get summoner info including puuid by summoner ID."""
        url = f"https://{PLATFORM_HOST}/lol/summoner/v4/summoners/{summoner_id}"
        return self._get(url)

    # ---- Data Dragon (static, not rate-limited) --------------------------

    def get_latest_version(self):
        """Get the latest Data Dragon version string (cached)."""
        if self._version_cache:
            return self._version_cache
        resp = requests.get(
            "https://ddragon.leagueoflegends.com/api/versions.json",
            timeout=10,
        )
        resp.raise_for_status()
        self._version_cache = resp.json()[0]
        return self._version_cache

    def get_champion_data(self, version: str = None):
        """Get champion id -> name mapping from Data Dragon (cached)."""
        if self._champion_cache:
            return self._champion_cache
        if version is None:
            version = self.get_latest_version()
        url = (
            f"https://ddragon.leagueoflegends.com/cdn/{version}"
            f"/data/en_US/champion.json"
        )
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        data = resp.json()["data"]
        mapping = {}
        for champ_name, champ_info in data.items():
            mapping[int(champ_info["key"])] = champ_name
        self._champion_cache = mapping
        return mapping

    def get_item_data(self, version: str = None):
        """Get item id -> item info mapping from Data Dragon (cached).

        Only includes items available on Summoner's Rift (map 11) that
        are purchasable in the shop. Filters out ARAM/Arena variants,
        removed items, and champion-specific items.
        """
        if self._item_cache:
            return self._item_cache
        if version is None:
            version = self.get_latest_version()
        url = (
            f"https://ddragon.leagueoflegends.com/cdn/{version}"
            f"/data/en_US/item.json"
        )
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        raw = resp.json()["data"]
        mapping = {}
        for item_id_str, item_info in raw.items():
            item_id_int = int(item_id_str)
            # Skip Swarm/Arena mode item variants (IDs 22XXXX, 32XXXX,
            # 44XXXX, 66XXXX, etc. — standard SR items are < 10000)
            if item_id_int >= 10000:
                continue
            # Skip items not available on Summoner's Rift (map 11)
            maps = item_info.get("maps", {})
            if not maps.get("11", True):
                continue
            # Skip items explicitly removed from shop
            if item_info.get("inStore") is False:
                continue
            # Skip champion-specific items (Gangplank upgrades, etc.)
            if item_info.get("requiredChampion"):
                continue
            # Skip items that aren't purchasable
            gold_info = item_info.get("gold", {})
            if not gold_info.get("purchasable", True):
                continue
            mapping[item_id_int] = {
                "name": item_info.get("name", ""),
                "description": item_info.get("plaintext", ""),
                "full_description": item_info.get("description", ""),
                "gold": gold_info.get("total", 0),
            }
        self._item_cache = mapping
        return mapping


def load_api_key() -> str:
    """Load the Riot API key from env var RIOT_API_KEY.

    Falls back to reading an api.key file for local development only.
    In production (Docker), the env var is the only source — the api.key
    file is excluded from the Docker image via .dockerignore.
    """
    env_key = os.environ.get("RIOT_API_KEY", "").strip()
    if not env_key:
        # Local dev fallback — read api.key file if it exists
        key_path = os.path.join(os.path.dirname(__file__), "api.key")
        try:
            with open(key_path, "r") as f:
                env_key = f.read().strip()
        except FileNotFoundError:
            pass
    if not env_key:
        raise RuntimeError(
            "RIOT_API_KEY environment variable is not set and no api.key file found. "
            "Set the RIOT_API_KEY env var to your Riot Games API key."
        )
    if not env_key.startswith("RGAPI-"):
        logger.warning(
            "API key does not start with 'RGAPI-' — this may not be a valid Riot API key"
        )
    return env_key
