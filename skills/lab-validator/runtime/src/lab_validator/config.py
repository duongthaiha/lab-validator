"""Typed configuration for the lab validator.

Secrets use :class:`pydantic.SecretStr`, which renders as ``**********`` in
reprs and log output — an accidental ``print(settings)`` cannot leak a key.

Resolution order: real environment variables > ``.env`` file > defaults.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[2]

#: DPAPI-encrypted Playwright storageState for Microsoft Learning Campus.
AUTH_DIR = REPO_ROOT / ".auth"
LEARNING_CAMPUS_STATE = AUTH_DIR / "mslearningcampus.state.enc"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=REPO_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    # --- Skillable Connect LAB API ---------------------------------------
    skillable_api_key: SecretStr | None = Field(default=None, alias="LV_SKILLABLE_API_KEY")
    skillable_api_base: str = Field(
        default="https://labondemand.com/api/v3", alias="LV_SKILLABLE_API_BASE"
    )
    skillable_tms_api_key: SecretStr | None = Field(
        default=None, alias="LV_SKILLABLE_TMS_API_KEY"
    )
    skillable_tms_api_base: str = Field(
        default="https://lms.learnondemand.net/api/2.0", alias="LV_SKILLABLE_TMS_API_BASE"
    )
    skillable_user_id: str = Field(default="lab-validator", alias="LV_SKILLABLE_USER_ID")
    skillable_user_email: str | None = Field(default=None, alias="LV_SKILLABLE_USER_EMAIL")

    # --- Learning Campus --------------------------------------------------
    learning_campus_url: str = Field(
        default="https://mslearningcampus.com/Pages/ms-learningcampus",
        alias="LV_LEARNING_CAMPUS_URL",
    )

    # --- Azure oracle -----------------------------------------------------
    # Intentionally no client secret: use DefaultAzureCredential (az login
    # locally, OIDC federation in CI).
    azure_subscription_id: str | None = Field(default=None, alias="AZURE_SUBSCRIPTION_ID")
    azure_tenant_id: str | None = Field(default=None, alias="AZURE_TENANT_ID")

    # --- Runtime ----------------------------------------------------------
    headless: bool = Field(default=True, alias="LV_HEADLESS")
    log_level: str = Field(default="INFO", alias="LV_LOG_LEVEL")
    artifact_retention: str = Field(default="on-failure", alias="LV_ARTIFACT_RETENTION")

    def require_skillable_api_key(self) -> str:
        if self.skillable_api_key is None:
            raise RuntimeError(
                "LV_SKILLABLE_API_KEY is not set. Copy .env.example to .env and "
                "fill it in, or export it in your shell."
            )
        return self.skillable_api_key.get_secret_value()

    def skillable_headers(self) -> dict[str, str]:
        """Headers for a Skillable Connect LAB API request."""
        return {"api_key": self.require_skillable_api_key(), "Accept": "application/json"}


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
