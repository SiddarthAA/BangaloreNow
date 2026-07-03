"""Approach A: custom scraper — raw httpx fetch + JSON-LD parse. No browser."""
import time

import httpx

from common import BROWSER_UA, TARGET_URL, extract_events_from_html


def scrape_custom() -> dict:
    t = time.perf_counter()
    with httpx.Client(follow_redirects=True, timeout=30, headers={"User-Agent": BROWSER_UA}) as c:
        r = c.get(TARGET_URL)
        html = r.text
    events = extract_events_from_html(html)
    return dict(
        name="custom (httpx + JSON-LD)",
        events=events,
        elapsed=time.perf_counter() - t,
        raw_chars=len(html),
        cost="free",
        notes=f"HTTP {r.status_code}, {len(html)//1024}KB",
    )
