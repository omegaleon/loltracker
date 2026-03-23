"""SQLite database layer for LolTracker.

Handles schema creation, migrations, and all CRUD operations.
Database file is stored at /data/loltracker.db (Docker volume mount)
or ./loltracker.db in development.
"""

import os
import json
import sqlite3
import threading
import logging
from contextlib import contextmanager

logger = logging.getLogger(__name__)

DB_PATH = os.environ.get("LOLTRACKER_DB_PATH", "/data/loltracker.db")

_local = threading.local()


def _get_conn() -> sqlite3.Connection:
    """Get a thread-local SQLite connection."""
    if not hasattr(_local, "conn") or _local.conn is None:
        os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
        _local.conn = sqlite3.connect(DB_PATH, timeout=30)
        _local.conn.row_factory = sqlite3.Row
        _local.conn.execute("PRAGMA journal_mode=WAL")
        _local.conn.execute("PRAGMA busy_timeout=30000")
        _local.conn.execute("PRAGMA foreign_keys=ON")
    return _local.conn


@contextmanager
def get_db():
    """Context manager for database operations."""
    conn = _get_conn()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise


def init_db():
    """Create all tables if they don't exist.

    Uses a dedicated short-lived connection so the schema creation
    and migrations don't leave lingering locks on the thread-local
    connection (which would block writes from other workers/greenlets).
    """
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=60)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=60000")
    conn.execute("PRAGMA foreign_keys=ON")
    try:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS profiles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS accounts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                profile_id INTEGER NOT NULL,
                puuid TEXT UNIQUE NOT NULL,
                game_name TEXT NOT NULL,
                tag_line TEXT NOT NULL,
                summoner_id TEXT,
                region TEXT DEFAULT 'na1',
                last_updated TIMESTAMP,
                FOREIGN KEY (profile_id) REFERENCES profiles(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS ranks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                account_id INTEGER NOT NULL,
                queue_type TEXT NOT NULL,
                tier TEXT,
                rank TEXT,
                lp INTEGER DEFAULT 0,
                wins INTEGER DEFAULT 0,
                losses INTEGER DEFAULT 0,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (account_id) REFERENCES accounts(id) ON DELETE CASCADE,
                UNIQUE(account_id, queue_type)
            );

            CREATE TABLE IF NOT EXISTS matches (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                match_id TEXT UNIQUE NOT NULL,
                game_start INTEGER,
                game_duration INTEGER,
                game_version TEXT,
                queue_id INTEGER
            );

            CREATE TABLE IF NOT EXISTS participants (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                match_id TEXT NOT NULL,
                puuid TEXT NOT NULL,
                champion_id INTEGER,
                champion_name TEXT,
                team_id INTEGER,
                position TEXT,
                win BOOLEAN,
                kills INTEGER DEFAULT 0,
                deaths INTEGER DEFAULT 0,
                assists INTEGER DEFAULT 0,
                cs INTEGER DEFAULT 0,
                gold INTEGER DEFAULT 0,
                damage INTEGER DEFAULT 0,
                vision_score INTEGER DEFAULT 0,
                summoner1_id INTEGER,
                summoner2_id INTEGER,
                item0 INTEGER DEFAULT 0,
                item1 INTEGER DEFAULT 0,
                item2 INTEGER DEFAULT 0,
                item3 INTEGER DEFAULT 0,
                item4 INTEGER DEFAULT 0,
                item5 INTEGER DEFAULT 0,
                item6 INTEGER DEFAULT 0,
                perk_primary INTEGER DEFAULT 0,
                perk_sub INTEGER DEFAULT 0,
                FOREIGN KEY (match_id) REFERENCES matches(match_id) ON DELETE CASCADE,
                UNIQUE(match_id, puuid)
            );

            CREATE TABLE IF NOT EXISTS predictions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                game_id TEXT,
                predicted_team INTEGER,
                confidence REAL,
                factors TEXT,
                blue_score REAL,
                red_score REAL,
                outcome TEXT DEFAULT 'pending',
                blue_players TEXT,
                red_players TEXT,
                resolved_match_id TEXT,
                resolved_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS match_predictions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                match_id TEXT UNIQUE NOT NULL,
                predicted_team INTEGER,
                confidence REAL,
                factors TEXT,
                blue_score REAL,
                red_score REAL,
                actual_winner INTEGER,
                outcome TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (match_id) REFERENCES matches(match_id) ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_accounts_profile
                ON accounts(profile_id);
            CREATE INDEX IF NOT EXISTS idx_participants_puuid
                ON participants(puuid);
            CREATE INDEX IF NOT EXISTS idx_participants_match
                ON participants(match_id);
            CREATE INDEX IF NOT EXISTS idx_matches_start
                ON matches(game_start);
            CREATE INDEX IF NOT EXISTS idx_predictions_game
                ON predictions(game_id);
            CREATE INDEX IF NOT EXISTS idx_match_predictions_match
                ON match_predictions(match_id);

            CREATE TABLE IF NOT EXISTS duo_cache (
                match_id TEXT PRIMARY KEY,
                duo_json TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS season_ranks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                account_id INTEGER NOT NULL,
                season_key TEXT NOT NULL,
                tier TEXT,
                division TEXT,
                lp INTEGER DEFAULT 0,
                peak_tier TEXT,
                peak_division TEXT,
                peak_lp INTEGER DEFAULT 0,
                source TEXT DEFAULT 'opgg',
                scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (account_id) REFERENCES accounts(id) ON DELETE CASCADE,
                UNIQUE(account_id, season_key)
            );
            CREATE INDEX IF NOT EXISTS idx_season_ranks_account
                ON season_ranks(account_id);

            CREATE TABLE IF NOT EXISTS rank_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                account_id INTEGER NOT NULL,
                queue_type TEXT NOT NULL,
                tier TEXT,
                rank TEXT,
                lp INTEGER DEFAULT 0,
                wins INTEGER DEFAULT 0,
                losses INTEGER DEFAULT 0,
                recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (account_id) REFERENCES accounts(id) ON DELETE CASCADE
            );
            CREATE INDEX IF NOT EXISTS idx_rank_history_account_queue_time
                ON rank_history(account_id, queue_type, recorded_at);
            CREATE INDEX IF NOT EXISTS idx_matches_queue
                ON matches(queue_id);
            CREATE INDEX IF NOT EXISTS idx_predictions_created
                ON predictions(created_at);
            CREATE UNIQUE INDEX IF NOT EXISTS idx_predictions_game_unique
                ON predictions(game_id);

            CREATE TABLE IF NOT EXISTS match_analysis (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                match_id TEXT NOT NULL,
                puuid TEXT NOT NULL,
                analysis_json TEXT NOT NULL,
                model TEXT DEFAULT 'claude-haiku-4-5',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (match_id) REFERENCES matches(match_id) ON DELETE CASCADE,
                UNIQUE(match_id, puuid)
            );
            CREATE INDEX IF NOT EXISTS idx_match_analysis_match
                ON match_analysis(match_id);

            CREATE TABLE IF NOT EXISTS live_analysis (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                game_id TEXT NOT NULL,
                puuid TEXT NOT NULL,
                analysis_json TEXT NOT NULL,
                model TEXT DEFAULT 'claude-haiku-4-5',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(game_id, puuid)
            );
            CREATE INDEX IF NOT EXISTS idx_live_analysis_game
                ON live_analysis(game_id);

            CREATE TABLE IF NOT EXISTS game_analysis (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                match_id TEXT NOT NULL,
                puuid TEXT NOT NULL,
                analysis_text TEXT NOT NULL,
                model TEXT DEFAULT 'claude-haiku-4-5',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (match_id) REFERENCES matches(match_id) ON DELETE CASCADE,
                UNIQUE(match_id, puuid)
            );
             CREATE INDEX IF NOT EXISTS idx_game_analysis_match
                ON game_analysis(match_id);

            CREATE TABLE IF NOT EXISTS dashboard_layouts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                profile_id INTEGER NOT NULL,
                layout_json TEXT NOT NULL DEFAULT '[]',
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (profile_id) REFERENCES profiles(id) ON DELETE CASCADE,
                UNIQUE(profile_id)
            );

            CREATE TABLE IF NOT EXISTS focus_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                profile_id INTEGER NOT NULL,
                rule_text TEXT NOT NULL,
                started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                ended_at TIMESTAMP DEFAULT NULL,
                FOREIGN KEY (profile_id) REFERENCES profiles(id) ON DELETE CASCADE
            );
            CREATE INDEX IF NOT EXISTS idx_focus_sessions_profile
                ON focus_sessions(profile_id, ended_at);

            CREATE TABLE IF NOT EXISTS focus_checkins (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER NOT NULL,
                match_id TEXT NOT NULL,
                account_id INTEGER NOT NULL,
                followed BOOLEAN NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (session_id) REFERENCES focus_sessions(id) ON DELETE CASCADE,
                UNIQUE(session_id, match_id, account_id)
            );
        """)

        # Migrations: add columns that may not exist in older databases
        _migrate(conn)

        # Seed rank_history with current ranks if empty (one-time bootstrap)
        seed_rank_history_from_current(conn)

        # Final commit to release any implicit read transactions from
        # migration/seed queries before closing the connection.
        conn.commit()

        logger.info("Database initialized at %s", DB_PATH)
    finally:
        conn.close()


def _migrate(conn):
    """Add columns introduced in Phase 3. Safe to run repeatedly."""
    # Extended participant stats
    _add_col(conn, "participants", "damage_taken", "INTEGER DEFAULT 0")
    _add_col(conn, "participants", "heal_total", "INTEGER DEFAULT 0")
    _add_col(conn, "participants", "heal_allies", "INTEGER DEFAULT 0")
    _add_col(conn, "participants", "time_cc", "INTEGER DEFAULT 0")
    _add_col(conn, "participants", "pentakills", "INTEGER DEFAULT 0")
    _add_col(conn, "participants", "quadrakills", "INTEGER DEFAULT 0")
    _add_col(conn, "participants", "triplekills", "INTEGER DEFAULT 0")
    _add_col(conn, "participants", "double_kills", "INTEGER DEFAULT 0")
    _add_col(conn, "participants", "first_blood", "BOOLEAN DEFAULT 0")
    _add_col(conn, "participants", "first_blood_assist", "BOOLEAN DEFAULT 0")
    _add_col(conn, "participants", "turret_kills", "INTEGER DEFAULT 0")
    _add_col(conn, "participants", "inhibitor_kills", "INTEGER DEFAULT 0")
    _add_col(conn, "participants", "wards_placed", "INTEGER DEFAULT 0")
    _add_col(conn, "participants", "wards_killed", "INTEGER DEFAULT 0")
    _add_col(conn, "participants", "largest_killing_spree", "INTEGER DEFAULT 0")
    _add_col(conn, "participants", "largest_multi_kill", "INTEGER DEFAULT 0")
    _add_col(conn, "participants", "total_time_dead", "INTEGER DEFAULT 0")
    _add_col(conn, "participants", "champion_level", "INTEGER DEFAULT 0")
    _add_col(conn, "participants", "game_name", "TEXT DEFAULT ''")
    _add_col(conn, "participants", "tag_line", "TEXT DEFAULT ''")
    # Season 2026: role-bound item (boots slot)
    _add_col(conn, "participants", "role_bound_item", "INTEGER DEFAULT 0")
    # Raw JSON on matches
    _add_col(conn, "matches", "raw_json", "TEXT")
    # Phase 17: Game notes
    _add_col(conn, "participants", "notes", "TEXT DEFAULT NULL")
    # Phase 25: Remake detection
    _add_col(conn, "matches", "is_remake", "BOOLEAN DEFAULT 0")
    conn.commit()

    # Backfill participant game_name/tag_line from raw_json where missing
    _backfill_participant_names(conn)
    # Backfill role_bound_item from raw_json where missing
    _backfill_role_bound_items(conn)
    # Backfill is_remake from raw_json (gameEndedInEarlySurrender) + duration fallback
    _backfill_is_remake(conn)


def _backfill_participant_names(conn):
    """Populate game_name/tag_line from raw_json for participants that have empty names."""
    try:
        # Only attempt backfill if there are matches with BOTH empty names AND raw_json
        rows = conn.execute(
            """SELECT DISTINCT m.match_id, m.raw_json FROM matches m
               JOIN participants p ON p.match_id = m.match_id
               WHERE m.raw_json IS NOT NULL
               AND (p.game_name IS NULL OR p.game_name = '')"""
        ).fetchall()
        if not rows:
            return

        logger.info("Backfilling participant names from %d matches...", len(rows))

        updated = 0
        for row in rows:
            try:
                data = json.loads(row["raw_json"])
                for p in data.get("info", {}).get("participants", []):
                    name = p.get("riotIdGameName", "")
                    tag = p.get("riotIdTagline", "")
                    puuid = p.get("puuid", "")
                    if name and puuid:
                        result = conn.execute(
                            """UPDATE participants SET game_name = ?, tag_line = ?
                               WHERE match_id = ? AND puuid = ?
                               AND (game_name IS NULL OR game_name = '')""",
                            (name, tag, row["match_id"], puuid)
                        )
                        updated += result.rowcount
            except (json.JSONDecodeError, TypeError):
                continue

        if updated > 0:
            conn.commit()
            logger.info("Backfilled %d participant names", updated)
    except sqlite3.OperationalError as e:
        if "locked" in str(e):
            logger.debug("Skipping name backfill — database locked")
        else:
            raise


def _backfill_role_bound_items(conn):
    """Populate role_bound_item from raw_json for participants that have it as 0/NULL."""
    try:
        # Only scan matches that have raw_json with participants needing backfill
        # Note: many participants legitimately have 0 (no boots bought), so we check
        # raw_json to see if the match data actually has a roleBoundItem value
        rows = conn.execute(
            """SELECT DISTINCT m.match_id, m.raw_json FROM matches m
               JOIN participants p ON p.match_id = m.match_id
               WHERE m.raw_json IS NOT NULL
               AND (p.role_bound_item IS NULL OR p.role_bound_item = 0)
               AND m.raw_json LIKE '%roleBoundItem%'"""
        ).fetchall()

        if not rows:
            return

        updated = 0
        for row in rows:
            try:
                data = json.loads(row["raw_json"])
                for p in data.get("info", {}).get("participants", []):
                    rbi = p.get("roleBoundItem", 0)
                    puuid = p.get("puuid", "")
                    if rbi and puuid:
                        result = conn.execute(
                            """UPDATE participants SET role_bound_item = ?
                               WHERE match_id = ? AND puuid = ?
                               AND (role_bound_item IS NULL OR role_bound_item = 0)""",
                            (rbi, row["match_id"], puuid)
                        )
                        updated += result.rowcount
            except (json.JSONDecodeError, TypeError):
                continue

        if updated > 0:
            conn.commit()
            logger.info("Backfilled %d role_bound_item values", updated)
    except sqlite3.OperationalError as e:
        if "locked" in str(e):
            logger.debug("Skipping role_bound_item backfill — database locked")
        else:
            raise


def _backfill_is_remake(conn):
    """Detect remakes and set is_remake=1 on matches table.

    Uses gameEndedInEarlySurrender from raw_json (authoritative).
    Falls back to game_duration < 210 for matches without raw_json.
    """
    try:
        # Check if any matches need backfill (is_remake is NULL or 0 but could be a remake)
        # First pass: matches with raw_json — use the authoritative flag
        rows = conn.execute(
            """SELECT match_id, raw_json, game_duration FROM matches
               WHERE raw_json IS NOT NULL
               AND (is_remake IS NULL OR is_remake = 0)
               AND game_duration < 300"""
        ).fetchall()

        updated = 0
        for row in rows:
            try:
                data = json.loads(row["raw_json"])
                participants = data.get("info", {}).get("participants", [])
                # gameEndedInEarlySurrender is the same for all participants
                if participants and participants[0].get("gameEndedInEarlySurrender", False):
                    conn.execute(
                        "UPDATE matches SET is_remake = 1 WHERE match_id = ?",
                        (row["match_id"],)
                    )
                    updated += 1
            except (json.JSONDecodeError, TypeError):
                continue

        # Second pass: matches without raw_json — use duration fallback
        result = conn.execute(
            """UPDATE matches SET is_remake = 1
               WHERE raw_json IS NULL
               AND game_duration > 0 AND game_duration < 210
               AND (is_remake IS NULL OR is_remake = 0)"""
        )
        updated += result.rowcount

        if updated > 0:
            conn.commit()
            logger.info("Backfilled is_remake on %d matches", updated)
    except sqlite3.OperationalError as e:
        if "locked" in str(e):
            logger.debug("Skipping is_remake backfill — database locked")
        else:
            raise


def _add_col(conn, table: str, column: str, col_type: str):
    """Add a column if it doesn't already exist. Silently ignores duplicates."""
    try:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}")
    except sqlite3.OperationalError:
        pass  # column already exists


# ---- Profile CRUD --------------------------------------------------------

def create_profile(name: str) -> dict:
    with get_db() as conn:
        cur = conn.execute(
            "INSERT INTO profiles (name) VALUES (?)", (name,)
        )
        return {"id": cur.lastrowid, "name": name}


def get_profiles() -> list:
    with get_db() as conn:
        rows = conn.execute(
            """SELECT p.id, p.name, p.created_at,
                      COUNT(a.id) AS account_count
               FROM profiles p
               LEFT JOIN accounts a ON a.profile_id = p.id
               GROUP BY p.id
               ORDER BY p.name COLLATE NOCASE""",
        ).fetchall()
        profiles = [dict(r) for r in rows]

        # Tier ordering for finding the highest rank
        _TIER_VAL = {
            "IRON": 0, "BRONZE": 4, "SILVER": 8, "GOLD": 12,
            "PLATINUM": 16, "EMERALD": 20, "DIAMOND": 24,
            "MASTER": 28, "GRANDMASTER": 30, "CHALLENGER": 32,
        }
        _DIV_VAL = {"IV": 0, "III": 1, "II": 2, "I": 3}

        # Attach account names for client-side filtering (lightweight)
        for prof in profiles:
            accts = conn.execute(
                "SELECT id, game_name, tag_line FROM accounts WHERE profile_id = ?",
                (prof["id"],)
            ).fetchall()
            prof["account_names"] = [
                f"{a['game_name']}#{a['tag_line']}" for a in accts
            ]
            prof["accounts_brief"] = [
                {"id": a["id"], "game_name": a["game_name"], "tag_line": a["tag_line"]}
                for a in accts
            ]

            # Find highest solo queue rank across all accounts
            acct_ids = [a["id"] for a in accts]
            best_tier = None
            best_rank = None
            best_score = -1
            if acct_ids:
                placeholders = ",".join("?" for _ in acct_ids)
                rank_rows = conn.execute(
                    f"""SELECT tier, rank FROM ranks
                        WHERE account_id IN ({placeholders})
                          AND queue_type = 'RANKED_SOLO_5x5'
                          AND tier IS NOT NULL""",
                    acct_ids
                ).fetchall()
                for rr in rank_rows:
                    t = (rr["tier"] or "").upper()
                    d = (rr["rank"] or "").upper()
                    score = (_TIER_VAL.get(t, 0) + _DIV_VAL.get(d, 0)) * 100
                    if score > best_score:
                        best_score = score
                        best_tier = t
                        best_rank = d

            prof["highest_tier"] = best_tier
            prof["highest_rank"] = best_rank

        return profiles


def get_profile(profile_id: int) -> dict | None:
    with get_db() as conn:
        row = conn.execute(
            "SELECT id, name, created_at FROM profiles WHERE id = ?",
            (profile_id,)
        ).fetchone()
        if not row:
            return None
        profile = dict(row)
        # Attach accounts with their ranks
        accounts = conn.execute(
            "SELECT * FROM accounts WHERE profile_id = ? ORDER BY game_name",
            (profile_id,)
        ).fetchall()
        profile["accounts"] = []
        for acct in accounts:
            acct_dict = dict(acct)
            ranks = conn.execute(
                "SELECT * FROM ranks WHERE account_id = ?",
                (acct_dict["id"],)
            ).fetchall()
            acct_dict["ranks"] = [dict(r) for r in ranks]
            profile["accounts"].append(acct_dict)
        return profile


def update_profile_name(profile_id: int, name: str) -> dict | None:
    with get_db() as conn:
        cur = conn.execute(
            "UPDATE profiles SET name = ? WHERE id = ?", (name, profile_id)
        )
        if cur.rowcount == 0:
            return None
        row = conn.execute(
            "SELECT id, name, created_at FROM profiles WHERE id = ?",
            (profile_id,)
        ).fetchone()
        return dict(row) if row else None


def delete_profile(profile_id: int) -> bool:
    with get_db() as conn:
        cur = conn.execute("DELETE FROM profiles WHERE id = ?", (profile_id,))
        return cur.rowcount > 0


def get_all_accounts_unique() -> list:
    """Return all accounts across all profiles, deduplicated by puuid.

    Sorted by profile's most recent game first so live-status checks
    hit active profiles before dormant ones. Accounts within the same
    profile belong to the same person who may switch between them.
    """
    with get_db() as conn:
        rows = conn.execute(
            """SELECT a.id, a.puuid, a.game_name, a.tag_line, a.profile_id,
                      COALESCE(profile_activity.last_game, 0) as profile_last_game
               FROM accounts a
               LEFT JOIN (
                   SELECT a2.profile_id, MAX(m.game_start) as last_game
                   FROM accounts a2
                   JOIN participants p ON p.puuid = a2.puuid
                   JOIN matches m ON m.match_id = p.match_id
                   GROUP BY a2.profile_id
               ) profile_activity ON profile_activity.profile_id = a.profile_id
               GROUP BY a.puuid
               ORDER BY profile_last_game DESC"""
        ).fetchall()
        return [dict(r) for r in rows]


# ---- Account CRUD --------------------------------------------------------

def add_account(profile_id: int, puuid: str, game_name: str,
                tag_line: str, summoner_id: str = None) -> dict:
    with get_db() as conn:
        cur = conn.execute(
            """INSERT INTO accounts (profile_id, puuid, game_name, tag_line, summoner_id)
               VALUES (?, ?, ?, ?, ?)
               ON CONFLICT(puuid) DO UPDATE SET
                 game_name = excluded.game_name,
                 tag_line = excluded.tag_line,
                 summoner_id = COALESCE(excluded.summoner_id, accounts.summoner_id),
                 profile_id = excluded.profile_id""",
            (profile_id, puuid, game_name, tag_line, summoner_id)
        )
        row = conn.execute(
            "SELECT * FROM accounts WHERE puuid = ?", (puuid,)
        ).fetchone()
        return dict(row)


def update_account_name(puuid: str, game_name: str, tag_line: str):
    """Update an account's gameName/tagLine if they changed (name changes)."""
    with get_db() as conn:
        conn.execute(
            """UPDATE accounts SET game_name = ?, tag_line = ?,
               last_updated = CURRENT_TIMESTAMP
               WHERE puuid = ? AND (game_name != ? OR tag_line != ?)""",
            (game_name, tag_line, puuid, game_name, tag_line)
        )


def delete_account(account_id: int) -> bool:
    with get_db() as conn:
        cur = conn.execute("DELETE FROM accounts WHERE id = ?", (account_id,))
        return cur.rowcount > 0


def get_account(account_id: int) -> dict | None:
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM accounts WHERE id = ?", (account_id,)
        ).fetchone()
        if not row:
            return None
        acct = dict(row)
        ranks = conn.execute(
            "SELECT * FROM ranks WHERE account_id = ?", (account_id,)
        ).fetchall()
        acct["ranks"] = [dict(r) for r in ranks]
        return acct


def get_account_by_puuid(puuid: str) -> dict | None:
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM accounts WHERE puuid = ?", (puuid,)
        ).fetchone()
        return dict(row) if row else None


# ---- Rank operations ------------------------------------------------------

def upsert_rank(account_id: int, queue_type: str, tier: str,
                rank: str, lp: int, wins: int, losses: int):
    with get_db() as conn:
        conn.execute(
            """INSERT INTO ranks (account_id, queue_type, tier, rank, lp, wins, losses, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
               ON CONFLICT(account_id, queue_type) DO UPDATE SET
                 tier = excluded.tier,
                 rank = excluded.rank,
                 lp = excluded.lp,
                 wins = excluded.wins,
                 losses = excluded.losses,
                 updated_at = CURRENT_TIMESTAMP""",
            (account_id, queue_type, tier, rank, lp, wins, losses)
        )


# ---- Match operations -----------------------------------------------------

def store_match(match_data: dict) -> bool:
    """Store a match and all its participants. Returns True if newly inserted.

    Stores both structured columns (fast queries) and raw JSON (flexibility).
    """
    import json as _json

    info = match_data.get("info", {})
    match_id = match_data.get("metadata", {}).get("matchId", "")
    if not match_id:
        return False

    with get_db() as conn:
        # Check if already stored
        existing = conn.execute(
            "SELECT 1 FROM matches WHERE match_id = ?", (match_id,)
        ).fetchone()
        if existing:
            # Backfill raw_json if missing
            has_json = conn.execute(
                "SELECT raw_json FROM matches WHERE match_id = ?", (match_id,)
            ).fetchone()
            if has_json and not has_json["raw_json"]:
                conn.execute(
                    "UPDATE matches SET raw_json = ? WHERE match_id = ?",
                    (_json.dumps(match_data), match_id)
                )
            # Backfill participant names and role_bound_item if missing
            for p in info.get("participants", []):
                riot_name = p.get("riotIdGameName", "")
                riot_tag = p.get("riotIdTagline", "")
                puuid = p.get("puuid", "")
                rbi = p.get("roleBoundItem", 0)
                if riot_name and puuid:
                    conn.execute(
                        """UPDATE participants SET game_name = ?, tag_line = ?
                           WHERE match_id = ? AND puuid = ?
                           AND (game_name IS NULL OR game_name = '')""",
                        (riot_name, riot_tag, match_id, puuid)
                    )
                if rbi and puuid:
                    conn.execute(
                        """UPDATE participants SET role_bound_item = ?
                           WHERE match_id = ? AND puuid = ?
                           AND (role_bound_item IS NULL OR role_bound_item = 0)""",
                        (rbi, match_id, puuid)
                    )
            return False

        # Detect remake: check gameEndedInEarlySurrender on first participant
        participants = info.get("participants", [])
        is_remake = False
        if participants:
            is_remake = bool(participants[0].get("gameEndedInEarlySurrender", False))

        conn.execute(
            """INSERT OR IGNORE INTO matches
               (match_id, game_start, game_duration, game_version, queue_id,
                raw_json, is_remake)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                match_id,
                info.get("gameCreation", 0),
                info.get("gameDuration", 0),
                info.get("gameVersion", ""),
                info.get("queueId", 0),
                _json.dumps(match_data),
                is_remake,
            )
        )

        for p in info.get("participants", []):
            cs = (p.get("totalMinionsKilled", 0)
                  + p.get("neutralMinionsKilled", 0))
            # Extract keystone rune
            perk_primary = 0
            perk_sub = 0
            perks = p.get("perks", {})
            styles = perks.get("styles", [])
            if styles:
                primary_sel = styles[0].get("selections", [])
                if primary_sel:
                    perk_primary = primary_sel[0].get("perk", 0)
                if len(styles) > 1:
                    perk_sub = styles[1].get("style", 0)

            # Riot ID stored per-participant for historical accuracy
            riot_name = p.get("riotIdGameName", "")
            riot_tag = p.get("riotIdTagline", "")

            conn.execute(
                """INSERT OR IGNORE INTO participants
                   (match_id, puuid, champion_id, champion_name, team_id,
                    position, win, kills, deaths, assists, cs, gold, damage,
                    vision_score, summoner1_id, summoner2_id,
                    item0, item1, item2, item3, item4, item5, item6,
                    perk_primary, perk_sub,
                    damage_taken, heal_total, heal_allies, time_cc,
                    pentakills, quadrakills, triplekills, double_kills,
                    first_blood, first_blood_assist,
                    turret_kills, inhibitor_kills,
                    wards_placed, wards_killed,
                    largest_killing_spree, largest_multi_kill,
                    total_time_dead, champion_level,
                    game_name, tag_line,
                    role_bound_item)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                           ?, ?, ?, ?, ?, ?, ?, ?, ?,
                           ?, ?, ?, ?,
                           ?, ?, ?, ?,
                           ?, ?,
                           ?, ?,
                           ?, ?,
                           ?, ?,
                           ?, ?,
                           ?, ?,
                           ?)""",
                (
                    match_id,
                    p.get("puuid", ""),
                    p.get("championId", 0),
                    p.get("championName", "Unknown"),
                    p.get("teamId", 0),
                    p.get("individualPosition", p.get("teamPosition", "")),
                    p.get("win", False),
                    p.get("kills", 0),
                    p.get("deaths", 0),
                    p.get("assists", 0),
                    cs,
                    p.get("goldEarned", 0),
                    p.get("totalDamageDealtToChampions", 0),
                    p.get("visionScore", 0),
                    p.get("summoner1Id", 0),
                    p.get("summoner2Id", 0),
                    p.get("item0", 0),
                    p.get("item1", 0),
                    p.get("item2", 0),
                    p.get("item3", 0),
                    p.get("item4", 0),
                    p.get("item5", 0),
                    p.get("item6", 0),
                    perk_primary,
                    perk_sub,
                    # Extended stats
                    p.get("totalDamageTaken", 0),
                    p.get("totalHeal", 0),
                    p.get("totalHealsOnTeammates", 0),
                    p.get("timeCCingOthers", 0),
                    p.get("pentaKills", 0),
                    p.get("quadraKills", 0),
                    p.get("tripleKills", 0),
                    p.get("doubleKills", 0),
                    p.get("firstBloodKill", False),
                    p.get("firstBloodAssist", False),
                    p.get("turretKills", 0),
                    p.get("inhibitorKills", 0),
                    p.get("wardsPlaced", 0),
                    p.get("wardsKilled", 0),
                    p.get("largestKillingSpree", 0),
                    p.get("largestMultiKill", 0),
                    p.get("totalTimeSpentDead", 0),
                    p.get("champLevel", 0),
                    riot_name,
                    riot_tag,
                    p.get("roleBoundItem", 0),
                )
            )
        return True


def get_matches_for_puuid(puuid: str, limit: int = 20, offset: int = 0,
                          start_time: int | None = None,
                          end_time: int | None = None) -> list:
    """Get matches for a puuid from the local DB, with optional season filtering.

    Excludes custom queue matches (queue_id = 0) per Riot's game-specific policy:
    custom match data may not be publicly displayed without player opt-in.
    """
    with get_db() as conn:
        where = ["p.puuid = ?", "m.queue_id != 0"]
        params: list = [puuid]
        # game_start is in milliseconds
        if start_time is not None:
            where.append("m.game_start >= ?")
            params.append(start_time * 1000)
        if end_time is not None:
            where.append("m.game_start < ?")
            params.append(end_time * 1000)
        where_clause = " AND ".join(where)
        params.extend([limit, offset])
        rows = conn.execute(
            f"""SELECT m.match_id, m.game_start, m.game_duration, m.queue_id,
                      COALESCE(m.is_remake, 0) as is_remake,
                      p.champion_id, p.champion_name, p.win, p.kills, p.deaths,
                      p.assists, p.cs, p.gold, p.damage, p.vision_score,
                      p.item0, p.item1, p.item2, p.item3, p.item4, p.item5, p.item6,
                      p.perk_primary, p.perk_sub, p.position, p.summoner1_id, p.summoner2_id,
                      p.role_bound_item, p.notes
               FROM participants p
               JOIN matches m ON m.match_id = p.match_id
               WHERE {where_clause}
               ORDER BY m.game_start DESC
               LIMIT ? OFFSET ?""",
            params
        ).fetchall()
        return [dict(r) for r in rows]


def count_matches_for_puuid(puuid: str, start_time: int | None = None,
                            end_time: int | None = None) -> int:
    """Count total matches for a puuid in the DB, with optional season filtering.

    Excludes custom queue matches (queue_id = 0).
    """
    with get_db() as conn:
        where = ["p.puuid = ?", "m.queue_id != 0"]
        params: list = [puuid]
        if start_time is not None:
            where.append("m.game_start >= ?")
            params.append(start_time * 1000)
        if end_time is not None:
            where.append("m.game_start < ?")
            params.append(end_time * 1000)
        where_clause = " AND ".join(where)
        row = conn.execute(
            f"""SELECT COUNT(*) as cnt
               FROM participants p
               JOIN matches m ON m.match_id = p.match_id
               WHERE {where_clause}""",
            params
        ).fetchone()
        return row["cnt"] if row else 0


def get_opponent_champions(match_ids: list, puuid: str) -> dict:
    """Get opponent champion names for a list of matches.

    Returns {match_id: [champion_name, ...]} for enemies (different team).
    """
    if not match_ids:
        return {}
    with get_db() as conn:
        placeholders = ",".join("?" for _ in match_ids)
        rows = conn.execute(
            f"""SELECT p_enemy.match_id, p_enemy.champion_name
                FROM participants p_enemy
                JOIN participants p_self ON p_self.match_id = p_enemy.match_id
                  AND p_self.puuid = ?
                WHERE p_enemy.match_id IN ({placeholders})
                  AND p_enemy.team_id != p_self.team_id
                ORDER BY p_enemy.match_id""",
            [puuid] + match_ids
        ).fetchall()
        result: dict = {}
        for r in rows:
            mid = r["match_id"]
            if mid not in result:
                result[mid] = []
            result[mid].append(r["champion_name"])
        return result


def get_matches_for_puuids(puuids: list, limit: int = 100) -> list:
    """Get recent matches for multiple puuids (cross-account).

    Excludes custom queue matches (queue_id = 0).
    """
    if not puuids:
        return []
    placeholders = ",".join("?" for _ in puuids)
    with get_db() as conn:
        rows = conn.execute(
            f"""SELECT m.match_id, m.game_start, m.game_duration, m.queue_id,
                       p.champion_id, p.champion_name, p.win, p.kills, p.deaths,
                       p.assists, p.cs, p.gold, p.damage, p.vision_score,
                       p.item0, p.item1, p.item2, p.item3, p.item4, p.item5, p.item6,
                       p.perk_primary, p.perk_sub, p.position, p.puuid,
                       p.summoner1_id, p.summoner2_id,
                       p.role_bound_item
                FROM participants p
                JOIN matches m ON m.match_id = p.match_id
                WHERE p.puuid IN ({placeholders})
                AND m.queue_id != 0
                ORDER BY m.game_start DESC
                LIMIT ?""",
            (*puuids, limit)
        ).fetchall()
        return [dict(r) for r in rows]


def get_champion_stats(puuids: list, start_time: int | None = None,
                       end_time: int | None = None) -> list:
    """Get aggregated champion stats across multiple puuids, with optional season filtering."""
    if not puuids:
        return []
    placeholders = ",".join("?" for _ in puuids)
    where = [f"p.puuid IN ({placeholders})", "m.queue_id IN (420, 440)",
             "COALESCE(m.is_remake, 0) = 0"]
    params: list = list(puuids)
    # game_start is stored in milliseconds
    if start_time is not None:
        where.append("m.game_start >= ?")
        params.append(start_time * 1000)
    if end_time is not None:
        where.append("m.game_start < ?")
        params.append(end_time * 1000)
    where_clause = " AND ".join(where)
    with get_db() as conn:
        rows = conn.execute(
            f"""SELECT
                    p.champion_id,
                    p.champion_name,
                    COUNT(*) as games,
                    SUM(CASE WHEN p.win THEN 1 ELSE 0 END) as wins,
                    ROUND(AVG(p.kills), 1) as avg_kills,
                    ROUND(AVG(p.deaths), 1) as avg_deaths,
                    ROUND(AVG(p.assists), 1) as avg_assists,
                    ROUND(AVG(p.cs), 0) as avg_cs,
                    ROUND(AVG(p.gold), 0) as avg_gold,
                    ROUND(AVG(p.damage), 0) as avg_damage,
                    ROUND(AVG(p.vision_score), 1) as avg_vision
                FROM participants p
                JOIN matches m ON m.match_id = p.match_id
                WHERE {where_clause}
                GROUP BY p.champion_id, p.champion_name
                ORDER BY games DESC""",
            params
        ).fetchall()
        return [dict(r) for r in rows]


def get_champion_stats_for_puuid(puuid: str, champion_name: str) -> dict | None:
    """Get a single player's stats on a specific champion from local DB."""
    with get_db() as conn:
        row = conn.execute(
            """SELECT COUNT(*) as games,
                      SUM(CASE WHEN p.win THEN 1 ELSE 0 END) as wins
               FROM participants p
               JOIN matches m ON m.match_id = p.match_id
               WHERE p.puuid = ? AND LOWER(p.champion_name) = LOWER(?)
                 AND m.queue_id IN (420, 440)
                 AND COALESCE(m.is_remake, 0) = 0""",
            (puuid, champion_name)
        ).fetchone()
        if not row or row["games"] == 0:
            return None
        return {"games": row["games"], "wins": row["wins"]}


def get_champion_builds(puuids: list, champion_name: str,
                        start_time: int | None = None,
                        end_time: int | None = None) -> list:
    """Get build details for a specific champion across accounts, with optional season filtering."""
    if not puuids:
        return []
    placeholders = ",".join("?" for _ in puuids)
    where = [f"p.puuid IN ({placeholders})", "LOWER(p.champion_name) = LOWER(?)",
             "m.queue_id IN (420, 440)", "COALESCE(m.is_remake, 0) = 0"]
    params: list = list(puuids) + [champion_name]
    # game_start is stored in milliseconds
    if start_time is not None:
        where.append("m.game_start >= ?")
        params.append(start_time * 1000)
    if end_time is not None:
        where.append("m.game_start < ?")
        params.append(end_time * 1000)
    where_clause = " AND ".join(where)
    with get_db() as conn:
        rows = conn.execute(
            f"""SELECT p.*, m.game_start, m.game_duration, m.queue_id
                FROM participants p
                JOIN matches m ON m.match_id = p.match_id
                WHERE {where_clause}
                ORDER BY m.game_start DESC""",
            params
        ).fetchall()
        return [dict(r) for r in rows]


# ---- Prediction operations ------------------------------------------------

def create_prediction(game_id: str, predicted_team: int, confidence: float,
                      factors: str, blue_score: float, red_score: float,
                      blue_players: str, red_players: str) -> dict:
    """Create a prediction, or return the existing one if a prediction for
    this game_id already exists (idempotent)."""
    with get_db() as conn:
        cur = conn.execute(
            """INSERT OR IGNORE INTO predictions
               (game_id, predicted_team, confidence, factors,
                blue_score, red_score, blue_players, red_players)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (game_id, predicted_team, confidence, factors,
             blue_score, red_score, blue_players, red_players)
        )
        if cur.lastrowid and cur.rowcount > 0:
            # New row inserted
            return {"id": cur.lastrowid, "game_id": game_id,
                    "predicted_team": predicted_team, "confidence": confidence,
                    "already_existed": False}
        # Insert was ignored — prediction already exists, return existing
        existing = conn.execute(
            "SELECT * FROM predictions WHERE game_id = ?", (game_id,)
        ).fetchone()
        return {**dict(existing), "already_existed": True} if existing else {
            "game_id": game_id, "predicted_team": predicted_team,
            "confidence": confidence, "already_existed": False
        }


def get_prediction_by_game(game_id: str) -> dict | None:
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM predictions WHERE game_id = ? ORDER BY created_at DESC LIMIT 1",
            (game_id,)
        ).fetchone()
        return dict(row) if row else None


def get_predictions(limit: int = 50) -> list:
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM predictions ORDER BY created_at DESC LIMIT ?",
            (limit,)
        ).fetchall()
        return [dict(r) for r in rows]


def get_all_predictions(limit: int = 20, offset: int = 0) -> dict:
    """Get merged predictions from both live and retroactive tables.

    Returns a unified list sorted by date, plus total counts for pagination.
    Each entry has a 'source' field: 'live' or 'match'.
    """
    with get_db() as conn:
        # Count totals for pagination
        live_count = conn.execute(
            "SELECT COUNT(*) FROM predictions"
        ).fetchone()[0]
        match_count = conn.execute(
            "SELECT COUNT(*) FROM match_predictions"
        ).fetchone()[0]
        total = live_count + match_count

        # Union query: normalize both tables to a common shape
        rows = conn.execute(
            """SELECT * FROM (
                SELECT
                    id, 'live' as source,
                    game_id, NULL as match_id,
                    predicted_team, confidence, factors,
                    blue_score, red_score,
                    outcome, blue_players, red_players,
                    resolved_match_id, resolved_at, created_at
                FROM predictions
                UNION ALL
                SELECT
                    id, 'match' as source,
                    NULL as game_id, match_id,
                    predicted_team, confidence, factors,
                    blue_score, red_score,
                    outcome, NULL as blue_players, NULL as red_players,
                    match_id as resolved_match_id, created_at as resolved_at, created_at
                FROM match_predictions
            ) ORDER BY created_at DESC
            LIMIT ? OFFSET ?""",
            (limit, offset)
        ).fetchall()

        # Stats across ALL predictions (not just this page)
        stats = conn.execute(
            """SELECT
                SUM(CASE WHEN outcome = 'correct' THEN 1 ELSE 0 END) as correct,
                SUM(CASE WHEN outcome = 'incorrect' THEN 1 ELSE 0 END) as incorrect,
                SUM(CASE WHEN outcome = 'pending' THEN 1 ELSE 0 END) as pending
            FROM (
                SELECT outcome FROM predictions
                UNION ALL
                SELECT outcome FROM match_predictions
            )"""
        ).fetchone()

        return {
            "predictions": [dict(r) for r in rows],
            "total": total,
            "correct": stats[0] or 0,
            "incorrect": stats[1] or 0,
            "pending": stats[2] or 0,
        }


def resolve_prediction(prediction_id: int, outcome: str,
                       resolved_match_id: str = None):
    with get_db() as conn:
        conn.execute(
            """UPDATE predictions
               SET outcome = ?, resolved_match_id = ?, resolved_at = CURRENT_TIMESTAMP
               WHERE id = ?""",
            (outcome, resolved_match_id, prediction_id)
        )


# ---- Full match detail (all 10 players) -----------------------------------

def get_match_detail(match_id: str) -> dict | None:
    """Get full match data: match info + all 10 participants with extended stats."""
    with get_db() as conn:
        match_row = conn.execute(
            "SELECT * FROM matches WHERE match_id = ?", (match_id,)
        ).fetchone()
        if not match_row:
            return None
        match = dict(match_row)

        participants = conn.execute(
            """SELECT * FROM participants WHERE match_id = ?
               ORDER BY team_id, position""",
            (match_id,)
        ).fetchall()
        match["participants"] = [dict(p) for p in participants]
        return match


def get_season_stats_for_puuid(puuid: str, start_time: int | None = None,
                               end_time: int | None = None) -> dict:
    """Get W/L stats for a puuid within a season time range.

    Returns {games, wins, losses, winrate} computed from stored matches.
    """
    with get_db() as conn:
        where = ["p.puuid = ?", "COALESCE(m.is_remake, 0) = 0"]
        params: list = [puuid]
        if start_time is not None:
            where.append("m.game_start >= ?")
            params.append(start_time * 1000)
        if end_time is not None:
            where.append("m.game_start < ?")
            params.append(end_time * 1000)
        where_clause = " AND ".join(where)
        row = conn.execute(
            f"""SELECT COUNT(*) as games,
                       SUM(CASE WHEN p.win THEN 1 ELSE 0 END) as wins
                FROM participants p
                JOIN matches m ON m.match_id = p.match_id
                WHERE {where_clause}""",
            params
        ).fetchone()
        games = row["games"] or 0
        wins = row["wins"] or 0
        losses = games - wins
        winrate = round(wins / games * 100) if games > 0 else 0
        return {"games": games, "wins": wins, "losses": losses, "winrate": winrate}


def get_batch_season_stats(puuids: list[str],
                           seasons: dict[str, tuple[int | None, int | None]],
                           ) -> dict[str, dict[str, dict]]:
    """Get W/L stats for multiple puuids across multiple seasons in a single pass.

    Args:
        puuids: List of puuids to query.
        seasons: Dict of {season_key: (start_epoch, end_epoch)}.  Only seasons
                 with ``start_epoch is not None`` are queried (old display-only
                 seasons are skipped and returned as zero-stubs).

    Returns:
        Nested dict ``{puuid: {season_key: {games, wins, losses, winrate}}}``.
    """
    if not puuids:
        return {}

    # Build CASE buckets for each filterable season
    filterable = {k: v for k, v in seasons.items() if v[0] is not None}
    if not filterable:
        # All seasons are display-only stubs
        stub = {"games": 0, "wins": 0, "losses": 0, "winrate": 0}
        return {p: {sk: dict(stub) for sk in seasons} for p in puuids}

    # Use a single query with CASE expressions to bucket matches into seasons.
    # game_start is stored in milliseconds.
    case_parts = []
    for skey, (start, end) in filterable.items():
        start_ms = start * 1000
        if end is not None:
            end_ms = end * 1000
            case_parts.append(
                f"WHEN m.game_start >= {start_ms} AND m.game_start < {end_ms} THEN '{skey}'"
            )
        else:
            case_parts.append(f"WHEN m.game_start >= {start_ms} THEN '{skey}'")

    case_expr = "CASE " + " ".join(case_parts) + " ELSE NULL END"
    placeholders = ",".join("?" for _ in puuids)

    sql = f"""
        SELECT p.puuid,
               {case_expr} AS season_key,
               COUNT(*) AS games,
               SUM(CASE WHEN p.win THEN 1 ELSE 0 END) AS wins
        FROM participants p
        JOIN matches m ON m.match_id = p.match_id
        WHERE p.puuid IN ({placeholders})
          AND ({case_expr}) IS NOT NULL
          AND COALESCE(m.is_remake, 0) = 0
        GROUP BY p.puuid, season_key
    """

    result: dict[str, dict[str, dict]] = {}
    stub = {"games": 0, "wins": 0, "losses": 0, "winrate": 0}

    # Pre-fill all puuids with stubs for all seasons
    for p in puuids:
        result[p] = {sk: dict(stub) for sk in seasons}

    with get_db() as conn:
        for row in conn.execute(sql, puuids):
            puuid = row["puuid"]
            skey = row["season_key"]
            games = row["games"] or 0
            wins = row["wins"] or 0
            losses = games - wins
            wr = round(wins / games * 100) if games > 0 else 0
            result[puuid][skey] = {
                "games": games, "wins": wins, "losses": losses, "winrate": wr,
            }

    return result


def get_match_raw_json(match_id: str) -> str | None:
    """Get the raw Riot API JSON for a match."""
    with get_db() as conn:
        row = conn.execute(
            "SELECT raw_json FROM matches WHERE match_id = ?", (match_id,)
        ).fetchone()
        return row["raw_json"] if row and row["raw_json"] else None


def get_match_brief(match_id: str) -> dict | None:
    """Get minimal match info (id, game_start) for pagination logic."""
    with get_db() as conn:
        row = conn.execute(
            "SELECT match_id, game_start FROM matches WHERE match_id = ?",
            (match_id,)
        ).fetchone()
        return dict(row) if row else None


def get_existing_match_ids(match_ids: list) -> dict:
    """Check which match IDs exist in DB and whether they have raw_json.

    Returns {match_id: bool} where bool = True if raw_json is populated.
    """
    if not match_ids:
        return {}
    with get_db() as conn:
        placeholders = ",".join("?" for _ in match_ids)
        rows = conn.execute(
            f"""SELECT match_id,
                       CASE WHEN raw_json IS NOT NULL AND raw_json != '' THEN 1 ELSE 0 END as has_json
                FROM matches WHERE match_id IN ({placeholders})""",
            match_ids
        ).fetchall()
        return {r["match_id"]: bool(r["has_json"]) for r in rows}


# ---- Match predictions (retroactive) --------------------------------------

def get_match_prediction(match_id: str) -> dict | None:
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM match_predictions WHERE match_id = ?", (match_id,)
        ).fetchone()
        return dict(row) if row else None


def save_match_prediction(match_id: str, predicted_team: int,
                          confidence: float, factors: str,
                          blue_score: float, red_score: float,
                          actual_winner: int, outcome: str) -> dict:
    with get_db() as conn:
        conn.execute(
            """INSERT INTO match_predictions
               (match_id, predicted_team, confidence, factors,
                blue_score, red_score, actual_winner, outcome)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(match_id) DO UPDATE SET
                 predicted_team = excluded.predicted_team,
                 confidence = excluded.confidence,
                 factors = excluded.factors,
                 blue_score = excluded.blue_score,
                 red_score = excluded.red_score,
                 actual_winner = excluded.actual_winner,
                 outcome = excluded.outcome""",
            (match_id, predicted_team, confidence, factors,
             blue_score, red_score, actual_winner, outcome)
        )
        return {"match_id": match_id, "predicted_team": predicted_team,
                "confidence": confidence, "outcome": outcome}


# ---- Duo Cache -----------------------------------------------------------------

def get_duo_cache(match_id: str) -> dict | None:
    """Get cached duo detection result for a match. Returns parsed JSON or None."""
    with get_db() as conn:
        row = conn.execute(
            "SELECT duo_json FROM duo_cache WHERE match_id = ?", (match_id,)
        ).fetchone()
        if row:
            return json.loads(row["duo_json"])
        return None


def set_duo_cache(match_id: str, duo_data: dict):
    """Cache duo detection result for a match."""
    with get_db() as conn:
        conn.execute(
            """INSERT INTO duo_cache (match_id, duo_json)
               VALUES (?, ?)
               ON CONFLICT(match_id) DO UPDATE SET duo_json = excluded.duo_json""",
            (match_id, json.dumps(duo_data))
        )


def get_match_participants_puuids(match_id: str) -> list[dict]:
    """Get participant puuids and team_ids for a match (for duo detection)."""
    with get_db() as conn:
        rows = conn.execute(
            """SELECT puuid, team_id, champion_id FROM participants
               WHERE match_id = ? AND puuid != ''""",
            (match_id,)
        ).fetchall()
        return [dict(r) for r in rows]


def get_match_start_time(match_id: str) -> int | None:
    """Get the game_start timestamp (epoch ms) for a match."""
    with get_db() as conn:
        row = conn.execute(
            "SELECT game_start FROM matches WHERE match_id = ?", (match_id,)
        ).fetchone()
        if row:
            return row["game_start"]
        return None


# ---- Season Ranks (scraped from op.gg) ----------------------------------------

def upsert_season_rank(account_id: int, season_key: str, tier: str,
                       division: str, lp: int,
                       peak_tier: str = "", peak_division: str = "",
                       peak_lp: int = 0, source: str = "opgg"):
    """Insert or update a scraped season rank for an account."""
    with get_db() as conn:
        conn.execute(
            """INSERT INTO season_ranks
               (account_id, season_key, tier, division, lp,
                peak_tier, peak_division, peak_lp, source, scraped_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
               ON CONFLICT(account_id, season_key) DO UPDATE SET
                 tier = excluded.tier,
                 division = excluded.division,
                 lp = excluded.lp,
                 peak_tier = excluded.peak_tier,
                 peak_division = excluded.peak_division,
                 peak_lp = excluded.peak_lp,
                 source = excluded.source,
                 scraped_at = CURRENT_TIMESTAMP""",
            (account_id, season_key, tier, division, lp,
             peak_tier, peak_division, peak_lp, source)
        )


def get_season_ranks_for_account(account_id: int) -> list[dict]:
    """Get all scraped season ranks for an account."""
    with get_db() as conn:
        rows = conn.execute(
            """SELECT * FROM season_ranks
               WHERE account_id = ?
               ORDER BY season_key DESC""",
            (account_id,)
        ).fetchall()
        return [dict(r) for r in rows]


def get_season_rank(account_id: int, season_key: str) -> dict | None:
    """Get a specific season rank for an account."""
    with get_db() as conn:
        row = conn.execute(
            """SELECT * FROM season_ranks
               WHERE account_id = ? AND season_key = ?""",
            (account_id, season_key)
        ).fetchone()
        return dict(row) if row else None


# ---- Rank history (LP tracking over time) ----------------------------------

def insert_rank_history(account_id: int, queue_type: str, tier: str,
                        rank: str, lp: int, wins: int, losses: int):
    """Insert a rank snapshot. Called every time ranks are refreshed from Riot API."""
    with get_db() as conn:
        conn.execute(
            """INSERT INTO rank_history
               (account_id, queue_type, tier, rank, lp, wins, losses)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (account_id, queue_type, tier, rank, lp, wins, losses)
        )


def get_rank_history(account_id: int, queue_type: str = "RANKED_SOLO_5x5",
                     start_time: int | None = None,
                     end_time: int | None = None) -> list[dict]:
    """Get rank history snapshots for an account, optionally filtered by time range.

    Returns list of {tier, rank, lp, wins, losses, recorded_at} ordered by time.
    """
    with get_db() as conn:
        sql = """SELECT tier, rank, lp, wins, losses, recorded_at
                 FROM rank_history
                 WHERE account_id = ? AND queue_type = ?"""
        params: list = [account_id, queue_type]
        if start_time is not None:
            sql += " AND recorded_at >= datetime(?, 'unixepoch')"
            params.append(start_time)
        if end_time is not None:
            sql += " AND recorded_at < datetime(?, 'unixepoch')"
            params.append(end_time)
        sql += " ORDER BY recorded_at ASC"
        rows = conn.execute(sql, params).fetchall()
        return [dict(r) for r in rows]


def seed_rank_history_from_current(conn=None):
    """One-time seed: copy current ranks into rank_history if no history exists yet.

    This gives a starting baseline so sparklines have at least one data point.
    """
    should_close = False
    if conn is None:
        conn = _get_conn()
        should_close = False

    # Only seed if rank_history is completely empty
    count = conn.execute("SELECT COUNT(*) as c FROM rank_history").fetchone()["c"]
    if count > 0:
        return 0

    rows = conn.execute(
        """SELECT account_id, queue_type, tier, rank, lp, wins, losses
           FROM ranks WHERE tier IS NOT NULL AND tier != ''"""
    ).fetchall()

    for r in rows:
        conn.execute(
            """INSERT INTO rank_history
               (account_id, queue_type, tier, rank, lp, wins, losses)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (r["account_id"], r["queue_type"], r["tier"], r["rank"],
             r["lp"], r["wins"], r["losses"])
        )
    conn.commit()
    if rows:
        logger.info("Seeded rank_history with %d existing rank snapshots", len(rows))
    return len(rows)


# ---- GDPR Data Deletion -------------------------------------------------------

def gdpr_delete_player(puuid: str) -> dict:
    """Delete all data associated with a player's puuid (GDPR compliance).

    Removes:
    - Account from accounts table (cascades to ranks, season_ranks, rank_history)
    - Participant rows from participants table
    - Player name/puuid from predictions JSON blobs (blue_players, red_players)
    - Player data from matches.raw_json JSON blobs
    - Duo cache entries for matches this player was in

    Returns a summary of what was deleted.
    """
    summary = {}

    with get_db() as conn:
        # 1. Find the account (if it's a tracked account)
        acct = conn.execute(
            "SELECT id, profile_id, game_name, tag_line FROM accounts WHERE puuid = ?",
            (puuid,)
        ).fetchone()

        if acct:
            account_id = acct["id"]
            # Delete the account — CASCADE handles ranks, season_ranks, rank_history
            conn.execute("DELETE FROM accounts WHERE id = ?", (account_id,))
            summary["account_deleted"] = True
            summary["account_name"] = f"{acct['game_name']}#{acct['tag_line']}"

            # Check if this was the last account in the profile
            remaining = conn.execute(
                "SELECT COUNT(*) as cnt FROM accounts WHERE profile_id = ?",
                (acct["profile_id"],)
            ).fetchone()["cnt"]
            if remaining == 0:
                conn.execute("DELETE FROM profiles WHERE id = ?", (acct["profile_id"],))
                summary["profile_deleted"] = True
        else:
            summary["account_deleted"] = False

        # 2. Delete participant rows for this puuid
        cursor = conn.execute(
            "DELETE FROM participants WHERE puuid = ?", (puuid,)
        )
        summary["participants_deleted"] = cursor.rowcount

        # 3. Scrub puuid and player name from predictions JSON blobs
        pred_rows = conn.execute(
            "SELECT id, blue_players, red_players, factors FROM predictions"
        ).fetchall()
        preds_scrubbed = 0
        for row in pred_rows:
            changed = False
            updates = {}
            for col in ("blue_players", "red_players", "factors"):
                val = row[col]
                if val and puuid in val:
                    # Replace puuid with "[redacted]" in the JSON text
                    val = val.replace(puuid, "[redacted]")
                    updates[col] = val
                    changed = True
            if changed:
                set_clause = ", ".join(f"{k} = ?" for k in updates)
                values = list(updates.values()) + [row["id"]]
                conn.execute(
                    f"UPDATE predictions SET {set_clause} WHERE id = ?", values
                )
                preds_scrubbed += 1
        summary["predictions_scrubbed"] = preds_scrubbed

        # 4. Scrub puuid from matches.raw_json
        match_rows = conn.execute(
            "SELECT match_id, raw_json FROM matches WHERE raw_json IS NOT NULL AND raw_json LIKE ?",
            (f"%{puuid}%",)
        ).fetchall()
        matches_scrubbed = 0
        for row in match_rows:
            raw = row["raw_json"]
            if puuid in raw:
                raw = raw.replace(puuid, "[redacted]")
                conn.execute(
                    "UPDATE matches SET raw_json = ? WHERE match_id = ?",
                    (raw, row["match_id"])
                )
                matches_scrubbed += 1
        summary["matches_raw_json_scrubbed"] = matches_scrubbed

        # 5. Delete duo cache entries for matches that involved this player
        # (We can't easily know which matches without checking, but since
        # participant rows are deleted, the cache is stale anyway)
        duo_rows = conn.execute(
            "SELECT match_id, duo_json FROM duo_cache WHERE duo_json LIKE ?",
            (f"%{puuid}%",)
        ).fetchall()
        if duo_rows:
            conn.executemany(
                "DELETE FROM duo_cache WHERE match_id = ?",
                [(r["match_id"],) for r in duo_rows]
            )
        summary["duo_cache_deleted"] = len(duo_rows)

    logger.info("GDPR deletion completed for puuid=%s: %s", puuid, summary)
    return summary


# ---- Game Notes (Phase 17) ----

def get_match_notes(match_id: str, puuid: str) -> str | None:
    """Get notes for a specific match + player."""
    with get_db() as conn:
        row = conn.execute(
            "SELECT notes FROM participants WHERE match_id = ? AND puuid = ?",
            (match_id, puuid)
        ).fetchone()
        if row:
            return row["notes"]
        return None


def save_match_notes(match_id: str, puuid: str, notes: str) -> bool:
    """Save notes for a specific match + player.

    Uses a dedicated short-lived connection with aggressive retry
    to avoid contention with long-lived thread-local connections
    that may hold implicit read transactions under gevent.
    """
    import time
    for attempt in range(5):
        conn = sqlite3.connect(DB_PATH, timeout=5)
        try:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA busy_timeout=5000")
            conn.execute("BEGIN IMMEDIATE")
            conn.execute(
                "UPDATE participants SET notes = ? WHERE match_id = ? AND puuid = ?",
                (notes, match_id, puuid)
            )
            conn.commit()
            return True
        except sqlite3.OperationalError as e:
            conn.rollback()
            if "locked" in str(e) and attempt < 4:
                logger.warning("save_match_notes locked, retry %d/4", attempt + 1)
                time.sleep(0.5 * (attempt + 1))
                continue
            raise
        finally:
            conn.close()
    return False


def delete_match_notes(match_id: str, puuid: str) -> bool:
    """Clear notes for a specific match + player."""
    import time
    for attempt in range(5):
        conn = sqlite3.connect(DB_PATH, timeout=5)
        try:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA busy_timeout=5000")
            conn.execute("BEGIN IMMEDIATE")
            conn.execute(
                "UPDATE participants SET notes = NULL WHERE match_id = ? AND puuid = ?",
                (match_id, puuid)
            )
            conn.commit()
            return True
        except sqlite3.OperationalError as e:
            conn.rollback()
            if "locked" in str(e) and attempt < 4:
                logger.warning("delete_match_notes locked, retry %d/4", attempt + 1)
                time.sleep(0.5 * (attempt + 1))
                continue
            raise
        finally:
            conn.close()
    return False


# ---- Match Analysis (Phase 19: LLM Build Recommendations) --------------------

def get_match_analysis(match_id: str, puuid: str) -> dict | None:
    """Get cached LLM build analysis for a match + player."""
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM match_analysis WHERE match_id = ? AND puuid = ?",
            (match_id, puuid)
        ).fetchone()
        return dict(row) if row else None


def save_match_analysis(match_id: str, puuid: str, analysis_json: str,
                        model: str = "claude-haiku-4-5") -> bool:
    """Save LLM build analysis. Uses dedicated connection with retry."""
    import time
    for attempt in range(5):
        conn = sqlite3.connect(DB_PATH, timeout=5)
        try:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA busy_timeout=5000")
            conn.execute("BEGIN IMMEDIATE")
            conn.execute(
                """INSERT INTO match_analysis
                   (match_id, puuid, analysis_json, model)
                   VALUES (?, ?, ?, ?)
                   ON CONFLICT(match_id, puuid) DO UPDATE SET
                     analysis_json = excluded.analysis_json,
                     model = excluded.model,
                     created_at = CURRENT_TIMESTAMP""",
                (match_id, puuid, analysis_json, model)
            )
            conn.commit()
            return True
        except sqlite3.OperationalError as e:
            conn.rollback()
            if "locked" in str(e) and attempt < 4:
                logger.warning("save_match_analysis locked, retry %d/4", attempt + 1)
                time.sleep(0.5 * (attempt + 1))
                continue
            raise
        finally:
            conn.close()
    return False


def get_live_analysis(game_id: str, puuid: str) -> dict | None:
    """Get cached LLM pre-game build analysis for a live game + player."""
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM live_analysis WHERE game_id = ? AND puuid = ?",
            (game_id, puuid)
        ).fetchone()
        return dict(row) if row else None


def save_live_analysis(game_id: str, puuid: str, analysis_json: str,
                       model: str = "claude-haiku-4-5") -> bool:
    """Save LLM pre-game build analysis. Uses dedicated connection with retry."""
    import time
    for attempt in range(5):
        conn = sqlite3.connect(DB_PATH, timeout=5)
        try:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA busy_timeout=5000")
            conn.execute("BEGIN IMMEDIATE")
            conn.execute(
                """INSERT INTO live_analysis
                   (game_id, puuid, analysis_json, model)
                   VALUES (?, ?, ?, ?)
                   ON CONFLICT(game_id, puuid) DO UPDATE SET
                     analysis_json = excluded.analysis_json,
                     model = excluded.model,
                     created_at = CURRENT_TIMESTAMP""",
                (game_id, puuid, analysis_json, model)
            )
            conn.commit()
            return True
        except sqlite3.OperationalError as e:
            conn.rollback()
            if "locked" in str(e) and attempt < 4:
                logger.warning("save_live_analysis locked, retry %d/4", attempt + 1)
                time.sleep(0.5 * (attempt + 1))
                continue
            raise
        finally:
            conn.close()
    return False


def get_game_analysis(match_id: str, puuid: str) -> dict | None:
    """Get cached game analysis for a match+player."""
    with get_db() as conn:
        row = conn.execute(
            "SELECT analysis_text, model, created_at FROM game_analysis WHERE match_id = ? AND puuid = ?",
            (match_id, puuid)
        ).fetchone()
        return dict(row) if row else None


def save_game_analysis(match_id: str, puuid: str, analysis_text: str, model: str = "claude-haiku-4-5") -> bool:
    """Save game analysis to cache. Uses dedicated connection with retry for locks."""
    import time
    for attempt in range(5):
        conn = sqlite3.connect(DB_PATH, timeout=5)
        try:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA busy_timeout=5000")
            conn.execute("BEGIN IMMEDIATE")
            conn.execute(
                """INSERT INTO game_analysis (match_id, puuid, analysis_text, model)
                   VALUES (?, ?, ?, ?)
                   ON CONFLICT(match_id, puuid) DO UPDATE SET
                     analysis_text = excluded.analysis_text,
                     model = excluded.model,
                     created_at = CURRENT_TIMESTAMP""",
                (match_id, puuid, analysis_text, model)
            )
            conn.commit()
            return True
        except sqlite3.OperationalError as e:
            conn.rollback()
            if "locked" in str(e) and attempt < 4:
                logger.warning("save_game_analysis locked, retry %d/4", attempt + 1)
                time.sleep(0.5 * (attempt + 1))
                continue
            raise
        finally:
            conn.close()
    return False


# -- Dashboard Layout -------------------------------------------------------

def get_dashboard_layout(profile_id: int) -> str | None:
    """Get saved dashboard layout JSON for a profile."""
    with get_db() as conn:
        row = conn.execute(
            "SELECT layout_json FROM dashboard_layouts WHERE profile_id = ?",
            (profile_id,)
        ).fetchone()
        return row[0] if row else None


def save_dashboard_layout(profile_id: int, layout_json: str) -> bool:
    """Save dashboard layout for a profile. Upserts."""
    import time
    for attempt in range(5):
        conn = sqlite3.connect(DB_PATH, timeout=5)
        try:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA busy_timeout=5000")
            conn.execute("BEGIN IMMEDIATE")
            conn.execute(
                """INSERT INTO dashboard_layouts (profile_id, layout_json)
                   VALUES (?, ?)
                   ON CONFLICT(profile_id) DO UPDATE SET
                     layout_json = excluded.layout_json,
                     updated_at = CURRENT_TIMESTAMP""",
                (profile_id, layout_json)
            )
            conn.commit()
            return True
        except sqlite3.OperationalError as e:
            conn.rollback()
            if "locked" in str(e) and attempt < 4:
                logger.warning("save_dashboard_layout locked, retry %d/4", attempt + 1)
                time.sleep(0.5 * (attempt + 1))
                continue
            raise
        finally:
            conn.close()
    return False


# ---- Focus Mode ----

def get_active_focus(profile_id: int) -> dict | None:
    """Get the active (non-ended) focus session for a profile."""
    with get_db() as conn:
        row = conn.execute(
            """SELECT id, rule_text, started_at FROM focus_sessions
               WHERE profile_id = ? AND ended_at IS NULL
               ORDER BY started_at DESC LIMIT 1""",
            (profile_id,)
        ).fetchone()
        if not row:
            return None
        stats = conn.execute(
            """SELECT COUNT(*) as total,
                      SUM(CASE WHEN followed THEN 1 ELSE 0 END) as followed_count
               FROM focus_checkins WHERE session_id = ?""",
            (row["id"],)
        ).fetchone()
        return {
            "id": row["id"],
            "rule_text": row["rule_text"],
            "started_at": row["started_at"],
            "total_checkins": stats["total"] or 0,
            "followed_count": stats["followed_count"] or 0,
        }


def set_focus(profile_id: int, rule_text: str) -> dict:
    """Set a new focus for the profile. Ends any previous active focus."""
    with get_db() as conn:
        conn.execute(
            """UPDATE focus_sessions SET ended_at = CURRENT_TIMESTAMP
               WHERE profile_id = ? AND ended_at IS NULL""",
            (profile_id,)
        )
        cur = conn.execute(
            """INSERT INTO focus_sessions (profile_id, rule_text)
               VALUES (?, ?)""",
            (profile_id, rule_text)
        )
        conn.commit()
        return {
            "id": cur.lastrowid,
            "rule_text": rule_text,
            "total_checkins": 0,
            "followed_count": 0,
        }


def end_focus(profile_id: int) -> bool:
    """End the active focus session."""
    with get_db() as conn:
        result = conn.execute(
            """UPDATE focus_sessions SET ended_at = CURRENT_TIMESTAMP
               WHERE profile_id = ? AND ended_at IS NULL""",
            (profile_id,)
        )
        conn.commit()
        return result.rowcount > 0


def save_focus_checkin(session_id: int, match_id: str, account_id: int, followed: bool) -> bool:
    """Save a focus check-in for a match. Upserts."""
    with get_db() as conn:
        conn.execute(
            """INSERT INTO focus_checkins (session_id, match_id, account_id, followed)
               VALUES (?, ?, ?, ?)
               ON CONFLICT(session_id, match_id, account_id)
               DO UPDATE SET followed = excluded.followed""",
            (session_id, match_id, account_id, followed)
        )
        conn.commit()
        return True


def get_focus_checkins_batch(session_id: int, match_ids: list) -> dict:
    """Get check-in results for multiple matches. Returns {match_id: followed}."""
    if not match_ids:
        return {}
    with get_db() as conn:
        placeholders = ",".join("?" for _ in match_ids)
        rows = conn.execute(
            f"""SELECT match_id, followed FROM focus_checkins
                WHERE session_id = ? AND match_id IN ({placeholders})""",
            [session_id] + match_ids
        ).fetchall()
        return {r["match_id"]: bool(r["followed"]) for r in rows}


def get_previous_focus_rules(profile_id: int, limit: int = 5) -> list:
    """Get previously used focus rules (unique, most recent first)."""
    with get_db() as conn:
        rows = conn.execute(
            """SELECT rule_text, MAX(started_at) as last_used
               FROM focus_sessions
               WHERE profile_id = ?
               GROUP BY rule_text
               ORDER BY last_used DESC
               LIMIT ?""",
            (profile_id, limit)
        ).fetchall()
        return [r["rule_text"] for r in rows]


def get_focus_stats(profile_id: int) -> dict:
    """Get focus adherence stats including winrate correlation."""
    with get_db() as conn:
        rows = conn.execute(
            """SELECT fc.followed, p.win
               FROM focus_checkins fc
               JOIN focus_sessions fs ON fs.id = fc.session_id
               JOIN participants p ON p.match_id = fc.match_id
               JOIN accounts a ON a.id = fc.account_id AND a.puuid = p.puuid
               WHERE fs.profile_id = ?""",
            (profile_id,)
        ).fetchall()

        total = len(rows)
        if total == 0:
            return {"total": 0}

        followed = [r for r in rows if r["followed"]]
        not_followed = [r for r in rows if not r["followed"]]
        followed_wins = sum(1 for r in followed if r["win"])
        not_followed_wins = sum(1 for r in not_followed if r["win"])

        return {
            "total": total,
            "followed_count": len(followed),
            "not_followed_count": len(not_followed),
            "adherence_pct": round(len(followed) / total * 100) if total > 0 else 0,
            "followed_winrate": round(followed_wins / len(followed) * 100) if followed else None,
            "not_followed_winrate": round(not_followed_wins / len(not_followed) * 100) if not_followed else None,
        }
