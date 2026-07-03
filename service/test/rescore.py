"""Re-score the saved per-scraper dumps in results/ without re-running any
scraper (no network, no Firecrawl credits). Useful after tweaking scoring.

    uv run python rescore.py
"""
import json
from pathlib import Path

from common import Event, score_run

RESULTS = Path(__file__).parent / "results"
LABELS = {
    "custom": "custom (httpx + JSON-LD)",
    "crawl4ai": "crawl4ai (headless browser + JSON-LD)",
    "firecrawl": "firecrawl (managed + LLM extract)",
}


def main():
    rows = []
    for slug, label in LABELS.items():
        path = RESULTS / f"{slug}.json"
        if not path.exists():
            continue
        events = [Event(**e) for e in json.loads(path.read_text())]
        rows.append({**score_run(events), "name": label})

    hdr = ["scraper", "events", "complete", "geo%", "url%", "img%", "desc%"]
    widths = [38, 6, 8, 6, 6, 6, 6]
    fmt = lambda cells: "  ".join(str(c).ljust(w) for c, w in zip(cells, widths))
    print("\n" + "=" * 88)
    print("  RE-SCORED (honest geo validation) — Eventbrite / Bangalore / Science & Tech")
    print("=" * 88)
    print(fmt(hdr))
    print("-" * 88)
    for r in rows:
        print(fmt([
            r["name"][:38], r["events"],
            f"{r['completeness']*100:.0f}%", f"{r['geo_pct']*100:.0f}%",
            f"{r['url_pct']*100:.0f}%", f"{r['img_pct']*100:.0f}%", f"{r['desc_pct']*100:.0f}%",
        ]))
    print("=" * 88)


if __name__ == "__main__":
    main()
