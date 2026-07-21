"""Validate whether the Tier-1 strategy (plain httpx + structured-data parsing)
generalizes beyond Eventbrite. For each source we fetch a listing/discovery page
with no browser and report:

  - does plain httpx even get through (status / blocked)?
  - is there structured data in the RAW html (JSON-LD, or a hidden JSON blob like
    __NEXT_DATA__ / __APOLLO_STATE__ that an SPA hydrates from)?
  - how many schema.org/Event objects can our existing parser extract, and how
    many carry usable coordinates?

A verdict is assigned per source: Tier-1 works as-is, Tier-1 with a
site-specific hidden-JSON parse, or it needs Tier-2/3 (browser / managed).

    uv run python validate_tier1.py
"""
import json
import re
import time
from pathlib import Path

import httpx

from common import BROWSER_UA, extract_events_from_html, valid_geo

# Listing / discovery pages — the entry points a crawler would start from.
SITES = [
    ("Luma (city)",        "https://lu.ma/bangalore"),
    ("Meetup (find tech)", "https://www.meetup.com/find/?keywords=technology&location=in--Bangalore&source=EVENTS"),
    ("Hasgeek",            "https://hasgeek.com/"),
    ("Allevents (tech)",   "https://allevents.in/bangalore/technology"),
    # 10times moved city pages to /<city>-in/ (old /bangalore/technology soft-404s since ~2026-07)
    ("10times (tech)",     "https://10times.com/bengaluru-in/technology"),
    ("Townscript (city)",  "https://www.townscript.com/discover/all-events/bangalore"),
]

HIDDEN_JSON = {
    "__NEXT_DATA__": r'id="__NEXT_DATA__"',
    "__APOLLO_STATE__": r'__APOLLO_STATE__',
    "__SERVER_DATA__": r'__SERVER_DATA__',
    "__NUXT__": r'window\.__NUXT__',
    "__remixContext": r'__remixContext',
    "__INITIAL_STATE__": r'__INITIAL_STATE__',
    'application/json (next/embed)': r'<script[^>]+type="application/json"',
}
BLOCK_MARKERS = [
    "captcha", "access denied", "unusual traffic", "px-captcha",
    "are you a human", "cf-browser-verification", "just a moment", "request blocked",
]

RESULTS = Path(__file__).parent / "results"
RESULTS.mkdir(exist_ok=True)


def probe(name: str, url: str) -> dict:
    rec: dict = {"name": name, "url": url}
    try:
        with httpx.Client(follow_redirects=True, timeout=30, headers={"User-Agent": BROWSER_UA}) as c:
            t = time.perf_counter()
            r = c.get(url)
            rec["elapsed"] = round(time.perf_counter() - t, 2)
        html = r.text
        low = html.lower()
        rec["status"] = r.status_code
        rec["kb"] = len(html) // 1024
        rec["blocked"] = any(m in low for m in BLOCK_MARKERS)
        rec["ld_blocks"] = len(re.findall(r"application/ld\+json", html))
        rec["type_event"] = len(re.findall(r'"@type"\s*:\s*"Event"', html))
        rec["hidden"] = [k for k, pat in HIDDEN_JSON.items() if re.search(pat, html)]
        events = extract_events_from_html(html)
        rec["jsonld_events"] = len(events)
        rec["geo_events"] = sum(1 for e in events if valid_geo(e))
        rec["sample"] = events[0].name if events else None
        (RESULTS / f"raw_{_slug(name)}.html").write_text(html[:400_000], errors="ignore")
    except Exception as e:  # noqa: BLE001
        rec["error"] = f"{type(e).__name__}: {e}"
    return rec


def verdict(r: dict) -> str:
    if "error" in r:
        return f"FAIL ({r['error'][:34]})"
    if r["status"] >= 400 or r["blocked"]:
        return f"BLOCKED (HTTP {r['status']}) -> Tier-2/3"
    if r["jsonld_events"] > 0:
        return f"TIER-1 OK (JSON-LD, geo {r['geo_events']}/{r['jsonld_events']})"
    if r["type_event"] > 0:
        return "TIER-1~ (Event JSON-LD present; parser tweak)"
    if r["hidden"]:
        return f"TIER-1* (parse {r['hidden'][0]})"
    return "needs browser/API (no struct data in raw html)"


def _slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")


def main():
    rows = [probe(n, u) for n, u in SITES]

    w = [20, 7, 6, 8, 8, 26, 7]
    hdr = ["source", "status", "kb", "ld-blks", "events", "hidden-json", "geo"]
    fmt = lambda cells: "  ".join(str(c).ljust(width) for c, width in zip(cells, w))
    print("\n" + "=" * 122)
    print("  TIER-1 GENERALIZATION PROBE  (plain httpx + structured-data parse, no browser)")
    print("=" * 122)
    print(fmt(hdr) + "  verdict")
    print("-" * 122)
    for r in rows:
        if "error" in r:
            print(fmt([r["name"][:20], "ERR", "-", "-", "-", "-", "-"]) + "  " + verdict(r))
            continue
        print(
            fmt([
                r["name"][:20], r["status"], r["kb"], r["ld_blocks"],
                r.get("jsonld_events", 0), (",".join(r["hidden"])[:26] or "-"),
                f"{r.get('geo_events',0)}/{r.get('jsonld_events',0)}",
            ])
            + "  " + verdict(r)
        )
    print("-" * 122)
    for r in rows:
        if r.get("sample"):
            print(f"  • {r['name']}: sample event = {r['sample'][:70]!r}")
    print("=" * 122)
    (RESULTS / "tier1_probe.json").write_text(json.dumps(rows, indent=2, default=str))
    print(f"\nFull probe records + raw HTML snapshots written to {RESULTS}/")


if __name__ == "__main__":
    main()
