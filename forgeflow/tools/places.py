"""Business listings from OpenStreetMap (Nominatim). Free and open data (ODbL); data © OpenStreetMap contributors.

Usage policy: at most one request per second, with an identifying User-Agent.
"""
from __future__ import annotations

import threading
import time
from functools import lru_cache

import requests
from pydantic import BaseModel

from .. import config

NOMINATIM = "https://nominatim.openstreetmap.org/search"
HEADERS = {"User-Agent": "ForgeFlowAI/0.1 (hackathon prototype; https://github.com/bella-luz/forgeflow-ai)"}
ATTRIBUTION = "Map data © OpenStreetMap contributors"

_lock = threading.Lock()
_last_call = [0.0]


class Area(BaseModel):
    name: str
    south: float
    north: float
    west: float
    east: float


class Place(BaseModel):
    name: str
    category: str = ""
    address: str = ""
    city: str = ""
    lat: float | None = None
    lon: float | None = None
    website: str = ""
    phone: str = ""
    email: str = ""
    opening_hours: str = ""
    brand: str = ""
    osm_url: str = ""


def _get(params: dict) -> list[dict] | None:
    """One throttled Nominatim request. None on any failure."""
    with _lock:
        wait = 1.1 - (time.monotonic() - _last_call[0])
        if wait > 0:
            time.sleep(wait)
        try:
            resp = requests.get(NOMINATIM, params={**params, "format": "jsonv2"}, headers=HEADERS, timeout=config.HTTP_TIMEOUT)
        except requests.RequestException:
            return None
        finally:
            _last_call[0] = time.monotonic()
    if resp.status_code != 200:
        return None
    try:
        data = resp.json()
    except ValueError:
        return None
    return data if isinstance(data, list) else None


def _clean_web(value: str) -> str:
    try:
        return config.clean_url(value) if value else ""
    except ValueError:
        return ""


def to_place(item: dict) -> Place | None:
    name = (item.get("name") or "").strip()
    if not name:
        return None
    tags = item.get("extratags") or {}
    addr = item.get("address") or {}
    street = " ".join(x for x in (addr.get("road", ""), addr.get("house_number", "")) if x)
    city = addr.get("city") or addr.get("town") or addr.get("village") or addr.get("municipality") or ""
    address = ", ".join(x for x in (street, " ".join(x for x in (addr.get("postcode", ""), city) if x)) if x)
    email = (tags.get("email") or tags.get("contact:email") or "").strip()
    try:
        lat, lon = float(item["lat"]), float(item["lon"])
    except (KeyError, TypeError, ValueError):
        lat = lon = None
    osm_type, osm_id = item.get("osm_type"), item.get("osm_id")
    return Place(
        name=name,
        category=f"{item.get('category', '')}={item.get('type', '')}",
        address=address,
        city=city,
        lat=lat,
        lon=lon,
        website=_clean_web(tags.get("website") or tags.get("contact:website") or ""),
        phone=(tags.get("phone") or tags.get("contact:phone") or "").split(";")[0].strip(),
        email=email if config.valid_email(email) else "",
        opening_hours=tags.get("opening_hours", ""),
        brand=tags.get("brand", "") or tags.get("brand:wikidata", ""),
        osm_url=f"https://www.openstreetmap.org/{osm_type}/{osm_id}" if osm_type and osm_id else "",
    )


@lru_cache(maxsize=128)
def geocode(text: str) -> Area | None:
    data = _get({"q": text, "limit": 1})
    if not data:
        return None
    try:
        s, n, w, e = (float(x) for x in data[0]["boundingbox"])
    except (KeyError, ValueError, TypeError):
        return None
    return Area(name=data[0].get("display_name", text), south=s, north=n, west=w, east=e)


def search_in_area(phrase: str, area: Area, limit: int = 40) -> list[Place]:
    data = _get({
        "q": phrase, "viewbox": f"{area.west},{area.north},{area.east},{area.south}", "bounded": 1,
        "limit": limit, "extratags": 1, "addressdetails": 1,
    })
    return [p for p in (to_place(x) for x in data or []) if p]


def lookup(text: str) -> Place | None:
    """The best match for one named business, e.g. 'Shop name, street, town, country'."""
    data = _get({"q": text, "limit": 1, "extratags": 1, "addressdetails": 1})
    return to_place(data[0]) if data else None


def locate(text: str) -> tuple[float, float] | None:
    """Coordinates of an address."""
    data = _get({"q": text, "limit": 1})
    try:
        return (float(data[0]["lat"]), float(data[0]["lon"])) if data else None
    except (KeyError, ValueError, TypeError):
        return None
