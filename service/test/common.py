"""Shared schema, JSON-LD extraction, and scoring for the scraper bake-off.

Every scraper normalizes into the same `Event` model so the comparison is
apples-to-apples. Scoring rewards the fields BangaloreNow actually needs to put
an event on the map: coordinates above all, then the display fields.
"""
from __future__ import annotations

import json
from pydantic import BaseModel, field_validator
from selectolax.parser import HTMLParser

# Eventbrite "Science & Tech" events in Bangalore. The /d/ discovery URL 301s here.
TARGET_URL = "https://www.eventbrite.com/b/india--bangalore/science-and-tech/"

BROWSER_UA = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)

# Fields that matter for the map + a tech-event feed. Coordinates are weighted
# implicitly by also being reported on their own (geo_pct).
CORE_FIELDS = ["name", "start_date", "url", "venue", "address", "lat", "lng", "image", "description"]


class Event(BaseModel):
    name: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    url: str | None = None
    venue: str | None = None
    address: str | None = None
    lat: float | None = None
    lng: float | None = None
    image: str | None = None
    description: str | None = None

    @field_validator("lat", "lng", mode="before")
    @classmethod
    def _coerce_float(cls, v):
        if v in (None, ""):
            return None
        try:
            return float(v)
        except (TypeError, ValueError):
            return None


# --------------------------------------------------------------------------- #
# JSON-LD extraction (shared by the custom + crawl4ai scrapers)
# --------------------------------------------------------------------------- #
def _addr_str(addr) -> str | None:
    if not isinstance(addr, dict):
        return None
    parts = [
        addr.get(k)
        for k in ("streetAddress", "addressLocality", "addressRegion", "postalCode", "addressCountry")
    ]
    parts = [p for p in parts if p]
    return ", ".join(parts) or None


def event_from_jsonld(item: dict) -> Event:
    loc = item.get("location") or {}
    if isinstance(loc, list):
        loc = loc[0] if loc else {}
    geo = loc.get("geo") or {} if isinstance(loc, dict) else {}
    addr = loc.get("address") if isinstance(loc, dict) else None
    img = item.get("image")
    if isinstance(img, list):
        img = img[0] if img else None
    return Event(
        name=item.get("name"),
        start_date=item.get("startDate"),
        end_date=item.get("endDate"),
        url=item.get("url"),
        venue=(loc.get("name") if isinstance(loc, dict) else None),
        address=_addr_str(addr),
        lat=geo.get("latitude") if isinstance(geo, dict) else None,
        lng=geo.get("longitude") if isinstance(geo, dict) else None,
        image=img,
        description=item.get("description"),
    )


def _iter_events(data):
    """Yield every schema.org/Event dict found in a parsed JSON-LD blob."""
    if isinstance(data, dict):
        t = data.get("@type")
        if t == "Event" or (isinstance(t, list) and "Event" in t):
            yield data
        items = data.get("itemListElement")
        if isinstance(items, list):
            for el in items:
                if isinstance(el, dict):
                    yield from _iter_events(el.get("item", el))
    elif isinstance(data, list):
        for el in data:
            yield from _iter_events(el)


def extract_events_from_html(html: str) -> list[Event]:
    """Pull schema.org/Event objects out of every JSON-LD block in the HTML."""
    events: list[Event] = []
    for node in HTMLParser(html).css('script[type="application/ld+json"]'):
        txt = node.text()
        if not txt:
            continue
        try:
            data = json.loads(txt)
        except json.JSONDecodeError:
            continue
        for item in _iter_events(data):
            events.append(event_from_jsonld(item))
    return _dedup(events)


def _dedup(events: list[Event]) -> list[Event]:
    seen, out = set(), []
    for e in events:
        key = (e.name, e.start_date)
        if key in seen:
            continue
        seen.add(key)
        out.append(e)
    return out


# --------------------------------------------------------------------------- #
# Scoring
# --------------------------------------------------------------------------- #
def valid_geo(e: Event) -> bool:
    """A coordinate is only useful for the map if it's real. Reject None and the
    (0,0) null-island placeholder LLM extractors love to emit, and sanity-check
    it falls inside India's bounding box."""
    if e.lat is None or e.lng is None:
        return False
    if abs(e.lat) < 0.01 and abs(e.lng) < 0.01:
        return False
    return 6.0 <= e.lat <= 38.0 and 68.0 <= e.lng <= 98.0


def _completeness(e: Event) -> float:
    present = 0
    geo_ok = valid_geo(e)
    for f in CORE_FIELDS:
        if f in ("lat", "lng"):
            present += 1 if geo_ok else 0
        elif getattr(e, f) not in (None, ""):
            present += 1
    return present / len(CORE_FIELDS)


def score_run(events: list[Event]) -> dict:
    n = len(events)
    if n == 0:
        return dict(events=0, completeness=0.0, geo_pct=0.0, url_pct=0.0, img_pct=0.0, desc_pct=0.0)
    return dict(
        events=n,
        completeness=sum(_completeness(e) for e in events) / n,
        geo_pct=sum(1 for e in events if valid_geo(e)) / n,
        url_pct=sum(1 for e in events if e.url) / n,
        img_pct=sum(1 for e in events if e.image) / n,
        desc_pct=sum(1 for e in events if e.description) / n,
    )
