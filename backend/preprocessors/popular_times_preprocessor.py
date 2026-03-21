from __future__ import annotations

from typing import Any

import database as db


def process_popular_times_signal(raw_json: dict[str, Any], location_id: str) -> list[dict[str, Any]]:
    """
    populartimes library output: popular_times list of 7 dicts Mon-Sun with data per hour,
    or raw_json['popular_times'] + optional current_popularity.
    Writes to popular_times_baseline via caller — returns empty list for processed_signals.
    """
    popular = raw_json.get("popular_times")
    rows: list[tuple[int, int, float]] = []

    if popular and isinstance(popular, list):
        for day_i, day in enumerate(popular):
            if not isinstance(day, dict):
                continue
            data = day.get("data") or day.get("hours") or []
            if len(data) >= 24:
                for h in range(24):
                    v = data[h]
                    if v is None:
                        v = 0
                    rows.append((day_i % 7, h, float(min(100, max(0, v)))))
            else:
                for entry in data:
                    if isinstance(entry, dict):
                        h = int(entry.get("hour", 0))
                        v = float(entry.get("busyness", entry.get("percentage", 0)))
                        rows.append((day_i % 7, h, min(100, max(0, v))))

    if not rows and raw_json.get("synthetic_baseline"):
        syn = raw_json["synthetic_baseline"]
        for d in range(7):
            for h in range(24):
                rows.append((d, h, float(syn.get(str(d), {}).get(str(h), 40))))

    if not rows:
        for d in range(7):
            base = 35 + (d % 2) * 5
            for h in range(24):
                bump = 25 if 11 <= h <= 14 or 17 <= h <= 20 else 0
                rows.append((d, h, float(min(100, base + bump))))

    db.write_popular_times_baseline(location_id, rows)
    return []
