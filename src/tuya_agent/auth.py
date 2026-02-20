"""HMAC-SHA256 request signing and token management for the Tuya Cloud API."""

from __future__ import annotations

import hashlib
import hmac
import time
import uuid
from dataclasses import dataclass, field

from tuya_agent.config import TuyaConfig


@dataclass
class TokenInfo:
    access_token: str
    refresh_token: str
    expire_time: int
    acquired_at: float = field(default_factory=time.time)

    @property
    def is_expired(self) -> bool:
        # Treat the token as expired 5 minutes before actual expiry.
        return time.time() >= self.acquired_at + self.expire_time - 300


def _sha256(content: str) -> str:
    return hashlib.sha256(content.encode()).hexdigest()


def _hmac_sha256(key: str, msg: str) -> str:
    return hmac.new(key.encode(), msg.encode(), hashlib.sha256).hexdigest().upper()


def sign_request(
    config: TuyaConfig,
    method: str,
    path: str,
    *,
    body: str = "",
    access_token: str = "",
    t: int | None = None,
    nonce: str | None = None,
) -> dict[str, str]:
    """Build the signed headers required for a Tuya Cloud API request.

    Returns a dict of headers to merge into the HTTP request.
    """
    t = t or int(time.time() * 1000)
    nonce = nonce or uuid.uuid4().hex

    content_hash = _sha256(body)
    string_to_sign = f"{method.upper()}\n{content_hash}\n\n{path}"

    sign_str = config.access_id + access_token + str(t) + nonce + string_to_sign
    signature = _hmac_sha256(config.access_secret, sign_str)

    return {
        "client_id": config.access_id,
        "sign": signature,
        "t": str(t),
        "sign_method": "HMAC-SHA256",
        "nonce": nonce,
        **({"access_token": access_token} if access_token else {}),
    }
