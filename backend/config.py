from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


_BACKEND_ROOT = Path(__file__).resolve().parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(_BACKEND_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    google_api_key: str = ""
    google_gemini_api_key: str = ""
    eventbrite_token: str = ""
    transport_nsw_api_key: str = ""
    ticketmaster_api_key: str = ""
    openrouter_api_key: str = ""

    dev_synthetic_signals: bool = False

    data_dir: Path = Path(__file__).resolve().parent / "data"
    models_dir: Path = Path(__file__).resolve().parent / "models"
    static_data_dir: Path = Path(__file__).resolve().parent / "data" / "static"
    database_path: Path = Path(__file__).resolve().parent / "data" / "forecast.db"


settings = Settings()
settings.data_dir.mkdir(parents=True, exist_ok=True)
settings.models_dir.mkdir(parents=True, exist_ok=True)
settings.static_data_dir.mkdir(parents=True, exist_ok=True)

# Full calendar days ahead from Australia/Sydney "today" (62 × 24h covers e.g. 22 Mar → 22 May inclusive).
FORECAST_HORIZON_DAYS = 62
