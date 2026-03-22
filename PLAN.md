# LolTracker - Implementation Plan

## Current Task: Phase 27 — Focus Mode

### Problem
Player knows what to do but doesn't do it under pressure. Fights when behind,
tilts from teammates, autopilot aggression. Knowledge isn't the bottleneck —
discipline is. Need a behavioral feedback loop, not more analysis.

### Design
- **One active focus per profile**, nullable, persists until changed
- **Pre-session**: Dashboard banner "What's your focus today?" with quick-picks + custom text
- **During session**: Focus rule pinned at top of dashboard, visible between games
- **Post-game**: Each new match card shows "Did you follow your rule? Yes/No"
- **Over time**: Track adherence %, correlate with winrate

### Data Model
```
focus_sessions:
  id INTEGER PRIMARY KEY,
  profile_id INTEGER NOT NULL,
  rule_text TEXT NOT NULL,
  started_at TEXT DEFAULT (datetime('now')),
  ended_at TEXT DEFAULT NULL,
  FOREIGN KEY (profile_id) REFERENCES profiles(id)

focus_checkins:
  id INTEGER PRIMARY KEY,
  session_id INTEGER NOT NULL,
  match_id TEXT NOT NULL,
  account_id INTEGER NOT NULL,
  followed BOOLEAN NOT NULL,
  created_at TEXT DEFAULT (datetime('now')),
  FOREIGN KEY (session_id) REFERENCES focus_sessions(id)
```

### API Endpoints
- `GET /api/profiles/{id}/focus` — Get active focus (or null)
- `POST /api/profiles/{id}/focus` — Set new focus {rule_text}; ends previous
- `DELETE /api/profiles/{id}/focus` — End current focus
- `POST /api/profiles/{id}/focus/checkin` — {match_id, account_id, followed}
- `GET /api/profiles/{id}/focus/stats` — Adherence %, winrate when followed vs not

### Quick-Pick Library
- "Farm safe when behind — no solo fights after 2 deaths"
- "Mute at first sign of tilt"
- "No chasing past river without vision"
- "Play for objectives, not kills"
- "Reset after dying — don't TP back to fight"
- "Track enemy jungler before trading"

### Frontend
1. Dashboard: focus banner above account cards
   - No focus: subtle "Set a focus for today?" card with quick-picks
   - Active focus: pinned banner showing rule, "X games, Y days active", change/end buttons
2. Match cards: check-in prompt on matches played during active focus session
   - Simple Yes/No buttons, saves immediately
   - Already checked in: shows result (green check / red x)
3. Focus stats card (later): adherence trend, winrate correlation

## Previous: Phase 26 — Match History Enhancements

### Features
Four new features for the match history and post-game detail views.

#### 26a: LP Change Per Game
Show "+18 LP" or "-15 LP" next to each ranked match in match history.

**Approach:**
- `rank_history` table already records snapshots (tier, rank, lp, recorded_at) after each refresh
- For each match, find the two closest rank_history snapshots (before and after game_start)
- Compute LP delta: `after.lp - before.lp` (accounting for tier/division changes)
- Backend: Add `lp_delta` field to match list API response
- Frontend: Show colored badge next to W/L indicator: green "+18", red "-15"
- Only for ranked queues (420, 440), skip for normals
- Edge case: tier promotion/demotion — convert to absolute score diff

**Files:** app.py (match list enrichment), database.py (rank_history query), app.js (render), style.css

#### 26b: Loss Streak Tilt Warning
Show a warning banner on the dashboard when a player loses 3+ games in a row in the current session.

**Approach:**
- Session stats already exist (`/api/accounts/{id}/session-stats`) — returns today's games + streak
- Backend: Already computes `streak` (count + type) — just need to expose to dashboard
- Frontend: In `loadSessionStats()`, if streak is loss >= 3, show a tilt warning banner on the account card
- Style: Red/orange banner with warning icon, e.g. "🔥 3 loss streak — consider taking a break"
- Dismiss: Auto-dismiss when streak breaks (win), no manual dismiss needed

**Files:** app.js (session stats render), style.css (tilt banner)

#### 26c: Match History Search by Opponent Champion
Filter match history by enemy champion — "show all games where I played against Yasuo."

**Approach:**
- We store all 10 participants per match in the `participants` table
- Backend: Add `vs_champion` query param to `GET /api/accounts/{id}/matches`
- Query: JOIN participants twice — once for the player, once for any enemy with that champion
- Frontend: Add "Vs Champion" filter dropdown next to existing filters, populated from opponent champions
- Populate from loaded matches (client-side filtering like existing champion filter)

**Files:** app.js (filter dropdown + logic), index.html (dropdown element)

#### 26d: Gold/Damage Bars in Post-Game Detail
Visual horizontal bars in the expanded match view showing relative gold and damage per player.

**Approach:**
- Data already available: `p.gold` and `p.damage` for each participant
- Find the max gold and max damage across all 10 players in the match
- Render proportional bars (width as % of max) under each player's stats
- Two thin bars per player: gold (yellow) and damage (red/blue by team)
- Add to `renderExpandTeamHighlighted` and `renderExpandTeam` functions

**Files:** app.js (bar rendering), style.css (bar styles)

### Order of Implementation
1. 26b (tilt warning) — quickest, uses existing data
2. 26a (LP change) — needs rank_history correlation
3. 26c (opponent filter) — client-side filtering
4. 26d (gold/damage bars) — visual addition

## Previous: Phase 25 — Remake Detection

### Problem
Remakes (games where someone AFKs in first ~2.5 min and team votes /remake) are being
counted as losses in W/L stats and shown as "L" in match history. Remakes should not count
toward wins or losses — they're non-games.

### Detection
- Riot API provides `gameEndedInEarlySurrender: true` per participant for remakes
- We store `raw_json` on matches table — can extract this flag
- Remakes: `gameEndedInEarlySurrender=True`, duration 67-163s
- Early FF (real games): `gameEndedInEarlySurrender=False`, duration 186s+
- Fallback for matches without raw_json: `game_duration < 210`

### Implementation
1. Add `is_remake BOOLEAN DEFAULT 0` column to `matches` table (migration)
2. Backfill existing matches from raw_json (`gameEndedInEarlySurrender`) + duration fallback
3. Set `is_remake` during `store_match()` for new matches
4. Filter `AND m.is_remake = 0` in: season stats, champion stats, batch season stats
5. Frontend: Show "Remake" label instead of W/L badge, gray styling, exclude from filters
6. Keep remakes visible in match history (informational) but don't count in stats

## Previous: Phase 24e — Pure Static Dashboard (No Customization)

### Status
- Phase 23b: COMPLETE (performance-score + game-analysis)
- Phase 24 (Dashboard Grid): FAILED
- Phase 24b: FAILED (gridstack sizeToContent unreliable)
- Phase 24c: FAILED (dual-mode gridstack — destroy/save race conditions)
- Phase 24d: FAILED (simple reorder/hide panel — still broken in production)
- Phase 24e (This task): IN PROGRESS — pure static, zero customization

### Phase 24e — Pure Static Dashboard

**Problem**: Every customization attempt (gridstack, reorder panel) has broken the dashboard.

**Solution**: Remove ALL customization. Hardcoded widget order, no gear icon, no edit panel,
no layout API calls. Just render 5 widgets in a fixed order every time.

**Architecture**:
- Fixed order: Quick Stats → Accounts → Heatmap + Role Performance (side-by-side) → Performance Score
- No layout API calls, no dashLayout state, no edit mode
- Just `renderDashboard()` builds divs in order and calls render functions
- Heatmap + role-stats paired side-by-side in CSS grid row
- No gridstack vendor files needed (can delete static/vendor/gridstack*)

### Architecture

**Library**: gridstack.js v12 (vendored at static/vendor/)
- ~83KB JS, zero dependencies, built-in drag/drop + resize
- CSS Grid-based layout engine with CSS variables
- Built-in save()/load() for JSON serialization
- Built-in responsive breakpoints

**DB Storage**: `dashboard_layouts` table
- profile_id (FK), layout_json (TEXT), updated_at
- One row per profile, stores the full widget positions array
- API: GET/PUT /api/profiles/{id}/dashboard-layout

**Default Layout** (12-column grid, cellHeight ~80px):
- quick-stats:    x=0, y=0,  w=12, h=1  (full width, fixed height)
- accounts:       x=0, y=1,  w=12, h=4  (full width, tall)
- heatmap:        x=0, y=5,  w=6,  h=4  (left half)
- role-stats:     x=6, y=5,  w=6,  h=3  (right half)
- performance:    x=6, y=8,  w=6,  h=4  (right half, below roles)

**Edit Mode**:
- Gear icon in dashboard header toggles edit mode
- In edit mode: drag handles visible, resize handles visible, dotted grid overlay
- "Add Widget" drawer shows hidden widgets that can be re-added
- "Reset Layout" button restores defaults
- Changes auto-save on every drag/resize via grid.on('change')
- Each widget gets an "X" close button in edit mode to hide it

**Widgets**:
- Each section becomes a widget with: id, title, render function
- Widget content renders inside .grid-stack-item-content
- On resize, SVG charts (radar, heatmap) auto-resize via viewBox
- Account cards grid uses CSS grid inside the widget (responsive within widget)

**Responsive**:
- Desktop: 12 columns
- Mobile (<768px): 1 column, all widgets stack vertically

### Goal
Two medium-effort features: a radar chart comparing player performance vs lobby averages,
and an LLM-powered post-game analysis that uses match timeline data.

### Feature 1: Performance Score (GPI-style Radar Chart)

**Approach**: Compare player's stats against the average of all other 9 participants in their
matches. Since matchmaking puts you with similarly-ranked players, "lobby average" IS your
rank-peer baseline.

**Dimensions (6-axis radar):**
1. CS/min — higher is better
2. Vision Score/min — higher is better
3. Kill Participation % — higher is better
4. Death Rate (deaths/min) — INVERTED, lower is better
5. Damage Share % — higher is better
6. Gold Efficiency (gold/min) — higher is better

**Scoring**: Each dimension = 0-100 where 50 = lobby average.
- Compute player's avg stat across recent N matches
- Compute lobby avg (other 9 players) across same matches
- Score = 50 + (player_avg - lobby_avg) / lobby_stddev * 15 (capped 0-100)
- Overall score = average of 6 dimensions

**Backend**: New endpoint GET /api/accounts/{id}/performance-score
- Query participants + matches, group by tracked puuid vs others
- Return per-dimension scores + raw values

**Frontend**: SVG radar chart in a new section on the dashboard below role stats.
One radar per account, or a combined view.

### Feature 2: LLM Post-Game Analysis (with Timeline)

**Flow:**
1. User clicks "Analyze" on match expand panel
2. Backend fetches match timeline from Riot API (1 API call)
   - GET /lol/match/v5/matches/{matchId}/timeline
   - Store timeline in DB for caching (new column or table)
3. Build structured prompt with:
   - Team comps, roles, ranks
   - Per-player stats: KDA, CS, vision, damage, gold
   - Timeline events: early kills (with timestamps + positions), jungle ganks (assists),
     dragon/baron sequence, tower plates, gold leads at 10/15/20 min
   - The tracked player's specific performance highlighted
4. Send to Claude haiku (fast + cheap)
5. Cache response in match_analysis table
6. Display in match expand panel

**Timeline data we extract:**
- Gold diff per team at frames 10, 15, 20 min
- First blood time + participants
- Dragon/Baron kill times + which team
- Early gank patterns: kills with jungle assist before 15 min
- Tower fall sequence
- Level advantages at key frames

**Prompt structure:**
- System: "You are a League of Legends analyst. Analyze this match from {player}'s perspective.
  Be specific about timing and causality. 3-4 sentences max. No generic advice."
- User: structured JSON of match + timeline data

**Cost**: ~1500 tok in + 200 tok out per analysis = ~$0.0004/analysis on haiku

**Model**: claude-haiku-4-5 (default), with option to use claude-sonnet-4-5 for deeper analysis

**Caching**: match_analysis table already exists with (match_id, puuid) key

---

## Previous: Phase 23 — Five Low-Effort Enhancement Features

### Goal
Build 5 new features that leverage existing DB data. All are UI/query work — no new API calls needed.
Dev only (no production deploy until user approves).

### Features

#### 1. Full LP Tracking Graph
- Click sparkline on account card → opens modal/panel with full interactive SVG chart
- X-axis: time, Y-axis: LP score (using rankToScore())
- Show tier boundaries as horizontal bands with tier colors
- Hover shows tooltip: date, rank, LP, W/L
- Time range buttons: 7d, 30d, Season, All
- No Chart.js — pure SVG like the sparkline, just bigger + interactive

#### 2. Game Time Heatmap
- New section on Dashboard (below account cards) or on Champions tab
- GitHub-style contribution grid: 7 rows (days) × N columns (weeks)
- Color intensity = games played that day, overlay text = win rate
- Below heatmap: "Best time to play" summary (highest WR time-of-day)
- Data: query matches.game_start for tracked accounts, group by date/hour
- API: new endpoint GET /api/profiles/{id}/play-times

#### 3. Win/Loss Streak & Session Stats
- On each account card, show "Today: 3W-1L (+47 LP)" badge
- Current streak: "🔥 4W streak" or "❄ 3L streak" (computed from recent matches)
- Data: matches + participants for today's games for each account
- Enhance the account card rendering, no new pages needed
- API: new endpoint GET /api/profiles/{id}/session-stats (or compute client-side from existing match data)

#### 4. Role Performance Breakdown
- New section on Champions tab or Dashboard
- Table/cards showing per-role stats: Games, WR%, Avg KDA, CS/min, Vision
- Highlight best/worst role
- Data: aggregate participants table grouped by position, filtered to tracked accounts
- API: new endpoint GET /api/profiles/{id}/role-stats

#### 5. Head-to-Head Comparison
- New tab or modal: pick 2 accounts, see side-by-side comparison
- Stats: Rank, WR, Avg KDA, CS/min, Vision, Damage/min, most played champs
- Visual bars showing who's ahead in each stat
- Data: aggregate from participants + ranks tables
- API: new endpoint GET /api/accounts/{id}/stats-summary

### Architecture Notes
- All features are pure DB aggregation + frontend rendering
- No new Riot API calls needed
- No Chart.js dependency — keep using pure SVG for consistency
- All new API endpoints return JSON, all rendering is client-side

---

## Previous: Phase 22 — Background Scheduler

### Goal
Automatic background updates so data is always fresh, not just when user loads pages.
Run at 8am EST daily (prep for the day) + once per hour. All existing task_lock mechanics
prevent conflicts with user-triggered refreshes.

### Schedule
- **Hourly**: Every hour on the hour
- **Daily at 8am EST**: Full refresh cycle (same jobs, just guaranteed morning run)
- Gunicorn runs 2 workers — scheduler runs in ONE worker only (use pid-based guard)

### Jobs (run sequentially to avoid rate limit storms)
1. **Refresh ranks** — for all accounts across all profiles
   - Reuse `_refresh_account_ranks(account_id, puuid)` 
   - Sequential per account (not parallel) to stay within rate limits
   - Respect `task_lock("refresh_account", ...)` — skip if user is already refreshing
   - ~2 API calls per account (get_account_by_puuid + get_league_entries)
   
2. **Fetch new matches** — for all accounts
   - Reuse `_fetch_and_store_matches(puuid, count=20)`
   - Sequential per account
   - Respect `task_lock("fetch_matches", ...)` — skip if user is already fetching
   - ~2 API calls per account for match IDs + N calls for new match details
   
3. **Auto-resolve pending predictions** — check if pending live games ended
   - Query `predictions` table for `outcome = 'pending'`
   - For each, call the resolve logic (get_account_by_riot_id + get_match_ids + get_match)
   - Skip if no pending predictions
   
4. **Scrape rank history** — op.gg season rank snapshots
   - Reuse `_scrape_and_store_season_ranks(account_id, game_name, tag_line)`
   - Only run on 8am daily cycle, not hourly (op.gg scraping is slow + not rate-limited by Riot)
   - Respect `task_lock("scrape", ...)` — skip if already in progress

### Status Tracking
- Global `_scheduler_status` dict: `{running: bool, last_run: timestamp, current_step: str}`
- API endpoint `GET /api/scheduler/status` for frontend to check
- Frontend shows "Background update in progress..." banner when scheduler is running
- Existing refresh buttons show "Updating..." and return 409 when task_lock is held by scheduler

### Implementation
- Simple `threading.Thread(daemon=True)` with a sleep loop — no external dependency needed
- Worker guard: only start scheduler if `os.getpid()` matches first worker (avoid duplicate timers)
- Use `schedule` library or manual time check in loop (check every 60s, run job if hour changed)
- All jobs run inside `try/except` so one failure doesn't kill the scheduler
- Log all scheduler activity at INFO level

### Rate Budget
With dev key (20/s, 100/2min):
- 6 profiles × ~2 accounts each = ~12 accounts
- Rank refresh: ~24 API calls (2 per account)
- Match fetch: ~24 API calls for IDs + maybe 10-20 for new match details
- Prediction resolve: ~15 API calls max (3 pending × 5 matches each)
- Total: ~60-80 calls per cycle — fits comfortably in 2-minute window
- Running sequentially (not parallel) avoids rate limit storms

## Phase 21 — Global Prediction History + Prediction Accuracy Overhaul [DONE]

### Problem Analysis (from production data)

**Live prediction accuracy: 27.8% (5/18)** — worse than coin flip.
**Retroactive prediction accuracy: 76.7% (33/43)** — much better.

Root causes identified:

1. **champion_exp is ALWAYS 50.0 in live predictions** — 15% weight on a constant = noise.
   Live game lookup doesn't fetch enough match history per player to measure experience.
   Fix: Remove or heavily reduce champion_exp weight.

2. **champion_wr has coarse/unreliable values** — based on few recent games. Values
   jump in increments of 10 (30, 40, 50, 60, 70). Small sample = high noise.
   Currently 25% weight but only 27.8% accuracy when used alone.

3. **Rank differences are tiny** (avg 1.4 out of 100) — matchmaking puts similar-ranked
   players together, so rank rarely discriminates. When it does discriminate (diff > 3),
   it's more accurate. But at 40% weight with avg 1.4 diff, rank barely moves the needle.

4. **Two separate tables create confusion** — `predictions` (live) and `match_predictions`
   (retroactive) store the same type of data but separately. Prediction history only shows
   the live predictions table, missing the retroactive ones entirely.

### Phase 21a: Global Prediction History

**Goal**: All predictions (live + retroactive) appear in one unified prediction history.
Paginated with load-more, toggleable count (all/last 20/50).

**Changes**:
1. Backend: New `GET /api/predictions` that merges both tables, sorted by date
2. Backend: Add pagination params `?limit=20&offset=0`
3. Frontend: Remove profile-based filtering — show ALL predictions globally
4. Frontend: Add pagination (load more button) and count toggle
5. Frontend: Show source indicator (Live / Retroactive)

### Phase 21b: Prediction Algorithm Reweighting

**Goal**: Improve accuracy by reweighting factors based on what actually predicts wins.

From production data analysis:
- rank_score-only: 50% live, 72.1% retro
- champion_wr-only: 27.8% live, 76.7% retro (but live data is garbage)
- recent_form-only: 44.4% live, 72.1% retro
- champion_exp-only: 33.3% live, 65.1% retro

Riot's claim: rank alone = ~75% correct. Our data shows 72.1% on retroactive (consistent).

New weights to test:
- rank_score: 60% (up from 40%) — most reliable single predictor
- recent_form: 25% (up from 20%) — second most reliable
- champion_wr: 15% (down from 25%) — only useful with good data
- champion_exp: 0% (removed) — useless in live predictions

Or even simpler: rank_score 70%, recent_form 20%, champion_wr 10%.

---

## Previous Task: Phase 20 — Write 10 Champion Build Guides

**Goal:** Write all 10 champion build guides using first-principles analysis from
gathered champion data. All raw ability data has been gathered and analyzed. Now
encode into the BUILD_GUIDES dict format in `build_guides.py`.

### Guides to Write
1. Samira — Bot (ADC): Crit + Lifesteal. R = 10 shots at full crit, 100% lifesteal each.
2. Darius — Top: Total AD scaling bruiser. E = 20-40% armor pen passive. R = true damage.
3. Miss Fortune — Bot (ADC): AD + Lethality first. R = 12-16 waves × 60% tAD.
4. Lux — Mid: 380% total AP ratio full combo. Burst mage.
5. Lux — Support: W shield (40% AP × 2 passes). Heal/Shield Power scaling.
6. Nidalee — Jungle: Full AP assassin. Max range spear = 487.5 + 1.625 AP.
7. Nidalee — Support: E heal (150 + 35% AP, up to 300 + 70% AP) + 70% AS steroid for ADC.
8. Garen — Top: E ticks scale with bonus AS. W shield = 18% bonus HP. R = true damage.
9. Master Yi — Jungle: On-hit/AS. Q applies on-hit at 75%. E = true damage on-hit.
10. Urgot — Top: W = fixed 3.0 AS, on-hit at 50%. Black Cleaver stacks in 2s.

### Frontend Work
- Add role tab switcher UI for Lux and Nidalee (multi-role champions)
- Backend already supports multi-role via "ChampionName:Role" keys

### Deploy
- Add new item IDs to ITEM_NAMES dict
- Bump cache bust version
- Deploy to Unraid

---

## Previous Task: Phase 19e — Fire LLM Immediately from Spectator Data

**Goal:** When a player is in a live game and there's NO cached LLM analysis, fire the LLM immediately using spectator data (champion names + roles) instead of waiting for the slow `_build_live_game()` (ranks, winrates, duos) to complete. This eliminates the minutes-long wait before the build recommendation appears.

### Architecture

**Current flow:**
1. `generate()` SSE → spectator check → cached LLM? send early → start `_build_live_game()` thread
2. `_build_live_game()` resolves names, ranks, winrates, duos (SLOW, minutes)
3. `_send_result_and_llm()` sends result, fires LLM if no cache → `build_recommendation` SSE

**New flow:**
1. `generate()` SSE → spectator check → cached LLM? send early
2. If NO cached LLM → build lightweight team comp from spectator data (champion IDs → names via DDragon, roles via Hungarian algorithm) → fire `_generate_live_build_analysis()` in background thread → send `cached_build` SSE when done
3. Start `_build_live_game()` thread concurrently
4. SSE loop drains both progress messages AND early LLM result
5. `_send_result_and_llm()` checks cache — if analysis already generated by early fire, skips duplicate LLM call

### Implementation Steps

1. After spectator check and cache miss (line ~1133), build a lightweight `live_result` dict:
   - Get `champion_map` from `_api.get_champion_data()`
   - Parse spectator participants into `teams_map` with champion_id, spell data
   - Run `_assign_team_roles(teams_map)` for role inference
   - Construct minimal teams structure (no names, ranks = None)
2. Fire `_generate_live_build_analysis(game_id, puuid, lightweight_result)` in a background thread
3. Add an `llm_q` queue that the early LLM thread puts results into
4. In the SSE loop, drain both `progress_q` (from `_build_live_game`) and `llm_q` (from early LLM)
5. `_send_result_and_llm()` already checks `db.get_live_analysis()` cache — the early-fired analysis will be cached, so it naturally skips the duplicate call

### Key Insight
`_generate_live_build_analysis()` already handles all the lock/dedup logic. If the early fire saves to DB, the later call in `_send_result_and_llm()` finds the cache and returns it instead of calling the LLM again.

---

## Prior Task: Phase 19d — Re-analyze with Model Selector + Font Fix + Deploy (COMPLETED)

**Goal:** Add re-analyze button with model selection (Haiku vs Sonnet), fix all fonts to Consolas, deploy everything as v=42.

### Re-analyze with Model Selector

**Backend changes:**
1. `llm_client.py`: Add `model` parameter to `analyze_match_build()` and `analyze_live_build()` — override the global MODEL constant per-call
2. `app.py`: Accept `model` and `force` params in POST `/api/matches/<match_id>/analyze` — when `force=true`, skip cache and re-run LLM. Pass `model` through to `llm_client`. Store `model` in the analysis JSON and in the DB `model` column.

**Frontend changes:**
1. When analysis already exists, show a "Re-analyze" button in the analysis header
2. Clicking "Re-analyze" shows a small inline model picker with two options:
   - Haiku (Fast, $) — `claude-haiku-4-5`
   - Sonnet (Smarter, $$) — `claude-sonnet-4-5`
3. Selecting a model triggers the POST with `force: true, model: "selected-model"`
4. Show which model produced the current analysis (small tag in header)
5. Lock/dedup still applies — re-analyze acquires the lock and replaces cached result

### Font Fix
- Changed `--font-display` from Rajdhani to Consolas (same as `--font-mono`)
- Removed Google Fonts `<link>` imports from index.html
- Entire app now uses Consolas monospace

### Prior Phase 19c changes (coded, awaiting deploy)
- Arrow visibility, instant LLM load, hide empty panels, timeline API, auto-refresh ranks, game notes rework, valid items filter, system prompt, boot ordering, spacing fixes

---

## Prior Task: Phase 19c-final — Deploy Remaining Fixes (COMPLETED IN CODE)

**Goal:** Deploy three remaining fixes from Phase 19c:
1. [DONE] Fuzzy item name matching (`_normalizeItemName()`) — already coded, needs deploy
2. [IN PROGRESS] Fix arrow visibility between items in live build bar (CSS fix)
3. [IN PROGRESS] Instant LLM load — send cached build recommendation as early SSE event before player data loads

### Implementation Details

**Arrow Visibility Fix (CSS):**
- `.live-build-arrow` uses `color: var(--text-dim)` and `font-size: 0.85rem` — too dim/small
- Fix: use a brighter purple color (`#7c5cbf`), larger font, and `›` HTML entity is fine

**Instant LLM Load (Architecture Change):**
- Current: LLM only fires after `_build_live_game()` completes (all player data fetched)
- New: In the `generate()` SSE function, after spectator API check confirms game exists, immediately check `live_analysis` DB cache by game_id and send an early `cached_build` SSE event
- The `_build_live_game()` already calls `_api.get_active_game(puuid)` as its first step which returns `gameId` — we need to do a lightweight spectator check BEFORE starting the full build thread
- Frontend: handle `cached_build` event that arrives before `result` — render the build bar immediately, even before the prediction panel exists. When `result` arrives and `renderLiveGame()` runs, it should NOT clobber the already-rendered build bar
- After `result` arrives with full data, if no cached build existed, the existing `build_recommendation` SSE flow continues as before

### Timeline API for Build Order (New Feature):
- Add `get_match_timeline()` to `riot_api.py` — single API call: `GET /lol/match/v5/matches/{matchId}/timeline`
- When user clicks "Analyze Build", fetch timeline (if not already cached)
- Parse `ITEM_PURCHASED` events for the player — extract item IDs + frame timestamps
- Pass actual build order to the LLM prompt so it can critique sequencing
- Frontend: show "Your Build Order: A → B → C" vs "Recommended: B → A → C"
- Store timeline in DB (or cache in match data) so it's only fetched once per match

### Auto-Refresh Ranks on Dashboard Load:
- When dashboard/profile loads, auto-trigger rank refresh in background (like showAccountDetail auto-fetches matches)
- Show cached data instantly, then update UI when rank refresh completes
- Remove the "Refresh Ranks" button since it's now redundant
- Frontend: `loadProfile()` should fire a background `POST /api/profiles/<id>/refresh` after rendering cached data
- Show a subtle indicator while refreshing (e.g., dim the rank badges or show a small spinner)

## Previous Task: Phase 19c — Live Game Caching + LLM Quality Fixes [DONE]

### Changes

**Backend (app.py):**
- Add `_live_game_cache` dict: `{game_id: {"result": dict, "timestamp": float}}` with 10-minute TTL
- In `_build_live_game()`: after building result, cache it by game_id
- In SSE generator: before running `_build_live_game()`, check cache first — instant return
- When lock is held by another request: block (with timeout), then return cached result
- Remove the "already in progress" error path entirely

**Backend (llm_client.py):**
- `build_prompt()` and `build_pregame_prompt()`: accept item_names list parameter
- Add `VALID ITEMS:` section to both prompts with all current-patch completed item names
- Add instruction: "ONLY recommend items from the VALID ITEMS list"
- `app.py`: pass item names from Data Dragon `item_map` to both prompt builders

**Frontend (app.js):**
- Post-game `_renderLlmAnalysis()`: render recommended items as `<img>` icons instead of text tags
- Live `_renderLiveBuildRecommendation()`: same — icons instead of text
- Build `nameToItemId` reverse map from cached item data for name→icon resolution
- Ensure item tooltip system works on recommended item icons
- Fallback to text tag if item name doesn't resolve to an ID (handles edge cases)

## Previous Task: Phase 19b — Live Game LLM Build Recommendation [DONE]

**Goal:** When a live game is found, auto-trigger an LLM build recommendation for the searched player based on the draft (champions, roles, ranks). No items exist yet (game hasn't started), so the prompt focuses on champion matchups and team comps. Results are cached in DB, sent as a follow-up SSE event so the main result isn't delayed, and cross-referenced in post-game expanded views.

### Architecture
- **Trigger**: Automatic after live game prediction completes (no button click needed)
- **SSE Pattern**: Main result sent immediately, then `build_recommendation` SSE event follows when LLM finishes
- **Cache**: `live_analysis` table — one row per (game_id, puuid)
- **Lock**: `task_lock("live_analysis", game_id)` prevents duplicate LLM calls
- **Cross-reference**: Post-game expanded view checks for pre-game recommendation via game_id (match_id = "NA1_" + game_id)

### Changes
1. **database.py**: Add `live_analysis` table, `get_live_analysis()`, `save_live_analysis()`
2. **llm_client.py**: Add `build_pregame_prompt()` + `analyze_live_build()` — draft-only context
3. **app.py**: After `_build_live_game()` returns result, fire LLM in background thread, send `build_recommendation` SSE event; add `GET /api/live-analysis/<game_id>` endpoint
4. **app.js**: Listen for `build_recommendation` SSE event, render recommendation UI below prediction; in post-game expanded view, check for pre-game recommendation
5. **style.css**: Styles for live build recommendation panel

### Prompt Design (Pre-Game)
Input:
- Your champion + role
- Your team: champions + roles + ranks
- Enemy team: champions + roles + ranks
- No items (game hasn't started)

Output JSON:
- `recommended_build_order`: [{item, reason}] — 6 items in priority order
- `boots`: {item, reason}
- `first_back_priority`: "What to buy on first recall"
- `key_matchup_notes`: ["Notes about specific matchups affecting item choices"]
- `synergy_notes`: ["How team comp affects your build"]

## Previous Task: Phase 19a — Post-Game LLM Match Build Analysis [DONE]

**Goal:** When a user expands a match and clicks "Analyze Build", call Claude Haiku to generate a context-aware item build recommendation based on the actual enemy team comp, teammate synergies, and items purchased by all players. Results are cached in DB so duplicate calls never happen.

### Architecture
- **LLM**: Claude Haiku 3.5 via Anthropic API (`anthropic` Python SDK)
- **API Key**: `ANTHROPIC_API_KEY` env var (same pattern as RIOT_API_KEY)
- **Cache**: `match_analysis` table — one row per (match_id, puuid), stores JSON recommendation
- **Lock**: `task_lock("analysis", f"{match_id}:{puuid}")` — prevents duplicate LLM calls
- **Trigger**: User clicks "Analyze Build" button in expanded match panel
- **Scope**: Itemization only (no gameplay/strategy tips)

### Prompt Design
Input to LLM:
- Your champion + role + items you built
- Your teammates' champions + roles + items
- Enemy team champions + roles + items they built
- Game duration (context for build completeness)

Output: JSON with fields:
- `recommended_items`: ordered list of item names with reasoning
- `situational_swaps`: conditional item changes based on enemy comp
- `synergy_notes`: how your build should interact with teammate kits
- `verdict`: one-line summary of actual build quality

### Build Audit Upgrade
- When LLM analysis is cached, build audit uses it instead of static guide
- If no LLM analysis, falls back to existing guide-based audit
- Audit accounts for actual enemy items (e.g., no armor bought → LDR not needed)

### Changes
1. **database.py**: Add `match_analysis` table, get/save functions
2. **llm_client.py**: New module — Anthropic SDK wrapper, prompt builder, response parser
3. **app.py**: New endpoint `POST /api/matches/<id>/analyze` with lock+cache pattern
4. **app.js**: "Analyze Build" button in expanded match, display recommendation, upgrade build audit
5. **style.css**: Styles for recommendation display
6. **requirements.txt**: Add `anthropic` package
7. **Docker**: Add `ANTHROPIC_API_KEY` env var

### Previous Task: Profile Selection Landing Page

**Goal:** When the site loads, show a profile selection page instead of auto-loading
the last-used profile. Users pick their profile from a card grid.

### Changes:
1. **Backend** - `GET /api/profiles` returns account_count per profile
2. **HTML** - Add `#profile-select-view` section in dashboard view (profile cards grid + create button)
3. **JS** - Remove localStorage auto-load. On init, show profile selection grid. Clicking a card loads that profile. Dropdown still works for quick switching. Nav brand click returns to profile selection.
4. **CSS** - Style profile selection cards (name, account count, click to enter)

## Overview

LolTracker is a League of Legends multi-account tracker that lets summoners:
1. **Track multiple ranked accounts** - See all your accounts' ranks at a glance
2. **Cross-account aggregated statistics** - "What's my best Caitlyn build across all 3 accounts?"
3. **Live game lookup with win prediction** - Look up a live game, predict the winner, store the prediction, and later show whether it was right
4. **Match history per account** - Recent ranked games with full stats

## Architecture

### Tech Stack
- **Backend:** Python 3.12 + Flask (matches duodetector patterns)
- **Frontend:** Vanilla JS single-page app (matches duodetector patterns)
- **Database:** SQLite (lightweight, file-based, perfect for Unraid Docker volume)
- **Server:** Gunicorn + gevent workers (for SSE streaming, matches duodetector)
- **Deployment:** Docker on Unraid, Cloudflare Tunnel via `tunnel-net`

### Why SQLite Instead of JSON Caches
Unlike duodetector (simple cache needs), LolTracker has relational data:
- Accounts belong to profiles
- Matches have participants, items, builds
- Predictions reference matches and have outcomes
- Aggregated stats need SQL GROUP BY queries across accounts

SQLite gives us real queries without adding infrastructure (no Postgres/MySQL container needed).

## Data Model

### Tables

```
profiles
  id              INTEGER PRIMARY KEY
  name            TEXT NOT NULL          -- user-chosen profile name
  created_at      TIMESTAMP

accounts
  id              INTEGER PRIMARY KEY
  profile_id      INTEGER FK -> profiles
  puuid           TEXT UNIQUE NOT NULL
  game_name       TEXT NOT NULL          -- Riot ID name
  tag_line        TEXT NOT NULL          -- Riot ID tag
  summoner_id     TEXT                   -- for league/rank API
  region          TEXT DEFAULT 'na1'
  last_updated    TIMESTAMP

ranks
  id              INTEGER PRIMARY KEY
  account_id      INTEGER FK -> accounts
  queue_type      TEXT NOT NULL          -- RANKED_SOLO_5x5, RANKED_FLEX_SR
  tier            TEXT                   -- IRON..CHALLENGER
  rank            TEXT                   -- I, II, III, IV
  lp              INTEGER
  wins            INTEGER
  losses          INTEGER
  updated_at      TIMESTAMP

matches
  id              INTEGER PRIMARY KEY
  match_id        TEXT UNIQUE NOT NULL   -- NA1_xxxxx
  game_start      TIMESTAMP
  game_duration   INTEGER               -- seconds
  game_version    TEXT
  queue_id        INTEGER

participants
  id              INTEGER PRIMARY KEY
  match_id        TEXT FK -> matches.match_id
  puuid           TEXT NOT NULL
  champion_id     INTEGER
  champion_name   TEXT
  team_id         INTEGER               -- 100 or 200
  position        TEXT                   -- TOP, JUNGLE, MIDDLE, BOTTOM, UTILITY
  win             BOOLEAN
  kills           INTEGER
  deaths          INTEGER
  assists         INTEGER
  cs              INTEGER               -- totalMinionsKilled + neutralMinionsKilled
  gold            INTEGER
  damage          INTEGER               -- totalDamageDealtToChampions
  vision_score    INTEGER
  summoner1_id    INTEGER
  summoner2_id    INTEGER
  item0-item6     INTEGER (7 columns)
  perk_primary    INTEGER               -- keystone rune
  perk_sub        INTEGER               -- secondary tree

predictions
  id              INTEGER PRIMARY KEY
  match_id        TEXT                   -- could be live game id or match id
  game_id         TEXT                   -- spectator gameId
  predicted_team  INTEGER               -- 100 or 200
  confidence      REAL                  -- 0.0 to 1.0
  prediction_factors TEXT               -- JSON blob with reasoning
  outcome         TEXT                   -- 'correct', 'incorrect', 'pending'
  resolved_at     TIMESTAMP
  created_at      TIMESTAMP
```

## API Routes

```
GET  /                              Serve SPA
GET  /riot.txt                      Riot API domain verification

# Profile Management
POST /api/profiles                  Create a new profile
GET  /api/profiles                  List all profiles
GET  /api/profiles/<id>             Get profile with accounts + ranks
DELETE /api/profiles/<id>           Delete profile

# Account Management
POST /api/profiles/<id>/accounts    Add account to profile (by Riot ID)
DELETE /api/accounts/<id>           Remove account from profile
POST /api/accounts/<id>/refresh     Refresh rank data for one account

# Ranks (bulk)
POST /api/profiles/<id>/refresh     Refresh all account ranks in profile
GET  /api/profiles/<id>/ranks       Get all ranks for all accounts in profile

# Match History
GET  /api/accounts/<id>/matches     Get recent matches (fetches + caches)
GET  /api/profiles/<id>/matches     Get recent matches across all accounts

# Aggregated Stats
GET  /api/profiles/<id>/stats                    Overall aggregated stats
GET  /api/profiles/<id>/stats/champions           Per-champion stats across accounts
GET  /api/profiles/<id>/stats/champions/<name>    Deep stats for one champion (builds, runes, etc.)

# Live Game
GET  /api/accounts/<id>/live        Check if account is in a live game
GET  /api/live-game/<puuid>         Get live game details + prediction (SSE)

# Predictions
GET  /api/predictions               List recent predictions with outcomes
GET  /api/predictions/<id>          Get one prediction detail
POST /api/predictions/<id>/resolve  Check if prediction game ended, resolve outcome
```

## Frontend Pages/Views

Single-page app with view switching (no router library needed):

1. **Dashboard View** (default)
   - Profile selector/creator at top
   - Grid of account cards showing: name, rank icon, tier/LP, win rate
   - "Refresh All" button
   - Quick stats bar: total games, overall WR, best champion

2. **Account Detail View**
   - Click an account card -> shows match history
   - Each match row: champion icon, KDA, items, CS, damage, win/loss
   - Filter by champion, queue type

3. **Champion Stats View**
   - Aggregated stats across all accounts for each champion
   - Click a champion -> deep dive: most common build paths, runes, win rates by item
   - "Best Caitlyn build" = most frequent item combination with highest win rate

4. **Live Game View**
   - Enter Riot ID or click "Check Live Game" on an account
   - Shows both teams with ranks, champion picks, summoner spells
   - Win prediction with confidence bar and reasoning
   - After game ends: shows whether prediction was correct

5. **Predictions History View**
   - Table of past predictions: date, teams, predicted winner, actual winner, correct/incorrect
   - Overall prediction accuracy stats

## Win Prediction Algorithm

Simple but effective heuristic-based prediction (no ML needed):

**Factors scored per team:**
1. **Rank Score** (weight: 40%) - Convert each player's rank to numeric (Iron4=0, Challenger=28), average per team
2. **Champion Win Rate** (weight: 25%) - Each player's win rate on their picked champion (from their recent matches)
3. **Recent Form** (weight: 20%) - Each player's win rate in last 10 games
4. **Champion Mastery Proxy** (weight: 15%) - Number of games on champion in recent history (experience indicator)

Score each team 0-100, predict the higher-scoring team wins. Confidence = score difference / max possible difference.

## Implementation Order

### Phase 1: Core Infrastructure
1. Project scaffolding (Flask app, SQLite setup, Riot API client)
2. Riot API client (port from duodetector with additions)
3. Database schema + models

### Phase 2: Profile & Account Management
4. Profile CRUD API
5. Account linking (Riot ID -> puuid resolution)
6. Rank fetching and display

### Phase 3: Match History & Stats
7. Match history fetching + storage
8. Per-account match history display
9. Cross-account champion stats aggregation

### Phase 4: Live Game & Predictions
10. Live game lookup
11. Win prediction algorithm
12. Prediction storage + resolution
13. Prediction history display

### Phase 5: Frontend Polish
14. Dashboard with account cards
15. Champion deep-dive stats (build paths)
16. Responsive dark theme (match duodetector aesthetic)

### Phase 6: Deployment
17. Dockerfile + docker-compose.yml
18. Unraid XML template
19. Cloudflare Tunnel integration

## Key Patterns from DuoDetector to Reuse
- Rate limiter (dual-window token bucket) from riot_api.py
- Riot API client structure with retry logic
- SSE streaming for long operations
- Dark theme CSS patterns
- Data Dragon CDN URLs for all images
- CommunityDragon for rank icons
- Summoner spell mappings
- Champion position data
- ThreadPoolExecutor for parallel API calls
- Atomic file writes (write .tmp then os.replace)
- op.gg linking pattern

## Phase 2 Features (v2) — Implementation Details

### 1. Edit Profile Name [IMPLEMENTING]
**Backend:** PATCH /api/profiles/<id> with `{"name": "new name"}`
- Add `update_profile_name(profile_id, name)` to database.py
- Add PATCH route to app.py

**Frontend:**
- Click profile name in dashboard header -> opens edit modal (reuses modal system)
- Also add edit icon (pencil) next to profile dropdown in nav
- After edit, update profileSelect option text + profileNameDisplay

### 2. Champion Page Filters [IMPLEMENTING]
**Backend:** GET /api/champion-positions -> returns name->position mapping
- Need a champion_id -> champion_name mapping (from Data Dragon or from DB)
- Actually: champion stats already come from DB with champion_name. We can add position data to champion stats response by looking up champion_id in CHAMPION_POSITIONS

**Frontend:**
- Role filter buttons (All / Top / Jungle / Mid / Bot / Support) above champion grid
- Search bar (text input) next to role filters
- Both combine: role AND name filter
- Client-side filtering of already-loaded champion data (no extra API calls)

### 3. Win Prediction Transparency [IMPLEMENTING]
**Backend:** Extend _predict_winner to include per-player factor data
- For each player, include: rank_score, champion_wr, recent_form, champion_exp
- Include per-team averages for each factor
- Include weight labels
- Store in prediction.factors JSON

**Frontend:**
- Expandable "Factor Breakdown" section in prediction panel
- Per-team average for each factor with visual bars
- Per-player detail rows showing individual factor values

### 4. Dashboard Account Ordering [DONE]

**Frontend-only:**
- Default sort: highest rank first (Challenger > Iron > Unranked)
- Drag-and-drop via HTML5 drag API on account cards
- Custom order saved in localStorage per profile

### 5. Delete Profile [DONE]
- Red "Delete Profile" button in edit modal
- Two-step confirmation (click -> "Are you sure?" -> click again)
- Auto-resets after 4 seconds

## Phase 3 Features (v3) — Post-Game Analytics [ALL DONE]

### Design Decisions
- Retroactive predictions use current player data (not historical snapshots)
- Store both extended stat columns (fast queries) AND raw match JSON (flexibility)
- Item tooltips fetched from Data Dragon and cached in memory (no rate limits on DDragon CDN)

### 1. Extended Match Data Storage [DONE]
**DB Migration:**
- Add to `participants`: damage_taken, heal_total, heal_allies, time_cc,
  pentakills, quadrakills, triplekills, double_kills, first_blood,
  first_blood_assist, turret_kills, inhibitor_kills, wards_placed,
  wards_killed, largest_killing_spree, largest_multi_kill,
  total_time_dead, champion_level
- Add to `matches`: raw_json TEXT (full Riot API response)
- Migration: ALTER TABLE ADD COLUMN with defaults for existing rows
- Re-fetch existing matches to backfill raw_json on demand

**store_match update:**
- Extract and save all new stat columns from match data
- Store raw JSON blob in matches.raw_json

### 2. Full Match Detail Endpoint [DONE]
`GET /api/matches/<match_id>/detail`
- Returns all 10 participants with full stats
- Includes computed stats: CS/min, damage share %, KP (kill participation)
- Includes team-level aggregates (total kills, total damage, objectives)

### 3. Retroactive Match Prediction [DONE]
`GET /api/matches/<match_id>/prediction`
- Fetches current rank data for all 10 participants
- Runs same prediction algorithm as live game
- Returns predicted winner, confidence, factor breakdown, actual outcome
- Caches result in a new `match_predictions` table

### 4. Item Tooltips [DONE]
`GET /api/items`
- Fetches item data from Data Dragon (item.json)
- Returns {id: {name, description, gold, image}} map
- Cached in memory (items don't change within a patch)
- Frontend: tooltip on item hover showing name + cleaned description

### 5. Post-Game Expanded View (Frontend) [DONE]
- Click any match row -> expands inline to show full game
- Layout similar to live game view (two teams, players in rows)
- Per-player stats: KDA, damage, damage taken, healing, CS/min, vision, items
- Team stat comparison bars (total damage, total gold)
- Prediction panel with factor breakdown + correct/incorrect badge

## Phase 3b — Prediction View Improvements

### Bug Fix: Retroactive predictions leaking into live predictions table
- `_predict_winner()` calls `db.create_prediction()` when called from the retroactive
  endpoint because `existing_pred` is None. Fix: add `save=True` parameter to
  `_predict_winner` so the retroactive endpoint can call it with `save=False`.
- Clean up junk predictions (IDs with "#" broken player names).

### 1. Prediction Row Click-to-Expand
- Click a resolved prediction row -> expand inline showing full post-game detail
- Uses existing `GET /api/matches/<match_id>/detail` (via `resolved_match_id`)
- Shows all 10 players, team comparison bars, items with tooltips

### 2. Highlight Current Profile's Accounts
- When rendering prediction player lists, cross-reference against current profile's
  account names (game_name#tag_line)
- Highlighted accounts get a distinct visual treatment (gold accent, bold)
- Applied in both the prediction row summary AND the expanded post-game detail

### 3. Team Metrics on Resolved Predictions
- After resolution, show team KDA and gold in the prediction row itself
- Fetched from match detail data (already available via resolved_match_id)

### 4. Factor Breakdown on All Prediction Views
- Both the expanded match view (retroactive prediction) and prediction history rows
  should show the full factor breakdown (rank score, champion WR, recent form,
  champion exp weights + per-player scores)
- Reuse the existing `pred-factors` UI pattern from the live game view

## Phase 3c — Bug Fixes & Match Backfill

### DB State (as of 2026-03-05)
```
| DB             | Matches | With raw_json | Participants | Missing game_name |
|----------------|---------|---------------|--------------|-------------------|
| Dev (local)    | 285     | 18            | 2856         | 2676              |
| Prod (Unraid)  | 267     | 0             | 2676         | 2676              |
```

Production DB path: `/mnt/user/appdata/loltracker/data/loltracker.db`
Access via: `ssh root@192.168.1.100`, then `docker exec tracker python3 ...`
No python3 on Unraid host — must use `docker exec tracker` for DB operations.

### Bug 1: Item tooltip shows gold/plaintext instead of full description [VERIFIED OK]
**Root cause**: The `/api/items` endpoint returns `{description: plaintext, full_description: html}`.
Frontend tooltip code (app.js:1793) already prefers `full_description`:
`const rawDesc = item.full_description || item.description || ""`
**Diagnosis needed**: Verify what the API actually returns — the field may be empty or the
HTML stripping may be too aggressive. Check Data Dragon response.

### Bug 2: Expanded game view items cut off by grid [DONE]
**Root cause**: `.expand-player-row` grid has `1fr` for items column, but 7 items at 24px
each = 168px + gaps. The `1fr` may collapse below that if other columns are wide.
**Fix**: Set `min-width` on items column or use `minmax(180px, 1fr)` in the grid template.

### Bug 3: Match history shows champion name instead of summoner name [DONE]
**Root cause**: `game_name`/`tag_line` columns empty for 2676/2856 participants (93%).
Only 18 matches have `raw_json` for backfill (dev), 0 on prod.
`store_match` already saves `riotIdGameName`/`riotIdTagline` for new matches.
**Fix strategy**:
1. Immediate: In match list, show "champion_name" is fine (it's the player's champion).
   In expanded view, where we show "player name" under champion, fall back gracefully.
2. Add a backfill endpoint/worker that re-fetches match data from Riot API to populate
   both `raw_json` and `game_name`/`tag_line` for existing participants.
3. This naturally aligns with Feature 6 (season backfill).

### Bug 4: Prediction factor table missing column headers + player names [DONE]
**Root cause**: `renderPredFactorBreakdown` (app.js:1686-1708) renders per-player rows
but the per-player section has no column header row (Factor labels are only on the
team-average section). Player rows show champion name but not summoner name.
**Fix**: Add a header row above per-player rows with: Player | Champion | Rank | Champ WR |
Form | Exp. Show player name (from factors.player_factors[teamId][i].name) in each row.

### Feature 5: Highlight 60%+ champion WR players [DONE]
Visual accent (e.g. green tint or WR badge) on players whose champion_wr >= 60 in the
factor breakdown and expanded game views.

### Feature 6: Season selector + background match backfill worker [DONE]
**Endpoint**: `POST /api/profiles/<id>/backfill` or `POST /api/accounts/<id>/backfill`
- SSE streaming progress updates
- Fetches match history going back to season start
- Re-fetches existing matches missing raw_json to backfill names + raw data
- Configurable: season start timestamp, max matches
- Rate-limit aware: 100 req/2min budget means ~50 matches/min (each match = 1 match-v5 call)
- Must run on BOTH dev and prod DBs
**Frontend**: Season dropdown, "Backfill" button with progress bar, ETA display

## Phase 4 — Live Game Indicators on Dashboard

### Goal
Show a pulsing "LIVE" indicator on account cards when the player is currently in a game.
Add a quick "Live" button that navigates to the Live Game Lookup view with that player
pre-filled and auto-searched.

### Backend
1. **`GET /api/profiles/<id>/live-status`** — Batch check all accounts in a profile
   - Uses ThreadPoolExecutor to check `get_active_game(puuid)` for all accounts in parallel
   - Returns `{ account_id: { active: bool, game_id: int|null } }` for each account
   - Timeout per call: 10s (spectator API can be slow)

### Frontend
1. **Live indicator on account cards** — When rendering cards, after data loads, poll
   `/api/profiles/<id>/live-status` and overlay a pulsing "LIVE" badge on active cards
2. **"Live" button** — When an account is live, show a button on the card that:
   - Switches to the Live Game view (`showView("live")`)
   - Pre-fills the riot ID input with the account's `game_name#tag_line`
   - Auto-triggers `doLiveSearch(puuid)` to load the live game immediately
3. **Polling** — Re-check live status every 60 seconds while on the dashboard view
   - Stop polling when leaving dashboard
   - Re-poll immediately on profile load or Refresh Ranks completion

### CSS
- `.live-badge` — Pulsing red dot + "LIVE" text, positioned top-right of account card
- `.live-btn` — Small button that appears when live, styled with game-active accent
- `@keyframes pulse` — Smooth pulse animation for the live dot

## Phase 5 — Duo Detection (ported from DuoDetector)

### Goal
Integrate duo detection from the standalone duodetector app. Show duo badges on:
1. Match history rows (auto-scanned top-to-bottom in background)
2. Expanded post-game views (when expanding a match row)
3. Live game views (during live game lookup)

### Algorithm (from duodetector)
- For each team, fetch last 20 match IDs per player (general, not champion-filtered)
- For historical matches, use `end_time` = game creation timestamp (only look at prior games)
- Two players on the same team are flagged as a duo if they share >= 2 recent match IDs
- Duo winrate: fetch details of shared matches, count wins when both on same team

### Backend

1. **`GET /api/matches/<match_id>/duos`** — Duo detection for a single historical match
   - Reads participants from `raw_json` (stored in matches table) or from participants table
   - Fetches 20 recent match IDs per player (before the match timestamp) in parallel
   - Does set intersection for same-team pairs
   - Returns `{ duos: [ { players: [puuid1, puuid2], shared_matches: N, duo_winrate: {wins, games, winrate} } ] }`
   - Rate-limit aware: ~20 match ID fetches + shared match detail fetches
   - Results cached in a `duo_cache` table (match_id -> JSON, never changes for historical)

2. **Live game duo detection** — Integrate into `_build_live_game()`
   - After fetching champion winrates (which already fetches match IDs), reuse the general
     match ID data to also detect duos
   - Add `duos` array to each team in the live game response
   - Minimal extra API calls since match IDs are already being fetched

### Frontend

1. **Match history rows** — Background duo scanner:
   - After match list renders, start scanning matches top-to-bottom
   - For each match, call `GET /api/matches/<match_id>/duos`
   - Cache results in `duoCache` Map (match_id -> duos)
   - Show duo badge on the match row if any duos found involving the tracked player
   - When next page loads, scan those new matches too
   - Scanner runs even if user navigates away (completes in background)

2. **Expanded post-game view** — Show duo badges on player rows:
   - Use cached duo data (already scanned) or fetch on-demand
   - Color-coded DUO badges matching duodetector styling (duo-1 through duo-4)
   - Show "DUO (N games)" + "Together: X% WR" per duo pair

3. **Live game view** — Show duo badges on player cards:
   - Data comes in the live game SSE response (no extra fetch needed)
   - Same color-coded DUO badges as historical view

### CSS
- `.duo-badge` — Colored duo indicator: "DUO (N)" with team-specific colors
- `.duo-wr-badge` — "Together: X% (NW NL)" sub-badge
- Four duo color classes: `.duo-1` (amber), `.duo-2` (purple), `.duo-3` (emerald), `.duo-4` (pink)
- Match row duo indicator: small colored dot or "DUO" pill next to player info

### Database
- `duo_cache` table: `match_id TEXT PRIMARY KEY, duo_json TEXT, created_at TIMESTAMP`
- Stores serialized duo detection results per match (historical matches never change)

## Phase 6 — Global Live Game Notification Bar

### Goal
Persistent notification bar below the nav that shows when ANY tracked account (across ALL
profiles) is in a live game. Visible on every page, not just the dashboard. Clicking it
auto-navigates to Live Game view and auto-submits the lookup — zero extra clicks.

### Backend
1. **`GET /api/all-live-status`** — Check live status across ALL profiles
   - Fetches all accounts from all profiles, deduplicates by puuid
   - Checks `get_active_game(puuid)` in parallel
   - Returns `{ puuid: { active: bool, game_name, tag_line, game_id } }`
   - Used by the global poll (replaces per-profile dashboard polling)

### Frontend
1. **Global live notification bar** — HTML element below `<nav>`, always present
   - Hidden by default, slides down when a player is detected in-game
   - Shows: "{PlayerName} is in a game — Watch Live" per active player
   - Clicking auto-switches to Live view, fills riot ID, calls `doLiveSearch(puuid)`
   - Multiple players = multiple notification rows or a combined bar

2. **Global polling** — Replaces dashboard-only `liveStatusTimer`
   - Polls `GET /api/all-live-status` every 60 seconds, runs on ALL pages
   - Starts on page load, never stops (except maybe when on Live view already watching)
   - Auto-dismisses notifications when player is no longer in game on next poll
   - Also feeds dashboard card LIVE badges (reuses same poll data)

3. **Dashboard LIVE badges** — Still show on account cards, but driven by global poll data
   instead of a separate per-profile poll

### CSS
- `.live-notification-bar` — Fixed below nav, gold/amber accent, slide-down animation
- `.live-notification-item` — Per-player notification row with pulsing dot + click handler

## Phase 7 — Per-Season Rank History on Account Cards

### Goal
When user switches the season dropdown, account card rank displays should change to show
the **peak rank achieved** during that season, instead of always showing the current live
rank. Current season still shows live rank from Riot API.

### Problem
Currently, `ranks` table stores exactly ONE row per account per queue type (UNIQUE constraint).
Every refresh overwrites it with the current live rank. No historical rank data exists.
The Riot match-v5 API does not include rank data in match responses, so we can't extract
it from stored matches retroactively.

### Solution: `rank_history` table
Track rank snapshots over time. Every time we refresh ranks from Riot API, also insert a
timestamped row in `rank_history`. Then query peak rank per season from this table.

### Database
```
rank_history
  id              INTEGER PRIMARY KEY AUTOINCREMENT
  account_id      INTEGER NOT NULL FK -> accounts
  queue_type      TEXT NOT NULL       -- RANKED_SOLO_5x5, RANKED_FLEX_SR
  tier            TEXT                -- IRON..CHALLENGER
  rank            TEXT                -- I, II, III, IV
  lp              INTEGER DEFAULT 0
  wins            INTEGER DEFAULT 0
  losses          INTEGER DEFAULT 0
  recorded_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP
  FOREIGN KEY (account_id) REFERENCES accounts(id) ON DELETE CASCADE
```
- Index on `(account_id, queue_type, recorded_at)` for fast season range queries
- No UNIQUE constraint — multiple rows per account per queue expected

### Backend Changes

1. **`database.py`**:
   - Create `rank_history` table in `init_db()`
   - `insert_rank_history(account_id, queue_type, tier, rank, lp, wins, losses)` — inserts a snapshot
   - `get_peak_rank_in_season(account_id, queue_type, start_time, end_time)` — returns the
     highest rank recorded during the time window. Uses tier/rank ordering:
     Challenger > Grandmaster > Master > Diamond I > Diamond II > ... > Iron IV
   - Seed existing current ranks into rank_history on first init (one-time migration)

2. **`app.py`**:
   - After every `upsert_rank()` call, also call `insert_rank_history()` with same data
   - In `get_profile()`, when a non-current season is selected, attach `season_peak_ranks`
     per account (peak solo + flex for that season) alongside the existing `ranks` (live)
   - For current season, continue using live `ranks` as-is

3. **API response shape**:
   - `acct.ranks` — always the live rank (unchanged)
   - `acct.season_peak_ranks` — `[{queue_type, tier, rank, lp, wins, losses}]` for the
     selected season (only present when a non-current season is selected)
   - Frontend decides which to display based on season selection

### Frontend Changes

1. **`createAccountCard(acct)`**:
   - If `acct.season_peak_ranks` exists and is non-empty, use those for the rank display
     instead of `acct.ranks`. Add a small "PEAK" label to indicate it's historical.
   - If current season selected (or no peak data), show `acct.ranks` as before.
   - `renderRankRow()` gets an optional `isPeak` parameter to show "PEAK" badge.

### Rank Ordering (for peak calculation)
Tier numeric values (higher = better):
```
CHALLENGER=9, GRANDMASTER=8, MASTER=7, DIAMOND=6, EMERALD=5,
PLATINUM=4, GOLD=3, SILVER=2, BRONZE=1, IRON=0
```
Division numeric values (higher = better): I=4, II=3, III=2, IV=1
Composite score: tier * 5 + division + (lp / 1000)  [LP as tiebreaker]
For apex tiers (Master+), division is always 4 (treated as I).

### Backfill Strategy
- On first deploy, seed rank_history with each account's current rank (from `ranks` table)
  with `recorded_at = NOW`. This gives us a starting point.
- Going forward, every rank refresh adds a new snapshot.
- We cannot recover true historical peaks before this feature was deployed — the seed
  gives us at minimum the current rank as a baseline for the current season.

## Phase 8 — Op.gg Past Season Rank Scraper [DONE]

### Goal
Scrape past season ending ranks from op.gg and display them on account cards when
the user selects a past season from the dropdown. This gives us historical rank data
that Riot's API doesn't provide.

### Discovery (confirmed via testing)
- Op.gg embeds season rank data in RSC (React Server Components) payload inside
  `self.__next_f.push()` script blocks in the page HTML
- URL pattern: `https://www.op.gg/summoners/na/{gameName}-{tagLine}` (# replaced with -)
- Data structure per season: `{"season":"S2025 ","rank_entries":{"high_rank_info":{"tier":"platinum 1","lp":"50"},"rank_info":{"tier":"gold 1","lp":"67"}}}`
- `rank_info` = ending rank, `high_rank_info` = peak rank (only recent seasons)
- Regex to extract: `"data":\[\{"season":"S202.+?\}\],"queueType":"TOTAL"`
- Tested successfully with Leon#NA420 — got history back to S4

### Season Key Mapping (op.gg → our keys)
```
"S2026 "/"S2026"   → "s2026"     (Current season)
"S2025 "/"S2025"   → "s2025"     (Season 2025)
"S2024 S3"         → "s2024_s3"  (S2024 Split 3)
"S2024 S2"         → "s2024_s2"  (S2024 Split 2)
"S2024 S1"         → "s2024_s1"  (S2024 Split 1)
```
Both op.gg and our keys now use Riot's calendar year naming convention.

### Database
```sql
CREATE TABLE IF NOT EXISTS season_ranks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    account_id INTEGER NOT NULL,
    season_key TEXT NOT NULL,        -- our season key: s2026, s2025, s2024_s3, etc.
    tier TEXT,                        -- GOLD, PLATINUM, etc.
    division TEXT,                    -- 1, 2, 3, 4
    lp INTEGER DEFAULT 0,
    peak_tier TEXT,                   -- peak rank tier (if available)
    peak_division TEXT,               -- peak rank division
    peak_lp INTEGER DEFAULT 0,
    source TEXT DEFAULT 'opgg',       -- where the data came from
    scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (account_id) REFERENCES accounts(id) ON DELETE CASCADE,
    UNIQUE(account_id, season_key)
);
```

### New Module: `opgg_scraper.py`
- `scrape_season_ranks(game_name, tag_line) -> list[dict]`
  - Fetches op.gg profile page
  - Parses RSC payload for season rank data
  - Maps op.gg season labels to our season keys
  - Returns list of `{season_key, tier, division, lp, peak_tier, peak_division, peak_lp}`
- Headers: modern User-Agent, Accept-Language to avoid Cloudflare blocks
- Timeout: 30s

### Backend Changes (app.py)
1. On account add: scrape op.gg for historical ranks, store in season_ranks
2. New endpoint: `POST /api/accounts/<id>/scrape-ranks` — re-scrape on demand
3. In `get_profile()`: attach `season_ranks` to each account from DB
4. Current season: still show live rank from Riot API (unchanged)
5. Past seasons: show ending rank from season_ranks table

### Frontend Changes (app.js)
1. In `createAccountCard()`: when a past season is selected, use `season_ranks`
   data for rank display (tier icon, tier text, division, LP)
2. `renderRankRow()`: accept season_rank data, show rank icon + tier/div/LP
3. Show "via op.gg" or similar subtle indicator so user knows it's scraped data

### Implementation Steps
1. Create `opgg_scraper.py` module
2. Add `season_ranks` table to `database.py`
3. Add DB functions: `upsert_season_rank()`, `get_season_ranks()`
4. Add scrape endpoint to `app.py` + integrate into account add flow
5. Update `get_profile()` to include season_ranks in response
6. Update frontend to display scraped rank data
7. Test end-to-end locally
8. Deploy to production

## Phase 9 — SEASONS Dict Fix + New Features [IMPLEMENTING]

### 9a. Fix SEASONS dict (keys off by one year) [DONE]

**Problem:** Every key in the SEASONS dict is off by one year. The timestamps are
for Riot Season 2024 splits and Season 2025, but the keys say 2025/2026.

Current (wrong):
```
s1_2026  start=Jan 8 2025  end=None      Actually = Riot Season 2025
s3_2025  start=Sep 25 2024 end=Jan 8 2025  Actually = Riot S2024 Split 3
s2_2025  start=May 14 2024 end=Sep 25 2024 Actually = Riot S2024 Split 2
s1_2025  start=Jan 8 2024  end=May 14 2024 Actually = Riot S2024 Split 1
```

Correct (rename to match Riot):
```
s2026     label="Current Season"   start=Jan 8, 2026   end=None
s2025     label="Season 2025"      start=Jan 8, 2025   end=Jan 8, 2026
s2024_s3  label="S2024 Split 3"    start=Sep 25, 2024  end=Jan 8, 2025
s2024_s2  label="S2024 Split 2"    start=May 14, 2024  end=Sep 25, 2024
s2024_s1  label="S2024 Split 1"    start=Jan 8, 2024   end=May 14, 2024
```

**Changes needed:**
1. `app.py`: Rename SEASONS keys + labels, update DEFAULT_SEASON, fix hardcoded
   fallback on line ~1970
2. `opgg_scraper.py`: Update OPGG_TO_SEASON_KEY values to new keys
3. DB migration: UPDATE season_ranks SET season_key = new_key WHERE season_key = old_key
4. `PLAN.md`: Update docs
5. Frontend: No code changes needed (all dynamic from backend)

### 9b. Auto-scrape on season switch [DONE]

When a user switches to a past season and an account has no scraped rank data,
fire a background scrape for that account and re-render when it returns.

**Backend:** `POST /api/accounts/<id>/scrape-ranks-if-missing`
- Checks if season_ranks exist (non-opgg_ keys)
- If not, scrapes from op.gg and returns the result
- If yes, returns existing data (no-op)

**Frontend:** In the season change handler, after loading profile, calls
`autoScrapeIfMissing()` which checks each account and fires scrape in background.

### 9c. Rank history snapshots [DONE]

- `rank_history` table with (account_id, queue_type, tier, rank, lp, wins, losses, recorded_at)
- `insert_rank_history()` called every time `_refresh_account_ranks()` runs
- `get_rank_history()` returns snapshots filtered by time range
- `seed_rank_history_from_current()` bootstraps existing ranks on first deploy
- `GET /api/accounts/<id>/rank-history?queue=X&season=Y` endpoint

### 9d. LP sparkline graph [DONE]

- SVG polyline sparkline rendered on account cards below rank display
- `rankToScore()` converts tier/division/LP to numeric score for Y axis
- `renderSparklineSVG()` generates inline SVG with polyline + last-point dot
- Color: green if trending up, red if trending down
- `loadSparklines()` called after dashboard renders, fetches rank-history per account
- Will populate over time as ranks are refreshed from Riot API

### 9e. Match history filters [DONE]

- Three filter dropdowns: Champion, Win/Loss, Queue Type
- `allLoadedMatches` array stores all matches loaded for current account
- `populateMatchFilters()` populates champion dropdown from loaded matches
- `applyMatchFilters()` filters client-side and re-renders match list
- Filter count indicator: "X of Y games"
- `queue_id` added to match API response for queue filtering

## Phase 10 — Extended Season History (S4 to S2023)

### Goal
Extend the SEASONS dict to cover all LoL ranked seasons from S4 (2014) through S2023,
so that op.gg scraped rank data for older seasons shows up on account cards. Currently
the SEASONS dict only goes back to S2024 Split 1, so seasons like S2023 S2, S2022, S9,
S5 etc. never appear in the card season history section.

### Problem
- Op.gg returns rank data going back to S4 for long-time players
- Our OPGG_TO_SEASON_KEY already maps S2020-S2023 to proper keys, but S4-S9 become `opgg_*`
- The SEASONS dict only has s2024_s1 through s2026 — older seasons are invisible on cards
- The season history on account cards iterates `allSeasons` (from SEASONS dict), so entries
  not in SEASONS never render

### Changes

1. **`app.py`**: Extend SEASONS dict with all historical seasons:
   - S2023 had 2 splits: S2023 S1 (Jan 10 2023 → Jun 2023), S2023 S2 (Jun 2023 → Jan 2024)
   - S2022 (Jan 7 2022 → Jan 10 2023) — single season, no splits
   - S2021 (Jan 8 2021 → Jan 7 2022)
   - S2020 (Jan 10 2020 → Jan 8 2021)
   - S9 / Season 2019 (Jan 23 2019 → Nov 19 2019)
   - S8 / Season 2018 (Jan 16 2018 → Nov 12 2018)
   - S7 / Season 2017 (Dec 7 2016 → Nov 7 2017)
   - S6 / Season 2016 (Jan 20 2016 → Nov 7 2016)
   - S5 / Season 2015 (Jan 21 2015 → Nov 11 2015)
   - S4 / Season 2014 (Jan 10 2014 → Nov 11 2014)

2. **`opgg_scraper.py`**: Add S4-S9 to OPGG_TO_SEASON_KEY mapping so they get
   proper keys instead of `opgg_*` prefixed keys

3. **DB migration**: Rename existing `opgg_s4` through `opgg_s9` entries to `s4`
   through `s9` in both dev and prod DBs. Also fix `s2023` → `s2023_s1` since
   op.gg returns "S2023 S1" for that split.

4. **Frontend**: The season history rendering already works if the season is in
   SEASONS dict — no JS changes needed. But we should NOT add old seasons to the
   season dropdown (only s2024+ are useful for match filtering). The old seasons
   are display-only in the card history section.

5. **API**: Separate "display seasons" (all, for card history) from "filter seasons"
   (recent, for dropdown). Or just send all and let frontend decide.

### Season Dates (approximate — only needed for ordering and display, not match filtering)
```
s4:        Jan 10 2014 – Nov 11 2014
s5:        Jan 21 2015 – Nov 11 2015
s6:        Jan 20 2016 – Nov 7 2016
s7:        Dec 7 2016 – Nov 7 2017
s8:        Jan 16 2018 – Nov 12 2018
s9:        Jan 23 2019 – Nov 19 2019
s2020:     Jan 10 2020 – Jan 8 2021
s2021:     Jan 8 2021 – Jan 7 2022
s2022:     Jan 7 2022 – Jan 10 2023
s2023_s1:  Jan 10 2023 – Jul 19 2023
s2023_s2:  Jul 19 2023 – Jan 10 2024
s2024_s1:  Jan 10 2024 – May 15 2024
s2024_s2:  May 15 2024 – Sep 25 2024
s2024_s3:  Sep 25 2024 – Jan 8 2025
s2025:     Jan 8 2025 – Jan 8 2026
s2026:     Jan 8 2026 – present
```

## Phase 11 — Performance & UI/UX Polish [IMPLEMENTING]

### Goal
Optimize backend query performance, improve frontend loading experience, and add
UI polish for a snappier, more polished feel.

### 11a. Fix get_profile() N+1 query explosion [HIGH]
**Problem**: `get_profile()` fires 50-100 DB queries for 5-10 accounts (per-account
per-season stats). With 17 seasons, most queries return empty results for old seasons.

**Fix**: Replace per-account-per-season loop with a single batch query that returns
all season stats for all accounts in one pass. Use `GROUP BY puuid, season_key` and
post-process in Python.

### 11b. Add lazy loading to images [HIGH]
**Problem**: Match list loads 160+ images eagerly (champion icons, item images per row).

**Fix**: Add `loading="lazy"` to all `<img>` tags generated in JS for champion icons,
item images, rank icons, and rune icons.

### 11c. Collapse season history on cards [HIGH]
**Problem**: With 15+ historical seasons, account cards get extremely tall. A player
active since S4 shows 15 rows (~360px) of season history.

**Fix**: Show only the 5 most recent seasons by default. Add a "Show N more" toggle
that expands to show all. Remember expanded state per session.

### 11d. Loading states for transitions [HIGH]
**Problem**: Season change, profile switch, and rank refresh have no loading indicators.
UI appears frozen during data fetch.

**Fix**:
- Add subtle loading overlay/fade on account cards during season change
- Show spinner on profile switch
- Show inline spinner on Refresh Ranks button

### 11e. View transition animations [MEDIUM]
**Problem**: Switching between Dashboard / Account Detail / Live Game / etc. is an
instant show/hide with no transition.

**Fix**: Add a brief CSS fade transition between views using opacity + transform.

### 11f. Smooth match panel expand/collapse [MEDIUM]
**Problem**: Expanding match details pops in with fadeInUp, but collapsing is instant
`.remove()` with no animation.

**Fix**: Add collapse animation (fade out + slide up) before removing the panel DOM.

### 11g. Add missing DB indexes [MEDIUM]
**Problem**: Several frequently-queried columns lack indexes.

**Fix**: Add indexes:
- `idx_participants_puuid_match` composite on `(puuid, match_id)`
- `idx_predictions_created` on `predictions(created_at)`
- `idx_matches_queue` on `matches(queue_id)`

### 11h. Fix rank_history time filter [MEDIUM]
**Problem**: `get_rank_history()` uses `strftime('%s', recorded_at)` which prevents
index usage. The composite index on `(account_id, queue_type, recorded_at)` can't be
used for the time range filter.

**Fix**: Store `recorded_at` as epoch integer instead of timestamp string, or change
the query to use direct string comparison (recorded_at >= '2025-01-08 00:00:00').

### 11i. Add gzip compression [MEDIUM]
**Problem**: 3,342-line JS and 3,176-line CSS served uncompressed.

**Fix**: Add Flask-Compress or a simple gzip middleware to compress responses.

### 11j. Basic accessibility [MEDIUM]
**Problem**: No ARIA attributes, no focus management, no keyboard navigation.

**Fix**: Add aria-labels to icon buttons, aria-live regions for toasts and live
notifications, focus trapping in modals, keyboard handlers for Escape to close.

## Phase 12 — Production API Key Readiness

### Goal
Address all Riot Games Developer Portal requirements to apply for a production API
key. This includes security hardening, rate limiter configurability, and ensuring
compliance with Riot's General Policies.

### Background (from Riot Developer Portal docs)
- **Development keys**: 20/1s + 100/2min, expire every 24 hours
- **Personal keys**: Same rate limits, no expiry, for private use only. Cannot run
  public-facing app on a personal key (even open alpha/beta).
- **Production keys**: 500/10s + 30,000/10min per region. Required for any public product.
- **Requirements**: Product must be registered, verified, and approved. Must benefit
  players (stat tracking, growth). Must not violate policies. Must be "quality" (working
  prototype required). API key must be properly secured (required by General Policies).
- **Domain verification**: `riot.txt` file served at root of domain (already done).

### Security Fixes Required

#### 12a. Create .dockerignore [HIGH — BLOCKING for production] [DONE]
**Problem**: `COPY . .` in Dockerfile copies `api.key` into every Docker image.
**Fix**: Create `.dockerignore` excluding `api.key`, `.env`, `*.db`, `data/`,
`__pycache__/`, `.opencode/`, `*.png`, `venv/`.

#### 12b. Remove api.key file fallback [HIGH — BLOCKING for production] [DONE]
**Problem**: `load_api_key()` falls back to reading `api.key` from disk. This is a
security risk — the key should ONLY come from environment variables in production.
**Fix**: Remove the file fallback. Only read from `RIOT_API_KEY` env var. Raise a
clear error if the env var is missing. Add key format validation (must start with
`RGAPI-`). Keep the file for local dev convenience by loading `.env` or similar,
but NEVER bake it into the Docker image.

#### 12c. Cap 429 retry depth [HIGH] [DONE]
**Problem**: `_get()` retries HTTP 429 responses recursively with no depth limit.
A persistently rate-limited key will hit Python's recursion limit (~1000 deep).
**Fix**: Add a `max_retries=10` cap for 429 responses. After 10 retries, raise
a clear exception instead of recursing infinitely.

#### 12d. Graceful error on missing API key [MEDIUM] [DONE]
**Problem**: If `RIOT_API_KEY` env var is not set, `load_api_key()` will raise an
unhandled `FileNotFoundError` (or `KeyError` after removing file fallback).
**Fix**: Raise `RuntimeError("RIOT_API_KEY environment variable is not set")` with
a clear message.

### Rate Limiter Upgrade

#### 12e. Configurable rate limiter [HIGH — needed for production key] [DONE]
**Problem**: Rate limiter is hardcoded to dev key limits (20/1s, 100/2min). A production
key has 500/10s + 30,000/10min — the hardcoded limiter would throttle to 1/50th of
available capacity.
**Fix**: Make `RateLimiter` accept configurable windows. Read limits from env vars:
- `RIOT_RATE_LIMIT_1` = "500:10" (requests:seconds) — default "20:1"
- `RIOT_RATE_LIMIT_2` = "30000:600" (requests:seconds) — default "100:120"
This way, upgrading to a production key only requires changing env vars, no code deploy.

### Policy Compliance

#### 12f. Riot legal disclaimer [REQUIRED by General Policies] [DONE]
**Requirement**: "You must post the following legal boilerplate to your product in a
location that is readily visible to players."
**Fix**: Added footer to index.html with the required disclaimer text:
> LolTracker isn't endorsed by Riot Games and doesn't reflect the views or opinions
> of Riot Games or anyone officially involved in producing or managing Riot Games
> properties. Riot Games, and all associated properties are trademarks or registered
> trademarks of Riot Games, Inc.

#### 12g. GDPR data deletion endpoint [REQUIRED by API Terms] [DONE]
**Requirement**: "When Riot Games receives a request from an end user to delete their
personal data, we will be passing the request to all active developers by sharing a
list of identifiers (e.g. accountId) for the end users."
**Fix**: Added `POST /api/gdpr/delete` endpoint that accepts `{"puuid": "..."}` or
`{"puuids": ["...", "..."]}`. Deletes:
- Account from accounts table (CASCADE handles ranks, season_ranks, rank_history)
- Participant rows from participants table
- Scrubs puuid from predictions JSON blobs (blue_players, red_players, factors)
- Scrubs puuid from matches.raw_json
- Removes stale duo_cache entries

#### 12h. Filter custom queue matches [REQUIRED by LoL Game Policy] [DONE]
**Requirement**: "Products may not publicly display a player's match history from the
custom match queue unless the player opts in."
**Fix**: Added `m.queue_id != 0` filter to all public match display queries:
- `get_matches_for_puuid()`
- `count_matches_for_puuid()`
- `get_matches_for_puuids()`
Note: We already only fetch queue 420/440 from Riot API, so custom matches don't
enter our DB in practice. This is belt-and-suspenders.

### Policies We Already Comply With

- **No MMR/ELO calculators**: Our win prediction is a fun heuristic, not an
  alternative ranking system. It does not track or display any form of MMR.
- **No de-anonymizing hidden players**: We only show data from Riot's public APIs
  for players in the current game or whose match history is public.
- **Game integrity**: We show stats to help players track growth (approved use case).
  We don't dictate decisions or track hidden info (e.g. enemy ult cooldowns).
- **No data brokering**: We don't resell or share API data with third parties.
- **SSL/HTTPS**: All Riot API calls are HTTPS. Site served via Cloudflare Tunnel (HTTPS).
- **One key per product**: Only LolTracker uses this key.
- **No betting/gambling**: Not applicable.
- **Not a game or IP violation**: We're a stat tracker, not a game.

### Application Checklist (for Riot Developer Portal registration)

**Technical:**
- [x] Working prototype deployed and publicly accessible
- [x] `riot.txt` domain verification file served at site root
- [x] API key secured (env var only, not in Docker image, not in source code)
- [x] `.dockerignore` prevents key from entering Docker images
- [x] Rate limiting with configurable windows (dev: 20/1s+100/120s, prod: 500/10s+30k/600s)
- [x] Proper 429 handling with Retry-After header + capped retries (max 10)
- [x] Proper 5xx retry with exponential backoff (1s, 5s, 10s)
- [x] GDPR data deletion endpoint (`POST /api/gdpr/delete`)
- [x] Custom queue matches excluded from public display

**Policy:**
- [x] Legal boilerplate displayed in site footer
- [x] Product benefits players (multi-account stat tracking, win predictions)
- [x] Does not create unfair advantage or alternative ranking system
- [x] Does not de-anonymize hidden players
- [x] Does not display hidden in-game information

**Registration (TODO — manual steps):**
- [ ] Register product on Riot Developer Portal (https://developer.riotgames.com)
- [ ] Fill out application form with product description and screenshots
- [ ] Verify domain ownership (riot.txt already deployed)
- [ ] Submit for review
- [ ] After approval, update Docker env vars with production key + rate limits:
      `RIOT_API_KEY=<new key>`
      `RIOT_RATE_LIMIT_1=500:10`
      `RIOT_RATE_LIMIT_2=30000:600`

## Phase 13 — Concurrent Request Deduplication

### Goal
Prevent duplicate background work when multiple users (or tabs) trigger the same
operation simultaneously. The DB is already safe (upserts / INSERT OR IGNORE), but
concurrent requests waste Riot API calls and op.gg scrapes.

### Approach: TaskLock Registry
A module-level `_task_locks` dict maps `(operation, resource_key)` -> `threading.Lock`.
A helper `task_lock(op, key)` returns a lock for any operation+resource combo, creating
it on first access. Operations `acquire(blocking=False)` — if the lock is already held,
the second caller gets a "already in progress" response (409 or the cached/in-flight
result) instead of running duplicate work.

For fire-and-forget background threads (op.gg scrape, backfill), the lock is held for
the thread's duration. For synchronous endpoints (refresh, fetch-new, duo detection),
the lock is held for the request's duration. For SSE (live game), the lock is keyed
by game_id (not puuid) so multiple lookups of the same game share the result.

### Operations to Guard

#### 13a. Live game SSE [HIGH — up to 400+ wasted API calls] [DONE]
Key: `("live_game", game_id)`. First request runs the full pipeline. Concurrent
requests for the same active game get a "already searching" error via SSE.

#### 13b. Profile refresh [HIGH] [DONE]
Key: `("refresh_profile", profile_id)`. Second click returns 409.

#### 13c. Account refresh [HIGH] [DONE]
Key: `("refresh_account", account_id)`. Second click returns 409.

#### 13d. Fetch new matches [HIGH] [DONE]
Key: `("fetch_matches", puuid)`. Second call returns 409.

#### 13e. Backfill [MEDIUM — already has weak guard] [DONE]
Replace TOCTOU dict check with proper `task_lock("backfill", account_id)`.

#### 13f. Duo detection [MEDIUM] [DONE]
Key: `("duos", match_id)`. Second call waits for first to finish (blocking=True)
then returns from cache.

#### 13g. Match prediction [MEDIUM] [DONE]
Key: `("prediction", match_id)`. Same wait-and-return-cache pattern as duos.

#### 13h. Op.gg scrape [MEDIUM] [DONE]
Key: `("scrape", account_id)`. Background thread holds lock. Concurrent scrape
requests for same account are skipped.

## Phase 14 — Champion Stats Season Filtering [IMPLEMENTING]

### Goal
Add season filtering to the Champions stats page. Currently it queries ALL matches
across ALL time with no season filter. The season dropdown already exists as a global
control — we just need to wire it into the champion stats queries and API calls.

### Changes

#### 14a. database.py — Add start_time/end_time to champion queries [HIGH]
- `get_champion_stats(puuids, start_time=None, end_time=None)` — add WHERE clauses
  for `m.game_start >= ?` and `m.game_start < ?` (milliseconds, same as match queries)
- `get_champion_builds(puuids, champion_name, start_time=None, end_time=None)` — same

#### 14b. app.py — Pass season times to champion endpoints [HIGH]
- `champion_stats()` — read `season` query param, call `_season_times()`, pass to DB
- `champion_detail()` — same pattern

#### 14c. app.js — Wire season param into champion URLs and reload [HIGH]
- `getChampStatsUrl()` — append `&season=${currentSeason}` (or `?season=` if first param)
- `getChampDetailUrl()` — same
- `seasonSelect` change handler — also reload champion stats if on champions view
- Clear `champData` cache on season change so fresh data loads

#### 14d. Cache bust to v=25 [LOW]
- Bump `?v=24` → `?v=25` in index.html

#### 14e. Deploy to dev and prod [HIGH]

## Phase 15 — Accurate Live Game Role Detection

### Goal
Replace the current heuristic-based `_assign_team_roles()` with a data-driven approach
that uses champion role frequency data + the Hungarian algorithm for optimal assignment.

### Problem
The spectator-v5 API provides NO role/position data. Current approach uses a static
`CHAMPION_POSITIONS` dict (one position per champion) which fails for:
- Flex picks (champions played in multiple roles)
- Off-meta picks (e.g., Yunara Bot when mapped as MIDDLE)
- New/unmapped champions (assigned leftover roles randomly)

### Approach

#### 15a. Extract champion role frequencies from stored matches [HIGH]
- Query production DB's 1,759 matches with `raw_json` containing `teamPosition`
- For each champion, count games per role: `{champion_id: {TOP: N, JG: N, MID: N, BOT: N, SUP: N}}`
- Convert counts to probabilities (0.0-1.0 per role)
- Also fetch community data (Data Dragon + community APIs) for champions with
  insufficient sample size (<5 games in our DB)

#### 15b. Create champion_role_rates.py [HIGH]
- Replace `champion_positions.py` (single position) with multi-role frequency data
- Format: `{champion_id: {"TOP": 0.05, "JUNGLE": 0.0, "MIDDLE": 0.60, "BOTTOM": 0.30, "SUPPORT": 0.05}}`
- Include a fallback for unknown champions (equal probability across all roles)
- Generated from DB data + community data merge

#### 15c. Implement Hungarian algorithm in _assign_team_roles() [HIGH]
- Build a 5x5 cost matrix: rows = players, cols = roles
- Cost = 1.0 - role_probability for each player-role pair
- Smite still hard-assigns Jungle (remove that row/col from matrix)
- Exhaust still biases toward Support (boost probability by 0.3)
- Heal/Barrier biases toward Bot (boost probability by 0.2)
- Use `scipy.optimize.linear_sum_assignment` or implement manually
  (avoid adding scipy dependency — implement the algorithm directly)
- The Hungarian algorithm finds the assignment that maximizes total probability

#### 15d. Add role field to prediction storage [MEDIUM]
- When storing predictions, include `role` in each player's data in the JSON blob
- Display roles on prediction history page

#### 15e. Test with known compositions [HIGH]
- Test against the user's reported game (Yunara/Xerath/Mel/DrMundo/Graves)
- Test against standard compositions
- Test against double-ADC / flex pick compositions

#### 15f. Deploy to dev and prod [HIGH]

---

## Phase 16: Champion Build Guide Integration [PLANNED - NOT STARTED]

### Goal
Add a "Build Guide" button to champion-specific pages in LolTracker that displays
first-principles optimal build analysis, including:
- Recommended build order with item-by-item reasoning
- Situational build branches (vs AD assassins, vs AP burst, vs tanks, etc.)
- Inflection points: "at X items, your power spike is Y — this is when you fight"
- Defensive itemization decision tree based on enemy comp/game state
- Component buy order for each back (what to buy at 350g, 600g, 875g, 1200g, 1300g+)
- Skill order with reasoning

### Data Model
- Build guides stored as structured JSON (not markdown) so the UI can render
  interactive sections, collapsible item explanations, conditional branches, etc.
- Could be per-champion rows in a `build_guides` table, or a JSON file per champion
- Need to support multiple roles per champion (e.g., Teemo Top vs Teemo JG)

### UI/UX
- New button on champion stats page: "Build Guide" (alongside existing stats)
- Opens a panel/modal/page with the full build analysis
- Sections: Core Build, Situational Items, Defensive Options, Skill Order, Power Spikes
- Decision tree UI for "if enemy has X, buy Y" branching
- Visual item icons (from Data Dragon CDN) with hover/click for details

### Champions with analysis completed
- Yunara ADC (see YUNARA_ADC_BUILD.md)
- Teemo Jungle (see TEEMO_JG_BUILD.md)

### Export to League Client
- "Copy to Client" button that generates a League client item set JSON and copies to clipboard
- User saves the JSON as a .json file into:
  `League of Legends\Config\Champions\{championKey}\Recommended\`
  or global: `League of Legends\Config\Global\Recommended\`
- JSON format (confirmed from user's actual client export):
  ```json
  {
    "title": "Yunara ADC - LolTracker",
    "associatedMaps": [11, 12],
    "associatedChampions": [897],
    "blocks": [
      {
        "type": "Core Build",
        "items": [
          {"id": "3032", "count": 1},
          {"id": "3006", "count": 1},
          {"id": "2512", "count": 1},
          {"id": "3031", "count": 1}
        ]
      },
      {
        "type": "BF First Back",
        "items": [
          {"id": "3032", "count": 1},
          {"id": "3031", "count": 1},
          {"id": "2512", "count": 1}
        ]
      },
      {
        "type": "vs AD Assassins",
        "items": [
          {"id": "3157", "count": 1},
          {"id": "3047", "count": 1},
          {"id": "3026", "count": 1}
        ]
      },
      {
        "type": "Shoes",
        "items": [
          {"id": "3006", "count": 1},
          {"id": "3047", "count": 1}
        ]
      }
    ]
  }
  ```
- Format notes:
  - `associatedMaps`: [11] = SR only, [11, 12] = SR + ARAM
  - `associatedChampions`: array of champion IDs (from Data Dragon)
  - `blocks`: array of sections, each with a `type` (label) and `items` array
  - `items`: `id` is a STRING of the Data Dragon item ID, `count` is always 1
  - No "map"/"mode"/"priority"/"sortrank" fields (old format, not used)
  - Blocks should mirror the build guide sections: Core, First Back Variants,
    Defense Options, Shoes, Situational
- Can generate multiple item sets per champion (one per role, one per matchup type)

### Implementation Steps
1. Design the build guide data schema (JSON structure)
2. Convert existing markdown analyses into structured JSON format
3. Backend: API endpoint to serve build guide data per champion/role
4. Backend: API endpoint to generate League client item set JSON from build guide data
5. Frontend: Build guide UI component with sections, item icons, decision trees
6. Frontend: "Copy to Client" button that calls the export endpoint and copies JSON to clipboard
7. Integrate into existing champion stats page with button/tab
8. Style to match existing LolTracker design
9. Deploy to dev and prod

---

## Phase 17: Game Notes [PLANNED - NOT STARTED]

### Goal
Allow users to add notes to individual games in their match history. Notes are
simple bullet-point reflections (learnings, mistakes, observations). Later these
could be analyzed for patterns (e.g., "you mention 'positioning' in 60% of losses").

### Format
- **Plain text with bullet points** — lines starting with `- ` are rendered as bullets,
  everything else is plain text paragraphs.
- No markdown, no WYSIWYG, no rich text. Keeps it simple, safe, and fast.
- Display renders `- ` lines as `<li>` items in a `<ul>`, plain lines as `<p>`.

### Security
User-generated text displayed back to the user. Must protect against:
- **XSS (Cross-Site Scripting)**: ALL text must be HTML-escaped before rendering.
  Use `textContent` (not `innerHTML`) or a whitelist sanitizer. No raw HTML ever.
- **SQL Injection**: Use parameterized queries (already the pattern in database.py).
  Never interpolate user text into SQL strings.
- **Stored XSS**: Notes are stored in DB and rendered later. The escaping must happen
  at RENDER time, not just at input time, so even if bad data gets into the DB somehow
  it can't execute.
- **Implementation**: Python `html.escape()` on the backend before returning to frontend,
  AND `textContent`/DOM API on the frontend when rendering. Belt and suspenders.

### Data Model
```sql
ALTER TABLE matches ADD COLUMN notes TEXT DEFAULT NULL;
```
- Single `notes` column on the existing `matches` table.
- NULL = no notes. Empty string = user cleared notes.
- Max length enforced: 2000 characters (prevent abuse/accidents).
- No separate table needed — notes are 1:1 with matches.

### API
- `GET /api/matches/<match_id>/notes` — returns `{"notes": "...", "match_id": "..."}`
- `PUT /api/matches/<match_id>/notes` — body `{"notes": "text"}` — saves/updates notes
  - Validates: max 2000 chars, strips leading/trailing whitespace
  - Returns `{"ok": true, "notes": "sanitized text"}`
- `DELETE /api/matches/<match_id>/notes` — clears notes (sets to NULL)

### UI/UX
- In match history, each game row gets a small "Notes" icon/indicator
  - Empty: subtle icon (gray pen/notepad)
  - Has notes: highlighted icon (gold pen) + preview tooltip on hover
- Clicking the icon or the game row opens/expands a notes panel below the match
- Notes panel has:
  - Textarea for editing (placeholder: "What did you learn from this game?")
  - "Save" button (or auto-save on blur/debounce)
  - Character count indicator (X/2000)
  - Saved notes rendered as bullet list below the textarea
- Notes also visible in champion detail → recent games section

### Implementation Steps
1. Add `notes` column to matches table (migration)
2. Backend: GET/PUT/DELETE endpoints for match notes
3. Backend: Include notes in match history and champion detail API responses
4. Frontend: Notes icon on match rows
5. Frontend: Expandable notes panel with textarea + save
6. Frontend: Render saved notes as bullet list (HTML-escaped)
7. CSS: Style notes panel to match existing design
8. Deploy to dev and prod

## Phase 18: Post-Game Item Build Audit [PLANNED]

### Goal
For every match in the expanded match detail, compare the player's actual item
build against the build guide (if one exists for that champion+role) and show
actionable feedback: what they built right, what was suboptimal, and what the
guide recommends instead.

### Design
- Runs client-side: the expanded match detail already has all 7 items + role_bound_item
  for the player, plus the enemy team composition (all 10 participants).
- Frontend fetches the build guide for the champion (if available) and compares.
- Audit checks:
  1. Core items present? In roughly correct order?
  2. Defensive item appropriate for enemy team comp? (e.g., Zhonya's vs AD assassins)
  3. Anti-heal built when needed? (enemy has healers)
  4. Armor pen built when needed? (enemy has tanks)
  5. Boots appropriate?
- Output: A small "Build Audit" section in the expanded match panel showing
  item-by-item assessment with icons.

### Implementation
1. Frontend: After rendering expanded match, check if build guide exists for
   the player's champion
2. Frontend: Compare actual items vs guide recommendations
3. Frontend: Render audit results as a compact card in the expansion panel
4. Backend: No changes needed — all data already available

## Batch Deploy — Phase 16 Fixes + Phase 17 + Phase 18

### Bug Fixes (deploying together)
- Fix item hover tooltips on build guide (add `.guide-item-img` to tooltip selectors)
- Fix `showToast` → `toast()` alias (4 broken call sites)
- Fix Yunara champion ID: 897 → 804 (confirmed from user's client export)
- Remove ARAM maps from all exports (only SR `[11]`)
- Move "Copy to Client" button to top of build guide panel
- Brighten build guide text (notes, descriptions, reasoning text was too dim)
