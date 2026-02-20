"""Core HTTP client for the Tuya Cloud API with automatic token management."""

from __future__ import annotations

import json
from typing import Any

import httpx

from tuya_agent.auth import TokenInfo, sign_request
from tuya_agent.config import TuyaConfig


class TuyaAPIError(Exception):
    """Raised when the Tuya API returns a non-success response."""

    def __init__(self, code: int, msg: str) -> None:
        self.code = code
        self.msg = msg
        super().__init__(f"Tuya API error {code}: {msg}")


class TuyaClient:
    """Async HTTP client for the Tuya Cloud API.

    Handles authentication, token lifecycle, and request signing automatically.
    All domain-specific methods (devices, logs, scenes) are accessed via
    sub-modules attached to this client.
    """

    def __init__(self, config: TuyaConfig | None = None) -> None:
        self.config = config or TuyaConfig()  # type: ignore[call-arg]
        self._http = httpx.AsyncClient(base_url=self.config.base_url, timeout=30)
        self._token: TokenInfo | None = None

        # Attach sub-modules.
        from tuya_agent.devices import DevicesMixin
        from tuya_agent.events import EventsMixin
        from tuya_agent.logs import LogsMixin
        from tuya_agent.scenes import ScenesMixin

        self.devices = DevicesMixin(self)
        self.events = EventsMixin(self)
        self.logs = LogsMixin(self)
        self.scenes = ScenesMixin(self)

    async def __aenter__(self) -> TuyaClient:
        await self.ensure_token()
        return self

    async def __aexit__(self, *exc: object) -> None:
        await self.close()

    async def close(self) -> None:
        await self._http.aclose()

    # -- Token management ----------------------------------------------------

    async def ensure_token(self) -> str:
        """Return a valid access token, fetching or refreshing as needed."""
        if self._token and not self._token.is_expired:
            return self._token.access_token

        if self._token and self._token.refresh_token:
            try:
                return await self._refresh_token()
            except TuyaAPIError:
                pass  # Fall through to a fresh token request.

        return await self._fetch_token()

    async def _fetch_token(self) -> str:
        path = "/v1.0/token?grant_type=1"
        headers = sign_request(self.config, "GET", path)
        resp = await self._http.get(path, headers=headers)
        data = resp.json()
        self._check_response(data)
        result = data["result"]
        self._token = TokenInfo(
            access_token=result["access_token"],
            refresh_token=result["refresh_token"],
            expire_time=result["expire_time"],
        )
        return self._token.access_token

    async def _refresh_token(self) -> str:
        assert self._token is not None
        path = f"/v1.0/token/{self._token.refresh_token}"
        headers = sign_request(self.config, "GET", path)
        resp = await self._http.get(path, headers=headers)
        data = resp.json()
        self._check_response(data)
        result = data["result"]
        self._token = TokenInfo(
            access_token=result["access_token"],
            refresh_token=result["refresh_token"],
            expire_time=result["expire_time"],
        )
        return self._token.access_token

    # -- Generic request -----------------------------------------------------

    async def request(
        self,
        method: str,
        path: str,
        *,
        body: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
    ) -> Any:
        """Make a signed API request and return the ``result`` field."""
        token = await self.ensure_token()

        # Build the full path including query parameters for signing.
        if params:
            query = "&".join(f"{k}={v}" for k, v in sorted(params.items()) if v is not None)
            sign_path = f"{path}?{query}" if query else path
        else:
            sign_path = path
            query = ""

        body_str = json.dumps(body) if body else ""
        headers = sign_request(
            self.config,
            method,
            sign_path,
            body=body_str,
            access_token=token,
        )
        if body is not None:
            headers["Content-Type"] = "application/json"

        resp = await self._http.request(
            method,
            path,
            headers=headers,
            content=body_str if body else None,
            params=params,
        )
        data = resp.json()
        self._check_response(data)
        return data.get("result")

    # -- Helpers -------------------------------------------------------------

    @staticmethod
    def _check_response(data: dict[str, Any]) -> None:
        if not data.get("success", False):
            raise TuyaAPIError(data.get("code", -1), data.get("msg", "unknown error"))
