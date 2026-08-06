import secrets

from fastapi import Depends, HTTPException, Security
from fastapi.security import APIKeyHeader

from server.config import Settings, get_settings

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def _check(provided: str | None, expected: str) -> None:
    if not provided:
        raise HTTPException(status_code=401, detail="Header X-API-Key ausente")
    if not secrets.compare_digest(provided, expected):
        raise HTTPException(status_code=403, detail="Chave de API inválida")


def require_client_key(
    key: str | None = Security(api_key_header),
    settings: Settings = Depends(get_settings),
) -> None:
    _check(key, settings.client_api_key)


def require_worker_key(
    key: str | None = Security(api_key_header),
    settings: Settings = Depends(get_settings),
) -> None:
    _check(key, settings.worker_api_key)
