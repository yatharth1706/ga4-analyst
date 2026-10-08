import os
from dataclasses import dataclass

from dotenv import load_dotenv


@dataclass(frozen=True)
class Settings:
    gemini_api_key: str
    gemini_model: str
    gcp_project: str
    gcp_service_account_json: str | None
    bq_location: str
    bq_max_bytes_billed: int
    bq_timeout_seconds: int
    bq_max_rows: int
    model_max_rows: int
    max_iterations: int
    access_code: str | None


def load_settings() -> Settings:
    load_dotenv()
    return Settings(
        gemini_api_key=_required("GEMINI_API_KEY"),
        gemini_model=_required("GEMINI_MODEL"),
        gcp_project=_required("GOOGLE_CLOUD_PROJECT"),
        gcp_service_account_json=os.getenv("GCP_SERVICE_ACCOUNT_JSON") or None,
        bq_location=os.getenv("BQ_LOCATION", "US"),
        bq_max_bytes_billed=int(os.getenv("BQ_MAX_BYTES_BILLED", 3_000_000_000)),
        bq_timeout_seconds=int(os.getenv("BQ_TIMEOUT_SECONDS", 30)),
        bq_max_rows=int(os.getenv("BQ_MAX_ROWS", 500)),
        model_max_rows=int(os.getenv("MODEL_MAX_ROWS", 100)),
        max_iterations=int(os.getenv("AGENT_MAX_ITERATIONS", 10)),
        access_code=os.getenv("APP_ACCESS_CODE") or None,
    )


def _required(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value
