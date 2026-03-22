from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Optional

import requests
import googlemaps

from config import settings


def geocode_address(address: str) -> tuple[float, float, str, str]:
    """Geocode using Google Geocoding API (preferred) or Nominatim fallback.
    Returns lat, lng, postcode, state."""
    if not address.strip():
        return -33.8688, 151.2093, "2000", "NSW"

    key = settings.google_api_key
    if key:
        try:
            r = requests.get(
                "https://maps.googleapis.com/maps/api/geocode/json",
                params={"address": address, "key": key},
                timeout=15,
            )
            data = r.json()
            if data.get("status") == "OK" and data.get("results"):
                loc = data["results"][0]["geometry"]["location"]
                lat = float(loc["lat"])
                lng = float(loc["lng"])
                postcode = "2000"
                state = "NSW"
                for comp in data["results"][0].get("address_components", []):
                    types = comp.get("types", [])
                    if "postal_code" in types:
                        postcode = comp["short_name"]
                    if "administrative_area_level_1" in types:
                        sn = comp["short_name"]
                        if sn in ("VIC", "QLD", "NSW", "ACT", "WA", "SA", "TAS", "NT"):
                            state = sn
                print(f"[GEOCODE] Google resolved '{address}' → lat={lat}, lng={lng}, postcode={postcode}, state={state}")
                return lat, lng, postcode, state
        except Exception as e:
            print(f"[GEOCODE] Google geocoding failed ({e}), falling back to Nominatim")

    # Nominatim fallback
    try:
        r = requests.get(
            "https://nominatim.openstreetmap.org/search",
            params={"q": address, "format": "json", "limit": 1},
            headers={"User-Agent": "FoundersHackForecast/1.0"},
            timeout=15,
        )
        r.raise_for_status()
        data = r.json()
        if not data:
            return -33.8688, 151.2093, "2000", "NSW"
        lat = float(data[0]["lat"])
        lng = float(data[0]["lon"])
        display = data[0].get("display_name", "")
        postcode = "2000"
        state = "NSW"
        parts = display.split(", ")
        for p in parts:
            if p.isdigit() and len(p) == 4:
                postcode = p
        if "Victoria" in display:
            state = "VIC"
        elif "Queensland" in display:
            state = "QLD"
        elif "New South Wales" in display or "NSW" in display:
            state = "NSW"
        print(f"[GEOCODE] Nominatim resolved '{address}' → lat={lat}, lng={lng}, postcode={postcode}, state={state}")
        return lat, lng, postcode, state
    except Exception:
        return -33.8688, 151.2093, "2000", "NSW"


def fetch_open_meteo(lat: float, lng: float) -> dict[str, Any]:
    try:
        url = "https://api.open-meteo.com/v1/forecast"
        r = requests.get(
            url,
            params={
                "latitude": lat,
                "longitude": lng,
                "hourly": "temperature_2m,precipitation,weathercode,wind_speed_10m",
                "forecast_days": 16,
                "timezone": "Australia/Sydney",
            },
            timeout=25,
        )
        r.raise_for_status()
        return r.json()
    except Exception:
        return _fallback_weather(lat, lng)


def _fallback_weather(lat: float, lng: float) -> dict[str, Any]:
    now = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
    times = []
    temps = []
    precips = []
    codes = []
    winds = []
    for i in range(24 * 10):
        t = now + timedelta(hours=i)
        times.append(t.strftime("%Y-%m-%dT%H:%M"))
        temps.append(22.0 + (i % 7) * 0.5)
        precips.append(0.0 if i % 11 else 3.0)
        codes.append(0)
    return {"hourly": {"time": times, "temperature_2m": temps, "precipitation": precips, "weathercode": codes}}


def fetch_eventbrite_nearby(lat: float, lng: float) -> dict[str, Any]:
    token = settings.eventbrite_token
    if not token:
        return {"source": "eventbrite", "location": {"lat": lat, "lng": lng}, "events": _demo_events(lat, lng)}
    try:
        # Modern Eventbrite replacement for deprecated /events/search/
        # Uses POST destination/search with point_radius
        url = "https://www.eventbriteapi.com/v3/destination/search/"
        payload = {
            "event_search": {
                "point_radius": {
                    "latitude": f"{lat}",
                    "longitude": f"{lng}",
                    "radius": "3km"
                },
                "dates": "current_future",
                "page_size": 20
            }
        }
        r = requests.post(
            url,
            json=payload,
            headers={"Authorization": f"Bearer {token}"},
            timeout=20,
        )
        if r.status_code != 200:
            return {"source": "eventbrite", "location": {"lat": lat, "lng": lng}, "events": _demo_events(lat, lng)}
        data = r.json()
        # Structural change: results are in p['events']['results']
        events_list = data.get("events", {}).get("results", [])
        events_out = []
        for ev in events_list:
            # Venue coordinates aren't easily part of this new payload without extra expansions
            # Fallback to search center if locations are generic
            events_out.append(
                {
                    "name": ev.get("name", "Event"),
                    "venue_lat": lat,
                    "venue_lng": lng,
                    "capacity": 8000,
                    "tickets_sold": 0,
                    "status": "onsale" if not ev.get("is_cancelled") else "cancelled",
                    # Format start/end from separate date/time fields
                    "event_start_datetime": f"{ev.get('start_date')}T{ev.get('start_time')}Z",
                    "event_end_time": f"{ev.get('end_date')}T{ev.get('end_time')}Z",
                    "source_url": ev.get("url", ""),
                }
            )
        _enrich_with_travel_times(events_out, lat, lng)
        return {"source": "eventbrite", "location": {"lat": lat, "lng": lng}, "events": events_out}
    except Exception:
        return {"source": "eventbrite", "location": {"lat": lat, "lng": lng}, "events": _demo_events(lat, lng)}


def _demo_events(lat: float, lng: float) -> list[dict[str, Any]]:
    start = datetime.now(timezone.utc) + timedelta(days=2)
    end = start + timedelta(hours=3)
    events = [
        {
            "name": "Local festival (demo)",
            "venue_lat": lat + 0.005,
            "venue_lng": lng + 0.005,
            "capacity": 12000,
            "tickets_sold": 4000,
            "status": "onsale",
            "event_start_datetime": start.isoformat(),
            "event_end_time": end.isoformat(),
            "source_url": "https://www.eventbrite.com/",
        }
    ]
    _enrich_with_travel_times(events, lat, lng)
    return events


def _enrich_with_travel_times(events: list[dict[str, Any]], biz_lat: float, biz_lng: float) -> None:
    key = settings.google_api_key
    if not key or not events:
        return
    try:
        gmaps = googlemaps.Client(key=key)
        for ev in events:
            vlat = ev.get("venue_lat")
            vlng = ev.get("venue_lng")
            if vlat is None or vlng is None:
                continue
            
            # walk
            try:
                wm = gmaps.distance_matrix(
                    origins=(biz_lat, biz_lng),
                    destinations=(vlat, vlng),
                    mode="walking"
                )
                if wm["rows"][0]["elements"][0]["status"] == "OK":
                    ev["walk_minutes"] = int(wm["rows"][0]["elements"][0]["duration"]["value"] / 60)
            except Exception as e:
                print(f"[GEOCODE] Walk distance matrix failed: {e}")

            # transit
            try:
                tm = gmaps.distance_matrix(
                    origins=(biz_lat, biz_lng),
                    destinations=(vlat, vlng),
                    mode="transit"
                )
                if tm["rows"][0]["elements"][0]["status"] == "OK":
                    ev["transit_minutes"] = int(tm["rows"][0]["elements"][0]["duration"]["value"] / 60)
            except Exception as e:
                print(f"[GEOCODE] Transit distance matrix failed: {e}")
    except Exception as e:
        print(f"[GEOCODE] Distance matrix client init failed: {e}")


def fetch_google_places_nearby(lat: float, lng: float, business_type: str = "restaurant") -> dict[str, Any]:
    key = settings.google_api_key
    if not key:
        return {
            "location": {"lat": lat, "lng": lng},
            "results": _demo_competitors(lat, lng),
        }
    try:
        r = requests.get(
            "https://maps.googleapis.com/maps/api/place/nearbysearch/json",
            params={
                "location": f"{lat},{lng}",
                "radius": 1500,
                "type": "restaurant",
                "key": key,
            },
            timeout=20,
        )
        data = r.json()
        results = data.get("results", [])
        return {"location": {"lat": lat, "lng": lng}, "results": results[:25]}
    except Exception:
        return {"location": {"lat": lat, "lng": lng}, "results": _demo_competitors(lat, lng)}


def _demo_competitors(lat: float, lng: float) -> list[dict[str, Any]]:
    return [
        {
            "place_id": "demo_closed_1",
            "name": "Demo Closed Diner",
            "business_status": "PERMANENTLY_CLOSED",
            "geometry": {"location": {"lat": lat + 0.002, "lng": lng + 0.001}},
        },
        {
            "place_id": "demo_open_1",
            "name": "Demo Open Cafe",
            "business_status": "OPERATIONAL",
            "geometry": {"location": {"lat": lat - 0.001, "lng": lng + 0.002}},
        },
    ]


def fetch_popular_times_raw(place_id: str, lat: float, lng: float) -> dict[str, Any]:
    key = settings.google_api_key
    if not key or not place_id:
        return {"synthetic_baseline": _default_synthetic_baseline(), "current_popularity": 45}
    try:
        import populartimes

        out = populartimes.get_id(key, place_id)
        return out if isinstance(out, dict) else {"synthetic_baseline": _default_synthetic_baseline()}
    except Exception:
        return {"synthetic_baseline": _default_synthetic_baseline(), "current_popularity": 45}


def _default_synthetic_baseline() -> dict[str, dict[str, float]]:
    out: dict[str, dict[str, float]] = {}
    for d in range(7):
        out[str(d)] = {}
        for h in range(24):
            base = 30
            if 11 <= h <= 14:
                base = 65
            if 17 <= h <= 21:
                base = 75
            if h < 7 or h > 22:
                base = 15
            out[str(d)][str(h)] = float(base)
    return out


def find_google_place_id(address: str, lat: float, lng: float) -> Optional[str]:
    key = settings.google_api_key
    if not key:
        return None
    try:
        r = requests.get(
            "https://maps.googleapis.com/maps/api/place/findplacefromtext/json",
            params={
                "input": address,
                "inputtype": "textquery",
                "fields": "place_id,geometry",
                "locationbias": f"circle:2000@{lat},{lng}",
                "key": key,
            },
            timeout=15,
        )
        cands = r.json().get("candidates") or []
        if cands:
            return cands[0].get("place_id")
    except Exception:
        return None
    return None


def fetch_transport_nsw_sample(lat: float, lng: float) -> dict[str, Any]:
    key = settings.transport_nsw_api_key
    if not key:
        return _demo_transport(lat, lng, "transport_nsw")
    base = "https://api.transport.nsw.gov.au/v1/gtfs/realtime/sydneytrains"
    try:
        r = requests.get(
            base,
            headers={"Authorization": f"apikey {key}"},
            timeout=20,
        )
        raw = {"gtfs_status": r.status_code, "snippet": r.text[:1500], "location": {"lat": lat, "lng": lng}}
        return {
            "signal_subtype": "transport_nsw",
            "location": {"lat": lat, "lng": lng},
            "incidents": [],
            "raw": raw,
        }
    except Exception:
        return _demo_transport(lat, lng, "transport_nsw")


def fetch_live_traffic_nsw(lat: float, lng: float) -> dict[str, Any]:
    url = (
        "https://opendata.transport.nsw.gov.au/data/dataset/"
        "86b2d56f-b784-4951-a6e8-e690fd7cc7ca/resource/"
        "74230226-c8cc-4d87-a1b8-886457ef0b1a/download/livetrafficsitestatus_0.json"
    )
    try:
        r = requests.get(url, timeout=30)
        data = r.json()
        feats = data if isinstance(data, list) else data.get("features") or []
        incidents = []
        for item in feats[:40]:
            geom = item.get("geometry") or {}
            coords = geom.get("coordinates")
            if not coords:
                continue
            ilat, ilng = float(coords[1]), float(coords[0])
            incidents.append(
                {
                    "incident_type": str(item.get("properties", {}).get("type", "MINOR_WORKS")).upper()
                    or "MINOR_WORKS",
                    "confirmed": True,
                    "start_time": datetime.now(timezone.utc).isoformat(),
                    "end_time": (datetime.now(timezone.utc) + timedelta(hours=12)).isoformat(),
                    "geometry": {"lat": ilat, "lng": ilng},
                    "roads_affected": item.get("properties", {}).get("title", "Traffic incident"),
                    "source_url": "https://opendata.transport.nsw.gov.au/",
                }
            )
        return {"signal_subtype": "live_traffic", "location": {"lat": lat, "lng": lng}, "incidents": incidents}
    except Exception:
        return _demo_transport(lat, lng, "live_traffic")


def _demo_transport(lat: float, lng: float, subtype: str) -> dict[str, Any]:
    return {
        "signal_subtype": subtype,
        "location": {"lat": lat, "lng": lng},
        "incidents": [
            {
                "incident_type": "MINOR_WORKS",
                "confirmed": True,
                "start_time": datetime.now(timezone.utc).isoformat(),
                "end_time": (datetime.now(timezone.utc) + timedelta(hours=8)).isoformat(),
                "geometry": {"lat": lat + 0.001, "lng": lng + 0.001},
                "roads_affected": "Demo lane reduction near location",
                "source_url": "https://opendata.transport.nsw.gov.au/",
            }
        ],
    }
