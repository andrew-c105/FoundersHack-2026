import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Generator, Optional

from config import settings


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def get_connection() -> sqlite3.Connection:
    path = settings.database_path
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


@contextmanager
def db_session() -> Generator[sqlite3.Connection, None, None]:
    conn = get_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db() -> None:
    with db_session() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS locations (
                id TEXT PRIMARY KEY,
                business_type TEXT NOT NULL,
                address TEXT,
                lat REAL NOT NULL,
                lng REAL NOT NULL,
                postcode TEXT,
                state TEXT DEFAULT 'NSW',
                google_place_id TEXT,
                max_staff INTEGER DEFAULT 5,
                trading_hours_json TEXT,
                signal_toggles_json TEXT,
                competitor_closed_tracking_json TEXT,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS raw_signals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                location_id TEXT NOT NULL,
                signal_type TEXT NOT NULL,
                fetched_at TEXT NOT NULL,
                raw_json TEXT NOT NULL,
                FOREIGN KEY (location_id) REFERENCES locations(id)
            );

            CREATE TABLE IF NOT EXISTS processed_signals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                location_id TEXT NOT NULL,
                signal_type TEXT NOT NULL,
                forecast_dt TEXT NOT NULL,
                uplift_pct REAL NOT NULL,
                confidence REAL NOT NULL,
                label TEXT,
                distance_km REAL,
                source_url TEXT,
                extra_json TEXT,
                FOREIGN KEY (location_id) REFERENCES locations(id)
            );

            CREATE TABLE IF NOT EXISTS popular_times_baseline (
                location_id TEXT NOT NULL,
                day_of_week INTEGER NOT NULL,
                hour INTEGER NOT NULL,
                busyness_score REAL NOT NULL,
                PRIMARY KEY (location_id, day_of_week, hour),
                FOREIGN KEY (location_id) REFERENCES locations(id)
            );

            CREATE TABLE IF NOT EXISTS predictions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                location_id TEXT NOT NULL,
                forecast_dt TEXT NOT NULL,
                busyness_index INTEGER NOT NULL,
                baseline_score REAL NOT NULL,
                deviation_pct INTEGER NOT NULL,
                confidence REAL NOT NULL,
                UNIQUE(location_id, forecast_dt),
                FOREIGN KEY (location_id) REFERENCES locations(id)
            );

            CREATE TABLE IF NOT EXISTS accuracy_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                location_id TEXT NOT NULL,
                evaluated_at TEXT NOT NULL,
                mae REAL NOT NULL,
                metric_name TEXT DEFAULT 'mae',
                FOREIGN KEY (location_id) REFERENCES locations(id)
            );

            CREATE TABLE IF NOT EXISTS daily_briefs (
                location_id TEXT NOT NULL,
                target_date TEXT NOT NULL,
                brief_text TEXT NOT NULL,
                generated_at TEXT NOT NULL,
                PRIMARY KEY (location_id, target_date),
                FOREIGN KEY (location_id) REFERENCES locations(id)
            );

            CREATE INDEX IF NOT EXISTS idx_raw_loc_type ON raw_signals(location_id, signal_type);
            CREATE INDEX IF NOT EXISTS idx_proc_loc_dt ON processed_signals(location_id, forecast_dt);
            CREATE INDEX IF NOT EXISTS idx_pred_loc_dt ON predictions(location_id, forecast_dt);
            """
        )


def insert_raw_signal(location_id: str, signal_type: str, raw: Any) -> int:
    with db_session() as conn:
        cur = conn.execute(
            """
            INSERT INTO raw_signals (location_id, signal_type, fetched_at, raw_json)
            VALUES (?, ?, ?, ?)
            """,
            (location_id, signal_type, _utc_now_iso(), json.dumps(raw)),
        )
        return int(cur.lastrowid)


def write_processed_signals(
    location_id: str,
    signal_type: str,
    rows: list[dict[str, Any]],
) -> None:
    if not rows:
        return
    with db_session() as conn:
        if signal_type == "static":
            conn.execute(
                """
                DELETE FROM processed_signals
                WHERE location_id = ? AND signal_type LIKE 'static_%'
                """,
                (location_id,),
            )
        else:
            conn.execute(
                "DELETE FROM processed_signals WHERE location_id = ? AND signal_type = ?",
                (location_id, signal_type),
            )
        for r in rows:
            conn.execute(
                """
                INSERT INTO processed_signals
                (location_id, signal_type, forecast_dt, uplift_pct, confidence, label, distance_km, source_url, extra_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    r.get("location_id", location_id),
                    r.get("signal_type", signal_type),
                    r["forecast_dt"],
                    float(r["uplift_pct"]),
                    float(r["confidence"]),
                    r.get("label"),
                    r.get("distance_km"),
                    r.get("source_url"),
                    json.dumps(r.get("extra")) if r.get("extra") is not None else None,
                ),
            )


def write_popular_times_baseline(
    location_id: str,
    rows: list[tuple[int, int, float]],
) -> None:
    """rows: (day_of_week 0-6, hour 0-23, busyness_score)"""
    with db_session() as conn:
        conn.execute(
            "DELETE FROM popular_times_baseline WHERE location_id = ?",
            (location_id,),
        )
        conn.executemany(
            """
            INSERT INTO popular_times_baseline (location_id, day_of_week, hour, busyness_score)
            VALUES (?, ?, ?, ?)
            """,
            [(location_id, d, h, s) for d, h, s in rows],
        )


def get_location(location_id: str) -> Optional[dict[str, Any]]:
    with db_session() as conn:
        row = conn.execute(
            "SELECT * FROM locations WHERE id = ?", (location_id,)
        ).fetchone()
        if not row:
            return None
        return dict(row)


def update_location_tracking(location_id: str, tracking: dict[str, Any]) -> None:
    with db_session() as conn:
        conn.execute(
            "UPDATE locations SET competitor_closed_tracking_json = ? WHERE id = ?",
            (json.dumps(tracking), location_id),
        )


def get_competitor_tracking(location_id: str) -> dict[str, Any]:
    loc = get_location(location_id)
    if not loc or not loc.get("competitor_closed_tracking_json"):
        return {}
    try:
        return json.loads(loc["competitor_closed_tracking_json"])
    except json.JSONDecodeError:
        return {}


def get_signal_uplift(location_id: str, signal_types: list[str], forecast_dt_iso: str) -> float:
    """Sum uplift for latest batch per type for this exact hour."""
    if not signal_types:
        return 0.0
    placeholders = ",".join("?" * len(signal_types))
    with db_session() as conn:
        rows = conn.execute(
            f"""
            SELECT signal_type, SUM(uplift_pct) as u
            FROM processed_signals
            WHERE location_id = ? AND forecast_dt = ? AND signal_type IN ({placeholders})
            GROUP BY signal_type
            """,
            (location_id, forecast_dt_iso, *signal_types),
        ).fetchall()
    return float(sum(float(r["u"] or 0) for r in rows))


def get_signal_confidence(
    location_id: str,
    signal_types: list[str],
    forecast_dt_iso: str,
    default: float = 0.1,
) -> float:
    if not signal_types:
        return default
    placeholders = ",".join("?" * len(signal_types))
    with db_session() as conn:
        rows = conn.execute(
            f"""
            SELECT AVG(confidence) as c
            FROM processed_signals
            WHERE location_id = ? AND forecast_dt = ? AND signal_type IN ({placeholders})
            """,
            (location_id, forecast_dt_iso, *signal_types),
        ).fetchone()
    if rows and rows["c"] is not None:
        return float(rows["c"])
    return default


def get_popular_times_baseline(location_id: str, day_of_week: int, hour: int) -> float:
    with db_session() as conn:
        row = conn.execute(
            """
            SELECT busyness_score FROM popular_times_baseline
            WHERE location_id = ? AND day_of_week = ? AND hour = ?
            """,
            (location_id, day_of_week, hour),
        ).fetchone()
    if row:
        return float(row["busyness_score"])
    return 40.0


def get_processed_signals_for_hour(location_id: str, forecast_dt_iso: str) -> list[dict[str, Any]]:
    with db_session() as conn:
        rows = conn.execute(
            """
            SELECT signal_type, forecast_dt, uplift_pct, confidence, label, distance_km, source_url
            FROM processed_signals
            WHERE location_id = ? AND forecast_dt = ?
            """,
            (location_id, forecast_dt_iso),
        ).fetchall()
    return [dict(r) for r in rows]


def write_predictions(rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    loc = rows[0]["location_id"]
    with db_session() as conn:
        conn.execute("DELETE FROM predictions WHERE location_id = ?", (loc,))
        conn.executemany(
            """
            INSERT INTO predictions (location_id, forecast_dt, busyness_index, baseline_score, deviation_pct, confidence)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    r["location_id"],
                    r["forecast_dt"],
                    r["busyness_index"],
                    r["baseline_score"],
                    r["deviation_pct"],
                    r["confidence"],
                )
                for r in rows
            ],
        )


def get_predictions_for_location(
    location_id: str,
    start: Optional[str] = None,
    end: Optional[str] = None,
) -> list[dict[str, Any]]:
    q = "SELECT * FROM predictions WHERE location_id = ?"
    params: list[Any] = [location_id]
    if start:
        q += " AND forecast_dt >= ?"
        params.append(start)
    if end:
        q += " AND forecast_dt <= ?"
        params.append(end)
    q += " ORDER BY forecast_dt"
    with db_session() as conn:
        rows = conn.execute(q, params).fetchall()
    return [dict(r) for r in rows]


def get_predictions_for_date(location_id: str, target_date: str) -> list[dict[str, Any]]:
    """target_date YYYY-MM-DD"""
    start = f"{target_date}T00:00:00"
    end = f"{target_date}T23:00:00"
    with db_session() as conn:
        rows = conn.execute(
            """
            SELECT * FROM predictions
            WHERE location_id = ? AND forecast_dt >= ? AND forecast_dt <= ?
            ORDER BY forecast_dt
            """,
            (location_id, start, end),
        ).fetchall()
    return [dict(r) for r in rows]


def save_daily_brief(location_id: str, target_date: str, text: str) -> None:
    with db_session() as conn:
        conn.execute(
            """
            INSERT INTO daily_briefs (location_id, target_date, brief_text, generated_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(location_id, target_date) DO UPDATE SET
                brief_text = excluded.brief_text,
                generated_at = excluded.generated_at
            """,
            (location_id, target_date, text, _utc_now_iso()),
        )


def get_daily_brief(location_id: str, target_date: str) -> Optional[str]:
    with db_session() as conn:
        row = conn.execute(
            "SELECT brief_text FROM daily_briefs WHERE location_id = ? AND target_date = ?",
            (location_id, target_date),
        ).fetchone()
    if row:
        return str(row["brief_text"])
    return None


def log_accuracy(location_id: str, mae: float, metric_name: str = "mae") -> None:
    with db_session() as conn:
        conn.execute(
            """
            INSERT INTO accuracy_history (location_id, evaluated_at, mae, metric_name)
            VALUES (?, ?, ?, ?)
            """,
            (location_id, _utc_now_iso(), mae, metric_name),
        )


def get_accuracy_history(location_id: str, limit: int = 60) -> list[dict[str, Any]]:
    with db_session() as conn:
        rows = conn.execute(
            """
            SELECT * FROM accuracy_history WHERE location_id = ?
            ORDER BY evaluated_at DESC LIMIT ?
            """,
            (location_id, limit),
        ).fetchall()
    return [dict(r) for r in rows]


def create_location(row: dict[str, Any]) -> None:
    with db_session() as conn:
        conn.execute(
            """
            INSERT INTO locations (
                id, business_type, address, lat, lng, postcode, state, google_place_id,
                max_staff, trading_hours_json, signal_toggles_json, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                row["id"],
                row["business_type"],
                row.get("address"),
                row["lat"],
                row["lng"],
                row.get("postcode"),
                row.get("state", "NSW"),
                row.get("google_place_id"),
                int(row.get("max_staff") or 5),
                row.get("trading_hours_json"),
                row.get("signal_toggles_json"),
                _utc_now_iso(),
            ),
        )


def list_locations() -> list[dict[str, Any]]:
    with db_session() as conn:
        rows = conn.execute("SELECT * FROM locations ORDER BY created_at DESC").fetchall()
    return [dict(r) for r in rows]


def update_location(location_id: str, fields: dict[str, Any]) -> None:
    if not fields:
        return
    cols = []
    vals: list[Any] = []
    for k, v in fields.items():
        if k == "id":
            continue
        cols.append(f"{k} = ?")
        vals.append(v)
    vals.append(location_id)
    with db_session() as conn:
        conn.execute(
            f"UPDATE locations SET {', '.join(cols)} WHERE id = ?",
            vals,
        )


def get_map_signals(location_id: str) -> list[dict[str, Any]]:
    """Latest processed rows with coordinates for map (approximate from labels)."""
    with db_session() as conn:
        rows = conn.execute(
            """
            SELECT signal_type, label, uplift_pct, confidence, distance_km, source_url, forecast_dt
            FROM processed_signals
            WHERE location_id = ?
            ORDER BY id DESC
            LIMIT 500
            """,
            (location_id,),
        ).fetchall()
    return [dict(r) for r in rows]
