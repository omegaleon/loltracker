# LolTracker — Agent Guide

LolTracker is a League of Legends multi-account tracker with live game lookups, champion statistics, and AI-powered build analysis.
Stack: **Python Flask + SQLite** (server) + **vanilla JS SPA** (client).

---

## Project Layout

```
/code/loltracker/
├── Dockerfile
├── docker-compose.yml
├── .dockerignore
├── tracker-unraid.xml
├── requirements.txt
├── PLAN.md
├── app.py                  # Main Flask app (~3300 lines)
├── database.py             # SQLite persistence layer
├── riot_api.py             # Riot Games API client
├── llm_client.py           # Anthropic/Claude API wrapper for build analysis
├── opgg_scraper.py         # Op.gg season rank scraping
├── champion_positions.py   # Champion → position mapping
├── champion_role_rates.py  # Role rate data
├── build_guides.py         # Champion build guide data
├── data/
│   └── loltracker.db       # SQLite database
├── static/
│   ├── app.js              # Frontend SPA JavaScript
│   ├── style.css           # Frontend styles
│   └── favicon.svg
└── templates/
    └── index.html           # Flask/Jinja SPA shell
```

---

## Build & Run

```bash
# Local dev
pip install -r requirements.txt
RIOT_API_KEY=RGAPI-xxx python app.py

# Docker
docker build -t tracker:latest .
```

---

## Deployment to Unraid Local Registry

All containers are deployed via a local Docker registry on Unraid at `registry.badatleague.games` (HTTPS via SWAG).

```bash
# Build, tag, and push to local registry
DOCKER_API_VERSION=1.43 docker build -t tracker:latest .
DOCKER_API_VERSION=1.43 docker tag tracker:latest registry.badatleague.games/tracker:latest
DOCKER_API_VERSION=1.43 docker push registry.badatleague.games/tracker:latest
```

The Unraid XML template is at `tracker-unraid.xml` and deployed to:
`/boot/config/plugins/dockerMan/templates-user/my-tracker.xml`

To deploy the template:
```bash
scp tracker-unraid.xml root@192.168.1.100:/boot/config/plugins/dockerMan/templates-user/my-tracker.xml
```

After pushing a new image, use Unraid's "Check for Updates" → "Apply Update" to pull the latest.

### Registry Info

- **Registry**: `registry.badatleague.games` (local `registry:2` container on Unraid, fronted by SWAG with TLS)
- **DOCKER_API_VERSION=1.43**: Required in this dev container because the Docker client version is newer than the daemon

---

## Key Configuration

- **RIOT_API_KEY** (required): Riot Games API key
- **ANTHROPIC_API_KEY** (optional): For AI build analysis
- **LOLTRACKER_DB_PATH**: Path to SQLite database (default: `/data/loltracker.db`)
- **TZ**: Timezone (default: `America/New_York`)

---

## Database

- SQLite at `/data/loltracker.db` inside container
- Mapped to `/mnt/user/appdata/loltracker/data` on Unraid host
- No python3 on Unraid host — must use `docker exec tracker` for DB operations
