"""Configuration for connecting to the Tuya Cloud API."""

from __future__ import annotations

from pydantic_settings import BaseSettings

_BASE_URLS: dict[str, str] = {
    "cn": "https://openapi.tuyacn.com",
    "us": "https://openapi.tuyaus.com",
    "us-e": "https://openapi-us-e.tuyaus.com",
    "eu": "https://openapi.tuyaeu.com",
    "in": "https://openapi.tuyain.com",
}

_PULSAR_URLS: dict[str, str] = {
    "cn": "wss://mqe.tuyacn.com:8285/",
    "us": "wss://mqe.tuyaus.com:8285/",
    "eu": "wss://mqe.tuyaeu.com:8285/",
    "in": "wss://mqe.tuyain.com:8285/",
}


class TuyaConfig(BaseSettings):
    """Tuya Cloud API configuration loaded from environment variables."""

    model_config = {"env_prefix": "TUYA_", "env_file": ".env"}

    access_id: str
    access_secret: str
    api_region: str = "us"

    @property
    def base_url(self) -> str:
        url = _BASE_URLS.get(self.api_region)
        if url is None:
            raise ValueError(
                f"Unknown region '{self.api_region}'. Valid regions: {', '.join(_BASE_URLS)}"
            )
        return url

    @property
    def pulsar_url(self) -> str:
        url = _PULSAR_URLS.get(self.api_region)
        if url is None:
            raise ValueError(
                f"No Pulsar endpoint for region '{self.api_region}'. "
                f"Valid regions: {', '.join(_PULSAR_URLS)}"
            )
        return url
