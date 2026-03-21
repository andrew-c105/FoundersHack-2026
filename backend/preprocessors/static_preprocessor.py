from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from config import settings
from preprocessors.common import format_forecast_dt, haversine_km


def _load_json(name: str) -> Any:
    p = settings.static_data_dir / name
    if not p.exists():
        return {}
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def process_static_signal(raw_json: dict[str, Any], location_id: str) -> list[dict[str, Any]]:
    """
    raw_json carries: location {lat,lng}, state, optional forecast_days (default 30)
    Loads school_terms, public_holidays, fixtures, uni_calendar from static JSON.
    """
    loc = raw_json.get("location") or {}
    biz_lat = float(loc.get("lat", -33.8688))
    biz_lng = float(loc.get("lng", 151.2093))
    state = str(raw_json.get("state") or "NSW").upper()
    days = int(raw_json.get("forecast_days") or 30)

    school_terms = _load_json("school_terms.json")
    holidays = _load_json("public_holidays.json")
    fixtures = _load_json("sport_fixtures.json")
    uni_cal = _load_json("uni_calendar.json")

    now = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    out: list[dict[str, Any]] = []

    def hours_for_date(d: datetime) -> list[datetime]:
        return [d.replace(hour=h, tzinfo=timezone.utc) for h in range(24)]

    for offset in range(days):
        day = now + timedelta(days=offset)
        ds = day.strftime("%Y-%m-%d")

        is_school_hol = _in_school_holiday(school_terms, state, ds)
        is_pub_hol = _is_public_holiday(holidays, state, ds)
        sport = _sporting_fixture_near(fixtures, biz_lat, biz_lng, ds)
        uni_exam, uni_oweek = _uni_flags(uni_cal, biz_lat, biz_lng, ds)

        for hr in hours_for_date(day):
            if is_school_hol:
                out.append(
                    _row(location_id, "static_school", hr, 0.08, 0.99, "School holiday", None)
                )
            if is_pub_hol:
                hn = holidays.get(state, {}).get(ds) or "Public holiday"
                out.append(
                    _row(location_id, "static_holiday", hr, 0.12, 0.99, str(hn), None)
                )
            if uni_exam:
                out.append(
                    _row(location_id, "static_uni", hr, -0.06, 0.90, "University exam period", None)
                )
            if uni_oweek:
                out.append(
                    _row(location_id, "static_uni", hr, 0.15, 0.95, "O-Week / orientation", None)
                )

        # Sport fixtures: only emit rows for the match time window
        if sport:
            match_start_h = int(sport.get("match_time", "15:00").split(":")[0])
            match_end_h = int(sport.get("match_end_time", "17:00").split(":")[0])
            # Include 1 hour before kick-off through 1 hour after end (dispersal)
            start_h = max(0, match_start_h - 1)
            end_h = min(23, match_end_h + 1)
            for h in range(start_h, end_h + 1):
                hr_dt = day.replace(hour=h, tzinfo=timezone.utc)
                out.append(
                    _row(
                        location_id,
                        "static_sport",
                        hr_dt,
                        0.20,
                        0.95,
                        sport.get("label", "Sporting fixture"),
                        sport.get("distance_km"),
                        sport.get("source_url"),
                    )
                )

    return out


def _row(
    location_id: str,
    stype: str,
    dt: datetime,
    uplift: float,
    conf: float,
    label: str,
    dist_km: float | None,
    source_url: str | None = None,
) -> dict[str, Any]:
    return {
        "location_id": location_id,
        "signal_type": stype,
        "forecast_dt": format_forecast_dt(dt),
        "uplift_pct": uplift,
        "confidence": conf,
        "label": label,
        "distance_km": dist_km,
        "source_url": source_url or "",
    }


def _in_school_holiday(data: Any, state: str, ds: str) -> bool:
    if not isinstance(data, dict):
        return False
    st = data.get(state) or data.get("NSW") or {}
    for hol in st.get("holidays", []):
        if hol.get("start") <= ds <= hol.get("end"):
            return True
    return False


def _is_public_holiday(data: Any, state: str, ds: str) -> bool:
    if not isinstance(data, dict):
        return False
    st = data.get(state, {})
    return ds in st


def _sporting_fixture_near(
    fixtures: Any, lat: float, lng: float, ds: str
) -> dict[str, Any] | None:
    if not isinstance(fixtures, list):
        return None
    best: dict[str, Any] | None = None
    best_d = 999.0
    for f in fixtures:
        if f.get("match_date") != ds:
            continue
        vlat = float(f.get("venue_lat", lat))
        vlng = float(f.get("venue_lng", lng))
        d = haversine_km(lat, lng, vlat, vlng)
        if d <= 5.0 and d < best_d:
            best_d = d
            best = {
                "label": f"{f.get('home_team','')} vs {f.get('away_team','')}",
                "distance_km": round(d, 2),
                "source_url": f.get("source_url", ""),
                "match_time": f.get("match_time", "15:00"),
                "match_end_time": f.get("match_end_time", "17:00"),
                "competition": f.get("competition", ""),
            }
    return best


def _uni_flags(uni_cal: Any, lat: float, lng: float, ds: str) -> tuple[bool, bool]:
    exam = False
    oweek = False
    if not isinstance(uni_cal, list):
        return exam, oweek
    for u in uni_cal:
        vlat = float(u.get("campus_lat", lat))
        vlng = float(u.get("campus_lng", lng))
        if haversine_km(lat, lng, vlat, vlng) > 2.0:
            continue
        et = u.get("event_type", "")
        start = u.get("start_date")
        end = u.get("end_date")
        if not start or not end:
            continue
        if start <= ds <= end:
            if et == "exam_period":
                exam = True
            if et in ("o_week", "orientation", "O-week"):
                oweek = True
    return exam, oweek
