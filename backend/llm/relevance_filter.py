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
    "mixed": 0.80,
    "local": 0.50,
    "destination": 0.20,
}


def build_relevance_prompt(
    raw_events: list[dict[str, Any]], business_profile: dict[str, str]
) -> str:
    return f"""
You are a demand analyst for a {business_profile['business_type']} called {business_profile['business_name']}.

Your job is to evaluate which upcoming events will meaningfully increase spontaneous foot traffic and demand at this business.

### THE CORE QUESTION
"Will this event cause a meaningful number of people who would not otherwise be nearby to walk past this business, feel hungry or thirsty, and be in a mindset where they would spontaneously enter a fast food restaurant?"

If the honest answer is no — exclude it. Default to exclusion, not inclusion.

### CATEGORIZATION GUIDELINES

#### HIGH Relevance (Score 0.7–1.0, crowd_type: transit)
- Large stadium/arena sporting events (AFL, NRL, Soccer, Cricket).
- Major outdoor festivals, street markets, or parades with general public attendance.
- Large concerts (1000+ capacity) especially with late finishers.
- Public transport disruptions re-routing volumes of commuters.

#### MEDIUM Relevance (Score 0.4–0.69, crowd_type: mixed)
- Community markets or large-scale outdoor events with walk-up attendance.
- Major public holidays with high street foot traffic expected.

#### LOW / EXCLUDE (Score < 0.4, crowd_type: local or destination)
- Professional networking, industry conferences, career fairs, corporate seminars.
- Educational info sessions, university open days, MBA events.
- Film clubs, book clubs, seniors' groups, hobby societies.
- Art gallery openings, wine tastings, fine dining events.
- Any event described as "niche", "professional", or "corporate".
- Any event requiring registration, ticket purchase, or membership.
- Any event with estimated attendance under 200 people.

### DISTANCE PENALTY
- If walk_minutes > 15 OR transit_minutes > 20, require an extremely strong justification (stadium-scale only).
- A networking event at this distance is an automatic EXCLUDE.

Events to evaluate:
{json.dumps(raw_events, indent=2)}

Return a JSON array only. Each item must have:
- event_name (string — exact match)
- relevance_score (float 0.0 to 1.0)
- relevance_reason (one sentence)
- crowd_type (transit, destination, local, mixed)
- include (boolean — true ONLY if relevance_score >= 0.65)
"""


def _fallback_scores(raw_events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Exclude all events by default when the LLM is unavailable."""
    print("[RELEVANCE] WARNING: fallback triggered — LLM did not run")
    return [
        {
            "event_name": e.get("name", "Unknown"),
            "relevance_score": 0.0,
            "relevance_reason": "Could not score — defaulting to exclude",
            "crowd_type": "mixed",
            "include": False,
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

    # Batch events to avoid token/credit limits (max 10 per call)
    BATCH_SIZE = 10
    all_scored_events: list[dict[str, Any]] = []
    all_raw_texts: list[str] = []

    print(f"\n{'='*60}")
    print(f"[RELEVANCE FILTER] {business_profile['business_name']} ({business_profile['business_type']})")
    print(f"[RELEVANCE] Evaluating {len(raw_events)} total events in batches of {BATCH_SIZE}")
    print(f"{'='*60}")

    key = settings.openrouter_api_key
    if not key:
        print("[RELEVANCE] No OPENROUTER_API_KEY — falling back")
        return _fallback_scores(raw_events)

    for i in range(0, len(raw_events), BATCH_SIZE):
        batch = raw_events[i : i + BATCH_SIZE]
        prompt = build_relevance_prompt(batch, business_profile)
        
        print(f"\n[RELEVANCE] Batch {i//BATCH_SIZE + 1}: Processing {len(batch)} events (Prompt: {len(prompt)} chars)")
        
        try:
            import requests

            payload = {
                "model": "google/gemini-3.1-flash-lite-preview",
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 2048,
                "temperature": 0.1,
            }
            
            resp = requests.post(
                url="https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {key}",
                    "Content-Type": "application/json",
                },
                json=payload,
                timeout=120,
            )
            resp.raise_for_status()
            data = resp.json()
            raw_text = data["choices"][0]["message"].get("content", "").strip()
            all_raw_texts.append(raw_text)

            if raw_text.startswith("```"):
                raw_text = raw_text.split("```")[1]
                if raw_text.startswith("json"):
                    raw_text = raw_text[4:]
            raw_text = raw_text.strip()

            batch_scored = json.loads(raw_text)
            if isinstance(batch_scored, list):
                for item in batch_scored:
                    print(
                        "[RELEVANCE] verdict | "
                        f"{item.get('event_name')} | "
                        f"include={item.get('include')} | "
                        f"relevance_score={item.get('relevance_score')} | "
                        f"crowd_type={item.get('crowd_type')}"
                    )
                all_scored_events.extend(batch_scored)
            else:
                print(f"[RELEVANCE] Error: LLM returned non-list for batch {i//BATCH_SIZE + 1}")
                fb = _fallback_scores(batch)
                for item in fb:
                    print(
                        "[RELEVANCE] verdict (fallback) | "
                        f"{item.get('event_name')} | include={item.get('include')} | "
                        f"relevance_score={item.get('relevance_score')} | "
                        f"crowd_type={item.get('crowd_type')}"
                    )
                all_scored_events.extend(fb)

        except Exception as exc:
            print(f"[RELEVANCE] Batch {i//BATCH_SIZE + 1} failed | Type: {type(exc).__name__} | Msg: {exc}")
            fb = _fallback_scores(batch)
            for item in fb:
                print(
                    "[RELEVANCE] verdict (fallback) | "
                    f"{item.get('event_name')} | include={item.get('include')} | "
                    f"relevance_score={item.get('relevance_score')} | "
                    f"crowd_type={item.get('crowd_type')}"
                )
            all_scored_events.extend(fb)
            all_raw_texts.append(f"ERROR: {exc}")

    # Final summary and persistence
    included_count = sum(1 for e in all_scored_events if e.get("include"))
    
    # Terminal log result summary
    print(f"\n[RELEVANCE] Final Result: {included_count}/{len(all_scored_events)} events included")
    print(f"{'='*60}\n")

    # Persist reasoning to database
    scored_at = datetime.now(timezone.utc).isoformat()
    reasoning_rows = []
    combined_raw_text = "\n---\n".join(all_raw_texts)
    
    for event in all_scored_events:
        reasoning_rows.append(
            {
                "id": str(uuid.uuid4()),
                "location_id": location_id,
                "event_name": event.get("event_name", "Unknown"),
                "event_date": event.get("event_date"),
                "relevance_score": float(event.get("relevance_score", 0.0)),
                "crowd_type": event.get("crowd_type", "mixed"),
                "reason": event.get("relevance_reason", ""),
                "include": bool(event.get("include", False)),
                "raw_llm_response": combined_raw_text,
                "prompt_used": "Multiple batches used",
                "scored_at": scored_at,
                "input_events_count": len(raw_events),
                "included_count": included_count,
                "excluded_count": len(all_scored_events) - included_count,
            }
        )
    db.save_event_reasoning(reasoning_rows)

    return all_scored_events


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
                "model": "google/gemini-3.1-flash-lite-preview",
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 1024,
                "temperature": 0.1,
            },
            timeout=120,
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
