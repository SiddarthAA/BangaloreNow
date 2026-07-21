# Scraper Bake-Off

Goal: decide **how** BangaloreNow's `services` scraper should fetch + extract
events — one scraper used everywhere, or a combination — by benchmarking three
strategies against the **same** target on the **same** normalized schema.

**Target:** Eventbrite → Bangalore → Science & Tech
(`https://www.eventbrite.com/b/india--bangalore/science-and-tech/`)

## The three strategies

| # | Strategy | Fetch | Extract | Cost |
|---|----------|-------|---------|------|
| A | **custom** | `httpx` (no browser) | parse `schema.org/Event` JSON-LD from HTML | free |
| B | **crawl4ai** | headless Chromium | same JSON-LD parser on rendered HTML | free (local CPU) |
| C | **firecrawl** | managed API | LLM structured extraction against our schema | API credits |

All three normalize into one `Event` model (`common.py`) and are scored on the
fields the map actually needs — coordinates first, then display fields.

## Results

```
scraper                                 events  complete  geo%    url%    img%    desc%   time(s)   cost
custom (httpx + JSON-LD)                7       100%      100%    100%    100%    100%    1.73      free
crawl4ai (headless browser + JSON-LD)   7       100%      100%    100%    100%    100%    1.80      free (local browser)
firecrawl (managed + LLM extract)       7       56%       0%      100%    100%    0%      20.75     5 credits
```

`geo%` uses **honest** coordinate validation (`valid_geo` in `common.py`):
rejects `None`, the `(0,0)` null-island placeholder, and anything outside
India's bounding box.

### Key findings

1. **Eventbrite embeds everything as JSON-LD in the raw HTML** — name, dates,
   url, image, description, full address, **and `geo` lat/long**. No browser and
   no geocoding needed. A plain `httpx` GET + JSON-LD parse gets 100% of every
   field in ~1.7s for free.

2. **The headless browser bought us nothing here.** crawl4ai tied custom on
   quality (same JSON-LD, same fields) because the page needs no JS. It only
   earns its keep on JS-rendered or bot-walled sites. It also drags in a
   ~115 MB Chromium + a large dependency tree (litellm, torch-adjacent libs).

3. **Firecrawl's LLM extraction silently fabricated coordinates.** It returned
   `(0.0, 0.0)` for *all 7* events (caught only because we validate geo) and
   dropped `end_date`, `address`, and `description` entirely. It was also ~12×
   slower and costs credits. Reason: LLM extraction reads the *visible* content,
   so machine-only data (coordinates) and long fields get lost or hallucinated.
   For a **map** product this is the worst possible failure — every event would
   land in the Gulf of Guinea.

   > Firecrawl *can* match custom if you use it only to **fetch** (`rawHtml`)
   > and parse JSON-LD yourself — but then you're paying it to be an HTTP client
   > for a site that doesn't need one.

### Data-quality note (about the source, not the scrapers)

4 of the 7 listings are **online webinars** with a generic `"Bengaluru"` venue
and city-centroid coordinates `(12.9715987, 77.5945627)`. Only 3 have real
venues (The Leela, We:Neighborhood, CGI). Eventbrite's Bangalore science-tech
feed is partly low-value online-workshop spam — for venue-based tech events,
Hasgeek / Meetup / Luma will likely be higher quality. Two follow-ups for the
real pipeline: (a) flag/exclude online events, (b) treat city-centroid coords as
"no real location."

## Recommendation: one extraction core, tiered fetch — not one scraper, not N bespoke scrapers

- **Don't** write a separate scraper per site (unmaintainable), and **don't**
  force a single fetch method everywhere (some sites need a browser).
- **Do** build **one shared extractor** (the `Event` schema + structured-data
  parser) behind a **pluggable fetch layer**, and escalate only when forced:

  1. **Tier 1 — `httpx` + structured-data parser (JSON-LD / hidden JSON).**
     The default workhorse. Most event platforms embed `schema.org/Event` for
     Google rich results, so this covers the majority of sources — fast, free,
     accurate, coordinates included.
  2. **Tier 2 — crawl4ai (headless browser), same parser.** Fallback only for
     sources that require JS or block plain HTTP.
  3. **Tier 3 — Firecrawl (managed).** Reserve for the nastiest anti-bot sites
     or long-tail one-offs where running browser infra isn't worth it. Use it to
     **fetch**, then parse structured data yourself; do **not** trust its LLM
     extraction for coordinates or exact dates.

Net: per-site differences become **config** (URL + which fetch tier), not new
code. The expensive tools are fallbacks, not the default.

## Tier-1 generalization (does plain httpx + JSON-LD work beyond Eventbrite?)

`validate_tier1.py` points the same extractor at six other sources. Result:
**structured-data parsing is the right default — most event platforms embed
`schema.org/Event` in raw HTML for Google rich results.**

| Source | httpx | Structured data in raw HTML | Events | Coords | Verdict |
|--------|:-----:|-----------------------------|:------:|:------:|---------|
| Eventbrite | ✅ | JSON-LD **+ geo** | 7 | ✅ direct | **Tier-1 full** |
| Luma | ✅ | JSON-LD **+ geo** (also `__NEXT_DATA__`) | 20 | ✅ direct | **Tier-1 full** |
| Allevents | ✅ | JSON-LD **+ geo** | 15 | ✅ direct | **Tier-1 full** |
| Meetup | ✅ | JSON-LD, full street address, **no geo** | 30 | ⚠️ geocode | **Tier-1 + geocode** |
| Hasgeek | ✅ | no `Event` JSON-LD anywhere (homepage *or* project pages) | — | — | Tier-1 fetch + **custom parser** |
| 10times | ✅ | JSON-LD, **no geo** (city page moved to `/bengaluru-in/`) | 10 | ⚠️ geocode | **Tier-1 + geocode** |
| Townscript | ✅ | 5KB SPA shell, hydrates via JS/API | 0 | — | **Tier-2 / its JSON API** |

Takeaways:
- **3 of 7 are fully Tier-1 with coordinates** out of the box (plus Eventbrite = 4).
- **Meetup and 10times** are Tier-1 for discovery + all fields *except* coordinates →
  they need a **geocoding step** on their addresses, not a browser.
- Escalation is the exception, and each kind is distinct: SPA (Townscript → its JSON
  API; browser-rendered DOM has no JSON-LD either, and the API 401s without an app
  token), no-structured-data (Hasgeek → small custom parser), and plain **source rot**
  (10times "block" was actually a moved URL). Confirms the tiered design below — and
  the per-source yield alerting in §9.

### Re-validation (2026-07-12)

Live re-run of `run.py` + `validate_tier1.py` reproduced the bake-off exactly
(custom 100% / 1.8s; crawl4ai 100% / 2.6s; firecrawl again fabricated `(0,0)`
for all 7 events and dropped end_date/address/description). Two verdicts moved:

- **10times**: the 2026-06 `403` became a soft-404 — the city page moved to
  `10times.com/bengaluru-in/technology`. The *new* URL is plain-httpx friendly:
  10 JSON-LD events, real conferences, no coords → reclassified **Tier-1 + geocode**.
  Not anti-bot after all; just URL churn.
- **Hasgeek**: fetches fine (homepage, `/fifthelephant`, `?past=1`) but emits zero
  `schema.org/Event` markup → needs a per-source `parse()` override, not a browser.
- **Townscript**: even rendered in Chromium there's no `Event` JSON-LD in the DOM;
  its `api/customsearch/events` returns 401 without an app token → adapter that
  mimics the app's API bootstrap, or skip for beta.

## Handling many sites: architecture

One **extraction core** + **per-source adapters** + a **tiered fetch layer**, run as
scheduled jobs. Per-site differences are mostly config, not new scrapers.

1. **Source adapter registry.** Each source declares: discovery URL(s)/API, fetch
   tier, pagination, politeness (rate limit, robots), and a `parse()` — which for
   most sources is just the shared JSON-LD parser; only oddballs override.
2. **Two-phase crawl.** *Discover* (listing/discovery → event URLs/stubs, paginated)
   → *Detail* (event page → full `Event`). Skip phase 2 when the listing already has
   everything + geo (Eventbrite/Luma/Allevents).
3. **Tiered fetch with auto-escalation.** `httpx` (async) by default → on 403/empty,
   escalate to **crawl4ai** (browser) → last resort **Firecrawl** (to *fetch*, then we
   parse). One `fetch(url, tier)` seam; adapters pick a starting tier.
4. **Concurrency + politeness.** `httpx.AsyncClient` + a global `Semaphore`, plus a
   **per-host** limiter (token bucket / per-domain semaphore + jittered delay), robots
   respect, and `tenacity` backoff on 429/403. Conditional-GET / last-seen caching.
5. **Normalize + enrich.** Dates → UTC; **geocode** addresses that lack coords (Meetup),
   caching by address to save quota; drop/flag online-only events; **classify tech vs
   not + tag** with a cheap LLM (Claude Haiku) since some feeds are loosely categorized.
6. **Cross-source dedup.** Same event appears on several platforms — fuzzy-match on
   (normalized name, date, venue/geo proximity) with `rapidfuzz`; keep the richest
   record and merge `sources`.
7. **Idempotent upsert** into the backend's Postgres, keyed by a stable dedup id; track
   `source`, `source_url`, `last_seen`, `scraped_at`; soft-expire past `endDate`.
8. **Orchestration.** GCP-native: each source = a **Cloud Run Job** on **Cloud
   Scheduler** cron, fanned out in parallel; idempotent so retries are safe. (In-process
   alt: `arq`/APScheduler.)
9. **Per-source observability.** Track events-found / errors / last-success per source
   and alert when a source's yield drops to zero — scrapers rot when sites change HTML.

## Run it

```bash
cd services/test
uv sync
uv run playwright install chromium      # for crawl4ai
uv run python run.py                     # live run of all three (spends Firecrawl credits)
uv run python rescore.py                 # re-score saved dumps, no network/credits
```

`FIRECRAWL_API_KEY` is read from `.env`. Per-scraper output + `summary.json` land
in `results/`.

## Files

- `common.py` — `Event` schema, JSON-LD extractor, honest scoring (`valid_geo`)
- `s_custom.py` / `s_crawl4ai.py` / `s_firecrawl.py` — the three strategies
- `run.py` — live benchmark (fetch → score → dump → table)
- `rescore.py` — re-score saved `results/` dumps offline
