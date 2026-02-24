from __future__ import annotations

from fastapi import Header, HTTPException, Request, status

from connector.config import settings
from connector.utils.hash_utils import compute_signature


# TODO: mTLS transport-level enforcement in production ingress.
async def verify_connector_auth(
    request: Request,
    x_api_key: str = Header(default="", alias="X-API-Key"),
    x_signature: str = Header(default="", alias="X-Signature"),
    x_signature_ts: str = Header(default="", alias="X-Signature-Timestamp"),
) -> None:
    if x_api_key != settings.connector_api_key:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")

    if not settings.require_signed_requests:
        return

    payload = f"{request.method}\n{request.url.path}\n{x_signature_ts}\n"
    expected = compute_signature(settings.signed_request_secret, payload)
    if not x_signature or x_signature != expected:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid request signature")
