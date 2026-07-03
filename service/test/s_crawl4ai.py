"""Approach B: crawl4ai — headless browser render, then JSON-LD parse of the
rendered HTML. Tests whether a real browser buys us anything over raw httpx."""
import time

from crawl4ai import AsyncWebCrawler, BrowserConfig, CacheMode, CrawlerRunConfig

from common import TARGET_URL, extract_events_from_html


async def scrape_crawl4ai() -> dict:
    t = time.perf_counter()
    browser_cfg = BrowserConfig(headless=True, verbose=False)
    run_cfg = CrawlerRunConfig(cache_mode=CacheMode.BYPASS, page_timeout=45000)
    async with AsyncWebCrawler(config=browser_cfg) as crawler:
        result = await crawler.arun(url=TARGET_URL, config=run_cfg)
    html = result.html or ""
    events = extract_events_from_html(html)
    return dict(
        name="crawl4ai (headless browser + JSON-LD)",
        events=events,
        elapsed=time.perf_counter() - t,
        raw_chars=len(html),
        cost="free (local browser)",
        notes=f"success={result.success}, {len(html)//1024}KB rendered",
    )
