"""Approach C: Firecrawl — managed scrape + LLM structured extraction.

We ask Firecrawl to return a structured list of events matching our schema, so
there is zero per-site parsing code. Cost: API credits. We try a couple of
request shapes because Firecrawl's structured-extract field has been renamed
across API versions.
"""
import os
import time

import httpx

from common import Event, TARGET_URL

FC_ENDPOINT = "https://api.firecrawl.dev/v1/scrape"

EVENT_SCHEMA = {
    "type": "object",
    "properties": {
        "events": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "start_date": {"type": "string"},
                    "end_date": {"type": "string"},
                    "url": {"type": "string"},
                    "venue": {"type": "string"},
                    "address": {"type": "string"},
                    "lat": {"type": "number"},
                    "lng": {"type": "number"},
                    "image": {"type": "string"},
                    "description": {"type": "string"},
                },
            },
        }
    },
    "required": ["events"],
}

PROMPT = (
    "Extract every event listed on this page. For each event include its name, "
    "start date, end date, ticket URL, venue name, full address, latitude, "
    "longitude, image URL, and a short description. Return them under 'events'."
)


def _request_shapes() -> list[tuple[str, dict]]:
    base = {"url": TARGET_URL, "onlyMainContent": False}
    return [
        # Modern: formats:["json"] + jsonOptions
        ("formats[json]+jsonOptions", {
            **base, "formats": ["json"],
            "jsonOptions": {"schema": EVENT_SCHEMA, "prompt": PROMPT},
        }),
        # Older: formats:["extract"] + extract
        ("formats[extract]+extract", {
            **base, "formats": ["extract"],
            "extract": {"schema": EVENT_SCHEMA, "prompt": PROMPT},
        }),
    ]


def scrape_firecrawl_json() -> dict:
    key = os.environ["FIRECRAWL_API_KEY"]
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    t = time.perf_counter()

    used_shape, data, resp_text, status = None, None, "", None
    with httpx.Client(timeout=180) as c:
        for label, payload in _request_shapes():
            r = c.post(FC_ENDPOINT, headers=headers, json=payload)
            status, resp_text = r.status_code, r.text
            try:
                body = r.json()
            except Exception:
                body = {}
            if body.get("success"):
                d = body.get("data", {})
                extracted = d.get("json") or d.get("extract") or d.get("llm_extraction")
                if extracted is not None:
                    used_shape, data = label, d
                    break

    events: list[Event] = []
    credits = None
    if data is not None:
        extracted = data.get("json") or data.get("extract") or data.get("llm_extraction") or {}
        items = extracted.get("events", []) if isinstance(extracted, dict) else []
        for it in items:
            if isinstance(it, dict):
                events.append(Event(**{k: v for k, v in it.items() if k in Event.model_fields}))
        credits = (data.get("metadata") or {}).get("creditsUsed")

    return dict(
        name="firecrawl (managed + LLM extract)",
        events=events,
        elapsed=time.perf_counter() - t,
        raw_chars=len(resp_text),
        cost=f"{credits} credits" if credits is not None else "? credits",
        notes=f"HTTP {status}, shape={used_shape}" if used_shape else f"HTTP {status}, no structured data",
    )
