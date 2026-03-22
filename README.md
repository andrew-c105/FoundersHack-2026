# PulsePoint – Demand Forecasting for Franchise Restaurants
**Know before it gets busy.** Hourly busyness predictions for the next 30 days, powered by real-world signals — weather, events, transport, school terms, and competitor activity.
Built for hackathon demo.

## How It Works
PulsePoint monitors external signals around your location and synthesises them into an hourly busyness index. No POS integration needed — just your address and business type. A McDonald's and a bubble tea shop both understand *"38% above your normal Sunday 9pm"*.

## Tech Stack
- **Frontend:** React, Tailwind CSS, Recharts, react-calendar-heatmap, React-Leaflet, Framer Motion
- **Backend:** FastAPI, APScheduler, XGBoost, scikit-learn, pandas
- **ML:** XGBoost regressor trained on Popular Times baselines + live signal uplifts
- **LLM:** Google Gemini (plain-English brief generation)
- **Storage:** SQLite (single `.db` file)

## Quick Start

### 1. Backend
```bash
cd backend
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

### 2. Frontend
```bash
cd frontend
npm install
npm run dev
```

Open **http://localhost:3000**

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | /locations | List registered locations |
| POST | /locations | Onboard a new location |
| GET | /locations/{id}/brief | Today's LLM-generated brief |
| GET | /locations/{id}/predictions | 30-day hourly forecast |
| GET | /locations/{id}/signals | Processed signal breakdown |
| GET | /locations/{id}/baseline | Popular Times baseline curve |
| POST | /locations/{id}/train | Trigger XGBoost retrain |
| GET | /locations/{id}/accuracy | Prediction vs actual history |
| GET | /locations/{id}/alerts | Hours exceeding +30% above normal |

## Signal Sources

**Polled every 6 hours**
- Open-Meteo — hourly weather forecast (temperature, precipitation, conditions)
- Eventbrite — local events within 3km
- Google Places — nearby competitor status and closures
- Google Popular Times — historical busyness baseline by day and hour
- Transport NSW — real-time bus, train, ferry, metro, and light rail disruptions
- Live Traffic NSW — road closures and incidents within 800m

**Loaded at onboarding, refreshed periodically**
- NSW school term dates (scraped from education.nsw.gov.au)
- Australian public holidays (data.gov.au)
- AFL, NRL, A-League, Cricket fixtures (scraped per season)
- University and TAFE academic calendars (USYD, UNSW, UTS, TAFE NSW)
- ABS demographic data — suburb-level age, income, and SEIFA index

## Requirements
- **Python 3.9+** for backend
- **Node 18+** for frontend
- **populartimes** — unofficial Google Popular Times scraper: `pip install populartimes`
- **FFmpeg** (optional): not required for core functionality
- API keys stored in `.env` — see `.env.example`

## Pages

| Page | Description |
|------|-------------|
| Landing | Value proposition, feature cards, single CTA |
| Onboarding | 4-step wizard: business type → address → trading hours → signal confirmation |
| Today's Brief | AI-written paragraph, 4 metric cards, signal breakdown chart, schedule approval |
| Monthly Forecast | Heatmap tab, day view tab, alerts tab |
| Signal Map | Leaflet map with circle overlays per signal, scaled by uplift percentage |
| Location Settings | Business profile, signal toggles, accuracy scoreboard, anomaly flagging |
| Accuracy History | Predicted vs actual line chart, 30-day track record, per-signal reliability |

## License
MIT
