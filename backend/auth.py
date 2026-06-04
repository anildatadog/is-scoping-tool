from __future__ import annotations

from dataclasses import dataclass

from google.auth.transport import requests as google_requests
from google.oauth2 import id_token


@dataclass
class AuthFailure(Exception):
    status_code: int
    detail: str


def verify_google_bearer(auth_header: str, client_id: str) -> dict:
    if not auth_header.startswith("Bearer "):
        raise AuthFailure(401, "Unauthorized")

    token = auth_header[7:]
    try:
        payload = id_token.verify_oauth2_token(
            token,
            google_requests.Request(),
            client_id,
        )
    except Exception as exc:
        raise AuthFailure(401, "Unauthorized") from exc

    email = payload.get("email", "")
    if not email.endswith("@datadoghq.com"):
        raise AuthFailure(403, "Forbidden - Datadog accounts only")

    return payload
