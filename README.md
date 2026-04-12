| Vista |
|------|
| **Dashboard** |
| <p align="center"><img src="assets/intranet.png" width="80%"></p> |
| **Menu Processor** |
| <p align="center"><img src="assets/menu_processor.png" width="50%"></p> |

# Intranet Casa — Dashboard v2.0

A self-hosted home dashboard running on a QNAP TS-264 NAS. Started as a learning exercise — Pi-hole stats, the weather, a shopping list. Iterated over time into something I actually rely on daily.

The goal was never to build something perfect. It was to **build something real**: integrate services I actually run, make decisions I had to defend, and learn what happens when "it works locally" meets constrained hardware. The codebase reflects that process.

---

## What it does

| Widget | Source | What made it interesting |
|--------|--------|--------------------------|
| 🌤️ Weather | OpenWeatherMap | Server-side proxy — API key never exposed to the browser |
| ⚡ Energy | Home Assistant | 3 parallel requests via `ThreadPoolExecutor` instead of sequential |
| 🏠 IoT Devices | Home Assistant | N parallel state fetches — adding a device is one line in `config.py` |
| 🛡️ Pi-hole | Pi-hole v6 | v6 changed the auth flow completely — had to reverse-engineer the new API |
| 🍳 Recipes | Mealie | Recipe count + today's meal plan |
| 🍽️ Weekly Menus | Menu Processor | Custom service I built separately — processes weekly menus, pushes shopping lists to Mealie |
| 💰 Finances | SettleUp / Firebase | Firebase auth with cached token (50 min TTL) to avoid re-auth on every request |
| 🛒 Shopping List | SQLite | Replaced a CSV with race condition risks — thread-safe, auto-migrates old data |
| 📁 Documents | NAS filesystem | Read-only mount, tree browser |
| 🔐 DNSCrypt | DNS health check | UDP query to verify encrypted DNS is alive |

---

## Stack — and why

**Backend:** Flask 3.0 · Gunicorn (1 worker, 4 gthreads) · Flask-Caching (FileSystemCache) · SQLite

**Frontend:** Vanilla JS · CSS custom properties · No build step, no bundler, no framework

**Infrastructure:** Docker Alpine · Nginx Proxy Manager · QNAP TS-264 · 384 MB / 0.5 CPU limit

The hardware constraint drove most decisions. With 384 MB and 0.5 CPU, there's no room for Node servers, Redis, or Celery workers. Flask on Gunicorn with a FileSystemCache that survives container restarts — that's the right fit.

Skipping React/Next.js was equally intentional. The dashboard is one page with ~600 lines of JS. A framework would add a build pipeline, a runtime overhead, and complexity with zero functional benefit. The question I kept asking was: *does this solve a problem I actually have?*

---

## Architecture

```
intranet/
├── app.py                    # Flask factory — create_app()
├── config.py                 # env_target() resolves URLs for local vs. NAS
├── blueprints/
│   ├── dashboard.py          # GET /  GET /finanzas
│   └── api/
│       ├── weather.py        # GET /api/weather
│       ├── energy.py         # GET /api/energy  GET /api/devices
│       ├── pihole.py         # GET /api/pihole
│       ├── mealie.py         # GET /api/mealie
│       ├── settleup.py       # GET /api/settleup
│       ├── shopping.py       # GET /api/shopping  POST /api/shopping  DELETE /api/shopping/<id>
│       ├── documents.py      # GET /api/docs/tree  GET /docs/<path>
│       └── services.py       # GET /api/menu-processor  GET /api/dnscrypt  GET /api/health
├── static/css/               # Design system: variables · base · components · dashboard
├── static/js/                # main.js (utils) + dashboard.js (widget controller)
└── templates/                # Jinja2
```

v2.0 split a 645-line `main.py` God File into 9 domain-specific blueprints. Each service follows the same pattern: `config.py` → optional client class → blueprint → frontend widget. The architecture is boring by design — consistent enough that adding a new integration is mechanical, not creative.

---

## Design

"Warm Observatory" — dark forest green (`#0B1414`) with warm amber accents (`#E4981E`).

Bento 2.0 grid: cards with visual hierarchy, not flat boxes. A few choices I'm proud of:

- **`@starting-style`** for staggered entrance animations — pure CSS, zero JS overhead, GPU-composited
- **DM Sans** for numeric displays — straight geometric digits vs. the curved display font
- **Glassmorphism** with `backdrop-filter: blur` — subtle, structural, not decorative
- **`prefers-reduced-motion`** respected throughout

---

## MCE — Model-Context Engineering

This project is also a case study in **Model-Context Engineering**: a structured development methodology where rules, reusable task templates, and persistent memory define *how* to work on a project — not just what to build. The goal is coherence across sessions: consistent patterns, no re-litigating past decisions, no architectural drift.

The `.windsurf.bak/` folder contains the original rules, skills, and workflows built for this project before consolidating them into a monorepo:

```
.windsurf.bak/
├── rules/          # How to work: backend conventions, CSS patterns, testing
├── skills/         # What to do: add-service, create-endpoint, create-widget
├── workflows/      # Sequences: validate, fix-lint
└── memories/       # Decisions that persist across sessions
```

The idea: rules define *how* to work, skills define *what* to do, memory preserves decisions already made. The result is a codebase that stays consistent even as the project grows and evolves over time.

---

## Running locally

```bash
python -m venv venv && source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt
cp .env.example .env  # fill in your API keys
python app.py
# → http://localhost:5000
```

Services you don't configure will show `--` or an error state. Everything else works fine locally.

---

## Adding a new integration

Every service follows the same 4-step pattern:

1. **Config** — add URL + credentials to `config.py` using `env_target()` / `env_str()`
2. **Client** — optional class in `blueprints/myservice_client.py`
3. **Blueprint** — `blueprints/api/myservice.py` with `@cache.cached(timeout=N)`
4. **Register** — one line in `blueprints/__init__.py`

Then add the card to `dashboard.html` and a `loadMyService()` method to `dashboard.js`.

IoT devices from Home Assistant are even simpler — just add an entry to `HA_DEVICES` in `config.py`. No code required.

---

## License

MIT
