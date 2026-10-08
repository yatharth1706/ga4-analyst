import os
from dataclasses import dataclass

from dotenv import load_dotenv


@dataclass(frozen=True)
class Settings:
    gemini_api_key: str
    gemini_model: str
    gcp_project: str
    gcp_service_account_json: str | None


def load_settings() -> Settings:
    load_dotenv()
    return Settings(
        gemini_api_key=_required("GEMINI_API_KEY"),
        gemini_model=_required("GEMINI_MODEL"),
        gcp_project=_required("GOOGLE_CLOUD_PROJECT"),
        gcp_service_account_json=os.getenv("GCP_SERVICE_ACCOUNT_JSON") or None,
    )


def _required(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value
