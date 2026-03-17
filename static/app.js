/* LolTracker Frontend
   =====================
   Single-page app with view switching: Dashboard, Champions, Live Game, Predictions
*/

// Summoner spell ID -> Data Dragon image name
const SPELL_IMG = {
  1: "SummonerBoost",       // Cleanse
  3: "SummonerExhaust",     // Exhaust
  4: "SummonerFlash",       // Flash
  6: "SummonerHaste",       // Ghost
  7: "SummonerHeal",        // Heal
  11: "SummonerSmite",      // Smite
  12: "SummonerTeleport",   // Teleport
  13: "SummonerMana",       // Clarity
  14: "SummonerDot",        // Ignite
  21: "SummonerBarrier",    // Barrier
  32: "SummonerSnowball",   // Mark (ARAM)
};

document.addEventListener("DOMContentLoaded", () => {

  // ---- State ----
  let currentProfileId = null;
  let currentProfile = null;  // full profile object with accounts
  let currentDetailAccount = null;  // currently viewed account in match detail
  let currentSeason = null;   // selected season key (e.g. "s2026")
  let matchOffset = 0;        // pagination offset for match list
  let matchHasMore = false;   // whether more matches can be loaded
  let liveGameTimer = null;
  let liveGameStart = null;
  let currentLiveSource = null;    // active EventSource for live game SSE
  let liveSearchInProgress = false; // guard against concurrent doLiveSearch calls
  let itemDataCache = null;   // {version, items: {id: {name, description, gold}}}
  let expandedMatchId = null; // currently expanded match row
  let liveStatusTimer = null; // polling timer for live game status on dashboard
  const duoCache = new Map();  // match_id -> { duos: [...] }
  let duoScanAbort = null;     // AbortController for current duo scan
  const DUO_COLORS = ["duo-1", "duo-2", "duo-3", "duo-4"];
  let allLoadedMatches = [];    // all matches loaded for current account (for filtering)
  let currentDdragonVersion = null; // ddragon version for current match list

  // ---- DOM refs ----
  const views = document.querySelectorAll(".view");
  const navTabs = document.querySelectorAll(".nav-tab");
  const profileSelect = document.getElementById("profile-select");
  const newProfileBtn = document.getElementById("new-profile-btn");
  const modalOverlay = document.getElementById("modal-overlay");
  const modal = document.getElementById("modal");
  const modalTitle = document.getElementById("modal-title");
  const modalBody = document.getElementById("modal-body");
  const modalClose = document.getElementById("modal-close");
  const toastEl = document.getElementById("toast");

  // Profile Landing
  const profileLanding = document.getElementById("profile-landing");
  const profileCardsGrid = document.getElementById("profile-cards");
  const dashboardContent = document.getElementById("dashboard-content");

  // Dashboard — these are set during renderDashboard()
  let accountsGrid = null;  // set during grid init
  let quickStats = null;    // set during grid init
  const emptyState = document.getElementById("empty-state");
  const addAccountBtn = document.getElementById("add-account-btn");
  const emptyAddBtn = document.getElementById("empty-add-btn");
  // Refresh ranks indicator (auto-refreshes on load, no button needed)
  const rankRefreshIndicator = document.getElementById("rank-refresh-indicator");
  const profileNameDisplay = document.getElementById("profile-name-display");
  const accountDetail = document.getElementById("account-detail");
  const detailMatches = document.getElementById("detail-matches");
  const detailAccountName = document.getElementById("detail-account-name");
  const backToGrid = document.getElementById("back-to-grid");
  const seasonSelect = document.getElementById("season-select");
  const backfillBtn = document.getElementById("backfill-btn");
  const backfillProgress = document.getElementById("backfill-progress");
  const loadMoreWrap = document.getElementById("load-more-wrap");
  const loadMoreBtn = document.getElementById("load-more-btn");
  const matchFilters = document.getElementById("match-filters");
  const filterChampion = document.getElementById("filter-champion");
  const filterResult = document.getElementById("filter-result");
  const filterQueue = document.getElementById("filter-queue");
  const filterVsChampion = document.getElementById("filter-vs-champion");
  const filterCount = document.getElementById("filter-count");

  // Champions
  const championsList = document.getElementById("champions-list");
  const championDetail = document.getElementById("champion-detail");
  const championDetailContent = document.getElementById("champion-detail-content");
  const backToChampions = document.getElementById("back-to-champions");

  // Live
  const liveSearchForm = document.getElementById("live-search-form");
  const liveRiotId = document.getElementById("live-riot-id");
  const liveSearchBtn = document.getElementById("live-search-btn");
  const liveAccountPills = document.getElementById("live-account-pills");
  const liveStatus = document.getElementById("live-status");
  const liveError = document.getElementById("live-error");
  const liveResults = document.getElementById("live-results");
  const liveNotInGame = document.getElementById("live-not-in-game");
  const liveQueue = document.getElementById("live-queue");
  const liveTimerEl = document.getElementById("live-timer");
  const predictionPanel = document.getElementById("prediction-panel");
  const liveBluePlayers = document.getElementById("live-blue-players");
  const liveRedPlayers = document.getElementById("live-red-players");

  // Predictions
  const predictionStats = document.getElementById("prediction-stats");
  const predictionsList = document.getElementById("predictions-list");

  // ---- Navigation ----
  const navHome = document.getElementById("nav-home");
  navHome.addEventListener("click", () => {
    currentProfileId = null;
    currentProfile = null;
    profileSelect.value = "";
    switchView("dashboard");
    showProfileLanding();
  });

  navTabs.forEach(tab => {
    tab.addEventListener("click", () => {
      const view = tab.dataset.view;
      switchView(view);
    });
  });

  function switchView(viewName) {
    views.forEach(v => v.classList.remove("active", "view-section"));
    navTabs.forEach(t => t.classList.remove("active"));

    const targetView = document.getElementById(`view-${viewName}`);
    if (targetView) {
      targetView.classList.add("active", "view-section");
    }

    const targetTab = document.querySelector(`.nav-tab[data-view="${viewName}"]`);
    if (targetTab) targetTab.classList.add("active");

    // Load data when switching views
    if (viewName === "dashboard") {
      if (currentProfileId) loadProfile();
      else showProfileLanding();
    }
    if (viewName === "champions" && currentProfileId) loadChampionStats();
    if (viewName === "live") renderLiveAccountPills();
    if (viewName === "predictions") loadPredictions();
  }

  // ---- Profiles ----
  let allProfiles = []; // cached profile list for landing page
  loadProfiles();

  async function loadProfiles() {
    try {
      const res = await fetch("/api/profiles");
      allProfiles = await res.json();
      profileSelect.innerHTML = '<option value="">Select Profile</option>';
      allProfiles.forEach(p => {
        const opt = document.createElement("option");
        opt.value = p.id;
        opt.textContent = p.name;
        profileSelect.appendChild(opt);
      });

      // Always start on profile selection landing
      if (!currentProfileId) {
        showProfileLanding();
      }
      // Update prediction filter dropdown with profile names
      if (typeof _populatePredFilter === "function") _populatePredFilter();
    } catch (e) {
      console.error("Failed to load profiles:", e);
    }
  }

  function showProfileLanding() {
    profileLanding.classList.remove("hidden");
    dashboardContent.classList.add("hidden");
    renderProfileCards();
  }

  function renderProfileCards() {
    profileCardsGrid.innerHTML = "";

    allProfiles.forEach(p => {
      const card = document.createElement("div");
      card.className = "profile-card";
      const count = p.account_count || 0;
      const acctLabel = count === 1 ? "1 account" : `${count} accounts`;

      let iconHtml;
      if (p.highest_tier) {
        const tierLower = p.highest_tier.toLowerCase();
        iconHtml = `<img class="profile-rank-icon" src="https://raw.communitydragon.org/latest/plugins/rcp-fe-lol-shared-components/global/default/${tierLower}.png" alt="${p.highest_tier}" onerror="this.style.display='none'">`;
      } else {
        iconHtml = `<svg viewBox="0 0 24 24" width="32" height="32" fill="none" stroke="currentColor" stroke-width="1.5">
            <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/>
            <circle cx="12" cy="7" r="4"/>
          </svg>`;
      }

      card.innerHTML = `
        <div class="profile-card-icon">${iconHtml}</div>
        <div class="profile-card-name">${escHtml(p.name)}</div>
        <div class="profile-card-count">${acctLabel}</div>
      `;
      card.addEventListener("click", () => selectProfile(p.id));
      profileCardsGrid.appendChild(card);
    });

    // "Create New Profile" card
    const createCard = document.createElement("div");
    createCard.className = "profile-card profile-card-create";
    createCard.innerHTML = `
      <div class="profile-card-icon create-icon">
        <svg viewBox="0 0 24 24" width="32" height="32" fill="none" stroke="currentColor" stroke-width="2">
          <line x1="12" y1="5" x2="12" y2="19"/>
          <line x1="5" y1="12" x2="19" y2="12"/>
        </svg>
      </div>
      <div class="profile-card-name">New Profile</div>
      <div class="profile-card-count">Create a new profile</div>
    `;
    createCard.addEventListener("click", () => showNewProfileModal());
    profileCardsGrid.appendChild(createCard);
  }

  function getActiveView() {
    const active = document.querySelector(".view.active");
    return active ? active.id.replace("view-", "") : "dashboard";
  }

  async function selectProfile(profileId) {
    currentProfileId = profileId;
    profileSelect.value = profileId;
    localStorage.setItem("loltracker_profile_id", String(profileId));
    profileLanding.classList.add("hidden");
    dashboardContent.classList.remove("hidden");

    // Reset champion account filter when switching profiles
    const champFilter = document.getElementById("champion-account-filter");
    if (champFilter) champFilter.value = "";
    champData = null;

    await loadProfile();

    // Reload data for the currently active view
    const view = getActiveView();
    if (view === "champions") loadChampionStats();
    if (view === "live") renderLiveAccountPills();
    if (view === "predictions") loadPredictions();
  }

  profileSelect.addEventListener("change", () => {
    const val = profileSelect.value;
    if (val) {
      selectProfile(parseInt(val));
    } else {
      currentProfileId = null;
      currentProfile = null;
      showProfileLanding();
    }
  });

  newProfileBtn.addEventListener("click", () => showNewProfileModal());
  const editProfileBtn = document.getElementById("edit-profile-btn");
  editProfileBtn.addEventListener("click", () => showEditProfileModal());

  function showNewProfileModal() {
    modalTitle.textContent = "New Profile";
    modalBody.innerHTML = `
      <input type="text" id="modal-input" placeholder="Profile name (e.g. My Accounts)" autofocus>
      <button class="btn btn-primary" id="modal-submit">Create</button>
      <div class="modal-status" id="modal-msg"></div>
    `;
    showModal();

    const input = document.getElementById("modal-input");
    const submit = document.getElementById("modal-submit");
    const msg = document.getElementById("modal-msg");

    const doCreate = async () => {
      const name = input.value.trim();
      if (!name) { msg.textContent = "Enter a name"; msg.className = "modal-status err"; return; }
      submit.disabled = true;
      try {
        const res = await fetch("/api/profiles", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ name }),
        });
        const data = await res.json();
        if (data.error) { msg.textContent = data.error; msg.className = "modal-status err"; submit.disabled = false; return; }
        hideModal();
        toast("Profile created");
        await loadProfiles();
        selectProfile(data.id);
      } catch (e) {
        msg.textContent = "Failed to create profile"; msg.className = "modal-status err";
        submit.disabled = false;
      }
    };

    submit.addEventListener("click", doCreate);
    input.addEventListener("keydown", e => { if (e.key === "Enter") doCreate(); });
  }

  function showEditProfileModal() {
    if (!currentProfileId || !currentProfile) {
      toast("No profile selected");
      return;
    }
    modalTitle.textContent = "Edit Profile";
    modalBody.innerHTML = `
      <input type="text" id="modal-input" value="${escHtml(currentProfile.name)}" autofocus>
      <button class="btn btn-primary" id="modal-submit">Save</button>
      <div class="modal-status" id="modal-msg"></div>
      <div class="modal-danger-zone">
        <button class="btn btn-danger" id="modal-delete">Delete Profile</button>
      </div>
    `;
    showModal();

    const input = document.getElementById("modal-input");
    const submit = document.getElementById("modal-submit");
    const msg = document.getElementById("modal-msg");
    const deleteBtn = document.getElementById("modal-delete");

    // Select all text on focus
    input.select();

    const doSave = async () => {
      const name = input.value.trim();
      if (!name) { msg.textContent = "Enter a name"; msg.className = "modal-status err"; return; }
      if (name === currentProfile.name) { hideModal(); return; }
      submit.disabled = true;
      try {
        const res = await fetch(`/api/profiles/${currentProfileId}`, {
          method: "PATCH",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ name }),
        });
        const data = await res.json();
        if (data.error) { msg.textContent = data.error; msg.className = "modal-status err"; submit.disabled = false; return; }
        hideModal();
        toast("Profile renamed");
        // Update local state
        currentProfile.name = data.name;
        profileNameDisplay.textContent = data.name;
        // Update dropdown option text
        const opt = profileSelect.querySelector(`option[value="${currentProfileId}"]`);
        if (opt) opt.textContent = data.name;
      } catch (e) {
        msg.textContent = "Failed to rename profile"; msg.className = "modal-status err";
        submit.disabled = false;
      }
    };

    submit.addEventListener("click", doSave);
    input.addEventListener("keydown", e => { if (e.key === "Enter") doSave(); });

    // Delete profile — two-step confirmation
    let deleteConfirmPending = false;
    let deleteResetTimer = null;
    deleteBtn.addEventListener("click", async () => {
      if (!deleteConfirmPending) {
        // First click: show confirmation state with account count warning
        deleteConfirmPending = true;
        const acctCount = (currentProfile.accounts || []).length;
        const acctWarning = acctCount > 0 ? ` and ${acctCount} account${acctCount > 1 ? "s" : ""}` : "";
        deleteBtn.textContent = `Delete "${currentProfile.name}"${acctWarning}? Click again to confirm`;
        deleteBtn.classList.add("btn-danger-confirm");
        // Auto-reset after 4 seconds if no second click
        deleteResetTimer = setTimeout(() => {
          deleteConfirmPending = false;
          deleteBtn.textContent = "Delete Profile";
          deleteBtn.classList.remove("btn-danger-confirm");
        }, 4000);
        return;
      }
      // Second click: actually delete
      clearTimeout(deleteResetTimer);
      deleteBtn.disabled = true;
      deleteBtn.textContent = "Deleting...";
      try {
        const res = await fetch(`/api/profiles/${currentProfileId}`, { method: "DELETE" });
        const data = await res.json();
        if (data.error) {
          msg.textContent = data.error; msg.className = "modal-status err";
          deleteBtn.disabled = false;
          deleteBtn.textContent = "Delete Profile";
          deleteConfirmPending = false;
          return;
        }
        hideModal();
        toast("Profile deleted");
        currentProfileId = null;
        currentProfile = null;
        localStorage.removeItem("loltracker_profile_id");
        await loadProfiles();
        showProfileLanding();
      } catch (e) {
        msg.textContent = "Failed to delete profile"; msg.className = "modal-status err";
        deleteBtn.disabled = false;
        deleteBtn.textContent = "Delete Profile";
        deleteConfirmPending = false;
      }
    });
  }

  // ---- Load Profile / Dashboard ----
  async function loadProfile() {
    if (!currentProfileId) return;
    try {
      let url = `/api/profiles/${currentProfileId}`;
      if (currentSeason) url += `?season=${currentSeason}`;
      const res = await fetch(url);
      const profile = await res.json();
      if (profile.error) { console.error(profile.error); return; }
      currentProfile = profile;
      renderDashboard();

      // Auto-refresh ranks in background (like profile loading pattern)
      _backgroundRefreshRanks();
    } catch (e) {
      console.error("Failed to load profile:", e);
    }
  }

  let _rankRefreshInFlight = false;
  async function _backgroundRefreshRanks() {
    if (!currentProfileId || _rankRefreshInFlight) return;
    _rankRefreshInFlight = true;
    const indicator = document.getElementById("rank-refresh-indicator");
    if (indicator) indicator.classList.remove("hidden");
    try {
      const res = await fetch(`/api/profiles/${currentProfileId}/refresh`, { method: "POST" });
      const data = await res.json();
      const changes = data.refresh_changes || [];
      if (changes.length > 0) {
        // Re-render dashboard with updated data
        const profileRes = await fetch(`/api/profiles/${currentProfileId}${currentSeason ? '?season=' + currentSeason : ''}`);
        const profile = await profileRes.json();
        if (!profile.error) {
          currentProfile = profile;
          renderDashboard();
        }
        toast(changes.join(" | "));
      }
    } catch (e) {
      // Silently fail — background refresh shouldn't interrupt the user
      console.warn("Background rank refresh failed:", e);
    } finally {
      _rankRefreshInFlight = false;
      if (indicator) indicator.classList.add("hidden");
    }
  }

  // Rank tier -> numeric score for sorting (JS-side mirror of backend TIER_SCORES)
  const TIER_SORT = {
    CHALLENGER: 32, GRANDMASTER: 30, MASTER: 28, DIAMOND: 24,
    EMERALD: 20, PLATINUM: 16, GOLD: 12, SILVER: 8, BRONZE: 4, IRON: 0,
  };
  const DIV_SORT = { I: 3, II: 2, III: 1, IV: 0 };

  function getAccountRankScore(acct) {
    const solo = (acct.ranks || []).find(r => r.queue_type === "RANKED_SOLO_5x5");
    if (!solo || !solo.tier) return -1; // Unranked sorts last
    const base = TIER_SORT[solo.tier.toUpperCase()] ?? 0;
    const div = DIV_SORT[solo.rank] ?? 0;
    const lp = solo.lp || 0;
    return base + div + lp / 100; // LP as tiebreaker
  }

  function getSortedAccounts(accounts) {
    const key = `loltracker_order_${currentProfileId}`;
    const saved = localStorage.getItem(key);
    if (saved) {
      try {
        const order = JSON.parse(saved); // array of account ids
        const idMap = {};
        accounts.forEach(a => idMap[a.id] = a);
        const sorted = [];
        order.forEach(id => { if (idMap[id]) { sorted.push(idMap[id]); delete idMap[id]; } });
        // Append any accounts not in saved order (newly added)
        Object.values(idMap).forEach(a => sorted.push(a));
        return sorted;
      } catch (e) { /* fall through to rank sort */ }
    }
    // Default: sort by rank (highest first)
    return [...accounts].sort((a, b) => getAccountRankScore(b) - getAccountRankScore(a));
  }

  function saveAccountOrder() {
    const key = `loltracker_order_${currentProfileId}`;
    if (!accountsGrid) return;
    const cards = accountsGrid.querySelectorAll(".account-card");
    const order = Array.from(cards).map(c => parseInt(c.dataset.accountId)).filter(Boolean);
    if (order.length > 0) {
      localStorage.setItem(key, JSON.stringify(order));
    }
  }

  function renderDashboard() {
    profileLanding.classList.add("hidden");
    dashboardContent.classList.remove("hidden");
    accountDetail.classList.add("hidden");

    const gridEl = document.getElementById("dashboard-grid");

    if (!currentProfile || !currentProfile.accounts || currentProfile.accounts.length === 0) {
      gridEl.style.display = "";
      gridEl.innerHTML = "";
      emptyState.classList.remove("hidden");
      profileNameDisplay.textContent = currentProfile ? currentProfile.name : "";
      return;
    }

    emptyState.classList.add("hidden");
    profileNameDisplay.textContent = currentProfile.name;
    gridEl.style.display = "";
    gridEl.innerHTML = "";

    // Fixed widget order — build DOM first, then render content
    // (render functions use getElementById which needs elements in DOM)

    // 1. Quick Stats
    const qsDiv = document.createElement("div");
    qsDiv.className = "dash-widget";
    qsDiv.innerHTML = '<div id="quick-stats" class="quick-stats-inner"></div>';
    gridEl.appendChild(qsDiv);
    quickStats = document.getElementById("quick-stats");
    if (currentProfile.accounts) renderQuickStats(currentProfile.accounts);

    // 2. Accounts
    const accDiv = document.createElement("div");
    accDiv.className = "dash-widget";
    accDiv.innerHTML = '<div id="accounts-grid" class="accounts-grid"></div>';
    gridEl.appendChild(accDiv);
    accountsGrid = document.getElementById("accounts-grid");
    if (currentProfile.accounts) {
      const sorted = getSortedAccounts(currentProfile.accounts);
      sorted.forEach(acct => accountsGrid.appendChild(createAccountCard(acct)));
      loadSparklines();
      loadSessionStats();
    }
  }

  function renderQuickStats(accounts) {
    let totalWins = 0, totalLosses = 0;

    accounts.forEach(acct => {
      const ss = acct.season_stats;
      if (ss && ss.games > 0) {
        totalWins += ss.wins;
        totalLosses += ss.losses;
      }
    });

    const totalGames = totalWins + totalLosses;
    const overallWR = totalGames > 0 ? Math.round(totalWins / totalGames * 100) : 0;
    // Label reflects the selected season
    const selectedSeason = allSeasons.find(s => s.key === currentSeason);
    const statsLabel = currentSeason === "all" ? "All Games" : (selectedSeason ? selectedSeason.label : "Games");

    quickStats.innerHTML = `
      <div class="stat-block">
        <span class="stat-label">Accounts</span>
        <span class="stat-value">${accounts.length}</span>
      </div>
      <div class="stat-block">
        <span class="stat-label">${statsLabel}</span>
        <span class="stat-value">${totalGames}</span>
      </div>
      <div class="stat-block">
        <span class="stat-label">Win Rate</span>
        <span class="stat-value ${wrClass(overallWR)}">${overallWR}%</span>
      </div>
      <div class="stat-block">
        <span class="stat-label">Record</span>
        <span class="stat-value">${totalWins}W ${totalLosses}L</span>
      </div>
    `;
    if (quickStats) quickStats.classList.remove("hidden");
  }

  function createAccountCard(acct) {
    const card = document.createElement("div");
    card.className = "account-card";
    card.draggable = true;
    card.dataset.accountId = acct.id;

    // Find solo queue rank (primary) and flex
    const soloRank = (acct.ranks || []).find(r => r.queue_type === "RANKED_SOLO_5x5");
    const flexRank = (acct.ranks || []).find(r => r.queue_type === "RANKED_FLEX_SR");

    // When a season is selected, overlay season W/L onto the rank display
    const ss = acct.season_stats;
    const isCurrentSeason = currentSeason === (allSeasons.length > 0 ? allSeasons[0].key : "");
    const isAllSeasons = currentSeason === "all";
    const isPastSeason = !isCurrentSeason && !isAllSeasons;

    // Look up scraped rank data for the selected past season
    const seasonRanks = acct.season_ranks || {};
    const scrapedRank = isPastSeason ? seasonRanks[currentSeason] : null;

    // All-season history rows at bottom of card
    const seasonRows = [];
    const allStats = acct.all_season_stats || {};
    allSeasons.forEach(s => {
      const sst = allStats[s.key];
      const sr = seasonRanks[s.key];
      if ((!sst || sst.games === 0) && !sr) return;
      const wins = sst ? sst.wins : 0;
      const losses = sst ? sst.losses : 0;
      const games = wins + losses;
      const wr = games > 0 ? Math.round(wins / games * 100) : 0;
      const isSelected = s.key === currentSeason;
      let rankText = "";
      let rankClass = "";
      if (sr && sr.tier) {
        const t = sr.tier.charAt(0).toUpperCase() + sr.tier.slice(1).toLowerCase();
        const d = sr.division || "";
        const isApex = ["master", "grandmaster", "challenger"].includes(sr.tier.toLowerCase());
        rankText = isApex ? t : t + " " + d;
        rankClass = ` tier-${sr.tier.toLowerCase()}`;
      }
      seasonRows.push(`
        <div class="season-history-row${isSelected ? " season-active" : ""}">
          <span class="season-history-label">${escHtml(s.label)}</span>
          <span class="season-history-rank${rankClass}">${rankText}</span>
          <span class="season-history-record">${games > 0 ? wins + "W " + losses + "L" : ""}</span>
          <span class="season-history-wr ${games > 0 ? wrClass(wr) : ""}">${games > 0 ? wr + "%" : ""}</span>
        </div>
      `);
    });
    const VISIBLE_SEASONS = 5;
    const hasMore = seasonRows.length > VISIBLE_SEASONS;
    const visibleHtml = seasonRows.slice(0, VISIBLE_SEASONS).join("");
    const hiddenHtml = hasMore ? seasonRows.slice(VISIBLE_SEASONS).join("") : "";
    const seasonHistoryHtml = visibleHtml
      + (hasMore ? `<div class="season-history-hidden" style="display:none">${hiddenHtml}</div>
         <button class="season-history-toggle" type="button">Show ${seasonRows.length - VISIBLE_SEASONS} more</button>` : "");

    card.innerHTML = `
      <div class="account-card-header">
        <div class="account-name">${acct.game_name}<span class="tag">#${acct.tag_line}</span></div>
        <button class="account-remove" data-id="${acct.id}" title="Remove account" aria-label="Remove ${escHtml(acct.game_name)}">&times;</button>
      </div>
      <div class="account-queues">
        ${isPastSeason && scrapedRank
          ? renderScrapedRankRow("Solo", scrapedRank, ss)
          : isPastSeason
            ? renderRankRow("Solo", soloRank, ss)
            : renderRankRow("Solo", soloRank)}
        ${!isPastSeason && flexRank ? renderRankRow("Flex", flexRank) : ""}
      </div>
      <div class="sparkline-container" data-sparkline-account="${acct.id}"></div>
      ${seasonHistoryHtml ? `<div class="account-season-history">${seasonHistoryHtml}</div>` : ""}
    `;

    // Season history "Show more" toggle
    const toggleBtn = card.querySelector(".season-history-toggle");
    if (toggleBtn) {
      toggleBtn.addEventListener("click", (e) => {
        e.stopPropagation();
        const hidden = card.querySelector(".season-history-hidden");
        if (!hidden) return;
        const showing = hidden.style.display !== "none";
        hidden.style.display = showing ? "none" : "";
        toggleBtn.textContent = showing
          ? `Show ${seasonRows.length - VISIBLE_SEASONS} more`
          : "Show less";
      });
    }

    // Click to view matches
    card.addEventListener("click", (e) => {
      if (e.target.closest(".account-remove") || e.target.closest(".season-history-toggle")) return;
      showAccountDetail(acct);
    });

    // Remove button
    const removeBtn = card.querySelector(".account-remove");
    removeBtn.addEventListener("click", (e) => {
      e.stopPropagation();
      removeAccount(acct.id, acct.game_name);
    });

    // Drag-and-drop
    card.addEventListener("dragstart", (e) => {
      card.classList.add("dragging");
      e.dataTransfer.effectAllowed = "move";
      e.dataTransfer.setData("text/plain", acct.id);
    });
    card.addEventListener("dragend", () => {
      card.classList.remove("dragging");
      document.querySelectorAll(".account-card.drag-over").forEach(c => c.classList.remove("drag-over"));
      saveAccountOrder();
    });
    card.addEventListener("dragover", (e) => {
      e.preventDefault();
      e.dataTransfer.dropEffect = "move";
      const dragging = accountsGrid.querySelector(".dragging");
      if (dragging && dragging !== card) {
        card.classList.add("drag-over");
        const rect = card.getBoundingClientRect();
        const midY = rect.top + rect.height / 2;
        const midX = rect.left + rect.width / 2;
        // Determine insertion point based on grid layout
        if (e.clientY < midY || (e.clientY < midY + rect.height * 0.3 && e.clientX < midX)) {
          accountsGrid.insertBefore(dragging, card);
        } else {
          accountsGrid.insertBefore(dragging, card.nextSibling);
        }
      }
    });
    card.addEventListener("dragleave", () => {
      card.classList.remove("drag-over");
    });
    card.addEventListener("drop", (e) => {
      e.preventDefault();
      card.classList.remove("drag-over");
    });

    return card;
  }

  function renderRankRow(label, rank, seasonStats) {
    // If season stats overlay is provided (past season), show only season W/L — no rank/LP
    if (seasonStats) {
      const wins = seasonStats.wins || 0;
      const losses = seasonStats.losses || 0;
      const games = wins + losses;
      const wr = games > 0 ? Math.round(wins / games * 100) : 0;

      if (games === 0) {
        return `
          <div class="queue-row">
            <span class="queue-label">${label}</span>
            <span class="rank-unranked">No games</span>
          </div>
        `;
      }

      return `
        <div class="queue-row">
          <span class="queue-label">${label}</span>
          <div class="rank-info">
            <span class="rank-wr-text ${wrClass(wr)}">${wr}% WR</span>
            <span class="rank-lp-text">${wins}W ${losses}L &middot; ${games} games</span>
          </div>
        </div>
      `;
    }

    if (!rank || !rank.tier) {
      return `
        <div class="queue-row">
          <span class="queue-label">${label}</span>
          <span class="rank-unranked">Unranked</span>
        </div>
      `;
    }

    const tier = rank.tier.charAt(0).toUpperCase() + rank.tier.slice(1).toLowerCase();
    const tierLower = tier.toLowerCase();
    const divShort = { "I": "1", "II": "2", "III": "3", "IV": "4" };
    const div = divShort[rank.rank] || rank.rank || "";
    const isApex = ["master", "grandmaster", "challenger"].includes(tierLower);
    const fullRank = isApex ? tier : `${tier} ${div}`;
    const total = (rank.wins || 0) + (rank.losses || 0);
    const wr = total > 0 ? Math.round(rank.wins / total * 100) : 0;

    return `
      <div class="queue-row">
        <span class="queue-label">${label}</span>
        <div class="account-rank-display">
          <img loading="lazy" class="rank-icon-large" src="https://raw.communitydragon.org/latest/plugins/rcp-fe-lol-shared-components/global/default/${tierLower}.png" alt="${tier}" onerror="this.style.display='none'">
          <div class="rank-info">
            <div class="rank-tier-text tier-${tierLower}">${fullRank} <span class="rank-lp-text">${rank.lp} LP</span></div>
            <span class="rank-wr-text ${wrClass(wr)}">${wr}% (${rank.wins}W ${rank.losses}L)</span>
          </div>
        </div>
      </div>
    `;
  }

  function renderScrapedRankRow(label, scrapedRank, seasonStats) {
    // Display scraped rank data from op.gg for a past season
    const tier = scrapedRank.tier
      ? scrapedRank.tier.charAt(0).toUpperCase() + scrapedRank.tier.slice(1).toLowerCase()
      : "";
    const tierLower = tier.toLowerCase();
    const div = scrapedRank.division || "";
    const isApex = ["master", "grandmaster", "challenger"].includes(tierLower);
    const fullRank = isApex ? tier : `${tier} ${div}`;
    const lp = scrapedRank.lp || 0;

    // Season W/L stats (from our match database)
    let wlHtml = "";
    if (seasonStats && seasonStats.games > 0) {
      const wr = Math.round(seasonStats.wins / seasonStats.games * 100);
      wlHtml = `<span class="rank-wr-text ${wrClass(wr)}">${wr}% WR (${seasonStats.wins}W ${seasonStats.losses}L)</span>`;
    }

    // Peak rank if available
    let peakHtml = "";
    if (scrapedRank.peak_tier) {
      const pt = scrapedRank.peak_tier.charAt(0).toUpperCase() + scrapedRank.peak_tier.slice(1).toLowerCase();
      const pd = scrapedRank.peak_division || "";
      const pApex = ["master", "grandmaster", "challenger"].includes(scrapedRank.peak_tier.toLowerCase());
      const peakFull = pApex ? pt : `${pt} ${pd}`;
      peakHtml = `<div class="rank-peak-text">Peak: ${peakFull} ${scrapedRank.peak_lp || 0} LP</div>`;
    }

    return `
      <div class="queue-row">
        <span class="queue-label">${label}</span>
        <div class="account-rank-display">
          <img loading="lazy" class="rank-icon-large" src="https://raw.communitydragon.org/latest/plugins/rcp-fe-lol-shared-components/global/default/${tierLower}.png" alt="${tier}" onerror="this.style.display='none'">
          <div class="rank-info">
            <div class="rank-tier-text tier-${tierLower}">${fullRank}</div>
            <div class="rank-lp-text">${lp} LP</div>
            ${wlHtml}
            ${peakHtml}
          </div>
        </div>
      </div>
    `;
  }

  // ---- Add Account ----
  addAccountBtn.addEventListener("click", showAddAccountModal);
  emptyAddBtn.addEventListener("click", showAddAccountModal);

  function showAddAccountModal() {
    if (!currentProfileId) {
      toast("Create a profile first");
      showNewProfileModal();
      return;
    }
    modalTitle.textContent = "Add Account";
    modalBody.innerHTML = `
      <input type="text" id="modal-input" placeholder="GameName#TagLine (e.g. Leon#NA420)" autofocus>
      <button class="btn btn-primary" id="modal-submit">Add Account</button>
      <div class="modal-status" id="modal-msg"></div>
    `;
    showModal();

    const input = document.getElementById("modal-input");
    const submit = document.getElementById("modal-submit");
    const msg = document.getElementById("modal-msg");

    const doAdd = async () => {
      const riotId = input.value.trim();
      if (!riotId || !riotId.includes("#")) {
        msg.textContent = "Use format: GameName#TagLine";
        msg.className = "modal-status err";
        return;
      }
      submit.disabled = true;
      msg.textContent = "Looking up account...";
      msg.className = "modal-status";
      try {
        const res = await fetch(`/api/profiles/${currentProfileId}/accounts`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ riot_id: riotId }),
        });
        const data = await res.json();
        if (data.error) {
          msg.textContent = data.error;
          msg.className = "modal-status err";
          submit.disabled = false;
          return;
        }
        hideModal();
        toast("Account added");
        loadProfile();
      } catch (e) {
        msg.textContent = "Failed to add account";
        msg.className = "modal-status err";
        submit.disabled = false;
      }
    };

    submit.addEventListener("click", doAdd);
    input.addEventListener("keydown", e => { if (e.key === "Enter") doAdd(); });
  }

  // ---- Remove Account ----
  async function removeAccount(accountId, name) {
    if (!confirm(`Remove ${name} from this profile?`)) return;
    try {
      await fetch(`/api/accounts/${accountId}`, { method: "DELETE" });
      toast("Account removed");
      loadProfile();
    } catch (e) {
      toast("Failed to remove account");
    }
  }

  // Ranks auto-refresh on profile load — no manual button needed.

  // ---- Global Live Status Polling ----
  // Polls ALL accounts across ALL profiles, shows notification bar on any page,
  // and also updates dashboard card badges when on dashboard.
  const liveNotifyBar = document.getElementById("live-notify-bar");

  function startGlobalLivePolling() {
    stopLiveStatusPolling();
    checkGlobalLiveStatus();
    liveStatusTimer = setInterval(checkGlobalLiveStatus, 60000);
  }

  function stopLiveStatusPolling() {
    if (liveStatusTimer) {
      clearInterval(liveStatusTimer);
      liveStatusTimer = null;
    }
  }

  async function checkGlobalLiveStatus() {
    try {
      const res = await fetch("/api/all-live-status");
      const activePlayers = await res.json();
      renderLiveNotifyBar(activePlayers);
    } catch (e) {
      // Silently fail — polling will retry
    }
  }

  function renderLiveNotifyBar(activePlayers) {
    if (!activePlayers || activePlayers.length === 0) {
      liveNotifyBar.classList.add("hidden");
      liveNotifyBar.innerHTML = "";
      return;
    }

    liveNotifyBar.innerHTML = "";
    liveNotifyBar.classList.remove("hidden");

    activePlayers.forEach(p => {
      const item = document.createElement("div");
      item.className = "live-notify-item";
      item.innerHTML = `
        <span class="live-notify-dot"></span>
        <span class="live-notify-name">${escHtml(p.game_name)}#${escHtml(p.tag_line)}</span>
        <span class="live-notify-msg">is in a game</span>
        <span class="live-notify-action">Analyze Match</span>
      `;
      item.addEventListener("click", () => {
        switchView("live");
        liveRiotId.value = `${p.game_name}#${p.tag_line}`;
        doLiveSearch(p.puuid);
      });
      liveNotifyBar.appendChild(item);
    });
  }

  // Start global polling immediately on page load
  startGlobalLivePolling();

  // ---- Background Scheduler Status Polling ----
  const schedulerBar = document.getElementById("scheduler-bar");
  let _schedulerPollTimer = null;

  function startSchedulerPolling() {
    checkSchedulerStatus();
    _schedulerPollTimer = setInterval(checkSchedulerStatus, 15000); // every 15s
  }

  async function checkSchedulerStatus() {
    try {
      const res = await fetch("/api/scheduler/status");
      const status = await res.json();
      if (status.running && status.current_step) {
        const stepLabels = {
          "starting": "Starting background update...",
          "refreshing ranks": "Updating ranks...",
          "fetching matches": "Fetching new matches...",
          "resolving predictions": "Resolving predictions...",
          "scraping season ranks": "Updating season history...",
        };
        const label = stepLabels[status.current_step] || status.current_step;
        schedulerBar.innerHTML = `<span class="spinner"></span> ${label}`;
        schedulerBar.classList.remove("hidden");
      } else {
        schedulerBar.classList.add("hidden");
      }
    } catch (_) {
      // Silently fail
    }
  }

  startSchedulerPolling();

  // ---- Account Detail (Match History) ----
  backToGrid.addEventListener("click", () => {
    accountDetail.classList.add("hidden");
    const gridEl = document.getElementById("dashboard-grid");
    if (gridEl) gridEl.style.display = "";
    matchFilters.classList.add("hidden");
    currentDetailAccount = null;
    allLoadedMatches = [];
  });

  // Load More button — appends next page of matches
  loadMoreBtn.addEventListener("click", async () => {
    if (!currentDetailAccount || !matchHasMore) return;
    loadMoreBtn.disabled = true;
    loadMoreBtn.textContent = "Loading...";
    try {
      let url = `/api/accounts/${currentDetailAccount.id}/matches?offset=${matchOffset}&limit=20`;
      if (currentSeason) url += `&season=${currentSeason}`;
      const res = await fetch(url);
      const data = await res.json();
      if (data.error) {
        toast("Failed to load more matches");
        return;
      }
      matchOffset = data.offset + data.matches.length;
      matchHasMore = data.has_more;
      allLoadedMatches = allLoadedMatches.concat(data.matches || []);
      renderMatchList(detailMatches, data.matches, data.ddragon_version, false, true);
      updateLoadMoreButton();
      populateMatchFilters(allLoadedMatches);
    } catch (e) {
      toast("Failed to load more matches");
    } finally {
      loadMoreBtn.disabled = false;
      loadMoreBtn.textContent = "Load More";
    }
  });

  // Load seasons into dropdown and set default
  let allSeasons = []; // cached season list [{key, label, filter}, ...]
  (async function loadSeasons() {
    try {
      const res = await fetch("/api/seasons");
      allSeasons = await res.json();
      // Only show filterable seasons in the dropdown (recent seasons with match data)
      const filterableSeasons = allSeasons.filter(s => s.filter !== false);
      seasonSelect.innerHTML = filterableSeasons.map(s =>
        `<option value="${s.key}">${s.label}</option>`
      ).join("") + `<option value="all">All Seasons</option>`;
      // Default to first (current) season
      if (filterableSeasons.length > 0) {
        currentSeason = filterableSeasons[0].key;
        seasonSelect.value = currentSeason;
      }
    } catch (e) {
      // fallback
    }
  })();

  // Season change reloads dashboard + drill-in if open + champion stats
  seasonSelect.addEventListener("change", async () => {
    currentSeason = seasonSelect.value;
    // Clear cached champion data so it reloads with new season filter
    champData = null;
    if (currentDetailAccount) {
      showAccountDetail(currentDetailAccount);
      if (currentProfileId) {
        try {
          let url = `/api/profiles/${currentProfileId}`;
          if (currentSeason) url += `?season=${currentSeason}`;
          const res = await fetch(url);
          const profile = await res.json();
          if (!profile.error) currentProfile = profile;
        } catch (e) { /* ignore */ }
      }
    } else if (currentProfileId) {
      if (accountsGrid) accountsGrid.classList.add("loading");
      await loadProfile();
      if (accountsGrid) accountsGrid.classList.remove("loading");
      autoScrapeIfMissing();
    }
    // Reload champion stats if currently on the champions view
    if (getActiveView() === "champions" && currentProfileId) {
      loadChampionStats();
    }
  });

  // Auto-scrape: when switching to a past season, check each account for missing
  // scraped rank data and fire a background scrape if needed.
  function autoScrapeIfMissing() {
    const isCurrentSeason = currentSeason === (allSeasons.length > 0 ? allSeasons[0].key : "");
    const isAllSeasons = currentSeason === "all";
    if (isCurrentSeason || isAllSeasons || !currentProfile) return;

    const accounts = currentProfile.accounts || [];
    accounts.forEach(acct => {
      const sr = acct.season_ranks || {};
      // Only scrape if account has no real season data at all
      const hasRealData = Object.keys(sr).some(k => !k.startsWith("opgg_"));
      if (hasRealData) return;

      // Fire scrape in background, update card when done
      fetch(`/api/accounts/${acct.id}/scrape-ranks-if-missing`, { method: "POST" })
        .then(r => r.json())
        .then(data => {
          if (data.scraped && data.season_ranks) {
            // Update local state and re-render just this card
            acct.season_ranks = data.season_ranks;
            const card = accountsGrid ? accountsGrid.querySelector(`[data-account-id="${acct.id}"]`) : null;
            if (card) {
              const newCard = createAccountCard(acct);
              card.replaceWith(newCard);
            }
          }
        })
        .catch(() => {}); // silently fail
    });
  }

  // ---- LP Sparkline Graphs ----
  // Convert tier+division+LP to a numeric score for sparkline Y axis
  function rankToScore(tier, rank, lp) {
    const TIER_VAL = {
      IRON: 0, BRONZE: 4, SILVER: 8, GOLD: 12,
      PLATINUM: 16, EMERALD: 20, DIAMOND: 24,
      MASTER: 28, GRANDMASTER: 30, CHALLENGER: 32,
    };
    const DIV_VAL = { IV: 0, III: 1, II: 2, I: 3 };
    const t = (tier || "").toUpperCase();
    const base = TIER_VAL[t] ?? 0;
    const div = DIV_VAL[(rank || "").toUpperCase()] ?? 0;
    return (base + div) * 100 + (lp || 0);
  }

  function renderSparklineSVG(dataPoints) {
    // dataPoints = [{score, tier, lp}, ...]
    if (dataPoints.length < 2) return "";

    const W = 160, H = 36, PAD = 2;
    const scores = dataPoints.map(d => d.score);
    const minS = Math.min(...scores);
    const maxS = Math.max(...scores);
    const range = maxS - minS || 1;

    const points = dataPoints.map((d, i) => {
      const x = PAD + (i / (dataPoints.length - 1)) * (W - PAD * 2);
      const y = H - PAD - ((d.score - minS) / range) * (H - PAD * 2);
      return `${x.toFixed(1)},${y.toFixed(1)}`;
    }).join(" ");

    // Determine color: trending up = green, down = red, flat = neutral
    const first = scores[0], last = scores[scores.length - 1];
    const color = last > first ? "var(--win)" : last < first ? "var(--loss)" : "var(--text-secondary)";

    // Last point dot
    const lastPt = dataPoints[dataPoints.length - 1];
    const lastX = PAD + ((dataPoints.length - 1) / (dataPoints.length - 1)) * (W - PAD * 2);
    const lastY = H - PAD - ((lastPt.score - minS) / range) * (H - PAD * 2);

    return `<svg class="lp-sparkline" viewBox="0 0 ${W} ${H}" preserveAspectRatio="none">
      <polyline points="${points}" fill="none" stroke="${color}" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
      <circle cx="${lastX.toFixed(1)}" cy="${lastY.toFixed(1)}" r="2.5" fill="${color}"/>
    </svg>`;
  }

  // Load sparklines for all visible account cards
  function loadSparklines() {
    const containers = accountsGrid.querySelectorAll("[data-sparkline-account]");
    containers.forEach(container => {
      const accountId = container.dataset.sparklineAccount;
      let url = `/api/accounts/${accountId}/rank-history?queue=RANKED_SOLO_5x5`;
      if (currentSeason && currentSeason !== "all") url += `&season=${currentSeason}`;
      fetch(url)
        .then(r => r.json())
        .then(data => {
          const history = data.history || [];
          if (history.length < 2) {
            container.innerHTML = "";
            return;
          }
          const pts = history.map(h => ({
            score: rankToScore(h.tier, h.rank, h.lp),
            tier: h.tier,
            lp: h.lp,
          }));
          container.innerHTML = renderSparklineSVG(pts);
        })
        .catch(() => {});
    });
  }

  // ---- Match History Filters ----
  function resetMatchFilters() {
    filterChampion.innerHTML = '<option value="">All Champions</option>';
    filterResult.value = "";
    filterQueue.value = "";
    filterVsChampion.value = "";
    filterCount.textContent = "";
  }

  function populateMatchFilters(matches) {
    if (!matches || matches.length === 0) {
      matchFilters.classList.add("hidden");
      return;
    }
    matchFilters.classList.remove("hidden");

    // Collect unique champions from loaded matches, preserving current selection
    const currentChamp = filterChampion.value;
    const champs = [...new Set(matches.map(m => m.champion_name).filter(Boolean))].sort();
    filterChampion.innerHTML = '<option value="">All Champions</option>' +
      champs.map(c => `<option value="${c}"${c === currentChamp ? " selected" : ""}>${c}</option>`).join("");

    // Collect unique opponent champions
    const currentVs = filterVsChampion.value;
    const vsChamps = [...new Set(matches.flatMap(m => m.vs_champions || []).filter(Boolean))].sort();
    filterVsChampion.innerHTML = '<option value="">Vs Champion</option>' +
      vsChamps.map(c => `<option value="${c}"${c === currentVs ? " selected" : ""}>${c}</option>`).join("");
  }

  function applyMatchFilters() {
    const champFilter = filterChampion.value;
    const resultFilter = filterResult.value;
    const queueFilter = filterQueue.value;
    const vsFilter = filterVsChampion.value;

    const filtered = allLoadedMatches.filter(m => {
      if (champFilter && m.champion_name !== champFilter) return false;
      if (resultFilter === "win" && (!m.win || m.is_remake)) return false;
      if (resultFilter === "loss" && (m.win || m.is_remake)) return false;
      if (resultFilter === "remake" && !m.is_remake) return false;
      if (queueFilter && String(m.queue_id) !== queueFilter) return false;
      if (vsFilter && !(m.vs_champions || []).includes(vsFilter)) return false;
      return true;
    });

    // Show count indicator
    if (champFilter || resultFilter || queueFilter || vsFilter) {
      filterCount.textContent = `${filtered.length} of ${allLoadedMatches.length} games`;
    } else {
      filterCount.textContent = "";
    }

    // Re-render with filtered matches
    renderMatchList(detailMatches, filtered, currentDdragonVersion);
  }

  filterChampion.addEventListener("change", applyMatchFilters);
  filterResult.addEventListener("change", applyMatchFilters);
  filterQueue.addEventListener("change", applyMatchFilters);
  filterVsChampion.addEventListener("change", applyMatchFilters);

  // Backfill button handler — starts a background task and polls for status
  let backfillPollTimer = null;

  backfillBtn.addEventListener("click", async () => {
    if (!currentDetailAccount) return;
    const season = seasonSelect.value;
    const accountId = currentDetailAccount.id;

    backfillBtn.disabled = true;
    backfillBtn.textContent = "Backfilling...";
    backfillProgress.classList.remove("hidden");
    backfillProgress.innerHTML = '<span class="spinner"></span> Starting backfill...';

    try {
      const res = await fetch(`/api/accounts/${accountId}/backfill`, {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({season}),
      });
      const data = await res.json();
      if (!res.ok) {
        // If already running, start polling that existing task
        if (res.status === 409) {
          startBackfillPolling(accountId);
          return;
        }
        backfillProgress.innerHTML = `<span class="bf-status bf-error">${data.error || "Failed to start"}</span>`;
        backfillBtn.disabled = false;
        backfillBtn.textContent = "Backfill Season";
        return;
      }
      startBackfillPolling(accountId);
    } catch (e) {
      backfillProgress.innerHTML = `<span class="bf-status bf-error">Failed to start backfill</span>`;
      backfillBtn.disabled = false;
      backfillBtn.textContent = "Backfill Season";
    }
  });

  function startBackfillPolling(accountId) {
    if (backfillPollTimer) clearInterval(backfillPollTimer);
    backfillPollTimer = setInterval(() => pollBackfillStatus(accountId), 1000);
  }

  async function pollBackfillStatus(accountId) {
    try {
      const res = await fetch(`/api/accounts/${accountId}/backfill/status`);
      const s = await res.json();

      if (s.state === "idle") {
        stopBackfillPolling();
        return;
      }

      const total = s.total || 0;
      const done = (s.skipped || 0) + (s.fetched || 0) + (s.errors || 0);
      const pct = total > 0 ? Math.round(done / total * 100) : 0;

      if (s.state === "running") {
        if (s.total_fetch > 0) {
          backfillProgress.innerHTML = `
            <div class="bf-bar-wrap">
              <div class="bf-bar" style="width:${pct}%"></div>
            </div>
            <span class="bf-status">
              ${escHtml(s.status)}
              (${s.fetched} new, ${s.skipped} cached${s.errors ? `, ${s.errors} errors` : ""})
            </span>
          `;
        } else {
          backfillProgress.innerHTML = `<span class="spinner"></span> <span class="bf-status">${escHtml(s.status)}</span>`;
        }
      } else if (s.state === "done") {
        stopBackfillPolling();
        backfillProgress.innerHTML = `
          <div class="bf-bar-wrap"><div class="bf-bar" style="width:100%"></div></div>
          <span class="bf-status bf-done">${escHtml(s.status)}</span>
        `;
        backfillBtn.disabled = false;
        backfillBtn.textContent = "Backfill Season";
        toast(`Backfill complete: ${s.fetched} new matches`);
        if (currentDetailAccount) showAccountDetail(currentDetailAccount);
      } else if (s.state === "error") {
        stopBackfillPolling();
        backfillProgress.innerHTML = `<span class="bf-status bf-error">${escHtml(s.status)}</span>`;
        backfillBtn.disabled = false;
        backfillBtn.textContent = "Backfill Season";
      }
    } catch (e) {
      // Network hiccup — keep polling, don't give up
    }
  }

  function stopBackfillPolling() {
    if (backfillPollTimer) {
      clearInterval(backfillPollTimer);
      backfillPollTimer = null;
    }
  }

  async function showAccountDetail(acct) {
    currentDetailAccount = acct;
    matchOffset = 0;
    matchHasMore = false;
    allLoadedMatches = [];
    currentDdragonVersion = null;
    const gridEl = document.getElementById("dashboard-grid");
    if (gridEl) gridEl.style.display = "none";
    accountDetail.classList.remove("hidden");
    backfillProgress.classList.add("hidden");
    loadMoreWrap.classList.add("hidden");
    matchFilters.classList.add("hidden");
    resetMatchFilters();
    stopBackfillPolling();
    detailAccountName.textContent = `${acct.game_name}#${acct.tag_line}`;
    detailMatches.innerHTML = '<div class="status-bar"><span class="spinner"></span> Loading matches...</div>';

    // Check if a backfill is already running for this account
    try {
      const bfRes = await fetch(`/api/accounts/${acct.id}/backfill/status`);
      const bfState = await bfRes.json();
      if (bfState.state === "running") {
        backfillBtn.disabled = true;
        backfillBtn.textContent = "Backfilling...";
        backfillProgress.classList.remove("hidden");
        backfillProgress.innerHTML = '<span class="spinner"></span> <span class="bf-status">Backfill in progress...</span>';
        startBackfillPolling(acct.id);
      }
    } catch (e) { /* ignore */ }

    // Step 1: Instantly load matches from DB (no Riot API calls)
    try {
      let url = `/api/accounts/${acct.id}/matches?offset=0&limit=20`;
      if (currentSeason) url += `&season=${currentSeason}`;
      const res = await fetch(url);
      const data = await res.json();
      if (data.error) {
        detailMatches.innerHTML = `<div class="error-bar">${data.error}</div>`;
        return;
      }
      matchOffset = data.offset + data.matches.length;
      matchHasMore = data.has_more;
      currentDdragonVersion = data.ddragon_version;
      allLoadedMatches = data.matches || [];
      renderMatchList(detailMatches, data.matches, data.ddragon_version);
      updateLoadMoreButton();
      populateMatchFilters(allLoadedMatches);
    } catch (e) {
      detailMatches.innerHTML = '<div class="error-bar">Failed to load matches</div>';
      return;
    }

    // Step 2: Background-fetch new matches from Riot API
    // This fires after the UI is already rendered with DB data
    // Show a status indicator while checking
    let fetchIndicator = detailMatches.parentElement.querySelector(".fetch-new-status");
    if (!fetchIndicator) {
      fetchIndicator = document.createElement("div");
      fetchIndicator.className = "fetch-new-status";
      detailMatches.parentElement.insertBefore(fetchIndicator, detailMatches);
    }
    fetchIndicator.innerHTML = '<span class="spinner-sm"></span> Checking for new matches...';

    try {
      const fetchRes = await fetch(`/api/accounts/${acct.id}/fetch-new`, { method: "POST" });
      const fetchData = await fetchRes.json();
      // If new matches were found and we're still viewing this account, re-render
      if (fetchData.new_matches > 0 && currentDetailAccount && currentDetailAccount.id === acct.id) {
        fetchIndicator.innerHTML = `Found ${fetchData.new_matches} new match${fetchData.new_matches > 1 ? "es" : ""}, updating...`;
        // Re-fetch from DB to get updated list including new matches
        let url = `/api/accounts/${acct.id}/matches?offset=0&limit=20`;
        if (currentSeason) url += `&season=${currentSeason}`;
        const res = await fetch(url);
        const data = await res.json();
        if (!data.error) {
          matchOffset = data.offset + data.matches.length;
          matchHasMore = data.has_more;
          currentDdragonVersion = data.ddragon_version;
          allLoadedMatches = data.matches || [];
          renderMatchList(detailMatches, data.matches, data.ddragon_version);
          updateLoadMoreButton();
          populateMatchFilters(allLoadedMatches);
          toast(`${fetchData.new_matches} new match${fetchData.new_matches > 1 ? "es" : ""} found`);
        }
      }
    } catch (e) {
      // Background fetch failed silently — DB data is already shown
    } finally {
      // Remove indicator after a brief moment
      if (fetchIndicator.parentElement) {
        fetchIndicator.classList.add("fetch-new-done");
        fetchIndicator.innerHTML = "Up to date";
        setTimeout(() => { if (fetchIndicator.parentElement) fetchIndicator.remove(); }, 2000);
      }
    }
  }

  // Show/hide Load More button based on pagination state
  function updateLoadMoreButton() {
    if (matchHasMore) {
      loadMoreWrap.classList.remove("hidden");
    } else {
      loadMoreWrap.classList.add("hidden");
    }
  }

  function renderMatchList(container, matches, version, showAccountTag = false, append = false) {
    if (!matches || matches.length === 0) {
      if (!append) {
        container.innerHTML = '<div class="not-in-game">No ranked games found.</div>';
      }
      return;
    }
    if (!append) {
      container.innerHTML = "";
      container.className = "match-list";
    }

    const newMatchIds = [];

    matches.forEach(m => {
      const row = document.createElement("div");
      row.className = `match-row ${m.is_remake ? "remake" : (m.win ? "win" : "loss")}`;
      if (m.match_id) {
        row.dataset.matchId = m.match_id;
        newMatchIds.push(m.match_id);
      }

      let accountTag = "";
      if (showAccountTag && m.account_name) {
        accountTag = `<span class="match-account-tag">${escHtml(m.account_name.split("#")[0])}</span>`;
      }

      const ver = m.ddragon_version || version;
      // Player name: use account tag if multi-account view, otherwise current detail account
      const playerName = m.account_name
        ? m.account_name.split("#")[0]
        : (currentDetailAccount ? currentDetailAccount.game_name : "");
      const posLabel = m.position ? ({"TOP":"Top","JUNGLE":"Jg","MIDDLE":"Mid","BOTTOM":"Bot","UTILITY":"Sup","SUPPORT":"Sup"}[m.position] || m.position) : "";
      const champAndPos = m.champion_name + (posLabel ? ` · ${posLabel}` : "");

      const hasNotes = m.notes ? true : false;
      const notesIcon = hasNotes
        ? `<span class="match-notes-icon has-notes" title="Has notes">&#9998;</span>`
        : `<span class="match-notes-icon" title="Add notes">&#9998;</span>`;

      row.innerHTML = `
        <span class="match-wl-badge ${m.is_remake ? "r" : (m.win ? "w" : "l")}">${m.is_remake ? "R" : (m.win ? "W" : "L")}</span>
        <img loading="lazy" class="match-champ-img" src="https://ddragon.leagueoflegends.com/cdn/${ver}/img/champion/${m.champion_name}.png" alt="${m.champion_name}" onerror="this.style.display='none'">
        <div class="match-info">
          <div class="match-top-line">
            <span class="match-player-name">${escHtml(playerName)}</span>
            <span class="match-champ-name">${champAndPos}</span>
            <span class="match-kda"><span class="k">${m.kills}</span> / <span class="d">${m.deaths}</span> / <span class="a">${m.assists}</span></span>
            ${accountTag}
            ${notesIcon}
          </div>
          <div class="match-items">${renderItems(m.items, ver)}${renderBootsItem(m.role_bound_item, ver)}</div>
          <div class="match-bottom-line">
            <span class="match-stat"><span class="sv">${m.cs}</span> CS</span>
            <span class="match-stat"><span class="sv">${formatK(m.gold)}</span> Gold</span>
            <span class="match-stat"><span class="sv">${formatK(m.damage)}</span> Dmg</span>
            <span class="match-stat"><span class="sv">${m.vision}</span> Vis</span>
            <span class="match-meta">${m.queue_name} · ${m.game_duration_str} · ${m.date_str}</span>
            <span class="match-expand-hint">Click to expand</span>
          </div>
        </div>
      `;

      // Make row expandable to show full game detail
      if (m.match_id) {
        makeMatchRowExpandable(row, m.match_id, ver);
      }

      container.appendChild(row);
    });

    // Start background duo scanning for new match rows
    if (newMatchIds.length > 0) {
      startDuoScan(newMatchIds, container);
    }

  }

  // ---- Background Duo Scanner ----
  function startDuoScan(matchIds, container) {
    // Abort any previous scan
    if (duoScanAbort) duoScanAbort.abort();
    duoScanAbort = new AbortController();
    const signal = duoScanAbort.signal;

    // Show scanning indicator
    let indicator = container.parentElement.querySelector(".duo-scan-status");
    if (!indicator) {
      indicator = document.createElement("div");
      indicator.className = "duo-scan-status";
      container.parentElement.insertBefore(indicator, container);
    }

    let scanned = 0;
    const total = matchIds.filter(id => !duoCache.has(id)).length;
    const cachedCount = matchIds.length - total;
    if (total === 0) {
      // All cached — apply immediately, no indicator needed
      matchIds.forEach(id => applyDuoBadgeToRow(container, id, duoCache.get(id)));
      indicator.remove();
      return;
    }

    indicator.innerHTML = `<span class="spinner-sm"></span> Scanning for duos... (${scanned}/${total})`;

    (async () => {
      // Apply cached results immediately
      matchIds.forEach(id => {
        if (duoCache.has(id)) applyDuoBadgeToRow(container, id, duoCache.get(id));
      });

      for (const matchId of matchIds) {
        if (signal.aborted) { indicator.remove(); return; }
        if (duoCache.has(matchId)) continue; // already applied above

        try {
          const res = await fetch(`/api/matches/${encodeURIComponent(matchId)}/duos`, { signal });
          if (signal.aborted) { indicator.remove(); return; }
          const data = await res.json();
          duoCache.set(matchId, data);
          applyDuoBadgeToRow(container, matchId, data);
          scanned++;
          if (indicator.parentElement) {
            indicator.innerHTML = `<span class="spinner-sm"></span> Scanning for duos... (${scanned}/${total})`;
          }
        } catch (e) {
          if (e.name === "AbortError") { indicator.remove(); return; }
          scanned++;
        }
      }

      // Done scanning
      if (indicator.parentElement) {
        indicator.classList.add("duo-scan-done");
        indicator.innerHTML = `Duo scan complete`;
        setTimeout(() => { if (indicator.parentElement) indicator.remove(); }, 3000);
      }
    })();
  }

  function applyDuoBadgeToRow(container, matchId, duoData) {
    if (!duoData || !duoData.duos || duoData.duos.length === 0) return;
    const row = container.querySelector(`.match-row[data-match-id="${matchId}"]`);
    if (!row) return;

    // Remove any existing duo badges (in case of re-render)
    row.querySelectorAll(".match-duo-badge").forEach(el => el.remove());

    const topLine = row.querySelector(".match-top-line");
    if (!topLine) return;

    // Show ALL duos prominently — enemy duos are the primary use case
    duoData.duos.forEach((d, i) => {
      const colorClass = DUO_COLORS[i % DUO_COLORS.length];
      const teamLabel = d.team_id === 100 ? "Blue" : d.team_id === 200 ? "Red" : "";
      const badge = document.createElement("span");
      badge.className = `match-duo-badge ${colorClass}`;
      const wrText = d.duo_winrate ? ` ${d.duo_winrate.winrate}%` : "";
      badge.textContent = `DUO${wrText}`;
      badge.title = `${teamLabel} side duo — ${d.shared_matches} shared recent games`;
      topLine.appendChild(badge);
    });

    row.classList.add("has-duo");
  }

  function renderItems(items, version) {
    if (!items) return "";
    return items.map((id, idx) => {
      if (id && id > 0) {
        return `<img loading="lazy" class="match-item-img" src="https://ddragon.leagueoflegends.com/cdn/${version}/img/item/${id}.png" alt="Item" onerror="this.style.display='none'">`;
      }
      return `<span class="match-item-empty"></span>`;
    }).join("");
  }

  function renderBootsItem(roleBoundItem, version) {
    if (!roleBoundItem || roleBoundItem <= 0) return "";
    return `<img loading="lazy" class="match-item-img match-item-boots" src="https://ddragon.leagueoflegends.com/cdn/${version}/img/item/${roleBoundItem}.png" alt="Boots" onerror="this.style.display='none'">`;
  }

  // ---- Champions View ----
  const championFilters = document.getElementById("champion-filters");
  const championSearch = document.getElementById("champion-search");
  const championAccountFilter = document.getElementById("champion-account-filter");
  const championStatsHeader = document.getElementById("champion-stats-header");
  const roleBtns = document.querySelectorAll(".role-btn");
  let champData = null;       // current loaded champion data {champions, version}
  let champActiveRole = "all";
  let champSearchTerm = "";

  backToChampions.addEventListener("click", () => {
    championDetail.classList.add("hidden");
    championsList.style.display = "";
    championFilters.classList.remove("hidden");
  });

  // Role filter buttons
  roleBtns.forEach(btn => {
    btn.addEventListener("click", () => {
      roleBtns.forEach(b => b.classList.remove("active"));
      btn.classList.add("active");
      champActiveRole = btn.dataset.role;
      filterAndRenderChampions();
    });
  });

  // Search filter (live typing)
  championSearch.addEventListener("input", () => {
    champSearchTerm = championSearch.value.trim().toLowerCase();
    filterAndRenderChampions();
  });

  // Account filter dropdown — re-fetches from API
  championAccountFilter.addEventListener("change", () => {
    loadChampionStats();
  });

  function populateChampionAccountFilter() {
    const current = championAccountFilter.value;
    championAccountFilter.innerHTML = '<option value="">All Accounts</option>';
    if (!currentProfile || !currentProfile.accounts) return;
    currentProfile.accounts.forEach(acct => {
      const opt = document.createElement("option");
      opt.value = acct.id;
      opt.textContent = `${acct.game_name}#${acct.tag_line}`;
      championAccountFilter.appendChild(opt);
    });
    // Restore selection if still valid
    if (current && championAccountFilter.querySelector(`option[value="${current}"]`)) {
      championAccountFilter.value = current;
    }
  }

  function getChampStatsUrl() {
    let url = `/api/profiles/${currentProfileId}/stats/champions`;
    const params = [];
    const acctId = championAccountFilter.value;
    if (acctId) params.push(`account_id=${acctId}`);
    if (currentSeason) params.push(`season=${currentSeason}`);
    if (params.length) url += `?${params.join("&")}`;
    return url;
  }

  function getChampDetailUrl(champName) {
    let url = `/api/profiles/${currentProfileId}/stats/champions/${encodeURIComponent(champName)}`;
    const params = [];
    const acctId = championAccountFilter.value;
    if (acctId) params.push(`account_id=${acctId}`);
    if (currentSeason) params.push(`season=${currentSeason}`);
    if (params.length) url += `?${params.join("&")}`;
    return url;
  }

  async function loadChampionStats() {
    if (!currentProfileId) {
      championsList.innerHTML = '<div class="not-in-game">Select a profile to see champion stats.</div>';
      championFilters.classList.add("hidden");
      return;
    }

    const profileIdAtStart = currentProfileId;
    championDetail.classList.add("hidden");
    championsList.style.display = "";
    // Show spinner only if we have no cached data to display
    if (!champData) {
      championsList.innerHTML = '<div class="status-bar"><span class="spinner"></span> Loading champion stats...</div>';
    }

    populateChampionAccountFilter();

    // Step 1: Instantly load champion stats from DB (no Riot API)
    try {
      const res = await fetch(getChampStatsUrl());
      const data = await res.json();
      if (currentProfileId !== profileIdAtStart) return; // profile changed mid-load
      if (!data.error) {
        champData = { champions: data.champions, version: data.ddragon_version };
        championFilters.classList.remove("hidden");
        renderChampionStatsHeader();
        filterAndRenderChampions();
      } else {
        championsList.innerHTML = `<div class="error-bar">${data.error}</div>`;
        championFilters.classList.add("hidden");
        return;
      }
    } catch (e) {
      championsList.innerHTML = '<div class="error-bar">Failed to load champion stats</div>';
      championFilters.classList.add("hidden");
      return;
    }

    // Step 2: Background-fetch new matches from Riot API, then re-render if data changed
    try {
      await fetch(`/api/profiles/${profileIdAtStart}/matches?count=40`);
    } catch (e) { /* ignore */ }

    // Re-query stats — if new matches arrived, data will differ
    if (currentProfileId !== profileIdAtStart) return; // profile changed mid-fetch
    try {
      const res = await fetch(getChampStatsUrl());
      const data = await res.json();
      if (currentProfileId !== profileIdAtStart) return;
      if (!data.error) {
        const oldCount = champData ? champData.champions.length : 0;
        const oldGames = champData ? champData.champions.reduce((s, c) => s + c.games, 0) : 0;
        const newGames = data.champions.reduce((s, c) => s + c.games, 0);
        if (newGames !== oldGames || data.champions.length !== oldCount) {
          champData = { champions: data.champions, version: data.ddragon_version };
          renderChampionStatsHeader();
          filterAndRenderChampions();
          showToast(`Champion stats updated (+${newGames - oldGames} games)`);
        }
      }
    } catch (e) { /* ignore — initial data already displayed */ }
  }

  function renderChampionStatsHeader() {
    if (!championStatsHeader) return;
    const profileName = currentProfile ? currentProfile.name : "";
    if (!profileName) {
      championStatsHeader.innerHTML = "";
      return;
    }
    const acctList = (currentProfile.accounts || []).map(a => `${a.game_name}#${a.tag_line}`).join(", ");
    // Find current season label
    const seasonObj = allSeasons.find(s => s.key === currentSeason);
    const seasonLabel = currentSeason === "all" ? "All Seasons" : (seasonObj ? seasonObj.label : "");
    const totalGames = champData ? champData.champions.reduce((s, c) => s + c.games, 0) : 0;
    const totalChamps = champData ? champData.champions.length : 0;
    championStatsHeader.innerHTML = `
      <div class="champ-header-tracking">
        <div class="champ-header-left">
          <span class="stat-label">Tracking</span>
          <span class="champ-header-profile">${escHtml(profileName)}</span>
          <span class="champ-header-accounts">${escHtml(acctList)}</span>
        </div>
        <div class="champ-header-right">
          <span class="champ-header-season">${escHtml(seasonLabel)}</span>
          <span class="champ-header-summary">${totalChamps} champions &middot; ${totalGames} games</span>
        </div>
      </div>
    `;
  }

  function filterAndRenderChampions() {
    if (!champData) return;
    let filtered = champData.champions;

    // Role filter
    if (champActiveRole !== "all") {
      filtered = filtered.filter(c => c.position === champActiveRole);
    }

    // Search filter
    if (champSearchTerm) {
      filtered = filtered.filter(c =>
        c.champion_name.toLowerCase().includes(champSearchTerm)
      );
    }

    renderChampionsList(filtered, champData.version);
  }

  function renderChampionsList(champions, version) {
    if (!champions || champions.length === 0) {
      championsList.innerHTML = '<div class="not-in-game">No champion data matches your filters.</div>';
      return;
    }

    championsList.innerHTML = "";
    championsList.className = "champions-grid";

    champions.forEach((c, i) => {
      const card = document.createElement("div");
      card.className = "champ-card";
      card.style.animationDelay = `${Math.min(i * 30, 300)}ms`;

      const wr = c.games > 0 ? Math.round(c.wins / c.games * 100) : 0;

      let posTag = "";
      if (c.position) {
        const roleClass = "role-" + c.position.toLowerCase();
        posTag = `<span class="role-tag ${roleClass}">${c.position}</span>`;
      }

      card.innerHTML = `
        <img loading="lazy" class="champ-icon" src="https://ddragon.leagueoflegends.com/cdn/${version}/img/champion/${c.champion_name}.png" alt="${c.champion_name}" onerror="this.style.display='none'">
        <div class="champ-info">
          <div class="champ-name">${c.champion_name} ${posTag}</div>
          <div class="champ-stats-line">
            <span class="champ-stat champ-games">${c.games} games</span>
            <span class="champ-stat champ-kda">${c.avg_kills}/${c.avg_deaths}/${c.avg_assists}</span>
          </div>
        </div>
        <span class="champ-wr-badge ${wrClass(wr)}">${wr}%</span>
      `;

      card.addEventListener("click", () => {
        championFilters.classList.add("hidden");
        loadChampionDetail(c.champion_name, version);
      });
      championsList.appendChild(card);
    });
  }

  async function loadChampionDetail(champName, version) {
    championsList.style.display = "none";
    championDetail.classList.remove("hidden");
    championDetailContent.innerHTML = '<div class="status-bar"><span class="spinner"></span> Loading build data...</div>';

    try {
      const res = await fetch(getChampDetailUrl(champName));
      const data = await res.json();
      if (data.error) {
        championDetailContent.innerHTML = `<div class="error-bar">${data.error}</div>`;
        return;
      }
      renderChampionDetail(data);
    } catch (e) {
      championDetailContent.innerHTML = '<div class="error-bar">Failed to load champion detail</div>';
    }
  }

  function renderChampionDetail(data) {
    const ver = data.ddragon_version;
    const wr = data.winrate || 0;

    let html = `
      <div class="champ-detail-header">
        <img loading="lazy" class="champ-icon-large" src="https://ddragon.leagueoflegends.com/cdn/${ver}/img/champion/${data.champion_name}.png" alt="${data.champion_name}" onerror="this.style.display='none'">
        <div>
          <h2 style="font-size:1.8rem;color:var(--text-primary);margin-bottom:0.5rem">${data.champion_name}</h2>
          <div class="champ-detail-stats">
            <div class="detail-stat">
              <span class="detail-stat-val ${wrClass(wr)}">${wr}%</span>
              <span class="detail-stat-label">Win Rate</span>
            </div>
            <div class="detail-stat">
              <span class="detail-stat-val">${data.games}</span>
              <span class="detail-stat-label">Games</span>
            </div>
            <div class="detail-stat">
              <span class="detail-stat-val">${data.avg_kills}/${data.avg_deaths}/${data.avg_assists}</span>
              <span class="detail-stat-label">Avg KDA</span>
            </div>
            <div class="detail-stat">
              <span class="detail-stat-val">${formatK(data.avg_damage || 0)}</span>
              <span class="detail-stat-label">Avg Damage</span>
            </div>
            <div class="detail-stat">
              <span class="detail-stat-val">${data.avg_cs || 0}</span>
              <span class="detail-stat-label">Avg CS</span>
            </div>
          </div>
        </div>
      </div>
    `;

    // Build guide button + panel — right after header, before everything else
    html += `<div id="build-guide-btn-slot"></div>`;
    html += `<div id="build-guide-panel"></div>`;

    // Common items
    if (data.common_items && data.common_items.length > 0) {
      html += `<h3 class="section-title">Most Built Items</h3><div class="items-grid">`;
      data.common_items.forEach(item => {
        html += `
          <div class="item-stat-card">
            <img loading="lazy" class="item-icon" src="https://ddragon.leagueoflegends.com/cdn/${ver}/img/item/${item.item_id}.png" alt="Item" onerror="this.style.display='none'">
            <div class="item-stat-info">
              <span class="item-stat-wr ${wrClass(item.winrate)}">${item.winrate}% WR</span>
              <span class="item-stat-meta">${item.count}x built · ${item.pick_rate}% of games</span>
            </div>
          </div>
        `;
      });
      html += `</div>`;
    }

    // Recent matches on this champion
    if (data.matches && data.matches.length > 0) {
      html += `<h3 class="section-title">Recent Games</h3><div id="champ-match-list"></div>`;
    }

    championDetailContent.innerHTML = html;

    // Render match list in the container
    if (data.matches && data.matches.length > 0) {
      const matchContainer = document.getElementById("champ-match-list");
      renderMatchList(matchContainer, data.matches, ver);
    }

    // Check if a build guide exists for this champion and add button if so
    checkBuildGuideAvailability(data.champion_name);
  }

  // ---- Build Guide ----
  let buildGuideVisible = false;
  let _guideChampCache = null; // Set of champion names with guides
  let _guideRolesCache = {}; // champName -> [role1, role2, ...] for multi-role champs
  let _activeGuideRole = null; // Currently selected role for multi-role guides

  async function _ensureGuideChampCache() {
    if (_guideChampCache) return _guideChampCache;
    try {
      const res = await fetch("/api/build-guides");
      const data = await res.json();
      _guideChampCache = new Set((data.guides || []).map(g => g.champion_name));
    } catch (e) {
      _guideChampCache = new Set();
    }
    return _guideChampCache;
  }

  async function checkBuildGuideAvailability(champName) {
    try {
      const res = await fetch(`/api/build-guides`);
      const data = await res.json();
      const guides = data.guides || [];
      const champGuides = guides.filter(g => g.champion_name === champName);
      const slot = document.getElementById("build-guide-btn-slot");
      if (champGuides.length > 0 && slot) {
        const roles = champGuides.map(g => g.role);
        _guideRolesCache[champName] = roles;
        _activeGuideRole = roles[0]; // default to first role
        if (roles.length > 1) {
          // Multi-role: show role tabs + guide button
          let tabsHtml = `<div class="guide-role-tabs">`;
          roles.forEach(role => {
            tabsHtml += `<button class="guide-role-tab${role === _activeGuideRole ? ' active' : ''}" `
              + `data-role="${role}" onclick="window._switchGuideRole('${champName}','${role}')">${role}</button>`;
          });
          tabsHtml += `</div>`;
          slot.innerHTML = tabsHtml + `
            <button class="build-guide-btn" onclick="window._toggleBuildGuide('${champName}')">
              <span class="guide-btn-icon">&#9876;</span> Build Guide
            </button>
          `;
        } else {
          slot.innerHTML = `
            <button class="build-guide-btn" onclick="window._toggleBuildGuide('${champName}')">
              <span class="guide-btn-icon">&#9876;</span> Build Guide
            </button>
          `;
        }
      }
    } catch (e) {
      // Silently fail — no build guide button if API is down
    }
  }

  window._switchGuideRole = function(champName, role) {
    _activeGuideRole = role;
    // Update tab active states
    document.querySelectorAll(".guide-role-tab").forEach(tab => {
      tab.classList.toggle("active", tab.dataset.role === role);
    });
    // If guide is currently visible, reload with new role
    if (buildGuideVisible) {
      buildGuideVisible = false; // force reload
      window._toggleBuildGuide(champName);
    }
  };

  window._toggleBuildGuide = async function(champName) {
    const panel = document.getElementById("build-guide-panel");
    if (!panel) return;

    if (buildGuideVisible) {
      panel.innerHTML = "";
      buildGuideVisible = false;
      return;
    }

    panel.innerHTML = `<div style="color:var(--text-muted);font-size:0.8rem;padding:1rem;">Loading build guide...</div>`;

    try {
      let url = `/api/build-guide/${encodeURIComponent(champName)}`;
      if (_activeGuideRole) {
        url += `?role=${encodeURIComponent(_activeGuideRole)}`;
      }
      const res = await fetch(url);
      const guide = await res.json();
      if (guide.error) {
        panel.innerHTML = `<div class="error-bar">${guide.error}</div>`;
        return;
      }
      panel.innerHTML = renderBuildGuide(guide, champName);
      buildGuideVisible = true;
    } catch (e) {
      panel.innerHTML = `<div class="error-bar">Failed to load build guide</div>`;
    }
  };

  function renderBuildGuide(guide, champName) {
    const ver = guide.patch || "16.5.1";
    let html = `<div class="build-guide-panel">`;

    // Title, meta, and export button at top
    html += `<div class="build-guide-top-row">`;
    html += `<div>`;
    html += `<div class="build-guide-title">${guide.title}</div>`;
    html += `<div class="build-guide-meta">Patch ${guide.patch} &middot; First Principles Analysis</div>`;
    html += `</div>`;
    html += `<button class="guide-export-btn" id="guide-export-btn" onclick="window._exportBuildGuide('${champName}')">&#128203; Copy to Client</button>`;
    html += `</div>`;

    // Skill Order
    if (guide.skill_order) {
      html += `<div class="guide-section">`;
      html += `<div class="guide-section-title">Skill Order</div>`;
      html += `<div class="guide-skill-order">`;
      const skills = guide.skill_order.priority.split(" > ");
      skills.forEach((s, i) => {
        const cls = s === "R" ? "skill-r" : s === "Q" ? "skill-q" : s === "W" ? "skill-w" : "skill-e";
        html += `<span class="guide-skill-badge ${cls}">${s}</span>`;
        if (i < skills.length - 1) html += `<span class="guide-skill-arrow">&#9654;</span>`;
      });
      html += `</div>`;
      if (guide.skill_order.first_three) {
        html += `<div class="guide-skill-note">First 3 levels: ${guide.skill_order.first_three.join(" → ")}</div>`;
      }
      if (guide.skill_order.reasoning) {
        html += `<div class="guide-skill-note">${guide.skill_order.reasoning}</div>`;
      }
      html += `</div>`;
    }

    // Core Build
    if (guide.core_build) {
      html += renderBuildSection(guide.core_build, ver, "Core Build");
    }

    // First Back Variant
    if (guide.first_back_variant) {
      html += `<div class="guide-section">`;
      html += `<div class="guide-variant-label">${guide.first_back_variant.label}</div>`;
      html += renderBuildRow(guide.first_back_variant.items, guide.first_back_variant.names, ver);
      if (guide.first_back_variant.notes && guide.first_back_variant.notes.length > 0) {
        html += `<div class="guide-build-notes">`;
        guide.first_back_variant.notes.forEach(n => {
          html += `<div class="guide-build-note">${n}</div>`;
        });
        html += `</div>`;
      }
      html += `</div>`;
    }

    // 4th Item Options
    if (guide.fourth_item_options) {
      html += renderOptionSection(guide.fourth_item_options, ver);
    }

    // 5th Item Options
    if (guide.fifth_item_options) {
      html += renderOptionSection(guide.fifth_item_options, ver);
    }

    // Defensive Options
    if (guide.defensive_options) {
      html += renderDefensiveSection(guide.defensive_options, ver);
    }

    // Boots
    if (guide.boots_options) {
      html += renderOptionSection(guide.boots_options, ver);
    }

    // Power Spikes
    if (guide.power_spikes && guide.power_spikes.length > 0) {
      html += `<div class="guide-section">`;
      html += `<div class="guide-section-title">Power Spikes</div>`;
      guide.power_spikes.forEach(spike => {
        html += `
          <div class="guide-spike">
            <span class="guide-spike-marker">${spike.items}</span>
            <span class="guide-spike-text">${spike.description}</span>
          </div>
        `;
      });
      html += `</div>`;
    }

    html += `</div>`;
    return html;
  }

  function renderBuildSection(section, ver, titleOverride) {
    let html = `<div class="guide-section">`;
    html += `<div class="guide-section-title">${titleOverride || section.label}</div>`;
    html += renderBuildRow(section.items, section.names, ver);
    if (section.notes && section.notes.length > 0) {
      html += `<div class="guide-build-notes">`;
      section.notes.forEach(n => {
        html += `<div class="guide-build-note">${n}</div>`;
      });
      html += `</div>`;
    }
    html += `</div>`;
    return html;
  }

  function renderBuildRow(itemIds, itemNames, ver) {
    let html = `<div class="guide-build-row">`;
    itemIds.forEach((id, i) => {
      if (i > 0) html += `<span class="guide-item-arrow">&#8250;</span>`;
      const name = itemNames && itemNames[i] ? itemNames[i] : id;
      html += `
        <div class="guide-item">
          <img class="guide-item-img" src="https://ddragon.leagueoflegends.com/cdn/${ver}/img/item/${id}.png"
               alt="${name}" title="${name}" onerror="this.style.display='none'">
          <span class="guide-item-name">${name}</span>
        </div>
      `;
    });
    html += `</div>`;
    return html;
  }

  function renderOptionSection(section, ver) {
    let html = `<div class="guide-section">`;
    html += `<div class="guide-section-title">${section.label}</div>`;
    (section.options || section.items || []).forEach(opt => {
      const itemId = opt.item_id || opt.id;
      const name = opt.name || "";
      const when = opt.when || "";
      const why = opt.why || "";
      html += `
        <div class="guide-option-card">
          <img class="guide-item-img" src="https://ddragon.leagueoflegends.com/cdn/${ver}/img/item/${itemId}.png"
               alt="${name}" title="${name}" onerror="this.style.display='none'">
          <div class="guide-option-info">
            <span class="guide-option-name">${name}</span>
            <span class="guide-option-when">${when}</span>
            <span class="guide-option-why">${why}</span>
          </div>
        </div>
      `;
    });
    html += `</div>`;
    return html;
  }

  function renderDefensiveSection(section, ver) {
    let html = `<div class="guide-section">`;
    html += `<div class="guide-section-title">${section.label}</div>`;
    (section.items || []).forEach(opt => {
      const itemId = opt.item_id || opt.id;
      const name = opt.name || "";
      const when = opt.when || "";
      const why = opt.why || "";
      html += `
        <div class="guide-option-card">
          <img class="guide-item-img" src="https://ddragon.leagueoflegends.com/cdn/${ver}/img/item/${itemId}.png"
               alt="${name}" title="${name}" onerror="this.style.display='none'">
          <div class="guide-option-info">
            <span class="guide-option-name">${name}</span>
            <span class="guide-option-when">${when}</span>
            <span class="guide-option-why">${why}</span>
          </div>
        </div>
      `;
    });
    html += `</div>`;
    return html;
  }

  window._exportBuildGuide = async function(champName) {
    const btn = document.getElementById("guide-export-btn");
    try {
      let exportUrl = `/api/build-guide/${encodeURIComponent(champName)}/export`;
      if (_activeGuideRole) {
        exportUrl += `?role=${encodeURIComponent(_activeGuideRole)}`;
      }
      const res = await fetch(exportUrl);
      const data = await res.json();
      if (data.error) {
        showToast(data.error, true);
        return;
      }
      const jsonStr = JSON.stringify(data, null, 2);
      await navigator.clipboard.writeText(jsonStr);
      if (btn) {
        btn.classList.add("copied");
        btn.innerHTML = "&#10003; Copied to Clipboard";
        setTimeout(() => {
          btn.classList.remove("copied");
          btn.innerHTML = `&#128203; Copy to Client`;
        }, 2500);
      }
      showToast("Item set JSON copied! Paste into a .json file in your League client's item sets folder.");
    } catch (e) {
      showToast("Failed to copy — try manually", true);
    }
  };

  // Delegated click on champion icons in expanded match → navigate to champion page
  document.addEventListener("click", async (e) => {
    const icon = e.target.closest(".ep-champ-icon.guide-link");
    if (!icon) return;
    e.stopPropagation(); // Don't collapse the match panel
    const champName = icon.dataset.champion;
    if (!champName) return;

    // Switch to champions view and load the champion detail page
    switchView("champions");
    const version = champData && champData.version ? champData.version : "16.5.1";
    loadChampionDetail(champName, version);
  });

  // ---- Live Game View ----
  function renderLiveAccountPills() {
    liveAccountPills.innerHTML = "";
    if (!currentProfile || !currentProfile.accounts) return;

    currentProfile.accounts.forEach(acct => {
      const pill = document.createElement("span");
      pill.className = "account-pill";
      pill.textContent = `${acct.game_name}#${acct.tag_line}`;
      pill.addEventListener("click", () => {
        liveRiotId.value = `${acct.game_name}#${acct.tag_line}`;
        doLiveSearch(acct.puuid);
      });
      liveAccountPills.appendChild(pill);
    });
  }

  liveSearchForm.addEventListener("submit", (e) => {
    e.preventDefault();
    if (liveSearchInProgress) return;
    const riotId = liveRiotId.value.trim();
    if (!riotId || !riotId.includes("#")) return;

    // First resolve the Riot ID to get puuid
    liveSearchBtn.disabled = true;
    showLiveStatus("Resolving player...");

    fetch(`/api/search?riot_id=${encodeURIComponent(riotId)}`)
      .then(r => r.json())
      .then(data => {
        if (data.error) {
          showLiveError(data.error);
          liveSearchBtn.disabled = false;
          return;
        }
        if (!data.in_game) {
          hideLiveStatus();
          liveResults.classList.add("hidden");
          liveNotInGame.classList.remove("hidden");
          liveSearchBtn.disabled = false;
          return;
        }
        doLiveSearch(data.puuid);
      })
      .catch(() => {
        showLiveError("Failed to search. Try again.");
        liveSearchBtn.disabled = false;
      });
  });

  function closeLiveSource() {
    if (currentLiveSource) {
      try { currentLiveSource.close(); } catch (_) {}
      currentLiveSource = null;
    }
  }

  function finishLiveSearch() {
    liveSearchInProgress = false;
    currentLiveSource = null;
    liveSearchBtn.disabled = false;
    setLiveClickable(true);
  }

  function setLiveClickable(enabled) {
    // Toggle pointer-events on notification bar items and account pills
    const notifyItems = liveNotifyBar.querySelectorAll(".live-notify-item");
    const pills = liveAccountPills.querySelectorAll(".account-pill");
    const style = enabled ? "" : "none";
    const opacity = enabled ? "" : "0.5";
    notifyItems.forEach(el => { el.style.pointerEvents = style; el.style.opacity = opacity; });
    pills.forEach(el => { el.style.pointerEvents = style; el.style.opacity = opacity; });
  }

  function doLiveSearch(puuid) {
    // Guard: prevent concurrent searches
    if (liveSearchInProgress) return;
    liveSearchInProgress = true;

    // Close any existing SSE connection
    closeLiveSource();

    // Reset UI
    liveResults.classList.add("hidden");
    liveNotInGame.classList.add("hidden");
    const gameDataPanel = document.getElementById("live-game-data");
    if (gameDataPanel) gameDataPanel.classList.add("hidden");
    hideLiveError();
    showLiveStatus("Connecting...");
    liveSearchBtn.disabled = true;
    setLiveClickable(false);
    stopLiveTimer();

    const source = new EventSource(`/api/live-game/${puuid}`);
    currentLiveSource = source;
    let gotResult = false; // track whether we received the main result
    let gotCachedBuild = false; // track whether early cached_build arrived

    source.addEventListener("progress", (e) => {
      const data = JSON.parse(e.data);
      if (gotCachedBuild) {
        // Build rec is already showing — make progress subtle inline
        _showSubtleProgress(data.step);
      } else {
        showLiveStatus(data.step);
      }
    });

    // Handle early cached build recommendation (arrives before result)
    source.addEventListener("cached_build", (e) => {
      const data = JSON.parse(e.data);
      if (data.ok && data.analysis) {
        // Show live-results area early so the build bar is visible
        // while player data is still loading in the background.
        liveResults.classList.remove("hidden");
        hideLiveStatus(); // hide the big spinner
        _ensureLiveBuildContainer();
        _renderLiveBuildRecommendation(data.analysis);
        gotCachedBuild = true;
      }
    });

    source.addEventListener("result", (e) => {
      gotResult = true;
      // Don't close source yet — wait for build_recommendation event
      hideLiveStatus();
      _hideSubtleProgress();
      finishLiveSearch();
      const data = JSON.parse(e.data);
      renderLiveGame(data);

      // If analysis was already cached and included in the result, render it
      if (data.build_recommendation) {
        _renderLiveBuildRecommendation(data.build_recommendation);
        source.close();
        currentLiveSource = null;
      } else if (gotCachedBuild) {
        // Early cached_build already rendered — no need for LLM, close SSE
        source.close();
        currentLiveSource = null;
      } else {
        // Show loading placeholder — LLM is generating
        _showLiveBuildLoading();
      }
    });

    source.addEventListener("build_recommendation", (e) => {
      source.close();
      currentLiveSource = null;
      const data = JSON.parse(e.data);
      if (data.ok && data.analysis) {
        _renderLiveBuildRecommendation(data.analysis);
      } else {
        _hideLiveBuildLoading();
      }
    });

    source.addEventListener("error", (e) => {
      source.close();
      currentLiveSource = null;
      if (gotResult) {
        // SSE closed after result was already received — just hide loading
        _hideLiveBuildLoading();
        return;
      }
      hideLiveStatus();
      finishLiveSearch();
      if (e.data) {
        const data = JSON.parse(e.data);
        if (data.error && data.error.includes("not currently in a game")) {
          liveNotInGame.classList.remove("hidden");
        } else {
          showLiveError(data.error || "Connection lost.");
        }
      } else {
        showLiveError("Connection lost. Try again.");
      }
    });
  }

  function renderLiveGame(data) {
    liveNotInGame.classList.add("hidden");
    liveResults.classList.remove("hidden");

    // Show the game data panel (prediction, teams) — was hidden until data arrived
    const gameDataPanel = document.getElementById("live-game-data");
    if (gameDataPanel) gameDataPanel.classList.remove("hidden");

    liveQueue.textContent = data.queue_name;

    // Timer
    if (data.game_start_time) {
      liveGameStart = data.game_start_time;
      startLiveTimer();
    }

    // Build recommendation container (above game data panel).
    // Preserve content if early cached_build already rendered.
    _ensureLiveBuildContainer(true);

    // Prediction
    renderPrediction(data.prediction);

    // Teams — render with role-aligned paired rows
    const teams = data.teams || [];
    const blueTeam = teams.find(t => t.team_id === 100) || teams[0];
    const redTeam = teams.find(t => t.team_id === 200) || teams[1];

    renderTeamsAligned(blueTeam, redTeam, data.ddragon_version, data.searched_puuid);
  }

  function renderPrediction(pred) {
    if (!pred) { predictionPanel.innerHTML = ""; return; }

    const blueScore = pred.blue_score || 50;
    const redScore = pred.red_score || 50;
    const total = blueScore + redScore;
    const bluePct = Math.round(blueScore / total * 100);
    const redPct = 100 - bluePct;
    const confPct = Math.round((pred.confidence || 0.5) * 100);
    const predictedLabel = pred.predicted_team === 100 ? "Blue Side" : "Red Side";

    let outcomeHtml = "";
    if (pred.already_predicted) {
      outcomeHtml = `<span class="pred-outcome-badge ${pred.outcome}">${pred.outcome === "pending" ? "Awaiting Result" : pred.outcome.toUpperCase()}</span>`;
    }

    // Factor breakdown section
    let factorsHtml = "";
    const factors = pred.factors || {};
    const teamFactors = factors.team_factors;
    const playerFactors = factors.player_factors;
    const weights = factors.weights;

    if (teamFactors && weights) {
      const factorDefs = [
        { key: "rank_score", label: "Rank Score", weight: weights.rank_score },
        { key: "champion_wr", label: "Champion WR", weight: weights.champion_wr },
        { key: "recent_form", label: "Recent Form", weight: weights.recent_form },
      ];

      const blueFacs = teamFactors["100"] || {};
      const redFacs = teamFactors["200"] || {};

      factorsHtml += `
        <div class="pred-factors-toggle">
          <button class="btn-back pred-toggle-btn" id="toggle-factors">Show Factor Breakdown</button>
        </div>
        <div class="pred-factors-body hidden" id="factors-body">
          <div class="pred-factors-header">
            <span class="pf-label">Factor</span>
            <span class="pf-weight">Weight</span>
            <span class="pf-team blue">Blue</span>
            <span class="pf-team red">Red</span>
          </div>
      `;

      factorDefs.forEach(f => {
        const bv = blueFacs[f.key] ?? 50;
        const rv = redFacs[f.key] ?? 50;
        const bWin = bv > rv;
        const rWin = rv > bv;
        factorsHtml += `
          <div class="pred-factor-row">
            <span class="pf-label">${f.label}</span>
            <span class="pf-weight">${Math.round(f.weight * 100)}%</span>
            <span class="pf-val ${bWin ? "pf-ahead" : ""}">${bv.toFixed(1)}</span>
            <span class="pf-val ${rWin ? "pf-ahead" : ""}">${rv.toFixed(1)}</span>
          </div>
        `;
      });

      // Per-player breakdown
      if (playerFactors) {
        ["100", "200"].forEach(teamId => {
          const players = playerFactors[teamId] || [];
          if (!players.length) return;
          const teamLabel = teamId === "100" ? "Blue" : "Red";
          const teamClass = teamId === "100" ? "blue" : "red";
          factorsHtml += `<div class="pf-player-section"><h4 class="pf-player-header ${teamClass}">${teamLabel} Side Players</h4>`;
          // Column headers for per-player table
          factorsHtml += `
            <div class="pf-player-row pf-player-col-header">
              <span class="pf-col-label">Player</span>
              <span class="pf-col-label">Champion</span>
              <span class="pf-col-label">Rank</span>
              <span class="pf-col-label">Champ WR</span>
              <span class="pf-col-label">Form</span>
              <span class="pf-col-label">Games</span>
            </div>
          `;
          players.forEach(pl => {
            const displayName = pl.name.split("#")[0];
            const playerName = displayName === "?" ? pl.champion : displayName;
            const highWr = pl.champion_wr >= 60;
            factorsHtml += `
              <div class="pf-player-row${highWr ? " pf-high-wr" : ""}">
                <span class="pf-player-name">${escHtml(playerName)}</span>
                <span class="pf-player-champ">${escHtml(pl.champion)}</span>
                <span class="pf-player-val" title="Rank Score">${pl.rank_score.toFixed(0)}</span>
                <span class="pf-player-val pf-wr${highWr ? " pf-wr-high" : ""}" title="Champ WR">${pl.champion_wr.toFixed(0)}${highWr ? "%" : ""}</span>
                <span class="pf-player-val" title="Recent Form">${pl.recent_form.toFixed(0)}</span>
                <span class="pf-player-val" title="Champ Games">${pl.champion_games || 0}</span>
              </div>
            `;
          });
          factorsHtml += `</div>`;
        });
      }

      factorsHtml += `</div>`;
    }

    predictionPanel.innerHTML = `
      <div class="pred-header">
        <span class="pred-title">Win Prediction</span>
        ${outcomeHtml}
      </div>
      <div class="pred-bar-container">
        <span class="pred-team-label blue">Blue</span>
        <div class="pred-bar">
          <div class="pred-bar-fill blue" style="width:${bluePct}%">${bluePct}%</div>
          <div class="pred-bar-fill red" style="width:${redPct}%">${redPct}%</div>
        </div>
        <span class="pred-team-label red">Red</span>
      </div>
      <div class="pred-confidence">
        Predicted winner: <strong style="color:var(--text-primary)">${predictedLabel}</strong>
        · Confidence: ${confPct}%
        ${pred.already_predicted ? " (prediction locked from first view)" : ""}
      </div>
      ${factorsHtml}
    `;

    // Toggle button for factor breakdown
    const toggleBtn = document.getElementById("toggle-factors");
    const factorsBody = document.getElementById("factors-body");
    if (toggleBtn && factorsBody) {
      toggleBtn.addEventListener("click", () => {
        const hidden = factorsBody.classList.toggle("hidden");
        toggleBtn.textContent = hidden ? "Show Factor Breakdown" : "Hide Factor Breakdown";
      });
    }
  }

  function renderTeamsAligned(blueTeam, redTeam, version, searchedPuuid) {
    // Get both containers from the DOM
    const blueContainer = document.getElementById("live-blue-players");
    const redContainer = document.getElementById("live-red-players");

    // Clear both; we'll use a new wrapper that spans the teams-container
    blueContainer.innerHTML = "";
    redContainer.innerHTML = "";

    const bluePlayers = blueTeam ? [...blueTeam.players] : [];
    const redPlayers = redTeam ? [...redTeam.players] : [];
    const blueDuos = blueTeam ? blueTeam.duos : [];
    const redDuos = redTeam ? redTeam.duos : [];

    // Sort both by role
    bluePlayers.sort((a, b) => positionOrder(a.role) - positionOrder(b.role));
    redPlayers.sort((a, b) => positionOrder(a.role) - positionOrder(b.role));

    // Build duo maps
    function buildLiveDuoMap(duos) {
      const map = {};
      if (duos && duos.length > 0) {
        duos.forEach((d, idx) => {
          const color = DUO_COLORS[idx % DUO_COLORS.length];
          d.players.forEach(pid => {
            if (!map[pid]) map[pid] = [];
            map[pid].push({ color, duo: d });
          });
        });
      }
      return map;
    }
    const blueDuoMap = buildLiveDuoMap(blueDuos);
    const redDuoMap = buildLiveDuoMap(redDuos);

    // Render paired cards into each team's container
    // By rendering into separate containers but using align-items: stretch
    // on a paired wrapper, we keep the existing HTML structure
    const maxLen = Math.max(bluePlayers.length, redPlayers.length);
    for (let i = 0; i < maxLen; i++) {
      const bp = bluePlayers[i];
      const rp = redPlayers[i];
      // Create cards for each side, wrapped in a role-pair container
      const blueCard = bp ? createLivePlayerCard(bp, version, searchedPuuid, blueDuoMap) : createEmptyPlayerCard();
      const redCard = rp ? createLivePlayerCard(rp, version, searchedPuuid, redDuoMap) : createEmptyPlayerCard();

      // We add data attributes so CSS can align them
      blueCard.dataset.roleIdx = i;
      redCard.dataset.roleIdx = i;

      blueContainer.appendChild(blueCard);
      redContainer.appendChild(redCard);
    }

    // After rendering, sync heights of paired role rows
    requestAnimationFrame(() => syncLiveRoleHeights());
  }

  function syncLiveRoleHeights() {
    const blueCards = document.querySelectorAll("#live-blue-players .player-card");
    const redCards = document.querySelectorAll("#live-red-players .player-card");
    const maxLen = Math.max(blueCards.length, redCards.length);
    for (let i = 0; i < maxLen; i++) {
      const bc = blueCards[i];
      const rc = redCards[i];
      if (bc) bc.style.minHeight = "";
      if (rc) rc.style.minHeight = "";
      if (bc && rc) {
        const h = Math.max(bc.offsetHeight, rc.offsetHeight);
        bc.style.minHeight = h + "px";
        rc.style.minHeight = h + "px";
      }
    }
  }

  function createEmptyPlayerCard() {
    const card = document.createElement("div");
    card.className = "player-card empty-slot";
    card.innerHTML = `<span class="player-empty-text">—</span>`;
    return card;
  }

  function createLivePlayerCard(p, version, searchedPuuid, duoMap) {
    const card = document.createElement("div");
    card.className = "player-card";
    if (p.puuid === searchedPuuid) card.classList.add("searched");
    if (p.hidden) card.classList.add("hidden-player");

    const playerDuos = duoMap[p.puuid] || [];
    if (playerDuos.length > 0) {
      card.classList.add("has-duo", playerDuos[0].color);
    }

    let nameHtml;
    if (p.hidden) {
      nameHtml = `<div class="player-name">Hidden Player</div>`;
    } else {
      const opgg = `https://www.op.gg/summoners/na/${encodeURIComponent(p.game_name)}-${encodeURIComponent(p.tag_line)}`;
      const searched = p.puuid === searchedPuuid ? " is-searched" : "";
      nameHtml = `<a class="player-name${searched}" href="${opgg}" target="_blank" rel="noopener">${escHtml(p.game_name)}#${escHtml(p.tag_line)}</a>`;
    }

    let rankHtml = "";
    if (p.rank) {
      const tierLower = p.rank.tier.toLowerCase();
      rankHtml = `
        <div class="player-rank-line">
          <img loading="lazy" class="player-rank-icon" src="https://raw.communitydragon.org/latest/plugins/rcp-fe-lol-shared-components/global/default/${tierLower}.png" alt="${p.rank.tier}" onerror="this.style.display='none'">
          <span class="player-rank-text tier-${tierLower}">${p.rank.full}</span>
          <span class="player-rank-lp">${p.rank.lp} LP</span>
          <span class="player-rank-wr ${wrClass(p.rank.winrate)}">${p.rank.winrate}%</span>
        </div>
      `;
    }

    let champLineHtml = `<span class="player-champ-name">${p.champion_name}</span>`;
    if (p.role) {
      const roleClass = "role-" + p.role.toLowerCase();
      champLineHtml += `<span class="role-tag ${roleClass}">${p.role}</span>`;
    }
    if (p.champion_winrate) {
      const cw = p.champion_winrate;
      champLineHtml += `<span class="player-champ-wr ${wrClass(cw.winrate)}">${cw.winrate}% (${cw.wins}W ${cw.games - cw.wins}L)</span>`;
    }

    let duoBadgeHtml = "";
    playerDuos.forEach(({ color, duo }) => {
      const wrText = duo.duo_winrate ? ` ${duo.duo_winrate.winrate}%` : "";
      duoBadgeHtml += `<span class="duo-badge ${color}">DUO${wrText}</span>`;
    });

    let spellsHtml = "";
    [p.spell1, p.spell2].forEach(spellId => {
      const key = SPELL_IMG[spellId];
      if (key) {
        spellsHtml += `<img loading="lazy" class="spell-icon" src="https://ddragon.leagueoflegends.com/cdn/${version}/img/spell/${key}.png" alt="" onerror="this.style.display='none'">`;
      }
    });

    card.innerHTML = `
      <img loading="lazy" class="player-champ-icon" src="https://ddragon.leagueoflegends.com/cdn/${version}/img/champion/${p.champion_name}.png" alt="${p.champion_name}" onerror="this.style.display='none'">
      <div class="player-spells">${spellsHtml}</div>
      <div class="player-info">
        ${nameHtml}
        ${rankHtml}
        <div class="player-champ-line">${champLineHtml}</div>
        ${duoBadgeHtml}
      </div>
    `;

    return card;
  }

  function renderTeamPlayers(container, players, version, searchedPuuid, duos) {
    container.innerHTML = "";

    // Sort players by role: Top, Jungle, Mid, Bot, Support
    players.sort((a, b) => positionOrder(a.role) - positionOrder(b.role));

    // Build puuid -> duo color mapping
    const duoColorMap = {};
    if (duos && duos.length > 0) {
      duos.forEach((d, idx) => {
        const color = DUO_COLORS[idx % DUO_COLORS.length];
        d.players.forEach(pid => {
          if (!duoColorMap[pid]) duoColorMap[pid] = [];
          duoColorMap[pid].push({ color, duo: d });
        });
      });
    }

    players.forEach(p => {
      const card = document.createElement("div");
      card.className = "player-card";
      if (p.puuid === searchedPuuid) card.classList.add("searched");
      if (p.hidden) card.classList.add("hidden-player");

      // Apply duo color accent
      const playerDuos = duoColorMap[p.puuid] || [];
      if (playerDuos.length > 0) {
        card.classList.add("has-duo", playerDuos[0].color);
      }

      let nameHtml;
      if (p.hidden) {
        nameHtml = `<div class="player-name">Hidden Player</div>`;
      } else {
        const opgg = `https://www.op.gg/summoners/na/${encodeURIComponent(p.game_name)}-${encodeURIComponent(p.tag_line)}`;
        const searched = p.puuid === searchedPuuid ? " is-searched" : "";
        nameHtml = `<a class="player-name${searched}" href="${opgg}" target="_blank" rel="noopener">${escHtml(p.game_name)}#${escHtml(p.tag_line)}</a>`;
      }

      // Rank line
      let rankHtml = "";
      if (p.rank) {
        const tierLower = p.rank.tier.toLowerCase();
        rankHtml = `
          <div class="player-rank-line">
            <img loading="lazy" class="player-rank-icon" src="https://raw.communitydragon.org/latest/plugins/rcp-fe-lol-shared-components/global/default/${tierLower}.png" alt="${p.rank.tier}" onerror="this.style.display='none'">
            <span class="player-rank-text tier-${tierLower}">${p.rank.full}</span>
            <span class="player-rank-lp">${p.rank.lp} LP</span>
            <span class="player-rank-wr ${wrClass(p.rank.winrate)}">${p.rank.winrate}%</span>
          </div>
        `;
      }

      // Champion + role line
      let champLineHtml = `<span class="player-champ-name">${p.champion_name}</span>`;
      if (p.role) {
        const roleClass = "role-" + p.role.toLowerCase();
        champLineHtml += `<span class="role-tag ${roleClass}">${p.role}</span>`;
      }
      if (p.champion_winrate) {
        const cw = p.champion_winrate;
        champLineHtml += `<span class="player-champ-wr ${wrClass(cw.winrate)}">${cw.winrate}% (${cw.wins}W ${cw.games - cw.wins}L)</span>`;
      }

      // Duo badges
      let duoBadgeHtml = "";
      playerDuos.forEach(({ color, duo }) => {
        const wrText = duo.duo_winrate ? ` ${duo.duo_winrate.winrate}%` : "";
        duoBadgeHtml += `<span class="duo-badge ${color}">DUO${wrText}</span>`;
      });

      // Spells
      let spellsHtml = "";
      [p.spell1, p.spell2].forEach(spellId => {
        const key = SPELL_IMG[spellId];
        if (key) {
          spellsHtml += `<img loading="lazy" class="spell-icon" src="https://ddragon.leagueoflegends.com/cdn/${version}/img/spell/${key}.png" alt="" onerror="this.style.display='none'">`;
        }
      });

      card.innerHTML = `
        <img loading="lazy" class="player-champ-icon" src="https://ddragon.leagueoflegends.com/cdn/${version}/img/champion/${p.champion_name}.png" alt="${p.champion_name}" onerror="this.style.display='none'">
        <div class="player-spells">${spellsHtml}</div>
        <div class="player-info">
          ${nameHtml}
          ${rankHtml}
          <div class="player-champ-line">${champLineHtml}</div>
          ${duoBadgeHtml}
        </div>
      `;

      container.appendChild(card);
    });
  }

  // Live game timer
  function startLiveTimer() {
    stopLiveTimer();
    if (!liveGameStart) return;
    updateLiveTimerDisplay();
    liveTimerEl.classList.remove("hidden");
    liveGameTimer = setInterval(updateLiveTimerDisplay, 1000);
  }

  function stopLiveTimer() {
    if (liveGameTimer) { clearInterval(liveGameTimer); liveGameTimer = null; }
    liveTimerEl.classList.add("hidden");
  }

  function updateLiveTimerDisplay() {
    if (!liveGameStart) return;
    const elapsed = Math.max(0, Math.floor((Date.now() - liveGameStart) / 1000));
    const min = Math.floor(elapsed / 60);
    const sec = elapsed % 60;
    liveTimerEl.textContent = `${min}:${String(sec).padStart(2, "0")}`;
  }

  // Live status/error helpers
  function showLiveStatus(msg) {
    liveStatus.innerHTML = `<span class="spinner"></span> ${msg}`;
    liveStatus.classList.remove("hidden");
    liveError.classList.add("hidden");
  }
  function hideLiveStatus() { liveStatus.classList.add("hidden"); }
  function _showSubtleProgress(msg) {
    // Small, unobtrusive progress indicator below the build bar
    let el = document.getElementById("live-subtle-progress");
    if (!el) {
      el = document.createElement("div");
      el.id = "live-subtle-progress";
      el.className = "live-subtle-progress";
      const buildContainer = document.getElementById("live-build-container");
      if (buildContainer) {
        buildContainer.after(el);
      } else {
        liveStatus.after(el);
      }
    }
    el.innerHTML = `<span class="spinner-sm"></span> ${msg}`;
    el.style.display = "";
  }
  function _hideSubtleProgress() {
    const el = document.getElementById("live-subtle-progress");
    if (el) el.style.display = "none";
  }
  function showLiveError(msg) {
    liveError.textContent = msg;
    liveError.classList.remove("hidden");
    liveStatus.classList.add("hidden");
  }
  function hideLiveError() { liveError.classList.add("hidden"); }

  // ---- Predictions View ----
  let _predOffset = 0;
  let _predLimit = 20;
  let _predTotal = 0;
  let _predLoadedPreds = [];
  let _predGlobalStats = null;
  let _predFilterProfile = "all"; // "all" or profile id

  // Populate prediction profile filter dropdown from cached allProfiles
  function _populatePredFilter() {
    const sel = document.getElementById("pred-profile-filter");
    if (!sel) return;
    // Preserve current selection
    const prev = sel.value;
    sel.innerHTML = '<option value="all">All Predictions</option>';
    allProfiles.forEach(p => {
      if (p.account_count > 0) {
        const opt = document.createElement("option");
        opt.value = p.id;
        opt.textContent = p.name;
        sel.appendChild(opt);
      }
    });
    sel.value = prev || "all";
  }

  // Get account names for a profile (lowercased for matching)
  function _getFilterAccountNames(profileId) {
    const names = new Set();
    const prof = allProfiles.find(p => String(p.id) === String(profileId));
    if (prof && prof.account_names) {
      prof.account_names.forEach(n => {
        names.add(n.toLowerCase());
        names.add(n.split("#")[0].toLowerCase());
      });
    }
    return names;
  }

  // Check if a prediction involves a given set of account names
  function _predMatchesFilter(pred, filterNames) {
    if (!filterNames || filterNames.size === 0) return true;
    const allPlayers = [
      ...(Array.isArray(pred.blue_players) ? pred.blue_players : []),
      ...(Array.isArray(pred.red_players) ? pred.red_players : []),
    ];
    return allPlayers.some(pl => {
      const name = (pl.name || "").toLowerCase();
      return filterNames.has(name) || filterNames.has(name.split("#")[0]);
    });
  }

  // Filter change handler
  const _predFilterSel = document.getElementById("pred-profile-filter");
  if (_predFilterSel) {
    _predFilterSel.addEventListener("change", () => {
      _predFilterProfile = _predFilterSel.value;
      // Re-render with current loaded data (client-side filter)
      renderPredictions(_predLoadedPreds);
    });
  }

  async function loadPredictions(append = false) {
    if (!append) {
      _predOffset = 0;
      _predLoadedPreds = [];
      _populatePredFilter();
      predictionsList.innerHTML = '<div class="status-bar"><span class="spinner"></span> Loading predictions...</div>';
    }

    try {
      const res = await fetch(`/api/predictions?limit=${_predLimit}&offset=${_predOffset}`);
      const data = await res.json();

      _predTotal = data.total || 0;
      _predGlobalStats = {
        correct: data.correct || 0,
        incorrect: data.incorrect || 0,
        pending: data.pending || 0,
      };

      const newPreds = data.predictions || [];
      _predLoadedPreds = append ? _predLoadedPreds.concat(newPreds) : newPreds;
      _predOffset += newPreds.length;

      renderPredictions(_predLoadedPreds);

      // Auto-resolve any pending live predictions in background
      _autoResolvePending(_predLoadedPreds);
    } catch (e) {
      predictionsList.innerHTML = '<div class="error-bar">Failed to load predictions</div>';
    }
  }

  // Automatically resolve pending live predictions without user interaction
  async function _autoResolvePending(preds) {
    const pendingLive = preds.filter(p => p.outcome === "pending" && p.source !== "match");
    if (!pendingLive.length) return;

    let anyResolved = false;
    for (const p of pendingLive) {
      try {
        const res = await fetch(`/api/predictions/${p.id}/resolve`, { method: "POST" });
        const data = await res.json();
        if (data.outcome && data.outcome !== "pending") {
          anyResolved = true;
        }
      } catch (_) { /* ignore individual failures */ }
    }
    // If any got resolved, reload the full list to get updated data
    if (anyResolved) {
      loadPredictions();
    }
  }

  // Build set of current profile's account names for highlighting
  function getProfileAccountNames() {
    const names = new Set();
    if (currentProfile && currentProfile.accounts) {
      currentProfile.accounts.forEach(a => {
        const full = `${a.game_name}#${a.tag_line}`.toLowerCase();
        names.add(full);
        // Also add just the game_name for looser matching
        names.add(a.game_name.toLowerCase());
      });
    }
    return names;
  }

  function isOwnAccount(name, ownNames) {
    if (!name || !ownNames.size) return false;
    const lower = name.toLowerCase();
    return ownNames.has(lower) || ownNames.has(lower.split("#")[0]);
  }

  function renderPredictions(preds) {
    if (!preds || preds.length === 0) {
      predictionStats.innerHTML = "";
      predictionsList.innerHTML = `<div class="not-in-game">No predictions yet. Look up a live game or expand a match to start predicting!</div>`;
      return;
    }

    const ownNames = getProfileAccountNames();

    // Apply client-side profile filter
    let filtered = preds;
    if (_predFilterProfile && _predFilterProfile !== "all") {
      const filterNames = _getFilterAccountNames(_predFilterProfile);
      filtered = preds.filter(p => _predMatchesFilter(p, filterNames));
    }

    if (filtered.length === 0) {
      predictionStats.innerHTML = "";
      predictionsList.innerHTML = `<div class="not-in-game">No predictions found for this profile. Try "All Predictions".</div>`;
      return;
    }

    // Compute stats from filtered set (not global stats when filtering)
    let correct, incorrect, pending, total;
    if (_predFilterProfile === "all") {
      // Use server-provided global stats for "All"
      const gs = _predGlobalStats || {};
      correct = gs.correct || 0;
      incorrect = gs.incorrect || 0;
      pending = gs.pending || 0;
      total = _predTotal;
    } else {
      // Recompute from filtered list
      correct = filtered.filter(p => p.outcome === "correct").length;
      incorrect = filtered.filter(p => p.outcome === "incorrect").length;
      pending = filtered.filter(p => p.outcome === "pending").length;
      total = filtered.length;
    }
    const resolved = correct + incorrect;
    const accuracy = resolved > 0 ? Math.round(correct / resolved * 100) : 0;

    predictionStats.innerHTML = `
      <div class="stat-block">
        <span class="stat-label">Total</span>
        <span class="stat-value">${total}</span>
      </div>
      <div class="stat-block">
        <span class="stat-label">Correct</span>
        <span class="stat-value" style="color:var(--win)">${correct}</span>
      </div>
      <div class="stat-block">
        <span class="stat-label">Incorrect</span>
        <span class="stat-value" style="color:var(--loss)">${incorrect}</span>
      </div>
      <div class="stat-block">
        <span class="stat-label">Pending</span>
        <span class="stat-value" style="color:var(--gold)">${pending}</span>
      </div>
      <div class="stat-block">
        <span class="stat-label">Accuracy</span>
        <span class="stat-value ${wrClass(accuracy)}">${accuracy}%</span>
      </div>
    `;

    // List
    predictionsList.innerHTML = "";
    predictionsList.className = "predictions-list";

    filtered.forEach(p => {
      const row = document.createElement("div");
      row.className = `pred-row ${p.outcome}`;

      const date = p.created_at ? new Date(p.created_at + "Z").toLocaleDateString() : "Unknown";
      const teamLabel = p.predicted_team === 100 ? "Blue" : "Red";
      const teamClass = p.predicted_team === 100 ? "blue" : "red";

      // Source badge
      const source = p.source || "live";
      const sourceBadge = source === "match"
        ? '<span class="pred-source-badge match">POST</span>'
        : '<span class="pred-source-badge live">LIVE</span>';

      // Build teams summary with highlighting
      const blue = Array.isArray(p.blue_players) ? p.blue_players : [];
      const red = Array.isArray(p.red_players) ? p.red_players : [];

      function renderPlayerName(player) {
        const name = player.name || "?";
        const shortName = name.split("#")[0];
        if (isOwnAccount(name, ownNames)) {
          return `<span class="pred-own-player">${escHtml(shortName)}</span>`;
        }
        return escHtml(shortName);
      }

      const blueNames = blue.slice(0, 3).map(renderPlayerName).join(", ");
      const redNames = red.slice(0, 3).map(renderPlayerName).join(", ");
      const teamsHtml = `${blueNames}${blue.length > 3 ? "..." : ""} <span class="pred-vs">vs</span> ${redNames}${red.length > 3 ? "..." : ""}`;

      // Team metrics for resolved predictions
      let metricsHtml = "";
      if (p.match_teams && p.outcome !== "pending") {
        const bt = p.match_teams["100"] || {};
        const rt = p.match_teams["200"] || {};
        const bKda = `${bt.kills || 0}/${bt.deaths || 0}/${bt.assists || 0}`;
        const rKda = `${rt.kills || 0}/${rt.deaths || 0}/${rt.assists || 0}`;
        metricsHtml = `
          <div class="pred-team-metrics">
            <span class="ptm blue">${bKda} <span class="ptm-gold">${formatK(bt.gold || 0)}g</span></span>
            <span class="ptm-vs">vs</span>
            <span class="ptm red">${rKda} <span class="ptm-gold">${formatK(rt.gold || 0)}g</span></span>
          </div>
        `;
      }

      const matchId = p.resolved_match_id || p.match_id;
      const expandable = matchId ? ' pred-expandable' : '';

      row.innerHTML = `
        <div class="pred-row-main${expandable}">
          ${sourceBadge}
          <span class="pred-date">${date}</span>
          <span class="pred-teams-col">${teamsHtml}</span>
          <span class="pred-pick ${teamClass}">${teamLabel}</span>
          <span class="pred-result ${p.outcome}">${p.outcome.toUpperCase()}</span>
          ${matchId ? '<span class="pred-expand-hint">Click for details</span>' : ''}
        </div>
        ${metricsHtml}
      `;

      // Click to expand for resolved predictions with a match ID
      if (matchId) {
        row.style.cursor = "pointer";
        const expandPred = {...p, resolved_match_id: matchId};
        row.addEventListener("click", (e) => {
          togglePredExpand(row, expandPred, ownNames);
        });
      }

      predictionsList.appendChild(row);
    });

    // Load More button
    if (_predLoadedPreds.length < _predTotal) {
      const loadMoreRow = document.createElement("div");
      loadMoreRow.className = "pred-load-more";
      loadMoreRow.innerHTML = `<button class="load-more-btn" onclick="window._loadMorePredictions()">Load More (${_predLoadedPreds.length} of ${_predTotal})</button>`;
      predictionsList.appendChild(loadMoreRow);
    }
  }

  window._loadMorePredictions = function() {
    loadPredictions(true);
  };

  // ---- Prediction Expand (click a resolved prediction to see post-game) ----
  function togglePredExpand(row, pred, ownNames) {
    const existing = row.nextElementSibling;
    if (existing && existing.classList.contains("pred-expand-panel")) {
      collapsePanel(existing, row);
      return;
    }

    // Collapse any other expanded
    document.querySelectorAll(".pred-expand-panel").forEach(el => collapsePanel(el));
    document.querySelectorAll(".pred-row.pred-expanded").forEach(el => el.classList.remove("pred-expanded"));

    row.classList.add("pred-expanded");
    const panel = document.createElement("div");
    panel.className = "pred-expand-panel";
    panel.innerHTML = '<div class="expand-loading"><span class="spinner"></span> Loading match details...</div>';
    row.after(panel);

    loadPredExpand(panel, pred, ownNames);
  }

  async function loadPredExpand(panel, pred, ownNames) {
    const matchId = pred.resolved_match_id;
    try {
      const [detailRes, predRes] = await Promise.all([
        fetch(`/api/matches/${encodeURIComponent(matchId)}/detail`),
        fetch(`/api/matches/${encodeURIComponent(matchId)}/prediction`),
      ]);

      if (!detailRes.ok) {
        const errText = detailRes.status === 500 ? "Server error — please retry." : `Error ${detailRes.status}`;
        panel.innerHTML = `<div class="expand-error">${escHtml(errText)}<br><button class="retry-btn" onclick="this.closest('.pred-expand-panel').previousElementSibling.click()">Retry</button></div>`;
        return;
      }
      const detail = await detailRes.json();
      const retroPred = predRes.ok ? await predRes.json() : null;

      if (detail.error) {
        panel.innerHTML = `<div class="expand-error">${escHtml(detail.error)}</div>`;
        return;
      }

      renderPredExpand(panel, detail, pred, retroPred, ownNames);
    } catch (e) {
      const msg = e.message || "Network error";
      panel.innerHTML = `<div class="expand-error">Failed to load match details: ${escHtml(msg)}<br><button class="retry-btn" onclick="this.closest('.pred-expand-panel').previousElementSibling.click()">Retry</button></div>`;
    }
  }

  function renderPredExpand(panel, detail, pred, retroPred, ownNames) {
    const ver = detail.ddragon_version || "";
    const duration = detail.game_duration || 0;
    const durStr = `${Math.floor(duration / 60)}:${String(duration % 60).padStart(2, "0")}`;

    const participants = detail.participants || [];
    const blue = participants.filter(p => p.team_id === 100);
    const red = participants.filter(p => p.team_id === 200);
    const teams = detail.teams || {};
    const winner = detail.winning_team;

    let html = `<div class="expand-header">
      <span class="expand-queue">${escHtml(detail.queue_name || "")}</span>
      <span class="expand-dur">${durStr}</span>
    </div>`;

    // Team comparison bars
    const blueT = teams[100] || { kills: 0, damage: 0, gold: 0 };
    const redT = teams[200] || { kills: 0, damage: 0, gold: 0 };
    html += renderTeamComparisonBars(blueT, redT);

    // Teams with role-aligned rows (with own-account highlighting)
    html += renderExpandTeamsAlignedHighlighted(blue, red, ver, winner, ownNames);

    // Factor breakdown — use retroactive prediction data or the stored factors
    const factors = (retroPred && retroPred.factors) || (pred.factors) || null;
    if (factors || retroPred) {
      html += renderPredFactorBreakdown(retroPred || pred, factors);
    }

    panel.innerHTML = html;
  }

  function renderExpandTeamsAlignedHighlighted(blue, red, ver, winner, ownNames) {
    blue.sort((a, b) => positionOrder(a.position) - positionOrder(b.position));
    red.sort((a, b) => positionOrder(a.position) - positionOrder(b.position));

    // Compute max damage/gold across all 10 players for bar widths
    const allPlayers = [...blue, ...red];
    const maxDmg = Math.max(...allPlayers.map(p => p.damage || 0), 1);
    const maxGold = Math.max(...allPlayers.map(p => p.gold || 0), 1);
    // Stash on players for cell renderers
    allPlayers.forEach(p => { p._maxDmg = maxDmg; p._maxGold = maxGold; });

    const blueWon = winner === 100;
    const redWon = winner === 200;

    let html = `<div class="expand-teams-aligned">`;

    html += `<div class="eta-header-row">
      <div class="eta-team-hdr blue">
        Blue Side ${blueWon ? '<span class="expand-winner-badge">VICTORY</span>' : '<span class="expand-loser-badge">DEFEAT</span>'}
      </div>
      <div class="eta-vs">VS</div>
      <div class="eta-team-hdr red">
        Red Side ${redWon ? '<span class="expand-winner-badge">VICTORY</span>' : '<span class="expand-loser-badge">DEFEAT</span>'}
      </div>
    </div>`;

    html += `<div class="eta-col-headers">
      <div class="eta-col-hdr-team">
        <span class="eph-champ">Player</span>
        <span class="eph-kda">KDA</span>
        <span class="eph-dmg">Dmg</span>
        <span class="eph-cs">CS</span>
        <span class="eph-vis">Vis</span>
        <span class="eph-items">Items</span>
      </div>
      <div class="eta-col-hdr-vs"></div>
      <div class="eta-col-hdr-team">
        <span class="eph-champ">Player</span>
        <span class="eph-kda">KDA</span>
        <span class="eph-dmg">Dmg</span>
        <span class="eph-cs">CS</span>
        <span class="eph-vis">Vis</span>
        <span class="eph-items">Items</span>
      </div>
    </div>`;

    const maxLen = Math.max(blue.length, red.length);
    for (let i = 0; i < maxLen; i++) {
      const bp = blue[i];
      const rp = red[i];
      html += `<div class="eta-pair-row">`;
      html += bp ? renderAlignedPlayerCellHighlighted(bp, ver, ownNames) : '<div class="eta-player-cell empty"></div>';
      html += `<div class="eta-role-divider">${bp ? ({"TOP":"Top","JUNGLE":"Jg","MIDDLE":"Mid","BOTTOM":"Bot","UTILITY":"Sup","SUPPORT":"Sup"}[bp.position] || "") : ""}</div>`;
      html += rp ? renderAlignedPlayerCellHighlighted(rp, ver, ownNames) : '<div class="eta-player-cell empty"></div>';
      html += `</div>`;
    }

    html += `</div>`;
    return html;
  }

  function _opggLink(gameName, tagLine, displayName, extraClass) {
    if (!gameName) return `<span class="${extraClass || ""}">${escHtml(displayName)}</span>`;
    const url = `https://www.op.gg/summoners/na/${encodeURIComponent(gameName)}-${encodeURIComponent(tagLine || "NA1")}`;
    return `<a class="${extraClass || ""}" href="${url}" target="_blank" rel="noopener" title="${escHtml(gameName)}#${escHtml(tagLine || "")}">${escHtml(displayName)}</a>`;
  }

  function renderAlignedPlayerCellHighlighted(p, ver, ownNames) {
    const kda = `${p.kills}/${p.deaths}/${p.assists}`;
    const items = [0,1,2,3,4,5,6].map(i => p[`item${i}`] || 0);
    const shortName = (p.game_name || "").split("#")[0] || p.champion_name;
    const fullName = ((p.game_name || "") + "#" + (p.tag_line || "")).replace(/^#|#$/g, "");
    const isOwn = isOwnAccount(fullName, ownNames);
    const ownClass = isOwn ? " ep-own" : "";

    const rbi = p.role_bound_item || 0;
    return `
      <div class="eta-player-cell ${p.win ? "win" : "loss"}${ownClass}">
        <div class="ep-champ">
          <img loading="lazy" class="ep-champ-icon" src="https://ddragon.leagueoflegends.com/cdn/${ver}/img/champion/${p.champion_name}.png" alt="" onerror="this.style.display='none'">
          <div class="ep-champ-info">
            ${_opggLink(p.game_name, p.tag_line, shortName, "ep-champ-name" + (isOwn ? " ep-own-name" : ""))}
            <span class="ep-player-name">${escHtml(p.champion_name)}</span>
          </div>
        </div>
        <span class="ep-kda">${kda}</span>
        <span class="ep-dmg">
          ${formatK(p.damage || 0)}
          ${p._maxDmg ? `<div class="ep-bar"><div class="ep-bar-fill ep-bar-dmg" style="width:${Math.round((p.damage || 0) / p._maxDmg * 100)}%"></div></div>` : ""}
        </span>
        <span class="ep-cs">${p.cs || 0}<span class="ep-csm">${p.cs_per_min || 0}/m</span></span>
        <span class="ep-vis">${p.vision_score || 0}</span>
        <div class="ep-items">${items.map(id => id > 0
          ? `<img loading="lazy" class="expand-item-img" src="https://ddragon.leagueoflegends.com/cdn/${ver}/img/item/${id}.png" alt="" onerror="this.style.display='none'">`
          : `<span class="expand-item-empty"></span>`
        ).join("")}${rbi > 0 ? `<img loading="lazy" class="expand-item-img expand-item-boots" src="https://ddragon.leagueoflegends.com/cdn/${ver}/img/item/${rbi}.png" alt="Boots" onerror="this.style.display='none'">` : ""}</div>
      </div>
    `;
  }

  function renderExpandTeamHighlighted(players, ver, teamId, winner, ownNames, maxDmg, maxGold) {
    const teamClass = teamId === 100 ? "blue" : "red";
    const teamLabel = teamId === 100 ? "Blue Side" : "Red Side";
    const isWinner = teamId === winner;

    // Sort by position: Top, Jungle, Mid, Bot, Support
    players.sort((a, b) => (positionOrder(a.position) - positionOrder(b.position)));
    // Stash max values for bar rendering
    if (maxDmg) players.forEach(p => { p._maxDmg = maxDmg; p._maxGold = maxGold; });

    let html = `<div class="expand-team">
      <div class="expand-team-header ${teamClass}">
        ${teamLabel}
        ${isWinner ? '<span class="expand-winner-badge">VICTORY</span>' : '<span class="expand-loser-badge">DEFEAT</span>'}
      </div>
      <div class="expand-player-list">`;

    html += `
      <div class="expand-player-header">
        <span class="eph-champ">Player</span>
        <span class="eph-kda">KDA</span>
        <span class="eph-dmg">Damage</span>
        <span class="eph-cs">CS</span>
        <span class="eph-vis">Vis</span>
        <span class="eph-kp">KP%</span>
        <span class="eph-items">Items</span>
      </div>
    `;

    players.forEach(p => {
      const kda = `${p.kills}/${p.deaths}/${p.assists}`;
      const items = [0,1,2,3,4,5,6].map(i => p[`item${i}`] || 0);
      const pos = p.position ? ({"TOP":"Top","JUNGLE":"Jg","MIDDLE":"Mid","BOTTOM":"Bot","UTILITY":"Sup","SUPPORT":"Sup"}[p.position] || "") : "";
      const fullName = ((p.game_name || "") + "#" + (p.tag_line || "")).replace(/^#|#$/g, "");
      const shortName = (p.game_name || "").split("#")[0] || p.champion_name;
      const isOwn = isOwnAccount(fullName, ownNames);
      const ownClass = isOwn ? " ep-own" : "";

      const rbi = p.role_bound_item || 0;
      html += `
        <div class="expand-player-row ${p.win ? "win" : "loss"}${ownClass}">
          <div class="ep-champ">
            <img loading="lazy" class="ep-champ-icon" src="https://ddragon.leagueoflegends.com/cdn/${ver}/img/champion/${p.champion_name}.png" alt="" onerror="this.style.display='none'">
            <div class="ep-champ-info">
              ${_opggLink(p.game_name, p.tag_line, shortName, "ep-champ-name" + (isOwn ? " ep-own-name" : ""))}
              <span class="ep-player-name">${escHtml(p.champion_name)}${pos ? ` <span class="ep-pos">${pos}</span>` : ""}</span>
            </div>
          </div>
          <span class="ep-kda">${kda}</span>
          <span class="ep-dmg">
            ${formatK(p.damage || 0)}
            ${p._maxDmg ? `<div class="ep-bar"><div class="ep-bar-fill ep-bar-dmg" style="width:${Math.round((p.damage || 0) / p._maxDmg * 100)}%"></div></div>` : ""}
          </span>
          <span class="ep-cs">${p.cs || 0}<span class="ep-csm">${p.cs_per_min || 0}/m</span></span>
          <span class="ep-vis">${p.vision_score || 0}</span>
          <span class="ep-kp">${p.kill_participation || 0}%</span>
          <div class="ep-items">${items.map(id => id > 0
            ? `<img loading="lazy" class="expand-item-img" src="https://ddragon.leagueoflegends.com/cdn/${ver}/img/item/${id}.png" alt="" onerror="this.style.display='none'">`
            : `<span class="expand-item-empty"></span>`
          ).join("")}${rbi > 0 ? `<img loading="lazy" class="expand-item-img expand-item-boots" src="https://ddragon.leagueoflegends.com/cdn/${ver}/img/item/${rbi}.png" alt="Boots" onerror="this.style.display='none'">` : ""}</div>
        </div>
      `;
    });

    html += `</div></div>`;
    return html;
  }

  function renderPredFactorBreakdown(pred, factors, collapsed) {
    const blueScore = pred.blue_score || 50;
    const redScore = pred.red_score || 50;
    const total = blueScore + redScore;
    const bluePct = Math.round(blueScore / total * 100);
    const redPct = 100 - bluePct;
    const confPct = Math.round((pred.confidence || 0.5) * 100);
    const predictedLabel = pred.predicted_team === 100 ? "Blue Side" : "Red Side";
    const outcomeClass = pred.outcome || "pending";
    const outcomeLabel = outcomeClass.toUpperCase();
    const hiddenClass = collapsed ? " hidden" : "";
    const toggleIcon = collapsed ? "&#9654;" : "&#9660;";

    let html = `
      <div class="expand-prediction">
        <div class="expand-pred-header pred-collapsible-toggle" style="cursor:pointer;user-select:none;">
          <span class="expand-pred-title"><span class="pred-toggle-arrow">${toggleIcon}</span> Prediction Analysis</span>
          <span class="pred-outcome-badge ${outcomeClass}">${outcomeLabel}</span>
        </div>
        <div class="pred-collapsible-body${hiddenClass}">
        <div class="pred-bar-container">
          <span class="pred-team-label blue">Blue</span>
          <div class="pred-bar">
            <div class="pred-bar-fill blue" style="width:${bluePct}%">${bluePct}%</div>
            <div class="pred-bar-fill red" style="width:${redPct}%">${redPct}%</div>
          </div>
          <span class="pred-team-label red">Red</span>
        </div>
        <div class="pred-confidence">
          Predicted: <strong style="color:var(--text-primary)">${predictedLabel}</strong>
          · Confidence: ${confPct}%
        </div>
    `;

    // Factor breakdown table
    if (factors) {
      const teamFactors = factors.team_factors;
      const playerFactors = factors.player_factors;
      const weights = factors.weights;

      if (teamFactors && weights) {
        const factorDefs = [
          { key: "rank_score", label: "Rank Score", weight: weights.rank_score },
          { key: "champion_wr", label: "Champion WR", weight: weights.champion_wr },
          { key: "recent_form", label: "Recent Form", weight: weights.recent_form },
        ];

        const blueFacs = teamFactors["100"] || {};
        const redFacs = teamFactors["200"] || {};

        html += `
          <div class="pred-factors-body" style="margin-top:1rem">
            <div class="pred-factors-header">
              <span class="pf-label">Factor</span>
              <span class="pf-weight">Weight</span>
              <span class="pf-team blue">Blue</span>
              <span class="pf-team red">Red</span>
            </div>
        `;

        factorDefs.forEach(f => {
          const bv = blueFacs[f.key] ?? 50;
          const rv = redFacs[f.key] ?? 50;
          const bWin = bv > rv;
          const rWin = rv > bv;
          html += `
            <div class="pred-factor-row">
              <span class="pf-label">${f.label}</span>
              <span class="pf-weight">${Math.round(f.weight * 100)}%</span>
              <span class="pf-val ${bWin ? "pf-ahead" : ""}">${bv.toFixed(1)}</span>
              <span class="pf-val ${rWin ? "pf-ahead" : ""}">${rv.toFixed(1)}</span>
            </div>
          `;
        });

        // Per-player breakdown
        if (playerFactors) {
          ["100", "200"].forEach(teamId => {
            const players = playerFactors[teamId] || [];
            if (!players.length) return;
            const teamLabel2 = teamId === "100" ? "Blue" : "Red";
            const teamClass2 = teamId === "100" ? "blue" : "red";
            html += `<div class="pf-player-section"><h4 class="pf-player-header ${teamClass2}">${teamLabel2} Side Players</h4>`;
            // Column headers for per-player table
            html += `
              <div class="pf-player-row pf-player-col-header">
                <span class="pf-col-label">Player</span>
                <span class="pf-col-label">Champion</span>
                <span class="pf-col-label">Rank</span>
                <span class="pf-col-label">Champ WR</span>
                <span class="pf-col-label">Form</span>
                <span class="pf-col-label">Games</span>
              </div>
            `;
            players.forEach(pl => {
              const isOwn = isOwnAccount(pl.name, getProfileAccountNames());
              const displayName = pl.name.split("#")[0];
              // If name is just "?" fallback to champion name
              const playerName = displayName === "?" ? pl.champion : displayName;
              const highWr = pl.champion_wr >= 60;
              html += `
                <div class="pf-player-row${isOwn ? " pf-own" : ""}${highWr ? " pf-high-wr" : ""}">
                  <span class="pf-player-name${isOwn ? " pf-own-name" : ""}">${escHtml(playerName)}</span>
                  <span class="pf-player-champ">${escHtml(pl.champion)}</span>
                  <span class="pf-player-val" title="Rank Score">${pl.rank_score.toFixed(0)}</span>
                  <span class="pf-player-val pf-wr${highWr ? " pf-wr-high" : ""}" title="Champ WR">${pl.champion_wr.toFixed(0)}${highWr ? "%" : ""}</span>
                  <span class="pf-player-val" title="Recent Form">${pl.recent_form.toFixed(0)}</span>
                  <span class="pf-player-val" title="Champ Games">${pl.champion_games || 0}</span>
                </div>
              `;
            });
            html += `</div>`;
          });
        }

        html += `</div>`;
      }
    }

    html += `</div>`; // close pred-collapsible-body
    html += `</div>`; // close expand-prediction
    return html;
  }

  // ---- Modal helpers ----
  function showModal() {
    modalOverlay.classList.remove("hidden");
    modal.setAttribute("role", "dialog");
    modal.setAttribute("aria-modal", "true");
    // Focus first input or close button
    requestAnimationFrame(() => {
      const firstInput = modal.querySelector("input, textarea, select");
      if (firstInput) firstInput.focus();
      else modalClose.focus();
    });
  }
  function hideModal() { modalOverlay.classList.add("hidden"); modal.classList.remove("modal-wide"); }
  modalClose.addEventListener("click", hideModal);
  modalOverlay.addEventListener("click", (e) => {
    if (e.target === modalOverlay) hideModal();
  });
  // Close modal on Escape key
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && !modalOverlay.classList.contains("hidden")) {
      hideModal();
    }
  });

  // ---- Build Audit (Phase 18) ----
  // Champions known to have significant healing
  const HEALER_CHAMPS = new Set([
    "Soraka", "Yuumi", "Sona", "Nami", "Lulu", "Janna",
    "Aatrox", "DrMundo", "Fiora", "Illaoi", "Irelia", "Kayn",
    "Olaf", "Swain", "Sylas", "Vladimir", "Warwick", "Zac",
    "Briar", "Belveth",
  ]);
  // Champions considered AD assassins
  const AD_ASSASSIN_CHAMPS = new Set([
    "Zed", "Talon", "Khazix", "Rengar", "Shaco", "Qiyana", "Naafiri", "Pyke",
  ]);
  // Champions considered AP assassins
  const AP_ASSASSIN_CHAMPS = new Set([
    "Evelynn", "LeBlanc", "Fizz", "Katarina", "Akali", "Diana", "Ekko",
  ]);
  // Anti-heal items
  const ANTIHEAL_ITEMS = new Set(["3033", "3011", "3123", "3165", "3075"]);
  // Armor pen items
  const ARMOR_PEN_ITEMS = new Set(["3036", "3033", "3035"]);
  // MR pen items
  const MR_PEN_ITEMS = new Set(["3135", "3020", "4645"]);

  async function _runBuildAudit(matchId, player, participants, ver) {
    const container = document.getElementById(`build-audit-${matchId}`);
    if (!container) return;

    const champName = player.champion_name;
    // Fetch build guide for this champion
    let guide;
    try {
      const res = await fetch(`/api/build-guide/${encodeURIComponent(champName)}`);
      if (!res.ok) return; // No guide — skip audit silently
      guide = await res.json();
      if (guide.error) return;
    } catch (e) {
      return;
    }

    // Gather player's items (as strings)
    const playerItems = [0,1,2,3,4,5,6].map(i => String(player[`item${i}`] || 0)).filter(id => id !== "0");
    const bootsItem = String(player.role_bound_item || 0);
    if (bootsItem !== "0") playerItems.push(bootsItem);

    // Gather enemy team champions
    const playerTeam = player.team_id;
    const enemies = participants.filter(p => p.team_id !== playerTeam);
    const enemyChamps = enemies.map(p => p.champion_name);

    // Run audit checks
    const findings = [];

    // 1. Core items check
    if (guide.core_build && guide.core_build.items) {
      const coreItems = guide.core_build.items;
      const coreMissing = coreItems.filter(id => !playerItems.includes(id));
      const corePresent = coreItems.filter(id => playerItems.includes(id));
      if (corePresent.length === coreItems.length) {
        findings.push({ type: "good", text: "Full core build completed" });
      } else if (corePresent.length > 0) {
        const missingNames = coreMissing.map(id => _itemName(guide, id)).join(", ");
        findings.push({ type: "info", text: `Core items missing: ${missingNames}` });
      }
    }

    // 2. Enemy team has healers — did they build anti-heal?
    const enemyHealers = enemyChamps.filter(c => HEALER_CHAMPS.has(c));
    if (enemyHealers.length > 0) {
      const hasAntiHeal = playerItems.some(id => ANTIHEAL_ITEMS.has(id));
      if (hasAntiHeal) {
        findings.push({ type: "good", text: `Anti-heal built vs ${enemyHealers.join(", ")}` });
      } else {
        findings.push({ type: "warn", text: `No anti-heal vs ${enemyHealers.join(", ")} — consider Mortal Reminder or Oblivion Orb` });
      }
    }

    // 3. Enemy has AD assassins — appropriate defense?
    const enemyADAssassins = enemyChamps.filter(c => AD_ASSASSIN_CHAMPS.has(c));
    if (enemyADAssassins.length > 0 && guide.defensive_options) {
      const adDefItems = guide.defensive_options.items
        .filter(o => o.when && o.when.toLowerCase().includes("ad"))
        .map(o => o.item_id);
      const hasADDef = adDefItems.some(id => playerItems.includes(id));
      if (hasADDef) {
        findings.push({ type: "good", text: `AD defense built vs ${enemyADAssassins.join(", ")}` });
      } else if (enemyADAssassins.length >= 1) {
        findings.push({ type: "warn", text: `Consider Zhonya's or Death's Dance vs ${enemyADAssassins.join(", ")}` });
      }
    }

    // 4. Enemy has AP assassins — appropriate defense?
    const enemyAPAssassins = enemyChamps.filter(c => AP_ASSASSIN_CHAMPS.has(c));
    if (enemyAPAssassins.length > 0 && guide.defensive_options) {
      const apDefItems = guide.defensive_options.items
        .filter(o => o.when && o.when.toLowerCase().includes("ap"))
        .map(o => o.item_id);
      const hasAPDef = apDefItems.some(id => playerItems.includes(id));
      if (hasAPDef) {
        findings.push({ type: "good", text: `AP defense built vs ${enemyAPAssassins.join(", ")}` });
      } else {
        findings.push({ type: "warn", text: `Consider Maw or Banshee's vs ${enemyAPAssassins.join(", ")}` });
      }
    }

    // 5. Boots check
    if (guide.boots_options && guide.boots_options.items) {
      const recBoots = guide.boots_options.items.map(o => o.item_id);
      const hasRecBoots = recBoots.some(id => playerItems.includes(id));
      if (!hasRecBoots && bootsItem !== "0") {
        const defaultBoot = guide.boots_options.items[0];
        if (defaultBoot) {
          findings.push({ type: "info", text: `Non-standard boots — guide recommends ${defaultBoot.name}` });
        }
      }
    }

    if (findings.length === 0) return; // Nothing to show

    // Render findings
    let html = `<div class="build-audit-panel">`;
    html += `<div class="build-audit-title">&#9878; Build Audit</div>`;
    findings.forEach(f => {
      const icon = f.type === "good" ? "&#10003;" : f.type === "warn" ? "&#9888;" : "&#8505;";
      html += `<div class="audit-finding ${f.type}"><span class="audit-icon">${icon}</span> ${f.text}</div>`;
    });
    html += `</div>`;
    container.innerHTML = html;
  }

  function _itemName(guide, itemId) {
    // Try to find name from guide sections
    const sections = [guide.core_build, guide.first_back_variant, guide.defensive_options];
    for (const sec of sections) {
      if (!sec) continue;
      if (sec.names && sec.items) {
        const idx = sec.items.indexOf(itemId);
        if (idx >= 0 && sec.names[idx]) return sec.names[idx];
      }
      if (sec.items && Array.isArray(sec.items)) {
        for (const item of sec.items) {
          if (item.item_id === itemId && item.name) return item.name;
        }
      }
    }
    const optSections = [guide.fourth_item_options, guide.fifth_item_options, guide.boots_options];
    for (const sec of optSections) {
      if (!sec) continue;
      const opts = sec.options || sec.items || [];
      for (const opt of opts) {
        if ((opt.item_id === itemId || opt.id === itemId) && opt.name) return opt.name;
      }
    }
    return `Item ${itemId}`;
  }

  // ---- LLM Build Analysis (Phase 19) ----
  let _llmAvailable = null; // cached availability check
  let _llmModels = [];      // available models [{id, label}]
  let _llmDefaultModel = "claude-haiku-4-5";
  let _nameToItemId = null; // reverse map: item name (lowercase) -> item id

  function _normalizeItemName(name) {
    // Strip apostrophes, commas, periods, hyphens and collapse spaces for fuzzy matching
    return name.toLowerCase().replace(/[''.,\-]/g, "").replace(/\s+/g, " ").trim();
  }

  async function _ensureNameToItemId() {
    if (_nameToItemId) return _nameToItemId;
    const data = await ensureItemData();
    _nameToItemId = {};
    if (data && data.items) {
      for (const [id, info] of Object.entries(data.items)) {
        if (info.name) {
          // Store both exact lowercase and normalized (no punctuation) keys
          const numId = parseInt(id);
          _nameToItemId[info.name.toLowerCase()] = numId;
          _nameToItemId[_normalizeItemName(info.name)] = numId;
        }
      }
    }
    return _nameToItemId;
  }

  function _itemIconHtml(itemName, ver) {
    // Try to resolve item name to icon; fall back to text tag
    if (!_nameToItemId || !ver) {
      return `<span class="llm-rec-tag">${escHtml(itemName)}</span>`;
    }
    // Try exact lowercase first, then normalized (strips apostrophes etc.)
    let id = _nameToItemId[itemName.toLowerCase()];
    if (!id) {
      id = _nameToItemId[_normalizeItemName(itemName)];
    }
    if (id) {
      return `<img class="llm-rec-icon item-icon" src="https://ddragon.leagueoflegends.com/cdn/${ver}/img/item/${id}.png" alt="${escHtml(itemName)}" title="${escHtml(itemName)}" onerror="this.outerHTML='<span class=\\'llm-rec-tag\\'>${escHtml(itemName)}</span>'">`;
    }
    return `<span class="llm-rec-tag">${escHtml(itemName)}</span>`;
  }

  async function _checkLlmAvailable() {
    if (_llmAvailable !== null) return _llmAvailable;
    try {
      const res = await fetch("/api/analysis/status");
      const data = await res.json();
      _llmAvailable = data.available === true;
      if (data.models) _llmModels = data.models;
      if (data.default_model) _llmDefaultModel = data.default_model;
    } catch (e) {
      _llmAvailable = false;
    }
    return _llmAvailable;
  }

  async function _initLlmAnalysis(matchId, puuid, player, participants, ver) {
    const container = document.getElementById(`llm-analysis-${matchId}`);
    if (!container) return;

    // Check if LLM is available
    const available = await _checkLlmAvailable();
    if (!available) return;

    // Ensure name->id map is ready for icon rendering
    await _ensureNameToItemId();

    // Gather player's actual items for comparison display
    const actualItems = [];
    for (let i = 0; i < 7; i++) {
      const id = player[`item${i}`];
      if (id && id !== 0) actualItems.push(id);
    }
    const actualBoots = player.role_bound_item || 0;

    // Check for cached analysis first
    try {
      const res = await fetch(`/api/matches/${encodeURIComponent(matchId)}/analyze?puuid=${encodeURIComponent(puuid)}`);
      const data = await res.json();
      if (data.ok && data.analysis) {
        _renderLlmAnalysis(container, data.analysis, matchId, actualItems, actualBoots, ver, puuid, player, participants);
        _upgradeBuildAudit(matchId, data.analysis, player, participants);
        return;
      }
    } catch (e) {
      // No cached analysis — show button
    }

    // Auto-trigger analysis — no button click needed
    container.innerHTML = `
      <div class="llm-auto-loading" id="llm-loading-${matchId}">
        <span class="spinner-sm"></span> Generating AI build analysis...
      </div>
    `;

    try {
      const res = await fetch(`/api/matches/${encodeURIComponent(matchId)}/analyze`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ puuid }),
      });
      const data = await res.json();

      if (res.status === 202 && data.status === "in_progress") {
        const loadEl = document.getElementById(`llm-loading-${matchId}`);
        if (loadEl) loadEl.innerHTML = '<span class="spinner-sm"></span> Analysis in progress...';
        _pollForAnalysis(container, matchId, puuid, player, participants, ver);
        return;
      }

      if (data.ok && data.analysis) {
        _renderLlmAnalysis(container, data.analysis, matchId, actualItems, actualBoots, ver, puuid, player, participants);
        _upgradeBuildAudit(matchId, data.analysis, player, participants);
      } else {
        container.innerHTML = `<div class="llm-error">${escHtml(data.error || "Analysis failed")}</div>`;
      }
    } catch (e) {
      container.innerHTML = '<div class="llm-error">Failed to reach analysis service</div>';
    }
  }

  async function _pollForAnalysis(container, matchId, puuid, player, participants, ver) {
    const actualItems = [];
    for (let i = 0; i < 7; i++) {
      const id = player[`item${i}`];
      if (id && id !== 0) actualItems.push(id);
    }
    const actualBoots = player.role_bound_item || 0;

    for (let i = 0; i < 15; i++) {
      await new Promise(r => setTimeout(r, 2000));
      try {
        const res = await fetch(`/api/matches/${encodeURIComponent(matchId)}/analyze?puuid=${encodeURIComponent(puuid)}`);
        const data = await res.json();
        if (data.ok && data.analysis) {
          _renderLlmAnalysis(container, data.analysis, matchId, actualItems, actualBoots, ver, puuid, player, participants);
          _upgradeBuildAudit(matchId, data.analysis, player, participants);
          return;
        }
      } catch (e) {
        // keep polling
      }
    }
    container.innerHTML = '<div class="llm-error">Analysis timed out — try again</div>';
  }

  function _renderLlmAnalysis(container, analysis, matchId, actualItems, actualBoots, ver, puuid, player, participants) {
    const modelUsed = analysis._model || "claude-haiku-4-5";
    const modelLabel = _llmModels.find(m => m.id === modelUsed)?.label || modelUsed.replace("claude-", "").replace("-4-5", "");

    let html = `<div class="llm-analysis-panel">`;
    html += `<div class="llm-analysis-header">
      <span class="llm-analysis-title">&#9733; AI Build Recommendation</span>
      <span class="llm-model-tag" title="Analyzed by ${escHtml(modelUsed)}">${escHtml(modelLabel)}</span>
      <button class="llm-reanalyze-btn" id="llm-reanalyze-${matchId}" title="Re-analyze with a different model">&#8635; Re-analyze</button>
      <div class="llm-model-picker" id="llm-model-picker-${matchId}" style="display:none;"></div>
    </div>`;

    // Support both old (recommended_build) and new (recommended_build_order) keys
    const recBuild = analysis.recommended_build_order || analysis.recommended_build || [];
    const recItems = recBuild.map(r => r.item);
    if (analysis.boots) recItems.push(analysis.boots.item);

    // Actual build order from timeline (if available)
    const actualOrder = analysis.actual_build_order || [];

    // Render actual item icons — use timeline order if available, else final items
    const trinkets = new Set([3340, 3363, 3364]);
    let displayActualHtml = "";

    if (actualOrder.length > 0) {
      // Show items in actual purchase order with timestamps
      actualOrder.forEach((bo, i) => {
        if (i > 0) displayActualHtml += `<span class="llm-build-arrow">&#8250;</span>`;
        const itemId = bo.item_id;
        displayActualHtml += `<span class="llm-build-step">`;
        displayActualHtml += `<img class="llm-compare-icon item-icon" src="https://ddragon.leagueoflegends.com/cdn/${ver}/img/item/${itemId}.png" alt="${escHtml(bo.item)}" title="${escHtml(bo.item)} (${bo.time})" onerror="this.style.display='none'">`;
        displayActualHtml += `<span class="llm-build-time">${bo.time}</span>`;
        displayActualHtml += `</span>`;
      });
    } else {
      // Fallback: show final items without order
      const allActual = [...actualItems];
      if (actualBoots && actualBoots !== 0) allActual.push(actualBoots);
      const displayActual = allActual.filter(id => !trinkets.has(id));
      displayActual.forEach(id => {
        displayActualHtml += `<img class="llm-compare-icon item-icon" src="https://ddragon.leagueoflegends.com/cdn/${ver}/img/item/${id}.png" alt="${id}" onerror="this.style.display='none'">`;
      });
    }

    // Recommended build in order with arrows
    let recHtml = "";
    recBuild.forEach((r, i) => {
      if (i > 0) recHtml += `<span class="llm-build-arrow">&#8250;</span>`;
      recHtml += _itemIconHtml(r.item, ver);
    });
    if (analysis.boots) {
      if (recBuild.length > 0) recHtml += `<span class="llm-build-arrow">&#8250;</span>`;
      recHtml += _itemIconHtml(analysis.boots.item, ver);
    }

    const yourLabel = actualOrder.length > 0 ? "Your Build Order" : "Your Build";
    const recLabel = "Recommended Order";

    html += `<div class="llm-comparison">`;
    html += `<div class="llm-compare-col">`;
    html += `<div class="llm-compare-label">${yourLabel}</div>`;
    html += `<div class="llm-compare-items">${displayActualHtml}</div>`;
    html += `</div>`;
    html += `<div class="llm-compare-arrow">&#10230;</div>`;
    html += `<div class="llm-compare-col">`;
    html += `<div class="llm-compare-label">${recLabel}</div>`;
    html += `<div class="llm-compare-items">${recHtml}</div>`;
    html += `</div>`;
    html += `</div>`;

    // Build order critique (from timeline analysis)
    if (analysis.build_order_critique) {
      html += `<div class="llm-section">`;
      html += `<div class="llm-section-label">Build Order Critique</div>`;
      html += `<div class="llm-note llm-critique">${escHtml(analysis.build_order_critique)}</div>`;
      html += `</div>`;
    }

    // Item details with reasoning
    if (recBuild.length > 0) {
      html += `<div class="llm-section">`;
      html += `<div class="llm-section-label">Build Priority Reasoning</div>`;
      recBuild.forEach((item, i) => {
        html += `<div class="llm-item-row">
          <span class="llm-item-num">${i + 1}.</span>
          <span class="llm-item-name">${escHtml(item.item)}</span>
          <span class="llm-item-reason">${escHtml(item.reason)}</span>
        </div>`;
      });
      if (analysis.boots) {
        html += `<div class="llm-item-row">
          <span class="llm-item-num">&#128095;</span>
          <span class="llm-item-name">${escHtml(analysis.boots.item)}</span>
          <span class="llm-item-reason">${escHtml(analysis.boots.reason)}</span>
        </div>`;
      }
      html += `</div>`;
    }

    // Situational notes
    if (analysis.situational_notes && analysis.situational_notes.length > 0) {
      html += `<div class="llm-section">`;
      html += `<div class="llm-section-label">Situational</div>`;
      analysis.situational_notes.forEach(note => {
        html += `<div class="llm-note">${escHtml(note)}</div>`;
      });
      html += `</div>`;
    }

    // Synergy notes
    if (analysis.synergy_notes && analysis.synergy_notes.length > 0) {
      html += `<div class="llm-section">`;
      html += `<div class="llm-section-label">Team Synergies</div>`;
      analysis.synergy_notes.forEach(note => {
        html += `<div class="llm-note llm-synergy">${escHtml(note)}</div>`;
      });
      html += `</div>`;
    }

    // Verdict
    if (analysis.verdict) {
      html += `<div class="llm-verdict">${escHtml(analysis.verdict)}</div>`;
    }

    html += `</div>`;
    container.innerHTML = html;

    // Wire up re-analyze button
    const reBtn = document.getElementById(`llm-reanalyze-${matchId}`);
    const picker = document.getElementById(`llm-model-picker-${matchId}`);
    if (reBtn && picker) {
      reBtn.addEventListener("click", () => {
        if (picker.style.display === "none") {
          // Build model picker buttons
          let pickerHtml = "";
          _llmModels.forEach(m => {
            const isCurrent = m.id === modelUsed;
            pickerHtml += `<button class="llm-model-option${isCurrent ? " current" : ""}" data-model="${escHtml(m.id)}" ${isCurrent ? "disabled" : ""}>
              ${escHtml(m.label)}${isCurrent ? " (current)" : ""}
            </button>`;
          });
          picker.innerHTML = pickerHtml;
          picker.style.display = "flex";

          // Add click handlers to model options
          picker.querySelectorAll(".llm-model-option:not([disabled])").forEach(optBtn => {
            optBtn.addEventListener("click", async () => {
              const selectedModel = optBtn.getAttribute("data-model");
              picker.style.display = "none";
              reBtn.disabled = true;
              reBtn.innerHTML = '<span class="spinner-sm"></span> Re-analyzing...';

              try {
                const res = await fetch(`/api/matches/${encodeURIComponent(matchId)}/analyze`, {
                  method: "POST",
                  headers: { "Content-Type": "application/json" },
                  body: JSON.stringify({ puuid, force: true, model: selectedModel }),
                });
                const data = await res.json();

                if (res.status === 202 && data.status === "in_progress") {
                  reBtn.innerHTML = '<span class="spinner-sm"></span> In progress...';
                  _pollForAnalysis(container, matchId, puuid, player, participants, ver);
                  return;
                }

                if (data.ok && data.analysis) {
                  _renderLlmAnalysis(container, data.analysis, matchId, actualItems, actualBoots, ver, puuid, player, participants);
                  _upgradeBuildAudit(matchId, data.analysis, player, participants);
                } else {
                  reBtn.disabled = false;
                  reBtn.innerHTML = "&#8635; Re-analyze";
                  _toast(data.error || "Re-analysis failed", "error");
                }
              } catch (e) {
                reBtn.disabled = false;
                reBtn.innerHTML = "&#8635; Re-analyze";
                _toast("Failed to reach analysis service", "error");
              }
            });
          });
        } else {
          picker.style.display = "none";
        }
      });
    }
  }

  function _upgradeBuildAudit(matchId, analysis, player, participants) {
    // If we have LLM analysis, replace/supplement the static build audit
    const auditContainer = document.getElementById(`build-audit-${matchId}`);
    if (!auditContainer) return;

    const playerItems = [0,1,2,3,4,5,6].map(i => String(player[`item${i}`] || 0)).filter(id => id !== "0");
    const bootsItem = String(player.role_bound_item || 0);
    if (bootsItem !== "0") playerItems.push(bootsItem);

    const enemies = participants.filter(p => p.team_id !== player.team_id);

    // Check enemy actual items for context-aware audit
    const enemyItemIds = new Set();
    enemies.forEach(e => {
      for (let i = 0; i < 7; i++) {
        const eid = e[`item${i}`];
        if (eid) enemyItemIds.add(String(eid));
      }
      if (e.role_bound_item) enemyItemIds.add(String(e.role_bound_item));
    });

    // Common armor item IDs
    const ARMOR_ITEM_IDS = new Set(["3075", "3110", "3143", "3068", "3742", "6333", "3082"]);
    const enemyBuiltArmor = [...enemyItemIds].some(id => ARMOR_ITEM_IDS.has(id));

    const findings = [];

    // Context-aware: check if player has LDR/armor pen when enemies didn't build armor
    if (!enemyBuiltArmor && playerItems.some(id => ARMOR_PEN_ITEMS.has(id))) {
      findings.push({ type: "info", text: "Armor pen built but enemies have no significant armor items — consider a different damage item" });
    }

    // Use LLM verdict as the primary audit message
    if (analysis.verdict) {
      findings.push({ type: "info", text: analysis.verdict });
    }

    if (findings.length === 0) return;

    let html = `<div class="build-audit-panel">`;
    html += `<div class="build-audit-title">&#9878; Build Audit</div>`;
    findings.forEach(f => {
      const icon = f.type === "good" ? "&#10003;" : f.type === "warn" ? "&#9888;" : "&#8505;";
      html += `<div class="audit-finding ${f.type}"><span class="audit-icon">${icon}</span> ${f.text}</div>`;
    });
    html += `</div>`;
    auditContainer.innerHTML = html;
  }

  // ---- Live Build Recommendation (Phase 19b) ----

  function _ensureLiveBuildContainer(preserveContent) {
    // Insert the build recommendation container ABOVE the game data panel.
    // If preserveContent is falsy and container exists, clear it.
    // If preserveContent is truthy, keep existing content (e.g., early cached build).
    const existing = document.getElementById("live-build-recommendation");
    if (existing) {
      if (!preserveContent) existing.innerHTML = "";
      return;
    }
    const container = document.createElement("div");
    container.id = "live-build-recommendation";
    container.className = "live-build-recommendation";
    // Insert before the game data panel (above prediction + teams)
    const gameData = document.getElementById("live-game-data");
    if (gameData) {
      gameData.parentNode.insertBefore(container, gameData);
    } else {
      // Fallback: insert at top of live-results
      liveResults.insertBefore(container, liveResults.firstChild);
    }
  }

  function _showLiveBuildLoading() {
    const container = document.getElementById("live-build-recommendation");
    if (!container) return;
    container.innerHTML = `
      <div class="live-build-bar live-build-loading">
        <span class="live-build-bar-label">&#9733; Build Recommendation</span>
        <span class="live-build-spinner-inline"><span class="spinner"></span> Generating...</span>
      </div>
    `;
  }

  function _hideLiveBuildLoading() {
    const container = document.getElementById("live-build-recommendation");
    if (container) container.innerHTML = "";
  }

  async function _renderLiveBuildRecommendation(analysis) {
    const container = document.getElementById("live-build-recommendation");
    if (!container) return;

    // Ensure name->id map for icons
    await _ensureNameToItemId();
    const data = await ensureItemData();
    const ver = (data && data.version) || "";

    // Collect all recommended items in order.
    // New format: boots are in recommended_build_order at correct position.
    // Old format (backward compat): boots as separate field, append at end.
    const allItems = [];
    if (analysis.recommended_build_order) {
      analysis.recommended_build_order.forEach(r => allItems.push(r));
    }
    if (analysis.boots && !allItems.some(i =>
      i.item.toLowerCase().includes("boots") || i.item.toLowerCase().includes("greaves")
      || i.item.toLowerCase().includes("treads") || i.item.toLowerCase().includes("shoes")
      || i.item.toLowerCase().includes("steelcaps") || i.item.toLowerCase().includes("lucidity")
      || i.item.toLowerCase().includes("swiftmarch") || i.item.toLowerCase().includes("crushers")
      || i.item.toLowerCase().includes("gunmetal") || i.item.toLowerCase().includes("spellslinger")
      || i.item.toLowerCase().includes("crimson") || i.item.toLowerCase().includes("advance")
    )) {
      // Boots not already in the build order — append (old format)
      allItems.push(analysis.boots);
    }

    // Build the collapsed bar: label + item icons in order with arrows
    let barIconsHtml = "";
    allItems.forEach((item, i) => {
      if (i > 0) barIconsHtml += `<span class="live-build-arrow">&#8250;</span>`;
      barIconsHtml += _itemIconHtml(item.item, ver);
    });

    // Build the expanded detail section
    let detailHtml = `<div class="live-build-detail hidden">`;

    // Item reasoning — all items numbered sequentially (boots included)
    if (allItems.length > 0) {
      detailHtml += `<div class="llm-section">`;
      detailHtml += `<div class="llm-section-label">Build Order Reasoning</div>`;
      allItems.forEach((item, i) => {
        detailHtml += `<div class="llm-item-row">
          <span class="llm-item-num">${i + 1}.</span>
          <span class="llm-item-name">${escHtml(item.item)}</span>
          <span class="llm-item-reason">${escHtml(item.reason)}</span>
        </div>`;
      });
      detailHtml += `</div>`;
    }

    // First back priority
    if (analysis.first_back_priority) {
      detailHtml += `<div class="llm-section">`;
      detailHtml += `<div class="llm-section-label">First Back Priority</div>`;
      detailHtml += `<div class="llm-note llm-first-back">${escHtml(analysis.first_back_priority)}</div>`;
      detailHtml += `</div>`;
    }

    // Key matchup notes
    if (analysis.key_matchup_notes && analysis.key_matchup_notes.length > 0) {
      detailHtml += `<div class="llm-section">`;
      detailHtml += `<div class="llm-section-label">Key Matchups</div>`;
      analysis.key_matchup_notes.forEach(note => {
        detailHtml += `<div class="llm-note">${escHtml(note)}</div>`;
      });
      detailHtml += `</div>`;
    }

    // Synergy notes
    if (analysis.synergy_notes && analysis.synergy_notes.length > 0) {
      detailHtml += `<div class="llm-section">`;
      detailHtml += `<div class="llm-section-label">Team Synergies</div>`;
      analysis.synergy_notes.forEach(note => {
        detailHtml += `<div class="llm-note llm-synergy">${escHtml(note)}</div>`;
      });
      detailHtml += `</div>`;
    }

    detailHtml += `</div>`;

    container.innerHTML = `
      <div class="live-build-bar">
        <div class="live-build-bar-toggle">
          <span class="live-build-bar-label">&#9733; Recommended Build</span>
          <div class="live-build-bar-icons">${barIconsHtml}</div>
          <span class="live-build-expand-arrow">&#9660;</span>
        </div>
        ${detailHtml}
      </div>
    `;

    // Wire up toggle
    const toggle = container.querySelector(".live-build-bar-toggle");
    const detail = container.querySelector(".live-build-detail");
    const arrow = container.querySelector(".live-build-expand-arrow");
    if (toggle && detail) {
      toggle.addEventListener("click", () => {
        const isHidden = detail.classList.toggle("hidden");
        if (arrow) arrow.innerHTML = isHidden ? "&#9660;" : "&#9650;";
      });
    }
  }

  // ---- Pre-Game Recommendation in Post-Game View (Phase 19b) ----

  async function _checkPreGameRecommendation(matchId, puuid) {
    // Derive game_id from match_id (NA1_XXXXXXX -> XXXXXXX)
    const gameId = matchId.replace(/^NA1_/, "");
    if (!gameId || gameId === matchId) return; // not an NA match

    const container = document.getElementById(`pregame-rec-${matchId}`);
    if (!container) return;

    try {
      const res = await fetch(`/api/live-analysis/${encodeURIComponent(gameId)}?puuid=${encodeURIComponent(puuid)}`);
      const data = await res.json();
      if (data.ok && data.analysis) {
        _renderPreGameInPostGame(container, data.analysis);
      }
    } catch (e) {
      // No pre-game recommendation available — hide container
    }
  }

  async function _renderPreGameInPostGame(container, analysis) {
    await _ensureNameToItemId();
    const data = await ensureItemData();
    const ver = (data && data.version) || "";

    let html = `<div class="llm-analysis-panel pregame-in-postgame">`;
    html += `<div class="llm-analysis-header">
      <span class="llm-analysis-title">&#9733; Pre-Game Build Recommendation</span>
      <span class="pregame-badge">From Live Game</span>
    </div>`;

    // Recommended build order as icons
    if (analysis.recommended_build_order && analysis.recommended_build_order.length > 0) {
      html += `<div class="llm-compare-items" style="margin-bottom: 0.5rem;">`;
      analysis.recommended_build_order.forEach(item => {
        html += _itemIconHtml(item.item, ver);
      });
      if (analysis.boots) {
        html += _itemIconHtml(analysis.boots.item, ver);
      }
      html += `</div>`;
    }

    // First back priority
    if (analysis.first_back_priority) {
      html += `<div class="llm-note llm-first-back" style="margin-bottom: 0.3rem;">${escHtml(analysis.first_back_priority)}</div>`;
    }

    html += `</div>`;
    container.innerHTML = html;
  }

  // ---- Game Notes (Phase 17) ----
  function _getPlayerPuuid() {
    // From single-account view
    if (currentDetailAccount && currentDetailAccount.puuid) return currentDetailAccount.puuid;
    // From cross-account dashboard — check loaded matches
    if (allLoadedMatches.length > 0 && allLoadedMatches[0].puuid) return allLoadedMatches[0].puuid;
    return null;
  }

  function renderNotesSection(matchId, puuid) {
    return `
      <div class="expand-notes-section" id="notes-${matchId}">
        <div class="expand-notes-header">
          <span class="expand-notes-title">&#9998; Game Notes</span>
          <button class="notes-edit-btn" id="notes-edit-${matchId}">Edit</button>
        </div>
        <div class="notes-display" id="notes-display-${matchId}">
          <span class="notes-empty">No notes yet — click Edit to add.</span>
        </div>
        <div class="notes-editor hidden" id="notes-editor-${matchId}">
          <textarea class="notes-textarea" id="notes-input-${matchId}"
            placeholder="What did you learn from this game?"
            maxlength="2000"></textarea>
          <div class="notes-actions">
            <button class="notes-save-btn" id="notes-save-${matchId}">Save</button>
            <button class="notes-cancel-btn" id="notes-cancel-${matchId}">Cancel</button>
            <span class="notes-char-count" id="notes-count-${matchId}"></span>
            <span class="notes-status" id="notes-status-${matchId}"></span>
          </div>
        </div>
      </div>
    `;
  }

  async function _initNotesPanel(matchId, puuid) {
    const input = document.getElementById(`notes-input-${matchId}`);
    const saveBtn = document.getElementById(`notes-save-${matchId}`);
    const cancelBtn = document.getElementById(`notes-cancel-${matchId}`);
    const editBtn = document.getElementById(`notes-edit-${matchId}`);
    const countEl = document.getElementById(`notes-count-${matchId}`);
    const statusEl = document.getElementById(`notes-status-${matchId}`);
    const displayEl = document.getElementById(`notes-display-${matchId}`);
    const editorEl = document.getElementById(`notes-editor-${matchId}`);
    if (!input || !saveBtn || !editBtn || !editorEl) return;

    let currentNotes = ""; // track the saved notes text

    // Load existing notes
    try {
      const res = await fetch(`/api/matches/${encodeURIComponent(matchId)}/notes?puuid=${encodeURIComponent(puuid)}`);
      const data = await res.json();
      if (data.notes) {
        currentNotes = data.notes;
        _renderNotesDisplay(displayEl, data.notes);
      }
    } catch (e) { /* no existing notes */ }

    // Character counter
    input.addEventListener("input", () => {
      const len = input.value.length;
      countEl.textContent = `${len}/2000`;
      countEl.style.color = len > 1800 ? "var(--loss)" : "var(--text-dim)";
    });

    function showEditor() {
      input.value = currentNotes;
      editorEl.classList.remove("hidden");
      displayEl.classList.add("hidden");
      editBtn.classList.add("hidden");
      if (input.value) {
        countEl.textContent = `${input.value.length}/2000`;
      }
      input.focus();
    }

    function showDisplay() {
      editorEl.classList.add("hidden");
      displayEl.classList.remove("hidden");
      editBtn.classList.remove("hidden");
      statusEl.textContent = "";
    }

    // Edit button
    editBtn.addEventListener("click", showEditor);

    // Cancel button — revert to display mode
    cancelBtn.addEventListener("click", showDisplay);

    // Save handler
    saveBtn.addEventListener("click", async () => {
      const notes = input.value.trim();
      saveBtn.disabled = true;
      cancelBtn.disabled = true;
      statusEl.textContent = "Saving...";
      statusEl.style.color = "var(--text-muted)";
      try {
        const res = await fetch(`/api/matches/${encodeURIComponent(matchId)}/notes`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ puuid, notes }),
        });
        const data = await res.json();
        if (data.ok) {
          currentNotes = data.notes || "";
          _renderNotesDisplay(displayEl, data.notes);
          _updateNotesIcon(matchId, !!data.notes);
          showDisplay();
        } else {
          statusEl.textContent = data.error || "Failed";
          statusEl.style.color = "var(--loss)";
        }
      } catch (e) {
        statusEl.textContent = "Failed to save";
        statusEl.style.color = "var(--loss)";
      }
      saveBtn.disabled = false;
      cancelBtn.disabled = false;
    });
  }

  function _renderNotesDisplay(el, notes) {
    if (!el) return;
    if (!notes) {
      el.innerHTML = `<span class="notes-empty">No notes yet — click Edit to add.</span>`;
      return;
    }
    // Render: lines starting with "- " become list items, rest are paragraphs
    // Notes are already HTML-escaped from the backend
    const lines = notes.split("\n");
    let html = "";
    let inList = false;
    lines.forEach(line => {
      if (line.startsWith("- ") || line.startsWith("&amp;#45; ")) {
        if (!inList) { html += "<ul>"; inList = true; }
        const content = line.replace(/^- /, "").replace(/^&amp;#45; /, "");
        html += `<li>${content}</li>`;
      } else {
        if (inList) { html += "</ul>"; inList = false; }
        if (line.trim()) html += `<p>${line}</p>`;
      }
    });
    if (inList) html += "</ul>";
    el.innerHTML = html;
  }

  function _updateNotesIcon(matchId, hasNotes) {
    const row = document.querySelector(`.match-row[data-match-id="${matchId}"]`);
    if (!row) return;
    const icon = row.querySelector(".match-notes-icon");
    if (icon) {
      if (hasNotes) {
        icon.classList.add("has-notes");
      } else {
        icon.classList.remove("has-notes");
      }
    }
  }

  // ---- Toast ----
  let toastTimer = null;
  function showToast(msg, duration = 2500) { return toast(msg, duration); }
  function toast(msg, duration = 2500) {
    toastEl.textContent = msg;
    toastEl.classList.remove("hidden");
    toastEl.classList.add("show");
    if (toastTimer) clearTimeout(toastTimer);
    // Longer messages get more time (min 2.5s, scale with length)
    const displayTime = Math.max(duration, Math.min(msg.length * 40, 8000));
    toastTimer = setTimeout(() => {
      toastEl.classList.remove("show");
      setTimeout(() => toastEl.classList.add("hidden"), 300);
    }, displayTime);
  }

  // ---- Utility ----
  // Position sort order: Top, Jungle, Mid, Bot, Support
  // Handles both match-v5 (TOP/JUNGLE/MIDDLE/BOTTOM/UTILITY) and live (Top/Jungle/Mid/Bot/Support)
  const POS_ORDER = {
    "TOP": 0, "Top": 0,
    "JUNGLE": 1, "Jungle": 1,
    "MIDDLE": 2, "Mid": 2,
    "BOTTOM": 3, "Bot": 3,
    "UTILITY": 4, "SUPPORT": 4, "Support": 4,
  };
  function positionOrder(pos) { return POS_ORDER[pos] ?? 9; }

  function wrClass(pct) {
    if (pct >= 55) return "wr-high";
    if (pct >= 45) return "wr-mid";
    return "wr-low";
  }

  function formatK(n) {
    if (n >= 1000) return (n / 1000).toFixed(1) + "k";
    return String(n);
  }

  function escHtml(str) {
    const div = document.createElement("div");
    div.textContent = str;
    return div.innerHTML;
  }

  // ---- Item Tooltip System ----
  // Fetches item data once, then shows tooltip on hover for any .match-item-img
  const tooltip = document.createElement("div");
  tooltip.className = "item-tooltip hidden";
  document.body.appendChild(tooltip);

  async function ensureItemData() {
    if (itemDataCache) return itemDataCache;
    try {
      const res = await fetch("/api/items");
      itemDataCache = await res.json();
    } catch (e) {
      console.error("Failed to load item data:", e);
      itemDataCache = { version: "", items: {} };
    }
    return itemDataCache;
  }

  // Preload item data on first interaction
  document.addEventListener("mouseover", function onFirstHover() {
    ensureItemData();
    document.removeEventListener("mouseover", onFirstHover);
  }, { once: true });

  // Delegated tooltip handlers on document
  document.addEventListener("mouseover", (e) => {
    const img = e.target.closest(".match-item-img, .item-icon, .expand-item-img, .guide-item-img");
    if (!img || !itemDataCache) return;
    const src = img.getAttribute("src") || "";
    const match = src.match(/\/item\/(\d+)\.png/);
    if (!match) return;
    const itemId = parseInt(match[1]);
    const item = (itemDataCache.items || {})[itemId];
    if (!item) return;

    // Use full_description (actual item effect text), fall back to description (plaintext summary)
    const rawDesc = item.full_description || item.description || "";
    // Strip HTML tags but preserve line breaks
    const desc = rawDesc.replace(/<br\s*\/?>/gi, "\n").replace(/<[^>]+>/g, "").replace(/\n+/g, "\n").trim();
    const goldStr = item.gold ? `${item.gold.toLocaleString()}g` : "";

    tooltip.innerHTML = `
      <div class="tt-name">${escHtml(item.name)}</div>
      ${goldStr ? `<div class="tt-gold">${goldStr}</div>` : ""}
      ${desc ? `<div class="tt-desc">${desc.split("\n").map(l => escHtml(l)).join("<br>")}</div>` : ""}
    `;
    tooltip.classList.remove("hidden");

    const rect = img.getBoundingClientRect();
    const ttRect = tooltip.getBoundingClientRect();
    let left = rect.left + rect.width / 2 - ttRect.width / 2;
    let top = rect.top - ttRect.height - 8;

    // Keep within viewport
    if (left < 4) left = 4;
    if (left + ttRect.width > window.innerWidth - 4) left = window.innerWidth - ttRect.width - 4;
    if (top < 4) top = rect.bottom + 8; // flip below if no room above

    tooltip.style.left = `${left}px`;
    tooltip.style.top = `${top}px`;
  });

  document.addEventListener("mouseout", (e) => {
    const img = e.target.closest(".match-item-img, .item-icon, .expand-item-img, .guide-item-img");
    if (img) tooltip.classList.add("hidden");
  });

  // ---- Post-Game Expanded View ----
  // Click a match row to expand inline with full game detail + retroactive prediction

  function makeMatchRowExpandable(row, matchId, version) {
    row.style.cursor = "pointer";
    row.addEventListener("click", (e) => {
      // Don't expand if clicking a link
      if (e.target.closest("a")) return;
      toggleMatchExpand(row, matchId, version);
    });
  }

  function collapsePanel(panel, parentRow) {
    panel.style.transition = "opacity 0.18s ease, max-height 0.25s ease";
    panel.style.opacity = "0";
    panel.style.maxHeight = panel.scrollHeight + "px";
    requestAnimationFrame(() => { panel.style.maxHeight = "0"; });
    if (parentRow) parentRow.classList.remove("match-expanded");
    setTimeout(() => panel.remove(), 250);
  }

  function toggleMatchExpand(row, matchId, version) {
    const existing = row.nextElementSibling;
    if (existing && existing.classList.contains("match-expand-panel")) {
      collapsePanel(existing, row);
      expandedMatchId = null;
      return;
    }

    // Collapse any other expanded row
    document.querySelectorAll(".match-expand-panel").forEach(el => collapsePanel(el));
    document.querySelectorAll(".match-row.match-expanded").forEach(el => el.classList.remove("match-expanded"));

    row.classList.add("match-expanded");
    expandedMatchId = matchId;

    const panel = document.createElement("div");
    panel.className = "match-expand-panel";
    panel.innerHTML = '<div class="expand-loading"><span class="spinner"></span> Loading match details...</div>';
    row.after(panel);

    loadMatchExpand(panel, matchId, version);
  }

  async function loadMatchExpand(panel, matchId, version) {
    try {
      // Fetch detail + prediction immediately (both are instant DB reads)
      const [detailRes, predRes] = await Promise.all([
        fetch(`/api/matches/${encodeURIComponent(matchId)}/detail`),
        fetch(`/api/matches/${encodeURIComponent(matchId)}/prediction`),
      ]);

      if (!detailRes.ok) {
        const errText = detailRes.status === 500 ? "Server error — please retry." : `Error ${detailRes.status}`;
        panel.innerHTML = `<div class="expand-error">${escHtml(errText)}<br><button class="retry-btn" onclick="this.closest('.match-expand-panel').previousElementSibling.click()">Retry</button></div>`;
        return;
      }
      const detail = await detailRes.json();
      const prediction = predRes.ok ? await predRes.json() : null;

      if (detail.error) {
        panel.innerHTML = `<div class="expand-error">${escHtml(detail.error)}<br><button class="retry-btn" onclick="this.closest('.match-expand-panel').previousElementSibling.click()">Retry</button></div>`;
        return;
      }

      // Render immediately with no duo data — duos load in background
      const cachedDuos = duoCache.has(matchId) ? duoCache.get(matchId) : null;
      renderMatchExpand(panel, detail, prediction, version, cachedDuos);

      // Fetch duos in background (may involve API calls — don't block render)
      if (!cachedDuos) {
        fetch(`/api/matches/${encodeURIComponent(matchId)}/duos`)
          .then(r => r.json())
          .then(duoData => {
            if (duoData && !duoData.error) {
              duoCache.set(matchId, duoData);
              // Re-render with duo data if panel is still open
              if (panel.isConnected) {
                renderMatchExpand(panel, detail, prediction, version, duoData);
              }
            }
          })
          .catch(() => {}); // silently fail — duos are non-critical
      }
    } catch (e) {
      const msg = e.message || "Network error";
      panel.innerHTML = `<div class="expand-error">Failed to load match details: ${escHtml(msg)}<br><button class="retry-btn" onclick="this.closest('.match-expand-panel').previousElementSibling.click()">Retry</button></div>`;
    }
  }

  function renderMatchExpand(panel, detail, prediction, fallbackVersion, duoData) {
    const ver = detail.ddragon_version || fallbackVersion;
    const duration = detail.game_duration || 0;
    const durStr = `${Math.floor(duration / 60)}:${String(duration % 60).padStart(2, "0")}`;
    const dateStr = detail.game_start
      ? new Date(detail.game_start).toLocaleDateString()
      : "";

    const participants = detail.participants || [];
    const blue = participants.filter(p => p.team_id === 100);
    const red = participants.filter(p => p.team_id === 200);
    const teams = detail.teams || {};
    const winner = detail.winning_team;

    // Organize duos by team
    const duosByTeam = { 100: [], 200: [] };
    if (duoData && duoData.duos) {
      duoData.duos.forEach(d => {
        if (d.team_id) duosByTeam[d.team_id].push(d);
      });
    }

    const playerPuuid = _getPlayerPuuid();

    let html = `<div class="expand-header">
      <span class="expand-queue">${escHtml(detail.queue_name || "")}</span>
      <span class="expand-dur">${durStr}</span>
      ${dateStr ? `<span class="expand-date">${dateStr}</span>` : ""}
    </div>`;

    // Game notes at the very top, then pre-game rec + build audit + AI analysis
    if (playerPuuid) {
      html += renderNotesSection(detail.match_id, playerPuuid);
    }

    html += `<div id="pregame-rec-${detail.match_id}" class="pregame-rec-section"></div>`;
    html += `<div id="build-audit-${detail.match_id}"></div>`;
    html += `<div id="llm-analysis-${detail.match_id}" class="llm-analysis-section"></div>`;
    html += `<div id="game-analysis-${detail.match_id}" class="game-analysis-section"></div>`;

    // Team comparison bars
    const blueT = teams[100] || { kills: 0, damage: 0, gold: 0 };
    const redT = teams[200] || { kills: 0, damage: 0, gold: 0 };
    html += renderTeamComparisonBars(blueT, redT);

    // Teams with role-aligned rows
    html += renderExpandTeamsAligned(blue, red, ver, winner, duosByTeam);

    // Retroactive prediction with full factor breakdown (collapsed by default)
    if (prediction && !prediction.error) {
      const factors = prediction.factors || null;
      html += renderPredFactorBreakdown(prediction, factors, true);
    }

    panel.innerHTML = html;

    // Wire up prediction analysis toggle
    panel.querySelectorAll(".pred-collapsible-toggle").forEach(toggle => {
      toggle.addEventListener("click", () => {
        const body = toggle.nextElementSibling;
        if (!body) return;
        const isHidden = body.classList.toggle("hidden");
        const arrow = toggle.querySelector(".pred-toggle-arrow");
        if (arrow) arrow.innerHTML = isHidden ? "&#9654;" : "&#9660;";
      });
    });

    // Initialize notes UI after DOM insertion
    if (playerPuuid) {
      _initNotesPanel(detail.match_id, playerPuuid);
    }

    // Run build audit async + initialize LLM analysis + check pre-game recommendation
    if (playerPuuid) {
      const player = participants.find(p => p.puuid === playerPuuid);
      if (player) {
        _runBuildAudit(detail.match_id, player, participants, ver);
        _initLlmAnalysis(detail.match_id, playerPuuid, player, participants, ver);
        _initGameAnalysis(detail.match_id, playerPuuid);
        _checkPreGameRecommendation(detail.match_id, playerPuuid);
      }
    }
  }

  function renderTeamComparisonBars(blue, red) {
    const bars = [
      { label: "Kills", bVal: blue.kills, rVal: red.kills },
      { label: "Damage", bVal: blue.damage, rVal: red.damage },
      { label: "Gold", bVal: blue.gold, rVal: red.gold },
    ];

    let html = '<div class="expand-comparison">';
    bars.forEach(b => {
      const total = (b.bVal + b.rVal) || 1;
      const bPct = Math.round(b.bVal / total * 100);
      const rPct = 100 - bPct;
      html += `
        <div class="comp-row">
          <span class="comp-val blue">${formatK(b.bVal)}</span>
          <div class="comp-bar">
            <div class="comp-fill blue" style="width:${bPct}%"></div>
            <div class="comp-fill red" style="width:${rPct}%"></div>
          </div>
          <span class="comp-val red">${formatK(b.rVal)}</span>
          <span class="comp-label">${b.label}</span>
        </div>
      `;
    });
    html += '</div>';
    return html;
  }

  function renderExpandTeamsAligned(blue, red, ver, winner, duosByTeam) {
    // Sort both teams by position
    blue.sort((a, b) => positionOrder(a.position) - positionOrder(b.position));
    red.sort((a, b) => positionOrder(a.position) - positionOrder(b.position));

    const blueWon = winner === 100;
    const redWon = winner === 200;

    // Build duo color maps for each team
    function buildDuoMap(duos) {
      const map = {};
      if (duos && duos.length > 0) {
        duos.forEach((d, idx) => {
          const color = DUO_COLORS[idx % DUO_COLORS.length];
          d.players.forEach(pid => {
            if (!map[pid]) map[pid] = [];
            map[pid].push({ color, duo: d });
          });
        });
      }
      return map;
    }
    const blueDuoMap = buildDuoMap(duosByTeam[100]);
    const redDuoMap = buildDuoMap(duosByTeam[200]);

    let html = `<div class="expand-teams-aligned">`;

    // Team headers row
    html += `<div class="eta-header-row">
      <div class="eta-team-hdr blue">
        Blue Side ${blueWon ? '<span class="expand-winner-badge">VICTORY</span>' : '<span class="expand-loser-badge">DEFEAT</span>'}
      </div>
      <div class="eta-vs">VS</div>
      <div class="eta-team-hdr red">
        Red Side ${redWon ? '<span class="expand-winner-badge">VICTORY</span>' : '<span class="expand-loser-badge">DEFEAT</span>'}
      </div>
    </div>`;

    // Column headers row
    html += `<div class="eta-col-headers">
      <div class="eta-col-hdr-team">
        <span class="eph-champ">Player</span>
        <span class="eph-kda">KDA</span>
        <span class="eph-dmg">Dmg</span>
        <span class="eph-cs">CS</span>
        <span class="eph-vis">Vis</span>
        <span class="eph-items">Items</span>
      </div>
      <div class="eta-col-hdr-vs"></div>
      <div class="eta-col-hdr-team">
        <span class="eph-champ">Player</span>
        <span class="eph-kda">KDA</span>
        <span class="eph-dmg">Dmg</span>
        <span class="eph-cs">CS</span>
        <span class="eph-vis">Vis</span>
        <span class="eph-items">Items</span>
      </div>
    </div>`;

    // Paired player rows (position-by-position)
    const maxLen = Math.max(blue.length, red.length);
    for (let i = 0; i < maxLen; i++) {
      const bp = blue[i];
      const rp = red[i];
      html += `<div class="eta-pair-row">`;
      html += bp ? renderAlignedPlayerCell(bp, ver, blueDuoMap) : '<div class="eta-player-cell empty"></div>';
      html += `<div class="eta-role-divider">${bp ? ({"TOP":"Top","JUNGLE":"Jg","MIDDLE":"Mid","BOTTOM":"Bot","UTILITY":"Sup","SUPPORT":"Sup"}[bp.position] || "") : ""}</div>`;
      html += rp ? renderAlignedPlayerCell(rp, ver, redDuoMap) : '<div class="eta-player-cell empty"></div>';
      html += `</div>`;
    }

    html += `</div>`;
    return html;
  }

  function renderAlignedPlayerCell(p, ver, duoMap) {
    const kda = `${p.kills}/${p.deaths}/${p.assists}`;
    const items = [0,1,2,3,4,5,6].map(i => p[`item${i}`] || 0);
    const name = (p.game_name || "").split("#")[0] || p.champion_name;
    const playerDuos = duoMap[p.puuid] || [];
    const duoClass = playerDuos.length > 0 ? ` has-duo ${playerDuos[0].color}` : "";

    let duoBadgeHtml = "";
    playerDuos.forEach(({ color, duo }) => {
      const wrText = duo.duo_winrate ? ` ${duo.duo_winrate.winrate}%` : "";
      duoBadgeHtml += `<span class="duo-badge ${color}">DUO${wrText}</span>`;
    });

    const rbi = p.role_bound_item || 0;
    return `
      <div class="eta-player-cell ${p.win ? "win" : "loss"}${duoClass}">
        <div class="ep-champ">
          <img loading="lazy" class="ep-champ-icon guide-link" data-champion="${p.champion_name}" src="https://ddragon.leagueoflegends.com/cdn/${ver}/img/champion/${p.champion_name}.png" alt="${p.champion_name}" title="View ${p.champion_name} build guide" onerror="this.style.display='none'">
           <div class="ep-champ-info">
            ${_opggLink(p.game_name, p.tag_line, name, "ep-champ-name")}
            <span class="ep-player-name">${escHtml(p.champion_name)}</span>
            ${duoBadgeHtml}

          </div>
        </div>
        <span class="ep-kda">${kda}</span>
        <span class="ep-dmg">${formatK(p.damage || 0)}</span>
        <span class="ep-cs">${p.cs || 0}<span class="ep-csm">${p.cs_per_min || 0}/m</span></span>
        <span class="ep-vis">${p.vision_score || 0}</span>
        <div class="ep-items">${items.map(id => id > 0
          ? `<img loading="lazy" class="expand-item-img" src="https://ddragon.leagueoflegends.com/cdn/${ver}/img/item/${id}.png" alt="" onerror="this.style.display='none'">`
          : `<span class="expand-item-empty"></span>`
        ).join("")}${rbi > 0 ? `<img loading="lazy" class="expand-item-img expand-item-boots" src="https://ddragon.leagueoflegends.com/cdn/${ver}/img/item/${rbi}.png" alt="Boots" onerror="this.style.display='none'">` : ""}</div>
      </div>
    `;
  }

  function renderExpandTeam(players, ver, teamId, winner, duos) {
    const teamClass = teamId === 100 ? "blue" : "red";
    const teamLabel = teamId === 100 ? "Blue Side" : "Red Side";
    const isWinner = teamId === winner;

    // Sort by position: Top, Jungle, Mid, Bot, Support
    players.sort((a, b) => (positionOrder(a.position) - positionOrder(b.position)));

    // Build puuid -> duo color mapping for this team
    const duoColorMap = {};
    if (duos && duos.length > 0) {
      duos.forEach((d, idx) => {
        const color = DUO_COLORS[idx % DUO_COLORS.length];
        d.players.forEach(pid => {
          if (!duoColorMap[pid]) duoColorMap[pid] = [];
          duoColorMap[pid].push({ color, duo: d });
        });
      });
    }

    let html = `<div class="expand-team">
      <div class="expand-team-header ${teamClass}">
        ${teamLabel}
        ${isWinner ? '<span class="expand-winner-badge">VICTORY</span>' : '<span class="expand-loser-badge">DEFEAT</span>'}
      </div>
      <div class="expand-player-list">`;

    // Column headers
    html += `
      <div class="expand-player-header">
        <span class="eph-champ">Player</span>
        <span class="eph-kda">KDA</span>
        <span class="eph-dmg">Damage</span>
        <span class="eph-cs">CS</span>
        <span class="eph-vis">Vis</span>
        <span class="eph-kp">KP%</span>
        <span class="eph-items">Items</span>
      </div>
    `;

    players.forEach(p => {
      const kda = `${p.kills}/${p.deaths}/${p.assists}`;
      const items = [0,1,2,3,4,5,6].map(i => p[`item${i}`] || 0);
      const pos = p.position ? ({"TOP":"Top","JUNGLE":"Jg","MIDDLE":"Mid","BOTTOM":"Bot","UTILITY":"Sup","SUPPORT":"Sup"}[p.position] || "") : "";
      const name = (p.game_name || "").split("#")[0] || p.champion_name;
      const playerDuos = duoColorMap[p.puuid] || [];
      const rowDuoClass = playerDuos.length > 0 ? ` has-duo ${playerDuos[0].color}` : "";

      // Build duo badge HTML for this player
      let duoBadgeHtml = "";
      playerDuos.forEach(({ color, duo }) => {
        const wrText = duo.duo_winrate ? ` ${duo.duo_winrate.winrate}%` : "";
        duoBadgeHtml += `<span class="duo-badge ${color}">DUO${wrText}</span>`;
      });

      const rbi = p.role_bound_item || 0;
      html += `
        <div class="expand-player-row ${p.win ? "win" : "loss"}${rowDuoClass}">
          <div class="ep-champ">
            <img loading="lazy" class="ep-champ-icon" src="https://ddragon.leagueoflegends.com/cdn/${ver}/img/champion/${p.champion_name}.png" alt="" onerror="this.style.display='none'">
            <div class="ep-champ-info">
              ${_opggLink(p.game_name, p.tag_line, name, "ep-champ-name")}
              <span class="ep-player-name">${escHtml(p.champion_name)}${pos ? ` <span class="ep-pos">${pos}</span>` : ""}</span>
              ${duoBadgeHtml}
            </div>
          </div>
          <span class="ep-kda">${kda}</span>
          <span class="ep-dmg">${formatK(p.damage || 0)}</span>
          <span class="ep-cs">${p.cs || 0}<span class="ep-csm">${p.cs_per_min || 0}/m</span></span>
          <span class="ep-vis">${p.vision_score || 0}</span>
          <span class="ep-kp">${p.kill_participation || 0}%</span>
          <div class="ep-items">${items.map(id => id > 0
            ? `<img loading="lazy" class="expand-item-img" src="https://ddragon.leagueoflegends.com/cdn/${ver}/img/item/${id}.png" alt="" onerror="this.style.display='none'">`
            : `<span class="expand-item-empty"></span>`
          ).join("")}${rbi > 0 ? `<img loading="lazy" class="expand-item-img expand-item-boots" src="https://ddragon.leagueoflegends.com/cdn/${ver}/img/item/${rbi}.png" alt="Boots" onerror="this.style.display='none'">` : ""}</div>
        </div>
      `;
    });

    html += `</div></div>`;
    return html;
  }

  function renderExpandPrediction(pred) {
    const blueScore = pred.blue_score || 50;
    const redScore = pred.red_score || 50;
    const total = blueScore + redScore;
    const bluePct = Math.round(blueScore / total * 100);
    const redPct = 100 - bluePct;
    const confPct = Math.round((pred.confidence || 0.5) * 100);
    const predictedLabel = pred.predicted_team === 100 ? "Blue Side" : "Red Side";

    let outcomeClass = pred.outcome || "pending";
    let outcomeLabel = outcomeClass.toUpperCase();

    return `
      <div class="expand-prediction">
        <div class="expand-pred-header">
          <span class="expand-pred-title">Retroactive Prediction</span>
          <span class="pred-outcome-badge ${outcomeClass}">${outcomeLabel}</span>
        </div>
        <div class="pred-bar-container">
          <span class="pred-team-label blue">Blue</span>
          <div class="pred-bar">
            <div class="pred-bar-fill blue" style="width:${bluePct}%">${bluePct}%</div>
            <div class="pred-bar-fill red" style="width:${redPct}%">${redPct}%</div>
          </div>
          <span class="pred-team-label red">Red</span>
        </div>
        <div class="pred-confidence">
          Predicted: <strong style="color:var(--text-primary)">${predictedLabel}</strong>
          · Confidence: ${confPct}%
        </div>
      </div>
    `;
  }

  // ===========================================================================
  // Phase 23: Analytics Features
  // ===========================================================================

  // ---- Feature 1: Full LP Tracking Graph (modal) ----------------------------

  function openLPGraph(accountId, accountName) {
    modal.classList.add("modal-wide");
    modalTitle.textContent = `LP History — ${accountName}`;
    modalBody.innerHTML = `
      <div class="lp-graph-controls">
        <button class="lp-range-btn active" data-range="30">30d</button>
        <button class="lp-range-btn" data-range="90">90d</button>
        <button class="lp-range-btn" data-range="season">Season</button>
        <button class="lp-range-btn" data-range="all">All</button>
      </div>
      <div class="lp-graph-container">
        <div class="lp-graph-loading">Loading...</div>
      </div>
      <div class="lp-graph-tooltip hidden"></div>
    `;
    showModal();

    const container = modalBody.querySelector(".lp-graph-container");
    const tooltip = modalBody.querySelector(".lp-graph-tooltip");
    let allHistory = [];

    // Fetch all history first, then filter client-side
    let url = `/api/accounts/${accountId}/rank-history?queue=RANKED_SOLO_5x5`;
    if (currentSeason && currentSeason !== "all") url += `&season=${currentSeason}`;

    fetch(url).then(r => r.json()).then(data => {
      allHistory = (data.history || []).map(h => ({
        score: rankToScore(h.tier, h.rank, h.lp),
        tier: h.tier,
        rank: h.rank,
        lp: h.lp,
        wins: h.wins,
        losses: h.losses,
        date: h.recorded_at,
      }));
      renderLPGraph(allHistory, container, tooltip, "30");
    }).catch(() => {
      container.innerHTML = `<div class="lp-graph-loading">Failed to load data</div>`;
    });

    // Range button clicks
    modalBody.querySelectorAll(".lp-range-btn").forEach(btn => {
      btn.addEventListener("click", () => {
        modalBody.querySelectorAll(".lp-range-btn").forEach(b => b.classList.remove("active"));
        btn.classList.add("active");
        renderLPGraph(allHistory, container, tooltip, btn.dataset.range);
      });
    });
  }

  function renderLPGraph(allData, container, tooltip, range) {
    if (allData.length < 2) {
      container.innerHTML = `<div class="lp-graph-loading">Not enough data points yet</div>`;
      return;
    }

    // Filter by range
    let data = allData;
    if (range !== "all" && range !== "season") {
      const days = parseInt(range) || 30;
      const cutoff = Date.now() - days * 86400000;
      data = allData.filter(d => new Date(d.date).getTime() > cutoff);
      if (data.length < 2) data = allData.slice(-Math.min(allData.length, 50));
    }

    const W = 700, H = 300, PAD_L = 70, PAD_R = 20, PAD_T = 20, PAD_B = 40;
    const plotW = W - PAD_L - PAD_R, plotH = H - PAD_T - PAD_B;

    const scores = data.map(d => d.score);
    const minS = Math.min(...scores);
    const maxS = Math.max(...scores);
    const range_s = maxS - minS || 100;

    // Tier boundaries for background bands
    const TIERS = [
      { name: "Iron", base: 0, color: "var(--tier-iron)" },
      { name: "Bronze", base: 400, color: "var(--tier-bronze)" },
      { name: "Silver", base: 800, color: "var(--tier-silver)" },
      { name: "Gold", base: 1200, color: "var(--tier-gold)" },
      { name: "Platinum", base: 1600, color: "var(--tier-platinum)" },
      { name: "Emerald", base: 2000, color: "var(--tier-emerald)" },
      { name: "Diamond", base: 2400, color: "var(--tier-diamond)" },
      { name: "Master", base: 2800, color: "var(--tier-master)" },
      { name: "GM", base: 3000, color: "var(--tier-grandmaster)" },
      { name: "Chall", base: 3200, color: "var(--tier-challenger)" },
    ];

    const toX = (i) => PAD_L + (i / (data.length - 1)) * plotW;
    const toY = (s) => PAD_T + plotH - ((s - minS) / range_s) * plotH;

    // Build SVG
    let svg = `<svg class="lp-graph-svg" viewBox="0 0 ${W} ${H}" preserveAspectRatio="xMidYMid meet">`;

    // Tier background bands
    const padScore = range_s * 0.05;
    TIERS.forEach((tier, idx) => {
      const nextBase = idx < TIERS.length - 1 ? TIERS[idx + 1].base : tier.base + 400;
      if (tier.base > maxS + padScore || nextBase < minS - padScore) return;
      const y1 = Math.max(PAD_T, toY(Math.min(nextBase, maxS + padScore)));
      const y2 = Math.min(PAD_T + plotH, toY(Math.max(tier.base, minS - padScore)));
      if (y2 - y1 < 2) return;
      svg += `<rect x="${PAD_L}" y="${y1}" width="${plotW}" height="${y2 - y1}" fill="${tier.color}" opacity="0.06"/>`;
      // Tier label on left
      const labelY = (y1 + y2) / 2;
      if (y2 - y1 > 16) {
        svg += `<text x="${PAD_L - 5}" y="${labelY + 4}" text-anchor="end" fill="${tier.color}" font-size="10" opacity="0.6">${tier.name}</text>`;
      }
    });

    // Grid lines
    const gridLines = 5;
    for (let i = 0; i <= gridLines; i++) {
      const y = PAD_T + (plotH / gridLines) * i;
      svg += `<line x1="${PAD_L}" y1="${y}" x2="${PAD_L + plotW}" y2="${y}" stroke="var(--border)" stroke-width="0.5"/>`;
      const scoreAtLine = maxS - (range_s / gridLines) * i;
      // Show LP value on Y axis
      const t = Math.floor(scoreAtLine / 100);
      const lpVal = Math.round(scoreAtLine % 100);
      svg += `<text x="${PAD_L - 8}" y="${y + 4}" text-anchor="end" fill="var(--text-muted)" font-size="9">${Math.round(scoreAtLine)}</text>`;
    }

    // X-axis date labels
    const dateStep = Math.max(1, Math.floor(data.length / 6));
    for (let i = 0; i < data.length; i += dateStep) {
      const x = toX(i);
      const d = new Date(data[i].date);
      const label = `${d.getMonth() + 1}/${d.getDate()}`;
      svg += `<text x="${x}" y="${H - 5}" text-anchor="middle" fill="var(--text-muted)" font-size="9">${label}</text>`;
    }

    // Main line
    const points = data.map((d, i) => `${toX(i).toFixed(1)},${toY(d.score).toFixed(1)}`).join(" ");
    const first = scores[0], last = scores[scores.length - 1];
    const lineColor = last > first ? "var(--win)" : last < first ? "var(--loss)" : "var(--blue-accent)";

    // Gradient fill under line
    svg += `<defs><linearGradient id="lpFill" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="${lineColor}" stop-opacity="0.2"/>
      <stop offset="100%" stop-color="${lineColor}" stop-opacity="0"/>
    </linearGradient></defs>`;

    // Area fill
    const areaPoints = `${toX(0).toFixed(1)},${(PAD_T + plotH).toFixed(1)} ${points} ${toX(data.length - 1).toFixed(1)},${(PAD_T + plotH).toFixed(1)}`;
    svg += `<polygon points="${areaPoints}" fill="url(#lpFill)"/>`;

    // Line
    svg += `<polyline points="${points}" fill="none" stroke="${lineColor}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>`;

    // Current point
    const lastX = toX(data.length - 1), lastY = toY(last);
    svg += `<circle cx="${lastX.toFixed(1)}" cy="${lastY.toFixed(1)}" r="4" fill="${lineColor}" stroke="var(--bg-surface)" stroke-width="2"/>`;

    // Invisible hit areas for tooltip
    data.forEach((d, i) => {
      const x = toX(i), y = toY(d.score);
      svg += `<circle cx="${x.toFixed(1)}" cy="${y.toFixed(1)}" r="8" fill="transparent" class="lp-hit" data-idx="${i}"/>`;
    });

    svg += `</svg>`;
    container.innerHTML = svg;

    // Tooltip interaction
    container.querySelectorAll(".lp-hit").forEach(hit => {
      hit.addEventListener("mouseenter", (e) => {
        const idx = parseInt(hit.dataset.idx);
        const d = data[idx];
        const dt = new Date(d.date);
        const dateStr = dt.toLocaleDateString("en-US", { month: "short", day: "numeric", hour: "numeric", minute: "2-digit" });
        tooltip.innerHTML = `
          <div><strong>${d.tier} ${d.rank || ""} ${d.lp} LP</strong></div>
          <div style="color:var(--text-secondary)">${dateStr}</div>
          <div style="color:var(--text-muted)">${d.wins}W ${d.losses}L</div>
        `;
        tooltip.classList.remove("hidden");
        const rect = container.getBoundingClientRect();
        tooltip.style.left = `${e.clientX - rect.left + 10}px`;
        tooltip.style.top = `${e.clientY - rect.top - 40}px`;
      });
      hit.addEventListener("mouseleave", () => tooltip.classList.add("hidden"));
    });
  }

  // Make sparklines clickable to open full graph (delegated to dashboard-grid since accountsGrid is dynamic)
  document.getElementById("dashboard-grid").addEventListener("click", (e) => {
    const sparkContainer = e.target.closest(".sparkline-container");
    if (!sparkContainer) return;
    e.stopPropagation();
    const accountId = sparkContainer.dataset.sparklineAccount;
    const card = sparkContainer.closest(".account-card");
    const nameEl = card ? card.querySelector(".account-name") : null;
    const name = nameEl ? nameEl.textContent : `Account ${accountId}`;
    openLPGraph(accountId, name);
  });


  // ---- Feature 2: Game Time Heatmap -----------------------------------------

  function renderHeatmap(data, section) {
    const days = data.days;
    const hours = data.hours;

    // Build 90-day calendar grid
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    const dayNames = ["S", "M", "T", "W", "T", "F", "S"];
    const COLS = 13; // ~13 weeks
    const CELL = 14, GAP = 2;

    // Find date range
    const startDate = new Date(today);
    startDate.setDate(startDate.getDate() - (COLS * 7 - 1));
    // Adjust to start on Sunday
    startDate.setDate(startDate.getDate() - startDate.getDay());

    // Max games per day for color scaling
    const maxGames = Math.max(1, ...Object.values(days).map(d => d.games));

    let cells = "";
    const allDates = [];
    for (let col = 0; col < COLS; col++) {
      for (let row = 0; row < 7; row++) {
        const d = new Date(startDate);
        d.setDate(d.getDate() + col * 7 + row);
        const key = d.toISOString().split("T")[0];
        const info = days[key];
        const games = info ? info.games : 0;
        const wins = info ? info.wins : 0;
        const wr = games > 0 ? Math.round(wins / games * 100) : -1;
        const intensity = games > 0 ? Math.min(1, games / maxGames) : 0;

        let fillColor;
        if (games === 0) {
          fillColor = "var(--bg-elevated)";
        } else if (wr >= 55) {
          fillColor = `rgba(45, 206, 137, ${0.2 + intensity * 0.6})`;  // green
        } else if (wr < 45) {
          fillColor = `rgba(245, 54, 92, ${0.2 + intensity * 0.6})`;   // red
        } else {
          fillColor = `rgba(200, 170, 110, ${0.2 + intensity * 0.6})`; // gold/neutral
        }

        const x = col * (CELL + GAP);
        const y = row * (CELL + GAP);
        const title = games > 0 ? `${key}: ${games} game${games > 1 ? "s" : ""}, ${wr}% WR` : key;
        cells += `<rect x="${x}" y="${y}" width="${CELL}" height="${CELL}" rx="2" fill="${fillColor}" data-tip="${escHtml(title)}"><title>${escHtml(title)}</title></rect>`;
      }
    }

    // Day labels
    let dayLabels = "";
    for (let i = 0; i < 7; i++) {
      if (i % 2 === 1) {
        dayLabels += `<text x="-6" y="${i * (CELL + GAP) + CELL - 2}" text-anchor="end" fill="var(--text-muted)" font-size="9">${dayNames[i]}</text>`;
      }
    }

    const svgW = COLS * (CELL + GAP);
    const svgH = 7 * (CELL + GAP);

    // Best time to play analysis
    let bestHour = null, bestWR = 0, bestGames = 0;
    const DOW_NAMES = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];
    const hourSummary = {};
    Object.entries(hours).forEach(([key, val]) => {
      const [h] = key.split("_").map(Number);
      if (!hourSummary[h]) hourSummary[h] = { games: 0, wins: 0 };
      hourSummary[h].games += val.games;
      hourSummary[h].wins += val.wins;
    });
    Object.entries(hourSummary).forEach(([h, val]) => {
      if (val.games >= 5) {
        const wr = Math.round(val.wins / val.games * 100);
        if (wr > bestWR || (wr === bestWR && val.games > bestGames)) {
          bestWR = wr;
          bestHour = parseInt(h);
          bestGames = val.games;
        }
      }
    });

    // Find worst time
    let worstHour = null, worstWR = 100, worstGames = 0;
    Object.entries(hourSummary).forEach(([h, val]) => {
      if (val.games >= 5) {
        const wr = Math.round(val.wins / val.games * 100);
        if (wr < worstWR || (wr === worstWR && val.games > worstGames)) {
          worstWR = wr;
          worstHour = parseInt(h);
          worstGames = val.games;
        }
      }
    });

    const fmtHour = (h) => h === 0 ? "12am" : h < 12 ? `${h}am` : h === 12 ? "12pm" : `${h - 12}pm`;

    const totalGames = Object.values(days).reduce((s, d) => s + d.games, 0);
    const totalWins = Object.values(days).reduce((s, d) => s + d.wins, 0);

    section.innerHTML = `
      <div class="heatmap-header">
        <h3 class="section-title">Play Activity</h3>
        <span class="heatmap-summary">${totalGames} ranked games, ${totalGames > 0 ? Math.round(totalWins / totalGames * 100) : 0}% WR (90 days)</span>
      </div>
      <div class="heatmap-grid-wrap">
        <svg class="heatmap-svg" viewBox="-10 0 ${svgW + 10} ${svgH}" preserveAspectRatio="xMinYMin meet">
          ${dayLabels}
          ${cells}
        </svg>
      </div>
      <div class="heatmap-insights">
        ${bestHour !== null ? `<span class="heatmap-insight good">Best: <strong>${fmtHour(bestHour)}</strong> (${bestWR}% over ${bestGames}g)</span>` : ""}
        ${worstHour !== null ? `<span class="heatmap-insight bad">Worst: <strong>${fmtHour(worstHour)}</strong> (${worstWR}% over ${worstGames}g)</span>` : ""}
      </div>
    `;
  }


  // ---- Feature 3: Session Stats & Streaks -----------------------------------

  function loadSessionStats() {
    if (!currentProfileId) return;

    fetch(`/api/profiles/${currentProfileId}/session-stats`)
      .then(r => r.json())
      .then(data => {
        if (!data.accounts) return;
        data.accounts.forEach(stat => {
          const card = accountsGrid.querySelector(`[data-account-id="${stat.account_id}"]`);
          if (!card) return;

          // Remove any existing session badge
          const existing = card.querySelector(".session-badge");
          if (existing) existing.remove();

          const totalToday = stat.today_wins + stat.today_losses;
          if (totalToday === 0 && stat.streak < 2) return;

          let html = `<div class="session-badge">`;

          // Today's record
          if (totalToday > 0) {
            const todayWR = Math.round(stat.today_wins / totalToday * 100);
            html += `<span class="session-today">Today: <strong>${stat.today_wins}W-${stat.today_losses}L</strong>`;
            if (stat.lp_change !== null && stat.lp_change !== 0) {
              const sign = stat.lp_change > 0 ? "+" : "";
              const cls = stat.lp_change > 0 ? "win" : "loss";
              html += ` <span class="session-lp ${cls}">${sign}${stat.lp_change} LP</span>`;
            }
            html += `</span>`;
          }

          // Streak
          if (stat.streak >= 2) {
            const icon = stat.streak_type === "W" ? "W" : "L";
            const cls = stat.streak_type === "W" ? "streak-win" : "streak-loss";
            html += `<span class="session-streak ${cls}">${stat.streak}${icon} streak</span>`;
          }

          // Tilt warning for 3+ loss streak
          if (stat.streak_type === "L" && stat.streak >= 3) {
            html += `<div class="tilt-warning">On a ${stat.streak} game loss streak — consider taking a break</div>`;
          }

          html += `</div>`;
          card.querySelector(".account-queues").insertAdjacentHTML("afterend", html);
        });
      })
      .catch(() => {});
  }


  // ---- Feature 4: Role Performance Breakdown --------------------------------

  function renderRoleStats(roles, section) {
    const ROLE_ORDER = ["Top", "Jungle", "Mid", "Bot", "Support"];
    const ROLE_ICONS = {
      Top: "T", Jungle: "J", Mid: "M", Bot: "B", Support: "S",
    };

    // Find best/worst role by WR (min 5 games, need 2+ qualifying roles)
    let bestRole = null, worstRole = null;
    let bestWR = -1, worstWR = 101;
    const qualifyingRoles = ROLE_ORDER.filter(r => roles[r] && roles[r].games >= 5);
    if (qualifyingRoles.length >= 2) {
      qualifyingRoles.forEach(r => {
        const d = roles[r];
        if (d.wr > bestWR) { bestWR = d.wr; bestRole = r; }
        if (d.wr < worstWR) { worstWR = d.wr; worstRole = r; }
      });
      // Don't label if best and worst are same role or same WR
      if (bestRole === worstRole || bestWR === worstWR) { bestRole = null; worstRole = null; }
    }

    const totalGames = ROLE_ORDER.reduce((s, r) => s + (roles[r] ? roles[r].games : 0), 0);

    let cardsHtml = "";
    ROLE_ORDER.forEach(role => {
      const d = roles[role];
      if (!d) return;
      const pct = totalGames > 0 ? Math.round(d.games / totalGames * 100) : 0;
      const isBest = role === bestRole;
      const isWorst = role === worstRole;
      const kda = d.avg_deaths > 0 ? ((d.avg_kills + d.avg_assists) / d.avg_deaths).toFixed(2) : "Perfect";
      const roleClass = role.toLowerCase();

      cardsHtml += `
        <div class="role-card ${isBest ? "role-best" : ""} ${isWorst ? "role-worst" : ""}">
          <div class="role-card-header">
            <span class="role-tag role-${roleClass}">${role}</span>
            <span class="role-games">${d.games}g (${pct}%)</span>
          </div>
          <div class="role-wr ${wrClass(d.wr)}">${d.wr}%</div>
          <div class="role-kda">${d.avg_kills}/${d.avg_deaths}/${d.avg_assists} <span class="role-kda-ratio">(${kda})</span></div>
          <div class="role-stats-row">
            <span>CS/m: ${d.cs_per_min || "—"}</span>
            <span>Vis: ${d.avg_vision || "—"}</span>
          </div>
          ${isBest ? '<div class="role-badge best">Best Role</div>' : ""}
          ${isWorst ? '<div class="role-badge worst">Weakest</div>' : ""}
        </div>
      `;
    });

    section.innerHTML = `
      <div class="role-stats-header">
        <h3 class="section-title">Role Performance</h3>
      </div>
      <div class="role-cards-grid">${cardsHtml}</div>
    `;
  }


  function renderRadarChart(card, data, name) {
    const dims = data.dimensions;
    const keys = ["cs_min", "kp", "dmg_share", "gold", "vision", "deaths"];
    const labels = keys.map(k => dims[k].label);
    const scores = keys.map(k => dims[k].score);
    const playerVals = keys.map(k => dims[k].player);
    const lobbyVals = keys.map(k => dims[k].lobby);

    const cx = 120, cy = 115, R = 80;
    const n = keys.length;
    const angles = keys.map((_, i) => (Math.PI * 2 * i / n) - Math.PI / 2);

    // Helper to get polygon point at a given score (0-100)
    function pt(angle, score) {
      const r = (score / 100) * R;
      return [cx + r * Math.cos(angle), cy + r * Math.sin(angle)];
    }

    // Background hexagon rings at 25, 50, 75, 100
    let gridLines = "";
    [25, 50, 75, 100].forEach(level => {
      const points = angles.map(a => pt(a, level).join(",")).join(" ");
      const opacity = level === 50 ? 0.4 : 0.15;
      const dash = level === 50 ? "" : 'stroke-dasharray="2,2"';
      gridLines += `<polygon points="${points}" fill="none" stroke="var(--text-muted)" stroke-opacity="${opacity}" ${dash} stroke-width="0.8"/>`;
    });

    // Axis lines
    let axisLines = "";
    angles.forEach(a => {
      const [ex, ey] = pt(a, 100);
      axisLines += `<line x1="${cx}" y1="${cy}" x2="${ex}" y2="${ey}" stroke="var(--text-muted)" stroke-opacity="0.15" stroke-width="0.5"/>`;
    });

    // Player polygon
    const playerPoints = angles.map((a, i) => pt(a, scores[i]).join(",")).join(" ");

    // Axis labels
    let labelEls = "";
    const labelR = R + 22;
    angles.forEach((a, i) => {
      const lx = cx + labelR * Math.cos(a);
      const ly = cy + labelR * Math.sin(a);
      const anchor = Math.abs(Math.cos(a)) < 0.3 ? "middle" : Math.cos(a) > 0 ? "start" : "end";
      labelEls += `<text x="${lx}" y="${ly}" text-anchor="${anchor}" dominant-baseline="central" fill="var(--text-secondary)" font-size="10" font-family="var(--font-mono)">${labels[i]}</text>`;
    });

    // Score dots with tooltips
    let dots = "";
    angles.forEach((a, i) => {
      const [dx, dy] = pt(a, scores[i]);
      const unit = keys[i] === "kp" || keys[i] === "dmg_share" ? "%" : "";
      const tip = `${labels[i]}: ${scores[i]}/100\nYou: ${playerVals[i]}${unit} | Lobby: ${lobbyVals[i]}${unit}`;
      dots += `<circle cx="${dx}" cy="${dy}" r="3" fill="var(--accent)" stroke="var(--bg-card)" stroke-width="1"><title>${escHtml(tip)}</title></circle>`;
    });

    // Overall score color — off-yellow (#e8d44d) for all scores,
    // slightly brighter for high scores, dimmer for low
    const overall = data.overall;
    let scoreColor = "#e8d44d";

    card.innerHTML = `
      <div class="perf-card-name">${escHtml(name)}</div>
      <svg class="perf-radar-svg" viewBox="0 0 240 235" preserveAspectRatio="xMidYMid meet">
        ${gridLines}
        ${axisLines}
        <polygon points="${playerPoints}" fill="var(--accent)" fill-opacity="0.2" stroke="var(--accent)" stroke-width="1.5"/>
        ${dots}
        ${labelEls}
        <text x="${cx}" y="${cy + 2}" text-anchor="middle" dominant-baseline="central" fill="${scoreColor}" font-size="22" font-weight="bold" font-family="var(--font-mono)">${overall}</text>
      </svg>
      <div class="perf-games">${data.games} games</div>
    `;
  }


  // ---- Feature 7: Game Analysis (LLM Post-Game) ----------------------------

  async function _initGameAnalysis(matchId, puuid) {
    const container = document.getElementById(`game-analysis-${matchId}`);
    if (!container) return;

    // Check cache first
    try {
      const res = await fetch(`/api/matches/${encodeURIComponent(matchId)}/game-analysis?puuid=${encodeURIComponent(puuid)}`);
      const data = await res.json();
      if (data.analysis) {
        _renderGameAnalysis(container, matchId, puuid, data.analysis, data.model, true);
        return;
      }
    } catch (e) {
      // No cached analysis
    }

    // Show "Analyze Game" button
    container.innerHTML = `
      <button class="btn btn-secondary btn-sm game-analysis-btn" id="game-analyze-btn-${matchId}">
        Analyze Game
      </button>
    `;

    document.getElementById(`game-analyze-btn-${matchId}`).addEventListener("click", () => {
      _triggerGameAnalysis(container, matchId, puuid);
    });
  }

  async function _triggerGameAnalysis(container, matchId, puuid, model) {
    container.innerHTML = `
      <div class="game-analysis-loading">
        <span class="spinner-sm"></span> Analyzing game with timeline data...
      </div>
    `;

    try {
      const body = { puuid };
      if (model) body.model = model;

      const res = await fetch(`/api/matches/${encodeURIComponent(matchId)}/game-analysis`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      const data = await res.json();

      if (data.analysis) {
        _renderGameAnalysis(container, matchId, puuid, data.analysis, data.model, false);
      } else {
        container.innerHTML = `<div class="game-analysis-error">${escHtml(data.error || "Analysis failed")}</div>`;
      }
    } catch (e) {
      container.innerHTML = `<div class="game-analysis-error">Failed to reach analysis service</div>`;
    }
  }

  function _renderGameAnalysis(container, matchId, puuid, analysisText, model, cached) {
    const modelLabel = model ? model.replace("claude-", "").replace("-4-5", "") : "haiku";

    container.innerHTML = `
      <div class="game-analysis-panel">
        <div class="game-analysis-header">
          <span class="game-analysis-title">Game Analysis</span>
          <span class="game-analysis-model" title="${escHtml(model || "")}">${escHtml(modelLabel)}</span>
          <button class="game-analysis-reanalyze" id="game-reanalyze-${matchId}" title="Re-analyze with different model">&#8635;</button>
        </div>
        <div class="game-analysis-text">${escHtml(analysisText)}</div>
      </div>
    `;

    // Wire re-analyze button
    const reBtn = document.getElementById(`game-reanalyze-${matchId}`);
    if (reBtn) {
      reBtn.addEventListener("click", () => {
        // Show model picker
        const panel = reBtn.closest(".game-analysis-panel");
        let picker = panel.querySelector(".game-analysis-picker");
        if (picker) {
          picker.style.display = picker.style.display === "none" ? "flex" : "none";
          return;
        }
        picker = document.createElement("div");
        picker.className = "game-analysis-picker";
        picker.innerHTML = `
          <button class="game-model-btn" data-model="claude-haiku-4-5">Haiku (Fast)</button>
          <button class="game-model-btn" data-model="claude-sonnet-4-5">Sonnet (Smarter)</button>
        `;
        panel.querySelector(".game-analysis-header").after(picker);

        picker.querySelectorAll(".game-model-btn").forEach(btn => {
          btn.addEventListener("click", () => {
            _triggerGameAnalysis(container, matchId, puuid, btn.dataset.model);
          });
        });
      });
    }
  }


  // ---- Feature 5: Head-to-Head Comparison -----------------------------------

  function openHeadToHead() {
    modal.classList.add("modal-wide");
    modalTitle.textContent = "Head-to-Head Comparison";
    modalBody.innerHTML = `<div class="h2h-loading">Loading accounts...</div>`;
    showModal();

    // Build options from allProfiles (cached), current profile's accounts first
    const currentAccounts = (currentProfile && currentProfile.accounts) || [];
    const currentIds = new Set(currentAccounts.map(a => a.id));

    // Current profile accounts as optgroup
    let optionsHtml = "";
    if (currentAccounts.length > 0) {
      optionsHtml += `<optgroup label="${escHtml(currentProfile.name)}">`;
      currentAccounts.forEach(a => {
        optionsHtml += `<option value="${a.id}">${escHtml(a.game_name)}#${escHtml(a.tag_line)}</option>`;
      });
      optionsHtml += `</optgroup>`;
    }

    // Other profiles from allProfiles (uses accounts_brief added to get_profiles response)
    allProfiles.forEach(p => {
      if (currentProfile && p.id === currentProfile.id) return;
      const briefs = p.accounts_brief || [];
      if (briefs.length === 0) return;
      optionsHtml += `<optgroup label="${escHtml(p.name)}">`;
      briefs.forEach(a => {
        optionsHtml += `<option value="${a.id}">${escHtml(a.game_name)}#${escHtml(a.tag_line)}</option>`;
      });
      optionsHtml += `</optgroup>`;
    });

    // Need at least 2 total accounts across all profiles
    const totalAccounts = allProfiles.reduce((s, p) => s + (p.accounts_brief || []).length, 0);
    if (totalAccounts < 2) {
      modalBody.innerHTML = `<div class="h2h-error">Need at least 2 accounts across all profiles to compare.</div>`;
      return;
    }

    modalBody.innerHTML = `
      <div class="h2h-selectors">
        <select id="h2h-left" class="h2h-select">${optionsHtml}</select>
        <span class="h2h-vs">VS</span>
        <select id="h2h-right" class="h2h-select">${optionsHtml}</select>
        <button id="h2h-compare-btn" class="btn btn-primary btn-sm">Compare</button>
      </div>
      <div id="h2h-results" class="h2h-results"></div>
    `;

    // Default: pick first two different accounts
    const rightSelect = document.getElementById("h2h-right");
    if (rightSelect.options.length >= 2) {
      // Find first option with a different value than left
      const leftVal = document.getElementById("h2h-left").value;
      for (let i = 0; i < rightSelect.options.length; i++) {
        if (rightSelect.options[i].value && rightSelect.options[i].value !== leftVal) {
          rightSelect.selectedIndex = i;
          break;
        }
      }
    }

    document.getElementById("h2h-compare-btn").addEventListener("click", () => {
      const leftId = document.getElementById("h2h-left").value;
      const rightId = document.getElementById("h2h-right").value;
      if (leftId === rightId) {
        document.getElementById("h2h-results").innerHTML = `<div class="h2h-error">Pick two different accounts</div>`;
        return;
      }
      loadH2HComparison(leftId, rightId);
    });

    // Auto-compare on load
    const leftId = document.getElementById("h2h-left").value;
    const rightId = document.getElementById("h2h-right").value;
    if (leftId !== rightId) loadH2HComparison(leftId, rightId);
  }

  function loadH2HComparison(leftId, rightId) {
    const resultsDiv = document.getElementById("h2h-results");
    resultsDiv.innerHTML = `<div class="h2h-loading">Loading stats...</div>`;

    Promise.all([
      fetch(`/api/accounts/${leftId}/stats-summary`).then(r => r.json()),
      fetch(`/api/accounts/${rightId}/stats-summary`).then(r => r.json()),
    ]).then(([left, right]) => {
      renderH2H(left, right, resultsDiv);
    }).catch(() => {
      resultsDiv.innerHTML = `<div class="h2h-error">Failed to load comparison data</div>`;
    });
  }

  function renderH2H(left, right, container) {
    const rankStr = (r) => {
      if (!r || !r.tier) return "Unranked";
      return `${r.tier} ${r.division || ""} ${r.lp} LP`;
    };

    const stats = [
      { label: "Win Rate", left: `${left.wr}%`, right: `${right.wr}%`, lv: left.wr, rv: right.wr, higher: "better" },
      { label: "Games", left: left.games, right: right.games, lv: left.games, rv: right.games, higher: "neutral" },
      { label: "Avg KDA", left: `${left.avg_kills}/${left.avg_deaths}/${left.avg_assists}`, right: `${right.avg_kills}/${right.avg_deaths}/${right.avg_assists}`,
        lv: left.avg_deaths > 0 ? (left.avg_kills + left.avg_assists) / left.avg_deaths : 99,
        rv: right.avg_deaths > 0 ? (right.avg_kills + right.avg_assists) / right.avg_deaths : 99, higher: "better" },
      { label: "CS/min", left: left.cs_per_min, right: right.cs_per_min, lv: left.cs_per_min || 0, rv: right.cs_per_min || 0, higher: "better" },
      { label: "Vision", left: left.avg_vision, right: right.avg_vision, lv: left.avg_vision || 0, rv: right.avg_vision || 0, higher: "better" },
      { label: "DMG/min", left: left.dmg_per_min, right: right.dmg_per_min, lv: left.dmg_per_min || 0, rv: right.dmg_per_min || 0, higher: "better" },
      { label: "Gold/min", left: left.gold_per_min, right: right.gold_per_min, lv: left.gold_per_min || 0, rv: right.gold_per_min || 0, higher: "better" },
    ];

    let rowsHtml = "";
    stats.forEach(s => {
      const leftWins = s.higher === "better" ? s.lv > s.rv : false;
      const rightWins = s.higher === "better" ? s.rv > s.lv : false;
      const totalVal = (s.lv + s.rv) || 1;
      const leftPct = Math.round((s.lv / totalVal) * 100);
      const rightPct = 100 - leftPct;

      rowsHtml += `
        <div class="h2h-row">
          <span class="h2h-val ${leftWins ? "h2h-winner" : ""}">${s.left}</span>
          <div class="h2h-bar-area">
            <div class="h2h-label">${s.label}</div>
            <div class="h2h-bar">
              <div class="h2h-bar-left" style="width:${leftPct}%"></div>
              <div class="h2h-bar-right" style="width:${rightPct}%"></div>
            </div>
          </div>
          <span class="h2h-val ${rightWins ? "h2h-winner" : ""}">${s.right}</span>
        </div>
      `;
    });

    // Top champions comparison
    const champHtml = (champs) => champs.slice(0, 3).map(c =>
      `<div class="h2h-champ">${escHtml(c.name)} <span class="${wrClass(c.wr)}">${c.wr}%</span> (${c.games}g)</div>`
    ).join("");

    container.innerHTML = `
      <div class="h2h-header">
        <div class="h2h-player">
          <div class="h2h-name">${escHtml(left.game_name)}</div>
          <div class="h2h-rank">${rankStr(left.rank)}</div>
        </div>
        <div class="h2h-player">
          <div class="h2h-name">${escHtml(right.game_name)}</div>
          <div class="h2h-rank">${rankStr(right.rank)}</div>
        </div>
      </div>
      ${rowsHtml}
      <div class="h2h-champs-section">
        <div class="h2h-champs-col">
          <div class="h2h-champs-title">Top Champions</div>
          ${champHtml(left.top_champions || [])}
        </div>
        <div class="h2h-champs-col">
          <div class="h2h-champs-title">Top Champions</div>
          ${champHtml(right.top_champions || [])}
        </div>
      </div>
    `;
  }


  // ---- Feature Integration: Hook into dashboard render ----------------------

  // Add H2H button to dashboard header
  const headerActions = document.querySelector(".header-actions");
  if (headerActions) {
    const h2hBtn = document.createElement("button");
    h2hBtn.className = "btn btn-secondary btn-sm";
    h2hBtn.textContent = "Compare";
    h2hBtn.title = "Head-to-Head Comparison";
    h2hBtn.addEventListener("click", (e) => {
      e.stopPropagation();
      openHeadToHead();
    });
    headerActions.insertBefore(h2hBtn, headerActions.querySelector("#add-account-btn"));
  }

});
