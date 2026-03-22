"""
LLM-powered event relevance filter using Gemini.

Sits between raw signal collection and the event preprocessor.
Scores each event for relevance to the specific business type,
returning a relevance score, crowd type, reason, and include/exclude decision.
"""
from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any

import database as db
from config import settings

logger = logging.getLogger("relevance_filter")

CROWD_CONFIDENCE_MODIFIER = {
    "transit": 1.0,
    "mixed": 0.85,
    "local": 0.70,
    "destination": 0.40,
}


def build_relevance_prompt(
    raw_events: list[dict[str, Any]], business_profile: dict[str, str]
) -> str:
    return f"""
You are a demand analyst for a {business_profile['business_type']} called \
{business_profile['business_name']} located at {business_profile['address']}.

Your job is to evaluate which upcoming events in the area are likely to \
meaningfully increase demand at this business.

Key principle: Events that create TRANSIT crowds (people moving through an \
area looking for food/drink) are relevant. Events that attract \
DESTINATION-specific crowds (people going specifically for that experience \
and unlikely to divert) are not relevant.

*** IMPORTANT: Factor travel time into your decision ***
The events now include `walk_minutes` and `transit_minutes` from the business.
Events over 20 mins walking AND over 15 mins by transit should require a much stronger crowd spillover justification to be included. An author signing or niche cultural event at that distance should be excluded. A stadium event at that distance may still be included if transit spillover is likely.

For a {business_profile['business_type']}, high relevance events include:
- Large sporting events (crowds before/after games want quick food)
- Street festivals and markets (general public foot traffic)
- Concerts and shows ending late (hungry crowds leaving venues)
- Public gatherings and parades

Low relevance events for a {business_profile['business_type']} include:
- Fine dining or wine events (wrong demographic)
- Private corporate functions (closed attendance)
- Niche hobby events (small destination-specific crowds)
- Art gallery openings (low foot traffic spillover)

Events to evaluate:
{json.dumps(raw_events, indent=2)}

Return a JSON array only. No other text. No markdown. No backticks.
Each item must have exactly these keys:
- event_name (string — must exactly match the name in the input)
- relevance_score (float 0.0 to 1.0)
- relevance_reason (one sentence, plain English, no jargon)
- crowd_type (exactly one of: transit, destination, local, mixed)
- include (boolean — true if relevance_score >= 0.4)
"""


def _fallback_scores(raw_events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Include all events with a neutral score when the LLM is unavailable."""
    return [
        {
            "event_name": e.get("name", "Unknown"),
            "relevance_score": 0.5,
            "relevance_reason": "Could not score — defaulting to include",
            "crowd_type": "mixed",
            "include": True,
        }
        for e in raw_events
    ]


def llm_relevance_filter(
    raw_events: list[dict[str, Any]],
    business_profile: dict[str, str],
    location_id: str,
) -> list[dict[str, Any]]:
    """
    Score each raw event for relevance to the business via Gemini.
    Returns scored events list. Saves reasoning to DB.
    Falls back to neutral scores if no API key or on error.
    """
    if not raw_events:
        return []

    prompt = build_relevance_prompt(raw_events, business_profile)

    logger.info(f"[RELEVANCE] Evaluating {len(raw_events)} events for {business_profile['business_name']}")
    print(f"\n{'='*60}")
    print(f"[RELEVANCE FILTER] {business_profile['business_name']} ({business_profile['business_type']})")
    print(f"[RELEVANCE] Evaluating {len(raw_events)} events")
    print(f"{'='*60}")

    key = settings.openrouter_api_key
    raw_text = ""
    if not key:
        print("[RELEVANCE] No OPENROUTER_API_KEY — falling back to neutral scores")
        scored_events = _fallback_scores(raw_events)
    else:
        try:
            import requests

            resp = requests.post(
                url="https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "qwen/qwen3-235b-a22b",
                    "messages": [{"role": "user", "content": prompt}],
                    "reasoning": {"enabled": True},
                },
                timeout=60,
            )
            resp.raise_for_status()
            data = resp.json()
            raw_text = data["choices"][0]["message"].get("content", "").strip()

            # Strip markdown fences if model added them
            if raw_text.startswith("```"):
                raw_text = raw_text.split("```")[1]
                if raw_text.startswith("json"):
                    raw_text = raw_text[4:]
            raw_text = raw_text.strip()

            scored_events = json.loads(raw_text)
        except Exception as exc:
            print(f"[RELEVANCE] Qwen call failed ({exc}) — falling back to neutral scores")
            scored_events = _fallback_scores(raw_events)
            raw_text = f"ERROR: {exc}"

    included_count = sum(1 for e in scored_events if e.get("include"))
    excluded_count = len(scored_events) - included_count

    # Terminal log each result
    for event in scored_events:
        status = "INCLUDE" if event.get("include") else "EXCLUDE"
        print(
            f"\n  [{status}] {event.get('event_name')}\n"
            f"    Score:      {event.get('relevance_score')}\n"
            f"    Crowd type: {event.get('crowd_type')}\n"
            f"    Reason:     {event.get('relevance_reason')}"
        )

    print(f"\n[RELEVANCE] Result: {included_count}/{len(scored_events)} events included")
    print(f"{'='*60}\n")

    # Persist reasoning to database
    scored_at = datetime.now(timezone.utc).isoformat()
    reasoning_rows = []
    for event in scored_events:
        reasoning_rows.append(
            {
                "id": str(uuid.uuid4()),
                "location_id": location_id,
                "event_name": event.get("event_name", "Unknown"),
                "event_date": event.get("event_date"),
                "relevance_score": float(event.get("relevance_score", 0.5)),
                "crowd_type": event.get("crowd_type", "mixed"),
                "reason": event.get("relevance_reason", ""),
                "include": bool(event.get("include", True)),
                "raw_llm_response": raw_text if "raw_text" in dir() else None,
                "prompt_used": prompt,
                "scored_at": scored_at,
                "input_events_count": len(raw_events),
                "included_count": included_count,
                "excluded_count": excluded_count,
            }
        )
    db.save_event_reasoning(reasoning_rows)

    return scored_events


def get_crowd_confidence_modifier(crowd_type: str, transit_minutes: float = 0.0) -> float:
    """Return confidence multiplier for a given crowd type, applying decay for transit distance."""
    base_modifier = CROWD_CONFIDENCE_MODIFIER.get(crowd_type, 0.70)
    if crowd_type == "transit" and transit_minutes > 20:
        decay = min(0.5, (transit_minutes - 20) * 0.02)
        base_modifier = max(0.1, base_modifier - decay)
    return base_modifier


def build_weather_prompt(
    weather_days: list[dict[str, Any]], business_profile: dict[str, str]
) -> str:
    return f"""
You are a demand analyst for a {business_profile['business_type']} called \
{business_profile.get('business_name', 'the business')} located in {business_profile.get('address', 'Sydney')}.

Your job is to evaluate the holistic impact of the weather forecast on foot traffic and customer demand.

Strictly adhere to these impact tiers for ALL evaluations:

Tier 1: Neutral
- Conditions: Clear, sunny, partly cloudy, mild, overcast, light cloud.
- impact_direction: neutral
- impact_magnitude: 0.0
- impact_conf: 1.0

Tier 2: Slight Drag  
- Conditions: Light rain, drizzle, showers.
- impact_direction: negative
- impact_magnitude: 0.05
- impact_conf: 0.95

Tier 3: Meaningful
- Conditions: Heavy rain, strong winds.
- impact_direction: negative
- impact_magnitude: 0.15
- impact_conf: 0.90

Tier 4: Severe
- Conditions: Storms, hail, flooding, extreme heat above 38°C, heatwave warnings.
- impact_direction: negative
- impact_magnitude: 0.30
- impact_conf: 0.85

Reason about the full weather picture holistically — temperature, precipitation, wind, and conditions together. Consider Sydney-specific norms.

Days to evaluate:
{json.dumps(weather_days, indent=2)}

Return a JSON array only. Each item must have:
- forecast_date (string)
- impact_direction (positive, negative, neutral)
- impact_magnitude (float matching the tier above)
- impact_conf (float matching the tier above)
- reasoning (one plain English sentence)
"""

def _fallback_weather_scores(weather_days: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "forecast_date": d.get("forecast_date", ""),
            "impact_direction": "neutral",
            "impact_magnitude": 0.0,
            "impact_conf": 0.70,
            "reasoning": "Could not score — defaulting to neutral",
        }
        for d in weather_days
    ]

def llm_weather_relevance(
    weather_days: list[dict[str, Any]],
    business_profile: dict[str, str],
    location_id: str,
) -> list[dict[str, Any]]:
    if not weather_days:
        return []

    prompt = build_weather_prompt(weather_days, business_profile)

    logger.info(f"[WEATHER_LLM] Evaluating {len(weather_days)} days for {business_profile.get('business_name', 'location')}")
    print(f"\n{'='*60}")
    print(f"[WEATHER LLM FILTER] {business_profile.get('business_name', 'location')} ({business_profile['business_type']})")
    print(f"[WEATHER_LLM] Evaluating {len(weather_days)} days")
    print(f"{'='*60}")

    key = settings.openrouter_api_key
    if not key:
        print("[WEATHER_LLM] No OPENROUTER_API_KEY — falling back to neutral scores")
        return _fallback_weather_scores(weather_days)

    try:
        import requests

        resp = requests.post(
            url="https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json",
            },
            json={
                "model": "qwen/qwen3-235b-a22b",
                "messages": [{"role": "user", "content": prompt}],
                "reasoning": {"enabled": True},
            },
            timeout=60,
        )
        resp.raise_for_status()
        data = resp.json()
        raw_text = data["choices"][0]["message"].get("content", "").strip()

        # Strip markdown fences if model added them
        if raw_text.startswith("```"):
            raw_text = raw_text.split("```")[1]
            if raw_text.startswith("json"):
                raw_text = raw_text[4:]
        raw_text = raw_text.strip()

        scored_days = json.loads(raw_text)
    except Exception as exc:
        print(f"[WEATHER_LLM] OpenRouter call failed ({exc}) — falling back to neutral scores")
        return _fallback_weather_scores(weather_days)

    # Terminal log each result
    if not isinstance(scored_days, list):
        print("[WEATHER_LLM] Invalid LLM response format — falling back")
        return _fallback_weather_scores(weather_days)
        
    for d in scored_days:
        print(
            f"\n  [{d.get('forecast_date')}] {str(d.get('impact_direction')).upper()}"
            f" (mag: {d.get('impact_magnitude')}, conf: {d.get('impact_conf')})\n"
            f"    Reason: {d.get('reasoning')}"
        )

    print(f"{'='*60}\n")
    return scored_days
