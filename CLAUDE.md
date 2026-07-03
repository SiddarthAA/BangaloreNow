# BangaloreNow — project context

Real-time dashboard for Bangalore. **Beta scope = events**: an automated pipeline
scrapes/enriches events and a Google-Maps frontend pins them. Live at
bangalorenow.live. Long-term vision (civic data, urban alerts) is out of scope now.

Repo: `git@github.com:SiddarthAA/BangaloreNow.git` (owner SiddarthAA). This is a
**re-created repo** — the old one was nuked.

## Current state (2026-07)

Fresh repo. Only two things exist:
- `README.md` — vision/marketing.
- `service/test/` — scraper strategy R&D (the bake-off). **Not the real service yet.**

The old repo's **backend** (FastAPI + SQLAlchemy + Postgres, 2 endpoints:
`get-all-events` for map markers, `get-event-details/{id}`) and **frontend**
(React 19 + Vite + Tailwind + Google Maps via `@vis.gl/react-google-maps`) are
**not yet migrated here**. If you need them, ask — don't assume they're present.

## Scraper decision — LOCKED, don't re-litigate

Benchmarked custom (httpx+JSON-LD) vs crawl4ai vs firecrawl on live sources.
Full write-up: `service/test/README.md`. Conclusion:

**One shared extraction core + per-source adapters + a tiered fetch layer.**
Per-site differences are config, not new scrapers.
1. `httpx` + `schema.org/Event` JSON-LD parse — the default (fast, free, has coords).
2. `crawl4ai` (headless browser), same parser — only when a site needs JS / blocks httpx.
3. `firecrawl` — last resort; use it to *fetch* only. **Its LLM extraction hallucinates
   `(0,0)` coordinates — never trust it for coords/dates.**

Source validation (Tier-1 = plain httpx works):

| Source | Verdict |
|---|---|
| Eventbrite, Luma, Allevents | Tier-1 full (JSON-LD + geo) |
| Meetup | Tier-1 + **geocode** (good addresses, no coords) |
| 10times | anti-bot (403) → Tier-2/3 |
| Townscript | SPA shell → browser / its JSON API |
| Hasgeek | homepage isn't a listing; find the real event URLs |

Real pipeline (not built yet): discover → fetch(tier) → parse JSON-LD → normalize →
geocode → classify tech-vs-not (Claude Haiku) → dedup (`rapidfuzz`) → upsert Postgres.
Deploy as GCP Cloud Run Jobs on Cloud Scheduler.

## Stack & conventions

- Python + **uv** (`uv sync`, `uv run …`). Node/Vite on the frontend when it lands.
- Secrets in `.env` (gitignored). Firecrawl key lives in `service/test/.env`. Never commit secrets.
- **One PR per folder** — reuse the same branch/PR across tasks for a given folder; title as `[folder] …`.
- Branch → PR → merge to `main`. Feature branches: `feat/...`.
- **Do NOT add `Co-Authored-By: Claude` to commits or PRs** (user's standing preference).

## Build/run

```bash
cd service/test && uv sync && uv run playwright install chromium  # crawl4ai
uv run python run.py            # bake-off (spends firecrawl credits)
uv run python validate_tier1.py # source probe
uv run python rescore.py        # re-score saved results, offline
```
