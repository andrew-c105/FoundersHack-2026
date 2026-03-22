# Swell – Demand Forecasting for Local Businesses
**Know before it gets busy.** Hourly busyness predictions for the next 60 days, powered by real-world signals — weather, events, transport, school terms, and competitor activity.
Built for hackathon demo.

## How It Works
Swell monitors external signals around your location and synthesises them into an hourly busyness index. No POS integration needed — just your address and business type. A retail store and a bubble tea shop both understand *"38% above your normal Sunday 9pm"*.

## Tech Stack
- **Frontend:** React 18, TypeScript, Vite, Tailwind CSS, Recharts, react-calendar-heatmap, Framer Motion
- **Backend:** FastAPI, APScheduler, XGBoost, scikit-learn, pandas
- **ML:** XGBoost regressor trained on Popular Times baselines + live signal uplifts
- **LLM:** OpenRouter (Gemini Flash) — event relevance filtering, weather summarisation, plain-English brief generation
- **Storage:** SQLite (single `.db` file)

**Fetched on refresh (scheduler every 6 hours, or manual refresh)**

- **Weather** — Open-Meteo hourly forecast (~16 days of real hourly data). Days beyond that are stored as **neutral placeholders** (no extra API calls) so the pipeline aligns with the 30-day horizon.
- **Events** — Eventbrite discovery near the location (when `EVENTBRITE_TOKEN` is set).
- **Competitors** — Google Places nearby search (open/permanently closed, ratings).
- **Transport / roads** — Transport NSW–style incident sample and Live Traffic NSW JSON feeds when keys/network allow (demo data may be used if APIs fail).

**From bundled static JSON** (`backend/data/static/`), expanded across the forecast window

- NSW school term / holiday-style flags  
- Australian public holidays by state  
- Sporting fixtures (geo-filtered)  
- University / TAFE calendar flags (geo-filtered)

**At onboarding**

- **Popular Times** (via the `populartimes` library and Google API key when configured) to seed the baseline busyness curve by day-of-week and hour.

There is **no** live ABS demographic ingestion or separate “signal map” page in the frontend; the API exposes `GET /api/locations/{id}/map-signals` if you want to build one.

## LLM relevance filtering (events & weather)

- **Events:** Raw Eventbrite (and similar) listings are batched to an **OpenRouter** chat model (`google/gemini-3.1-flash-lite-preview`). The model returns `relevance_score`, `crowd_type`, and an **include/exclude** flag so small professional or niche events are dropped before they affect the forecast. Reasoning rows can be stored for debugging (`event_reasoning` table).
- **Weather:** Non-trivial days can be summarized through the same OpenRouter path against tiered impact rules; results are cached per location/day.
- **Daily brief:** The manager brief is generated via OpenRouter from **already computed** prediction/signal JSON (not from free-form guessing).

If `OPENROUTER_API_KEY` is missing, the app falls back to template text and conservative defaults.

## Tech stack (as implemented)

| Layer | Stack |
|--------|--------|
| Backend | Python 3.9+, **FastAPI**, **SQLite**, **APScheduler** |
| ML | **XGBoost**, **scikit-learn**, **pandas** |
| LLM | **OpenRouter** (Gemini-flash model id above) |
| Frontend | **React 18**, **Vite**, **TypeScript**, **Tailwind CSS**, **Recharts**, **react-calendar-heatmap**, **Framer Motion** |

## Run locally

### Prerequisites

- Python **3.9+**, Node **18+**
- `pip install -r backend/requirements.txt` (includes `populartimes` for Popular Times)

### Environment variables

Create `backend/.env` (see repo root `.env.example` for a starting list). Commonly used:

| Variable | Role |
|----------|------|
| `GOOGLE_API_KEY` | Geocoding, Places, Popular Times |
| `EVENTBRITE_TOKEN` | Nearby events |
| `TRANSPORT_NSW_API_KEY` | Transport feeds (when used) |
| `OPENROUTER_API_KEY` | Event relevance, weather LLM pass, daily brief |
| `DEV_SYNTHETIC_SIGNALS` | If `true`, injects demo rows for a fixed date (development only) |

Frontend optional: `frontend/.env` with `VITE_API_URL` (defaults to `http://127.0.0.1:8000`).

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Open **http://localhost:5173**

## Environment Variables
Create `backend/.env` — see `.env.example` for the full list.

| Variable | Role |
|----------|------|
| `GOOGLE_API_KEY` | Geocoding, Places, Popular Times |
| `EVENTBRITE_TOKEN` | Nearby events |
| `TRANSPORT_NSW_API_KEY` | Transport feeds |
| `OPENROUTER_API_KEY` | LLM filtering and brief generation |
| `DEV_SYNTHETIC_SIGNALS` | If `true`, injects demo rows for development |

### Typical flow

| Method | Path | Description |
|--------|------|-------------|
| POST | /api/locations/onboarding | Create location + initial pipeline |
| POST | /api/locations/{id}/refresh | Re-fetch and preprocess signals |
| POST | /api/locations/{id}/train | Train model only |
| POST | /api/locations/{id}/predict | Run inference only |
| POST | /api/locations/{id}/bootstrap-model | Train + predict |
| GET | /api/locations/{id}/predictions | 60-day hourly forecast |
| GET | /api/locations/{id}/brief | Plain-English brief for a date |
| GET | /api/locations/{id}/signals/day | Aggregated signals for a calendar day |
| GET | /api/locations/{id}/alerts | Hours exceeding deviation threshold |
| GET | /api/locations/{id}/accuracy | Prediction vs actual history |

## Useful API routes

**Polled every 6 hours**
- Open-Meteo — hourly weather forecast (temperature, precipitation, conditions)
- Eventbrite — local events within 3km
- Google Places — nearby competitor status and closures
- Google Popular Times — historical busyness baseline by day and hour
- Transport NSW — real-time bus, train, ferry, metro, and light rail disruptions
- Live Traffic NSW — road closures and incidents within 800m

**Bundled static data, refreshed periodically**
- NSW school term dates
- Australian public holidays by state
- Sporting fixtures (AFL, NRL, A-League, Cricket) — geo-filtered
- University and TAFE academic calendars — geo-filtered

## Requirements
- **Python 3.9+** for backend
- **Node 18+** for frontend
- **populartimes** — unofficial Google Popular Times scraper: `pip install populartimes`
- API keys stored in `.env` — see `.env.example`

## Pages

| Page | Description |
|------|-------------|
| Landing | Value proposition, feature cards, single CTA |
| Onboarding | 4-step wizard: business type → address → trading hours → signal confirmation |
| Today's Brief | AI-written brief, 4 metric cards, signal breakdown chart, schedule approval |
| Forecast | 60-day heatmap, day view with hourly bars, alerts tab |
| Location Settings | Business profile, signal toggles, accuracy scoreboard |
| Accuracy History | Predicted vs actual line chart, per-signal reliability |

## License

MIT
