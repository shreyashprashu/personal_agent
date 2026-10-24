from functools import lru_cache

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_ignore_empty=True,
        extra="ignore",
    )

    azure_ai_project_endpoint: str | None = None
    azure_ai_api_key: SecretStr | None = None
    azure_ai_deployment_name: str | None = None

    azure_speech_key: SecretStr | None = None
    azure_speech_region: str | None = None
    azure_speech_voice: str = "en-US-JennyNeural"

    assistant_api_key: SecretStr | None = None

    model_timeout_seconds: float = Field(default=45.0, ge=5.0, le=120.0)
    max_model_concurrency: int = Field(default=4, ge=1, le=32)

    @property
    def model_is_configured(self) -> bool:
        return all(
            (
                self.azure_ai_project_endpoint,
                self.azure_ai_api_key
                and self.azure_ai_api_key.get_secret_value().strip(),
                self.azure_ai_deployment_name,
            )
        )

    @property
    def speech_is_configured(self) -> bool:
        return all(
            (
                self.azure_speech_key
                and self.azure_speech_key.get_secret_value().strip(),
                self.azure_speech_region
                and self.azure_speech_region.strip(),
            )
        )

    @property
    def api_auth_is_configured(self) -> bool:
        return bool(
            self.assistant_api_key
            and self.assistant_api_key.get_secret_value().strip()
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
