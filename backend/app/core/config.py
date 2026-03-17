import os
from functools import cached_property

from dotenv import load_dotenv


load_dotenv()


class Settings:
    @property
    def app_name(self) -> str:
        return os.getenv("APP_NAME", "Crowdless Backend")

    @property
    def api_prefix(self) -> str:
        return os.getenv("API_PREFIX", "/api/v1")

    @property
    def app_host(self) -> str:
        return os.getenv("APP_HOST", "0.0.0.0")

    @property
    def app_port(self) -> int:
        return int(os.getenv("APP_PORT", "8000"))

    @property
    def firestore_project_id(self) -> str | None:
        return os.getenv("FIRESTORE_PROJECT_ID") or None

    @property
    def google_application_credentials(self) -> str | None:
        return os.getenv("GOOGLE_APPLICATION_CREDENTIALS") or None

    @cached_property
    def cors_origins(self) -> list[str]:
        raw_origins = os.getenv("CORS_ORIGINS", "*")
        if raw_origins.strip() == "*":
            return ["*"]
        return [origin.strip() for origin in raw_origins.split(",") if origin.strip()]

    @property
    def default_currency(self) -> str:
        return os.getenv("DEFAULT_CURRENCY", "USD")

    @property
    def adult_ticket_price(self) -> float:
        return float(os.getenv("ADULT_TICKET_PRICE", "20"))

    @property
    def child_ticket_price(self) -> float:
        return float(os.getenv("CHILD_TICKET_PRICE", "10"))


settings = Settings()
