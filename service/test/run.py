"""Run all three scrapers against the same Eventbrite URL, score them on the
same normalized schema, dump per-scraper output, and print a comparison table.

    uv run python run.py
"""
import asyncio
import json
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from common import score_run  # noqa: E402
from s_crawl4ai import scrape_crawl4ai  # noqa: E402
from s_custom import scrape_custom  # noqa: E402
from s_firecrawl import scrape_firecrawl_json  # noqa: E402

RESULTS = Path(__file__).parent / "results"
RESULTS.mkdir(exist_ok=True)


def _safe(label, fn, is_async=False):
    try:
        return asyncio.run(fn()) if is_async else fn()
    except Exception as e:  # noqa: BLE001 — bake-off: a broken scraper shouldn't kill the run
        return dict(name=label, events=[], elapsed=0.0, raw_chars=0, cost="-",
                    notes=f"ERROR: {type(e).__name__}: {e}")


def _slug(name: str) -> str:
    return name.split()[0].strip("(")


def main():
    runs = [
        _safe("custom", scrape_custom),
        _safe("crawl4ai", scrape_crawl4ai, is_async=True),
        _safe("firecrawl", scrape_firecrawl_json),
    ]

    rows = []
    for r in runs:
        s = score_run(r["events"])
        (RESULTS / f"{_slug(r['name'])}.json").write_text(
            json.dumps([e.model_dump() for e in r["events"]], indent=2, default=str)
        )
        rows.append({**s, "name": r["name"], "elapsed": r["elapsed"],
                     "cost": r["cost"], "notes": r["notes"]})

    _print_table(rows)
    (RESULTS / "summary.json").write_text(json.dumps(rows, indent=2))
    print(f"\nPer-scraper event dumps + summary.json written to {RESULTS}/")


def _print_table(rows):
    hdr = ["scraper", "events", "complete", "geo%", "url%", "img%", "desc%", "time(s)", "cost"]
    widths = [38, 6, 8, 6, 6, 6, 6, 8, 14]

    def fmt_row(cells):
        return "  ".join(str(c).ljust(w) for c, w in zip(cells, widths))

    print("\n" + "=" * 110)
    print("  SCRAPER BAKE-OFF — Eventbrite / Bangalore / Science & Tech")
    print("=" * 110)
    print(fmt_row(hdr))
    print("-" * 110)
    for r in rows:
        print(fmt_row([
            r["name"][:38],
            r["events"],
            f"{r['completeness']*100:.0f}%",
            f"{r['geo_pct']*100:.0f}%",
            f"{r['url_pct']*100:.0f}%",
            f"{r['img_pct']*100:.0f}%",
            f"{r['desc_pct']*100:.0f}%",
            f"{r['elapsed']:.2f}",
            r["cost"],
        ]))
    print("-" * 110)
    for r in rows:
        print(f"  • {r['name']}: {r['notes']}")
    print("=" * 110)


if __name__ == "__main__":
    main()
