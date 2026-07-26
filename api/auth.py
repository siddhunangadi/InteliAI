"""API key authentication and per-identity rate limiting.

Centralized here so every route imports the same ``get_identity`` dependency
rather than re-implementing key checks. See ``Settings.api_keys`` docstring
for the no-op-when-unset dev fallback and the production requirement.
"""

import hashlib
import uuid
from dataclasses import dataclass

from fastapi import Depends, Header, HTTPException, Request

from api.dependencies import Container, get_container
from rag_hybrid_search.audit import AuditEvent, now_utc

_ANONYMOUS_KEY_ID = "anonymous"


def _record_auth_failure(
    container: Container, request: Request, request_id: str, key_id: str, action: str
) -> None:
    """Record an auth-failure audit event, isolated so logging never masks the 401/403."""
    try:
        container.audit_log.record(
            AuditEvent(
                event_id=str(uuid.uuid4()),
                event_type="auth_failure",
                timestamp=now_utc(),
                request_id=request_id,
                key_id=key_id,
                endpoint=request.url.path,
                action=action,
                status="failure",
            )
        )
    except Exception:  # noqa: BLE001 - never let audit logging break the 401/403
        pass


@dataclass(frozen=True)
class Identity:
    key_id: str
    request_id: str
    role: str = "admin"


def get_identity(
    request: Request,
    container: Container = Depends(get_container),
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
) -> Identity:
    """Resolve the caller's identity, enforcing auth and rate limits.

    No keys configured (``Settings.api_keys`` empty) -> every request is
    allowed, rate-limited per client IP, matching this project's existing
    "unset config = open dev default" convention -- role defaults to
    "admin" in that case too (nothing to distinguish callers by), same as
    before roles existed. Once RAG_API_KEYS is set, each key's role (see
    ``Settings.api_keys_roles``) is actually enforced by ``require_admin``.
    """
    request_id = getattr(request.state, "request_id", "unknown")

    api_keys_roles = container.settings.api_keys_roles
    if not api_keys_roles:
        identifier = request.client.host if request.client else _ANONYMOUS_KEY_ID
        container.rate_limiter.check(identifier)
        identity = Identity(key_id=_ANONYMOUS_KEY_ID, request_id=request_id, role="admin")
        request.state.identity = identity
        return identity

    if not x_api_key:
        _record_auth_failure(container, request, request_id, _ANONYMOUS_KEY_ID, "missing_api_key")
        raise HTTPException(status_code=401, detail="missing X-API-Key header")
    if x_api_key not in api_keys_roles:
        key_id = hashlib.sha256(x_api_key.encode()).hexdigest()[:12]
        _record_auth_failure(container, request, request_id, key_id, "invalid_api_key")
        raise HTTPException(status_code=401, detail="invalid X-API-Key")

    key_id = hashlib.sha256(x_api_key.encode()).hexdigest()[:12]
    container.rate_limiter.check(key_id)
    identity = Identity(key_id=key_id, request_id=request_id, role=api_keys_roles[x_api_key])
    request.state.identity = identity
    return identity


def require_admin(identity: Identity = Depends(get_identity)) -> Identity:
    """Gate for endpoints docstring'd as admin-only (``/audit/events``,
    ``/diagnostics``) -- enforced in code, not just documented. 403s any
    identity whose role isn't "admin" (only reachable when RAG_API_KEYS is
    set with non-admin entries; the no-keys-configured dev default is
    always "admin", unchanged)."""
    if identity.role != "admin":
        raise HTTPException(status_code=403, detail="admin role required")
    return identity
