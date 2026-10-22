from __future__ import annotations

import base64
from datetime import datetime
import hashlib
import logging
import mimetypes
from pathlib import Path
import re
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlsplit
from urllib.request import HTTPRedirectHandler, Request as UrlRequest, build_opener
from uuid import uuid4
from typing import Any

from fastapi import FastAPI, File, Header, HTTPException, Query, Request, Response, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from .admin_routes import router as admin_router
from .admin_auth import ensure_default_bootstrap_admin_user, is_admin_ip_allowed, resolve_client_ip
from .cloudbase_auth import (
    build_current_identity_token,
    parse_cloudbase_identity,
    reset_request_identity,
    set_request_identity,
)
from .db import init_db
from .image_validation import matches_image_content_type
from .runtime_config import (
    collect_release_configuration_warnings,
    ensure_production_configuration,
    get_app_env,
    get_backend_upload_dir,
)
from .schemas import (
    ActionResultOut,
    AuthUserOut,
    BindPhoneIn,
    CadreAccessPasswordIn,
    CadreAccessStatusOut,
    CadreAccessVerifyIn,
    CadreAccessVerifyOut,
    CadreLoginIn,
    GovServiceApplicationCreateIn,
    GovServiceApplicationOut,
    GovServiceApplicationUpdateIn,
    GovServiceDetailOut,
    GovServiceOut,
    LedgerCreate,
    LedgerOut,
    LoginOut,
    NoticeCreate,
    NoticeDetailOut,
    NoticeOut,
    NoticeSubscriptionRecordIn,
    NoticeSubscriptionStatusOut,
    PrivacyConsentIn,
    PrivacyConsentOut,
    PrivacyPolicyOut,
    PrivacyWithdrawIn,
    RealnameSubmitIn,
    RosterImportBatchOut,
    RosterImportOut,
    UploadImageCloudFileIn,
    UploadImageInlineIn,
    UploadImageOut,
    TrainingProgramOut,
    TrainingSignupCreate,
    TrainingSignupOut,
    VillageOpenProfileOut,
    VillageMetricOut,
    VillageMetricsUpdateIn,
    VillagerRequestCreateIn,
    VillagerRequestOut,
    VillagerRequestUpdateIn,
    VolunteerActivityOut,
    VolunteerActivitySignupCreate,
    VolunteerActivitySignupOut,
    ProposalCreateIn,
    ProposalSubmitOut,
    ProposalStatusOut,
    LocalProductOut,
    WechatLoginIn,
)
from .services import (
    bind_phone,
    backfill_missing_identity_gender,
    backfill_phone_security,
    build_upload_access_url,
    cancel_gov_application,
    cancel_villager_request,
    consume_rate_limit,
    create_gov_application,
    create_ledger,
    create_notice,
    create_villager_request,
    get_gov_service,
    get_gov_application_detail,
    get_cadre_access_status,
    delete_notice,
    export_latest_villager_registry_csv,
    ensure_default_cadre_authorizations,
    get_stored_file_record,
    get_notice_detail,
    get_notice_subscription_status,
    get_privacy_policy,
    get_user_by_token,
    get_villager_request_detail,
    import_villager_roster,
    list_ledgers,
    list_notices,
    list_gov_applications,
    list_gov_services,
    list_privacy_consents,
    list_training_programs,
    list_village_metrics,
    get_village_open_profile,
    list_villager_requests,
    list_roster_import_batches,
    list_volunteer_activities,
    logout_session,
    resolve_role_by_token,
    record_notice_subscription_result,
    signup_training_program,
    signup_volunteer_activity,
    create_proposal,
    proposal_status,
    get_openid_by_token_optional,
    list_local_products,
    get_local_product,
    update_notice,
    submit_privacy_consent,
    submit_realname,
    update_gov_application,
    update_gov_service,
    update_village_metrics,
    update_villager_request,
    validate_upload_scene_access,
    verify_upload_access_signature,
    wechat_login,
    withdraw_privacy_consent,
    store_uploaded_file_record,
)
from .storage import build_download_url, resolve_local_file_path


BASE_DIR = Path(__file__).resolve().parent.parent
UPLOAD_DIR = get_backend_upload_dir()
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
MAX_IMAGE_BYTES = 8 * 1024 * 1024
UPLOAD_FILENAME_PATTERN = re.compile(r"^[A-Za-z0-9_.-]{1,160}$")
ALLOWED_IMAGE_TYPES = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "image/heic": ".heic",
    "image/heif": ".heif",
}
UPLOAD_SCENE_PATTERN = re.compile(r"^[a-z0-9_-]{1,32}$")
UPLOAD_SCENE_WHITELIST = {
    "notice",
    "request",
    "gov_apply",
    "request_reply",
    "gov_reply",
    "open",
    "gov",
    "gov_service",
    "gov_detail",
    "ledger",
    "shop",
}


app = FastAPI(
    title="Deshengcun 1.1.0 API",
    version="1.1.0",
    description="Village governance 1.1.0 backend with identity, open data and government service workflow.",
)
app.include_router(admin_router)

ADMIN_WEB_DIR = Path(__file__).resolve().parent / "admin_web"
ADMIN_WEB_ASSETS_DIR = ADMIN_WEB_DIR / "assets"
ADMIN_WEB_INDEX = ADMIN_WEB_DIR / "index.html"
ADMIN_WEB_FAVICON = ADMIN_WEB_DIR / "favicon.png"

if ADMIN_WEB_ASSETS_DIR.is_dir():
    app.mount(
        "/admin/assets",
        StaticFiles(directory=str(ADMIN_WEB_ASSETS_DIR)),
        name="admin_web_assets",
    )

logger = logging.getLogger("deshengcun.runtime")
STARTUP_RUNTIME_STATE = {
    "db_ready": False,
    "db_error": "",
}


def _normalize_upload_scene(scene: str) -> str:
    scene_text = str(scene or "").strip().lower()
    if not UPLOAD_SCENE_PATTERN.fullmatch(scene_text):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="invalid_upload_scene",
        )
    if scene_text not in UPLOAD_SCENE_WHITELIST:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="invalid_upload_scene",
        )
    return scene_text


def _validate_image_upload_bytes(*, content_type: str, file_bytes: bytes) -> tuple[str, int]:
    content_type_text = str(content_type or "").lower().strip()
    suffix = ALLOWED_IMAGE_TYPES.get(content_type_text)
    if suffix is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="unsupported_image_type",
        )

    size = len(file_bytes)
    if size <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="empty_image_file",
        )
    if size > MAX_IMAGE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="image_file_too_large",
        )
    if not matches_image_content_type(content_type_text, file_bytes):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="image_content_mismatch",
        )
    return suffix, size


def _is_allowed_cloud_upload_source_url(source_url: str) -> bool:
    text = str(source_url or "").strip()
    if not text:
        return False
    parsed = urlsplit(text)
    if parsed.scheme.lower() != "https":
        return False
    hostname = str(parsed.hostname or "").strip().lower()
    if not hostname:
        return False
    allowed_suffixes = (
        ".tcb.qcloud.la",
        ".myqcloud.com",
        ".myqcloud.net",
        ".cloudbaseapp.cn",
    )
    return hostname.endswith(allowed_suffixes)


class _AllowedCloudRedirectHandler(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if not _is_allowed_cloud_upload_source_url(newurl):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="invalid_upload_source_url",
            )
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def _download_cloud_upload_bytes(source_url: str) -> tuple[bytes, str]:
    if not _is_allowed_cloud_upload_source_url(source_url):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="invalid_upload_source_url",
        )
    request_obj = UrlRequest(
        source_url,
        headers={
            "User-Agent": "deshengcun-upload-relay/1.0",
            "Accept": "image/*,*/*;q=0.8",
        },
        method="GET",
    )
    try:
        opener = build_opener(_AllowedCloudRedirectHandler())
        with opener.open(request_obj, timeout=20) as response:
            file_bytes = response.read()
            content_type = str(response.headers.get("Content-Type") or "").split(";")[0].strip().lower()
            return file_bytes, content_type
    except (HTTPError, URLError, TimeoutError, OSError) as exc:
        logger.exception(
            "cloud relay image fetch failed",
            extra={"upload_source_host": str(urlsplit(source_url).hostname or "")[:120]},
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="source_image_fetch_failed",
        ) from exc


app.add_middleware(
    CORSMiddleware,
    allow_origins=(
        ["https://admin.example.invalid"]
        if get_app_env() == "production"
        else ["http://localhost:5173", "http://127.0.0.1:5173"]
    ),
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "X-Admin-Token", "X-Token", "X-Cadre-Token", "X-Role"],
)


@app.middleware("http")
async def admin_network_access_middleware(request: Request, call_next):
    path = str(request.url.path or "")
    if path.startswith("/api/v1/admin"):
        request_ip = _request_ip(request)
        if not is_admin_ip_allowed(request_ip):
            logger.warning("security_alert event=admin_ip_denied ip=%s path=%s", request_ip, path[:160])
            return JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                content={"detail": "admin_network_not_allowed"},
                headers={"Cache-Control": "no-store"},
            )
    return await call_next(request)


@app.middleware("http")
async def security_headers_middleware(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers[
        "Content-Security-Policy"
    ] = (
        "default-src 'self'; "
        "base-uri 'self'; object-src 'none'; frame-ancestors 'none'; form-action 'self'; "
        "script-src 'self' https://api.example.invalid; "
        "style-src 'self' 'unsafe-inline' https://api.example.invalid; "
        "img-src 'self' data: blob: https:; font-src 'self' data: https:; "
        "connect-src 'self' https://api.example.invalid"
    )
    forwarded_proto = str(request.headers.get("x-forwarded-proto") or "").split(",", 1)[0].strip().lower()
    if get_app_env() == "production" and (
        request.url.scheme == "https" or forwarded_proto == "https"
    ):
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

    path = str(request.url.path or "")
    sensitive_path = (
        path in {"/admin", "/admin/"}
        or path.startswith("/admin/login")
        or path.startswith("/api/v1/admin")
        or path.startswith("/api/v1/auth")
        or path.startswith("/api/v1/requests")
        or path.startswith("/api/v1/gov/applications")
        or path.startswith("/api/v1/ledgers")
        or path.startswith("/api/v1/uploads/access")
    )
    if sensitive_path:
        response.headers["Cache-Control"] = "no-store"
        response.headers["Pragma"] = "no-cache"
    return response


@app.middleware("http")
async def cloudbase_identity_middleware(request: Request, call_next):
    identity = parse_cloudbase_identity(request.headers)
    token = set_request_identity(identity)
    try:
        return await call_next(request)
    finally:
        reset_request_identity(token)


@app.on_event("startup")
def on_startup() -> None:
    ensure_production_configuration()
    for warning in collect_release_configuration_warnings():
        logger.warning("release_config_warning: %s", warning)
    _initialize_runtime_dependencies()


def _record_runtime_db_error(exc: Exception) -> None:
    STARTUP_RUNTIME_STATE["db_ready"] = False
    STARTUP_RUNTIME_STATE["db_error"] = f"{exc.__class__.__name__}: {exc}"[:240]


def _initialize_runtime_dependencies() -> bool:
    try:
        init_db()
        backfill_phone_security()
        gender_backfill_count = backfill_missing_identity_gender()
        if gender_backfill_count:
            logger.info("identity_gender_backfill: updated_count=%d", gender_backfill_count)
        ensure_default_cadre_authorizations()
        bootstrap_result = ensure_default_bootstrap_admin_user()
        STARTUP_RUNTIME_STATE["db_ready"] = True
        STARTUP_RUNTIME_STATE["db_error"] = ""
        if bootstrap_result.get("status") == "created":
            logger.warning(
                "bootstrap_admin_created: login_name=%s authorization_id=%s",
                bootstrap_result.get("login_name", ""),
                bootstrap_result.get("cadre_authorization_id", 0),
            )
        elif bootstrap_result.get("status") == "login_name_conflict":
            logger.warning(
                "bootstrap_admin_login_name_conflict: login_name=%s authorization_id=%s",
                bootstrap_result.get("login_name", ""),
                bootstrap_result.get("authorization_id", 0),
            )
        return True
    except Exception as exc:  # pragma: no cover - runtime connectivity branch
        _record_runtime_db_error(exc)
        logger.exception(
            "runtime_startup_db_init_failed: service will stay online and retry when dependencies recover"
        )
        return False


def _probe_runtime_db_status() -> str:
    if STARTUP_RUNTIME_STATE.get("db_ready"):
        return "ok"
    if _initialize_runtime_dependencies():
        return "ok"
    return "degraded"


def _serve_admin_web_index() -> FileResponse:
    if not ADMIN_WEB_INDEX.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="admin_web_not_found")
    return FileResponse(path=str(ADMIN_WEB_INDEX))


def _serve_admin_web_favicon() -> FileResponse:
    if not ADMIN_WEB_FAVICON.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="admin_favicon_not_found")
    return FileResponse(path=str(ADMIN_WEB_FAVICON), media_type="image/png")


@app.get("/admin", include_in_schema=False)
def admin_web_root() -> RedirectResponse:
    if not ADMIN_WEB_INDEX.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="admin_web_not_found")
    return RedirectResponse(url="/admin/", status_code=status.HTTP_307_TEMPORARY_REDIRECT)


@app.get("/admin/", include_in_schema=False)
def admin_web_index() -> FileResponse:
    return _serve_admin_web_index()


@app.get("/admin/favicon.png", include_in_schema=False)
def admin_web_favicon() -> FileResponse:
    return _serve_admin_web_favicon()


@app.get("/admin/{full_path:path}", include_in_schema=False)
def admin_web_spa(full_path: str) -> FileResponse:
    if str(full_path or "").startswith("assets/"):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="admin_asset_not_found")
    return _serve_admin_web_index()


def require_token(x_token: str | None) -> str:
    token = (x_token or "").strip() or build_current_identity_token()
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="login_required",
        )
    return token


def _request_ip(request: Request) -> str:
    client_host = getattr(request.client, "host", "") if request.client else ""
    return resolve_client_ip(
        peer_ip=str(client_host or ""),
        forwarded_for=str(request.headers.get("x-forwarded-for") or ""),
        real_ip=str(request.headers.get("x-real-ip") or ""),
    )[:128]


def _token_rate_identity(token: str | None) -> str:
    text = str(token or "").strip()
    if not text:
        return ""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:24]


def apply_rate_limit(
    request: Request,
    *,
    scope: str,
    limit: int,
    window_seconds: int,
    identity: str = "",
) -> None:
    ip = _request_ip(request)
    bucket = ip if not identity else f"{ip}|{identity}"
    try:
        consume_rate_limit(scope, bucket, limit, window_seconds)
    except ValueError as exc:
        detail = str(exc)
        raise HTTPException(
            status_code=map_value_error_to_http(detail),
            detail=detail,
        ) from exc


def get_user_from_token_or_401(x_token: str | None) -> dict[str, Any]:
    token = require_token(x_token)
    try:
        user = get_user_by_token(token)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
        ) from exc
    return user


def require_cadre(
    x_role: str | None,
    x_token: str | None,
    x_cadre_token: str | None,
) -> None:
    _ = x_role
    token = require_token(x_token)
    try:
        status_row = get_cadre_access_status(token, x_cadre_token)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
        ) from exc
    if not status_row.get("cadre_eligible"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="cadre_authorization_required",
        )
    if not status_row.get("session_active"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="cadre_stepup_required",
        )


def map_value_error_to_http(detail: str) -> int:
    if detail in {"invalid_token", "token_expired", "login_required"}:
        return status.HTTP_401_UNAUTHORIZED
    if detail in {"invalid_manager_credentials"}:
        return status.HTTP_401_UNAUTHORIZED
    if detail in {
        "cadre_password_login_disabled",
        "cadre_role_required",
        "cadre_authorization_required",
        "cadre_stepup_required",
        "cadre_operation_password_not_set",
        "villager_role_required",
        "verified_villager_required",
    }:
        return status.HTTP_403_FORBIDDEN
    if detail in {"invalid_cadre_operation_password"}:
        return status.HTTP_401_UNAUTHORIZED
    if detail in {"cadre_access_locked"}:
        return status.HTTP_423_LOCKED
    if detail in {"invalid_upload_signature", "upload_url_expired", "upload_access_denied"}:
        return status.HTTP_403_FORBIDDEN
    if detail in {"invalid_id_card_aes_key", "id_card_encrypt_failed", "id_card_decrypt_failed"}:
        return status.HTTP_500_INTERNAL_SERVER_ERROR
    if detail in {
        "request_not_found",
        "notice_not_found",
        "gov_service_not_found",
        "gov_application_not_found",
        "training_program_not_found",
        "volunteer_activity_not_found",
        "local_product_not_found",
    }:
        return status.HTTP_404_NOT_FOUND
    if detail in {"signup_conflict", "request_duplicate_submission", "gov_application_duplicate_submission"}:
        return status.HTTP_409_CONFLICT
    if detail in {"id_card_already_verified", "certificate_duplicate_submission"}:
        return status.HTTP_409_CONFLICT
    if detail in {"rate_limit_exceeded", "certificate_daily_limit_reached", "proposal_daily_limit"}:
        return status.HTTP_429_TOO_MANY_REQUESTS
    if detail in {"roster_not_ready", "upload_store_failed"}:
        return status.HTTP_503_SERVICE_UNAVAILABLE
    if detail in {
        "wechat_login_unconfigured",
        "wechat_phone_unconfigured",
        "wechat_notice_template_unconfigured",
        "wechat_phone_unavailable",
        "wechat_notice_send_unavailable",
        "wechat_service_unavailable",
    }:
        return status.HTTP_503_SERVICE_UNAVAILABLE
    return status.HTTP_400_BAD_REQUEST


def raise_cadre_web_admin_only() -> None:
    raise HTTPException(
        status_code=status.HTTP_410_GONE,
        detail="cadre_web_admin_only",
    )


@app.get("/health")
def health() -> dict[str, str]:
    payload = {
        "status": "ok",
        "db": _probe_runtime_db_status(),
    }
    db_error = str(STARTUP_RUNTIME_STATE.get("db_error") or "").strip()
    if db_error:
        payload["detail"] = db_error
    return payload


@app.get("/api/v1/privacy/policy", response_model=PrivacyPolicyOut)
def api_privacy_policy() -> PrivacyPolicyOut:
    return PrivacyPolicyOut(**get_privacy_policy())


@app.get("/api/v1/privacy/consents", response_model=PrivacyConsentOut)
def api_privacy_consents(x_token: str | None = Header(default=None)) -> PrivacyConsentOut:
    token = require_token(x_token)
    try:
        data = list_privacy_consents(token)
    except ValueError as exc:
        raise HTTPException(
            status_code=map_value_error_to_http(str(exc)),
            detail=str(exc),
        ) from exc
    return PrivacyConsentOut(**data)


@app.post("/api/v1/privacy/consent", response_model=PrivacyConsentOut)
def api_privacy_consent(
    payload: PrivacyConsentIn,
    x_token: str | None = Header(default=None),
) -> PrivacyConsentOut:
    token = require_token(x_token)
    try:
        data = submit_privacy_consent(token, payload.model_dump())
    except ValueError as exc:
        raise HTTPException(
            status_code=map_value_error_to_http(str(exc)),
            detail=str(exc),
        ) from exc
    return PrivacyConsentOut(**data)


@app.post("/api/v1/privacy/withdraw", response_model=ActionResultOut)
def api_privacy_withdraw(
    payload: PrivacyWithdrawIn,
    x_token: str | None = Header(default=None),
) -> ActionResultOut:
    token = require_token(x_token)
    try:
        data = withdraw_privacy_consent(token, payload.model_dump())
    except ValueError as exc:
        raise HTTPException(
            status_code=map_value_error_to_http(str(exc)),
            detail=str(exc),
        ) from exc
    return ActionResultOut(**data)


@app.post("/api/v1/auth/wechat-login", response_model=LoginOut)
def api_wechat_login(request: Request, payload: WechatLoginIn) -> LoginOut:
    apply_rate_limit(request, scope="auth_wechat_login", limit=20, window_seconds=300)
    try:
        data_payload = payload.model_dump()
        identity = parse_cloudbase_identity(request.headers)
        if identity is not None:
            data_payload["cloudbase_identity"] = {
                "openid": identity.openid,
                "unionid": identity.unionid,
            }
        data = wechat_login(data_payload)
    except ValueError as exc:
        detail = str(exc)
        raise HTTPException(
            status_code=map_value_error_to_http(detail),
            detail=detail,
        ) from exc
    return LoginOut(**data)


@app.post("/api/v1/auth/cadre-login", response_model=LoginOut)
def api_cadre_login(request: Request, payload: CadreLoginIn) -> LoginOut:
    void = (request, payload)
    raise_cadre_web_admin_only()


@app.get("/api/v1/auth/me", response_model=AuthUserOut)
def api_auth_me(x_token: str | None = Header(default=None)) -> AuthUserOut:
    user = get_user_from_token_or_401(x_token)
    return AuthUserOut(**user)


@app.get("/api/v1/cadre/access/status", response_model=CadreAccessStatusOut)
def api_cadre_access_status(
    x_token: str | None = Header(default=None),
    x_cadre_token: str | None = Header(default=None),
) -> CadreAccessStatusOut:
    void = (x_token, x_cadre_token)
    raise_cadre_web_admin_only()


@app.post("/api/v1/cadre/access/password", response_model=CadreAccessStatusOut)
def api_set_cadre_access_password(
    request: Request,
    payload: CadreAccessPasswordIn,
    x_token: str | None = Header(default=None),
) -> CadreAccessStatusOut:
    void = (request, payload, x_token)
    raise_cadre_web_admin_only()


@app.post("/api/v1/cadre/access/verify", response_model=CadreAccessVerifyOut)
def api_verify_cadre_access(
    request: Request,
    payload: CadreAccessVerifyIn,
    x_token: str | None = Header(default=None),
) -> CadreAccessVerifyOut:
    void = (request, payload, x_token)
    raise_cadre_web_admin_only()


@app.post("/api/v1/cadre/access/logout", response_model=ActionResultOut)
def api_logout_cadre_access(
    x_token: str | None = Header(default=None),
    x_cadre_token: str | None = Header(default=None),
) -> ActionResultOut:
    void = (x_token, x_cadre_token)
    raise_cadre_web_admin_only()


@app.post("/api/v1/auth/logout", response_model=ActionResultOut)
def api_auth_logout(x_token: str | None = Header(default=None)) -> ActionResultOut:
    token = require_token(x_token)
    try:
        data = logout_session(token)
    except ValueError as exc:
        detail = str(exc)
        raise HTTPException(
            status_code=map_value_error_to_http(detail),
            detail=detail,
        ) from exc
    return ActionResultOut(**data)


@app.post("/api/v1/auth/bind-phone", response_model=AuthUserOut)
def api_bind_phone(
    request: Request,
    payload: BindPhoneIn,
    x_token: str | None = Header(default=None),
) -> AuthUserOut:
    token = require_token(x_token)
    apply_rate_limit(
        request,
        scope="auth_bind_phone",
        limit=12,
        window_seconds=3600,
        identity=_token_rate_identity(token),
    )
    try:
        user = bind_phone(token, payload.model_dump())
    except ValueError as exc:
        detail = str(exc)
        raise HTTPException(
            status_code=map_value_error_to_http(detail),
            detail=detail,
        ) from exc
    return AuthUserOut(**user)


@app.post("/api/v1/auth/realname-submit", response_model=AuthUserOut)
def api_submit_realname(
    request: Request,
    payload: RealnameSubmitIn,
    x_token: str | None = Header(default=None),
) -> AuthUserOut:
    token = require_token(x_token)
    apply_rate_limit(
        request,
        scope="auth_realname_submit",
        limit=6,
        window_seconds=3600,
        identity=_token_rate_identity(token),
    )
    try:
        user = submit_realname(token, payload.model_dump())
    except ValueError as exc:
        detail = str(exc)
        raise HTTPException(
            status_code=map_value_error_to_http(detail),
            detail=detail,
        ) from exc
    return AuthUserOut(**user)


@app.post("/api/v1/roster/import", response_model=RosterImportOut)
async def api_roster_import(
    file: UploadFile = File(...),
    x_role: str | None = Header(default=None),
    x_token: str | None = Header(default=None),
    x_cadre_token: str | None = Header(default=None),
) -> RosterImportOut:
    require_cadre(x_role, x_token, x_cadre_token)
    token = require_token(x_token)
    try:
        file_bytes = await file.read()
        data = import_villager_roster(token, file.filename or "roster.csv", file_bytes)
    except ValueError as exc:
        detail = str(exc)
        raise HTTPException(
            status_code=map_value_error_to_http(detail),
            detail=detail,
        ) from exc
    return RosterImportOut(**data)


@app.post("/api/v1/uploads/images", response_model=UploadImageOut, status_code=201)
async def api_upload_image(
    request: Request,
    file: UploadFile = File(...),
    scene: str = Query(default=""),
    x_role: str | None = Header(default=None),
    x_token: str | None = Header(default=None),
    x_cadre_token: str | None = Header(default=None),
) -> UploadImageOut:
    _ = x_role
    token = require_token(x_token)
    _ = get_user_from_token_or_401(token)
    apply_rate_limit(
        request,
        scope="upload_image",
        limit=60,
        window_seconds=600,
        identity=_token_rate_identity(token),
    )

    file_bytes = await file.read()
    content_type = (file.content_type or "").lower().strip()
    suffix, size = _validate_image_upload_bytes(
        content_type=content_type,
        file_bytes=file_bytes,
    )

    scene_text = _normalize_upload_scene(scene)
    try:
        validate_upload_scene_access(token, scene_text, x_cadre_token)
    except ValueError as exc:
        detail = str(exc)
        raise HTTPException(
            status_code=map_value_error_to_http(detail),
            detail=detail,
        ) from exc

    filename = f"{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{uuid4().hex[:12]}{suffix}"
    try:
        store_uploaded_file_record(
            scene=scene_text,
            filename=filename,
            content_type=content_type,
            file_bytes=file_bytes,
            uploaded_by_token=token,
        )
    except Exception as exc:
        logger.exception(
            "image upload persistence failed",
            extra={"upload_scene": scene_text, "upload_filename": filename},
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="upload_store_failed",
        ) from exc
    canonical_url = f"{str(request.base_url).rstrip('/')}/api/v1/uploads/access/{quote(scene_text)}/{quote(filename)}"
    url = build_upload_access_url(canonical_url)

    return UploadImageOut(
        url=url,
        filename=filename,
        size=size,
        content_type=content_type,
    )


@app.post("/api/v1/uploads/images-inline", response_model=UploadImageOut, status_code=201)
def api_upload_image_inline(
    request: Request,
    payload: UploadImageInlineIn,
    x_role: str | None = Header(default=None),
    x_token: str | None = Header(default=None),
    x_cadre_token: str | None = Header(default=None),
) -> UploadImageOut:
    _ = x_role
    token = require_token(x_token)
    _ = get_user_from_token_or_401(token)
    apply_rate_limit(
        request,
        scope="upload_image",
        limit=60,
        window_seconds=600,
        identity=_token_rate_identity(token),
    )

    try:
        file_bytes = base64.b64decode(str(payload.data_base64 or "").strip(), validate=True)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="empty_image_file",
        ) from exc

    content_type = str(payload.content_type or "").lower().strip()
    suffix, size = _validate_image_upload_bytes(
        content_type=content_type,
        file_bytes=file_bytes,
    )

    scene_text = _normalize_upload_scene(payload.scene)
    try:
        validate_upload_scene_access(token, scene_text, x_cadre_token)
    except ValueError as exc:
        detail = str(exc)
        raise HTTPException(
            status_code=map_value_error_to_http(detail),
            detail=detail,
        ) from exc

    filename = f"{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{uuid4().hex[:12]}{suffix}"
    try:
        store_uploaded_file_record(
            scene=scene_text,
            filename=filename,
            content_type=content_type,
            file_bytes=file_bytes,
            uploaded_by_token=token,
        )
    except Exception as exc:
        logger.exception(
            "inline image upload persistence failed",
            extra={"upload_scene": scene_text, "upload_filename": filename},
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="upload_store_failed",
        ) from exc
    canonical_url = f"{str(request.base_url).rstrip('/')}/api/v1/uploads/access/{quote(scene_text)}/{quote(filename)}"
    url = build_upload_access_url(canonical_url)

    return UploadImageOut(
        url=url,
        filename=filename,
        size=size,
        content_type=content_type,
    )


@app.post("/api/v1/uploads/images-from-cloud", response_model=UploadImageOut, status_code=201)
def api_upload_image_from_cloud(
    request: Request,
    payload: UploadImageCloudFileIn,
    x_role: str | None = Header(default=None),
    x_token: str | None = Header(default=None),
    x_cadre_token: str | None = Header(default=None),
) -> UploadImageOut:
    _ = x_role
    token = require_token(x_token)
    _ = get_user_from_token_or_401(token)
    apply_rate_limit(
        request,
        scope="upload_image",
        limit=60,
        window_seconds=600,
        identity=_token_rate_identity(token),
    )

    scene_text = _normalize_upload_scene(payload.scene)
    try:
        validate_upload_scene_access(token, scene_text, x_cadre_token)
    except ValueError as exc:
        detail = str(exc)
        raise HTTPException(
            status_code=map_value_error_to_http(detail),
            detail=detail,
        ) from exc

    file_bytes, response_content_type = _download_cloud_upload_bytes(payload.source_url)
    content_type = str(payload.content_type or "").strip().lower() or response_content_type
    suffix, size = _validate_image_upload_bytes(
        content_type=content_type,
        file_bytes=file_bytes,
    )

    filename = f"{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{uuid4().hex[:12]}{suffix}"
    try:
        store_uploaded_file_record(
            scene=scene_text,
            filename=filename,
            content_type=content_type,
            file_bytes=file_bytes,
            uploaded_by_token=token,
        )
    except Exception as exc:
        logger.exception(
            "cloud relay image persistence failed",
            extra={"upload_scene": scene_text, "upload_filename": filename},
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="upload_store_failed",
        ) from exc
    canonical_url = f"{str(request.base_url).rstrip('/')}/api/v1/uploads/access/{quote(scene_text)}/{quote(filename)}"
    url = build_upload_access_url(canonical_url)
    return UploadImageOut(
        url=url,
        filename=filename,
        size=size,
        content_type=content_type,
    )


@app.get("/api/v1/uploads/access/{scene}/{filename}")
def api_upload_access(
    scene: str,
    filename: str,
    exp: str = Query(default=""),
    sig: str = Query(default=""),
) -> FileResponse:
    scene_text = str(scene or "").strip().lower()
    filename_text = str(filename or "").strip()
    if not UPLOAD_SCENE_PATTERN.fullmatch(scene_text) or scene_text not in UPLOAD_SCENE_WHITELIST:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="file_not_found")
    if not UPLOAD_FILENAME_PATTERN.fullmatch(filename_text):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="file_not_found")
    try:
        verify_upload_access_signature(scene_text, filename_text, exp, sig)
    except ValueError as exc:
        detail = str(exc)
        raise HTTPException(
            status_code=map_value_error_to_http(detail),
            detail=detail,
        ) from exc
    record = get_stored_file_record(scene_text, filename_text)
    if record is not None:
        try:
            signed_url = build_download_url(
                record=record,
                expires_in_seconds=600 if int(record.get("is_private") or 0) else 300,
            )
        except FileNotFoundError:
            signed_url = ""
        if signed_url:
            return RedirectResponse(
                url=signed_url,
                status_code=status.HTTP_307_TEMPORARY_REDIRECT,
                headers={"Cache-Control": "no-store", "Pragma": "no-cache"},
            )
        file_path = resolve_local_file_path(record).resolve()
        if not file_path.is_file():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="file_not_found")
        media_type = str(record.get("content_type") or "").strip() or mimetypes.guess_type(str(file_path))[0] or "application/octet-stream"
        return FileResponse(
            path=file_path,
            media_type=media_type,
            headers={"Cache-Control": "no-store", "Pragma": "no-cache"},
        )
    file_path = (UPLOAD_DIR / scene_text / filename_text).resolve()
    scene_root = (UPLOAD_DIR / scene_text).resolve()
    if not str(file_path).startswith(str(scene_root)) or not file_path.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="file_not_found")
    media_type = mimetypes.guess_type(str(file_path))[0] or "application/octet-stream"
    return FileResponse(
        path=file_path,
        media_type=media_type,
        headers={"Cache-Control": "no-store", "Pragma": "no-cache"},
    )


@app.get("/api/v1/metrics", response_model=list[VillageMetricOut])
def api_list_metrics() -> list[VillageMetricOut]:
    return [VillageMetricOut(**row) for row in list_village_metrics()]


@app.get("/api/v1/open/profile", response_model=VillageOpenProfileOut)
def api_get_open_profile() -> VillageOpenProfileOut:
    return VillageOpenProfileOut(**get_village_open_profile())


@app.put("/api/v1/metrics", response_model=list[VillageMetricOut])
def api_update_metrics(
    payload: VillageMetricsUpdateIn,
    x_role: str | None = Header(default=None),
    x_token: str | None = Header(default=None),
    x_cadre_token: str | None = Header(default=None),
) -> list[VillageMetricOut]:
    require_cadre(x_role, x_token, x_cadre_token)
    token = require_token(x_token)
    try:
        rows = update_village_metrics(token, payload.model_dump())
    except ValueError as exc:
        detail = str(exc)
        raise HTTPException(
            status_code=map_value_error_to_http(detail),
            detail=detail,
        ) from exc
    return [VillageMetricOut(**row) for row in rows]


@app.get("/api/v1/gov/services", response_model=list[GovServiceOut])
def api_list_gov_services(
    x_token: str | None = Header(default=None),
    x_cadre_token: str | None = Header(default=None),
) -> list[GovServiceOut]:
    try:
        rows = list_gov_services(x_token, x_cadre_token)
    except ValueError as exc:
        detail = str(exc)
        raise HTTPException(
            status_code=map_value_error_to_http(detail),
            detail=detail,
        ) from exc
    return [GovServiceOut(**row) for row in rows]


@app.get("/api/v1/gov/services/{service_id}", response_model=GovServiceDetailOut)
def api_get_gov_service(
    service_id: int,
    x_token: str | None = Header(default=None),
    x_cadre_token: str | None = Header(default=None),
) -> GovServiceDetailOut:
    try:
        row = get_gov_service(x_token, service_id, x_cadre_token)
    except ValueError as exc:
        detail = str(exc)
        raise HTTPException(
            status_code=map_value_error_to_http(detail),
            detail=detail,
        ) from exc
    return GovServiceDetailOut(**row)


@app.put("/api/v1/gov/services/{service_id}", response_model=GovServiceDetailOut)
def api_update_gov_service(
    service_id: int,
    payload: GovServiceUpdateIn,
    x_role: str | None = Header(default=None),
    x_token: str | None = Header(default=None),
    x_cadre_token: str | None = Header(default=None),
) -> GovServiceDetailOut:
    require_cadre(x_role, x_token, x_cadre_token)
    token = require_token(x_token)
    try:
        row = update_gov_service(token, service_id, payload.model_dump())
    except ValueError as exc:
        detail = str(exc)
        raise HTTPException(
            status_code=map_value_error_to_http(detail),
            detail=detail,
        ) from exc
    return GovServiceDetailOut(**row)


@app.post("/api/v1/gov/applications", response_model=GovServiceApplicationOut, status_code=201)
def api_create_gov_application(
    request: Request,
    payload: GovServiceApplicationCreateIn,
    x_token: str | None = Header(default=None),
) -> GovServiceApplicationOut:
    token = require_token(x_token)
    apply_rate_limit(
        request,
        scope="gov_application_create",
        limit=20,
        window_seconds=3600,
        identity=_token_rate_identity(token),
    )
    try:
        row = create_gov_application(token, payload.model_dump())
    except ValueError as exc:
        detail = str(exc)
        raise HTTPException(
            status_code=map_value_error_to_http(detail),
            detail=detail,
        ) from exc
    return GovServiceApplicationOut(**row)


@app.get("/api/v1/gov/applications", response_model=list[GovServiceApplicationOut])
def api_list_gov_applications(
    x_token: str | None = Header(default=None),
    x_cadre_token: str | None = Header(default=None),
) -> list[GovServiceApplicationOut]:
    token = require_token(x_token)
    try:
        rows = list_gov_applications(token, x_cadre_token)
    except ValueError as exc:
        detail = str(exc)
        raise HTTPException(
            status_code=map_value_error_to_http(detail),
            detail=detail,
        ) from exc
    return [GovServiceApplicationOut(**row) for row in rows]


@app.get("/api/v1/gov/applications/{application_id}", response_model=GovServiceApplicationOut)
def api_get_gov_application_detail(
    application_id: int,
    x_token: str | None = Header(default=None),
    x_cadre_token: str | None = Header(default=None),
) -> GovServiceApplicationOut:
    token = require_token(x_token)
    try:
        row = get_gov_application_detail(token, application_id, x_cadre_token)
    except ValueError as exc:
        detail = str(exc)
        raise HTTPException(
            status_code=map_value_error_to_http(detail),
            detail=detail,
        ) from exc
    return GovServiceApplicationOut(**row)


@app.patch("/api/v1/gov/applications/{application_id}", response_model=GovServiceApplicationOut)
def api_update_gov_application(
    request: Request,
    application_id: int,
    payload: GovServiceApplicationUpdateIn,
    x_role: str | None = Header(default=None),
    x_token: str | None = Header(default=None),
    x_cadre_token: str | None = Header(default=None),
) -> GovServiceApplicationOut:
    require_cadre(x_role, x_token, x_cadre_token)
    token = require_token(x_token)
    apply_rate_limit(
        request,
        scope="gov_application_update",
        limit=60,
        window_seconds=600,
        identity=_token_rate_identity(token),
    )
    try:
        row = update_gov_application(token, application_id, payload.model_dump())
    except ValueError as exc:
        detail = str(exc)
        raise HTTPException(
            status_code=map_value_error_to_http(detail),
            detail=detail,
        ) from exc
    return GovServiceApplicationOut(**row)


@app.post("/api/v1/gov/applications/{application_id}/cancel", response_model=ActionResultOut)
def api_cancel_gov_application(
    application_id: int,
    x_token: str | None = Header(default=None),
) -> ActionResultOut:
    token = require_token(x_token)
    try:
        row = cancel_gov_application(token, application_id)
    except ValueError as exc:
        detail = str(exc)
        raise HTTPException(
            status_code=map_value_error_to_http(detail),
            detail=detail,
        ) from exc
    return ActionResultOut(**row)


@app.post("/api/v1/requests", response_model=VillagerRequestOut, status_code=201)
def api_create_villager_request(
    request: Request,
    payload: VillagerRequestCreateIn,
    x_token: str | None = Header(default=None),
) -> VillagerRequestOut:
    token = require_token(x_token)
    apply_rate_limit(
        request,
        scope="villager_request_create",
        limit=20,
        window_seconds=3600,
        identity=_token_rate_identity(token),
    )
    try:
        row = create_villager_request(token, payload.model_dump())
    except ValueError as exc:
        detail = str(exc)
        raise HTTPException(
            status_code=map_value_error_to_http(detail),
            detail=detail,
        ) from exc
    return VillagerRequestOut(**row)


@app.get("/api/v1/requests", response_model=list[VillagerRequestOut])
def api_list_villager_requests(
    x_token: str | None = Header(default=None),
    x_cadre_token: str | None = Header(default=None),
) -> list[VillagerRequestOut]:
    token = require_token(x_token)
    try:
        rows = list_villager_requests(token, x_cadre_token)
    except ValueError as exc:
        detail = str(exc)
        raise HTTPException(
            status_code=map_value_error_to_http(detail),
            detail=detail,
        ) from exc
    return [VillagerRequestOut(**row) for row in rows]


@app.get("/api/v1/requests/{request_id}", response_model=VillagerRequestOut)
def api_get_villager_request_detail(
    request_id: int,
    x_token: str | None = Header(default=None),
    x_cadre_token: str | None = Header(default=None),
) -> VillagerRequestOut:
    token = require_token(x_token)
    try:
        row = get_villager_request_detail(token, request_id, x_cadre_token)
    except ValueError as exc:
        detail = str(exc)
        raise HTTPException(
            status_code=map_value_error_to_http(detail),
            detail=detail,
        ) from exc
    return VillagerRequestOut(**row)


@app.patch("/api/v1/requests/{request_id}", response_model=VillagerRequestOut)
def api_update_villager_request(
    request: Request,
    request_id: int,
    payload: VillagerRequestUpdateIn,
    x_role: str | None = Header(default=None),
    x_token: str | None = Header(default=None),
    x_cadre_token: str | None = Header(default=None),
) -> VillagerRequestOut:
    require_cadre(x_role, x_token, x_cadre_token)
    token = require_token(x_token)
    apply_rate_limit(
        request,
        scope="villager_request_update",
        limit=60,
        window_seconds=600,
        identity=_token_rate_identity(token),
    )
    try:
        row = update_villager_request(token, request_id, payload.model_dump())
    except ValueError as exc:
        detail = str(exc)
        raise HTTPException(
            status_code=map_value_error_to_http(detail),
            detail=detail,
        ) from exc
    return VillagerRequestOut(**row)


@app.post("/api/v1/requests/{request_id}/cancel", response_model=ActionResultOut)
def api_cancel_villager_request(
    request_id: int,
    x_token: str | None = Header(default=None),
) -> ActionResultOut:
    token = require_token(x_token)
    try:
        row = cancel_villager_request(token, request_id)
    except ValueError as exc:
        detail = str(exc)
        raise HTTPException(
            status_code=map_value_error_to_http(detail),
            detail=detail,
        ) from exc
    return ActionResultOut(**row)


@app.get("/api/v1/roster/import-batches", response_model=list[RosterImportBatchOut])
def api_roster_import_batches(
    x_role: str | None = Header(default=None),
    x_token: str | None = Header(default=None),
    x_cadre_token: str | None = Header(default=None),
) -> list[RosterImportBatchOut]:
    require_cadre(x_role, x_token, x_cadre_token)
    token = require_token(x_token)
    try:
        rows = list_roster_import_batches(token)
    except ValueError as exc:
        detail = str(exc)
        raise HTTPException(
            status_code=map_value_error_to_http(detail),
            detail=detail,
        ) from exc
    return [RosterImportBatchOut(**row) for row in rows]


@app.get("/api/v1/roster/export-latest")
def api_export_latest_roster(
    x_role: str | None = Header(default=None),
    x_token: str | None = Header(default=None),
    x_cadre_token: str | None = Header(default=None),
) -> Response:
    require_cadre(x_role, x_token, x_cadre_token)
    token = require_token(x_token)
    try:
        content = export_latest_villager_registry_csv(token, x_cadre_token)
    except ValueError as exc:
        detail = str(exc)
        raise HTTPException(
            status_code=map_value_error_to_http(detail),
            detail=detail,
        ) from exc
    filename = f"得胜村_村民户籍最新_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    return Response(
        content=content,
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename)}",
            "Cache-Control": "no-store",
        },
    )


@app.get("/api/v1/notices", response_model=list[NoticeOut])
def api_list_notices() -> list[NoticeOut]:
    return [NoticeOut(**row) for row in list_notices()]


@app.get("/api/v1/notice-subscriptions/status", response_model=NoticeSubscriptionStatusOut)
def api_get_notice_subscription_status(
    x_token: str | None = Header(default=None),
) -> NoticeSubscriptionStatusOut:
    token = require_token(x_token)
    try:
        data = get_notice_subscription_status(token)
    except ValueError as exc:
        detail = str(exc)
        raise HTTPException(
            status_code=map_value_error_to_http(detail),
            detail=detail,
        ) from exc
    return NoticeSubscriptionStatusOut(**data)


@app.post("/api/v1/notice-subscriptions/record", response_model=NoticeSubscriptionStatusOut)
def api_record_notice_subscription(
    payload: NoticeSubscriptionRecordIn,
    x_token: str | None = Header(default=None),
) -> NoticeSubscriptionStatusOut:
    token = require_token(x_token)
    try:
        data = record_notice_subscription_result(token, payload.model_dump())
    except ValueError as exc:
        detail = str(exc)
        raise HTTPException(
            status_code=map_value_error_to_http(detail),
            detail=detail,
        ) from exc
    return NoticeSubscriptionStatusOut(**data)


@app.get("/api/v1/notices/{notice_id}", response_model=NoticeDetailOut)
def api_get_notice_detail(
    notice_id: int,
) -> NoticeDetailOut:
    try:
        data = get_notice_detail(notice_id)
    except ValueError as exc:
        detail = str(exc)
        raise HTTPException(
            status_code=map_value_error_to_http(detail),
            detail=detail,
        ) from exc
    return NoticeDetailOut(**data)


@app.post("/api/v1/notices", response_model=NoticeOut, status_code=201)
def api_create_notice(
    request: Request,
    payload: NoticeCreate,
    x_role: str | None = Header(default=None),
    x_token: str | None = Header(default=None),
    x_cadre_token: str | None = Header(default=None),
) -> NoticeOut:
    require_cadre(x_role, x_token, x_cadre_token)
    token = require_token(x_token)
    apply_rate_limit(
        request,
        scope="notice_create",
        limit=40,
        window_seconds=600,
        identity=_token_rate_identity(token),
    )
    try:
        row = create_notice(payload.model_dump())
    except ValueError as exc:
        detail = str(exc)
        raise HTTPException(
            status_code=map_value_error_to_http(detail),
            detail=detail,
        ) from exc
    return NoticeOut(**row)


@app.put("/api/v1/notices/{notice_id}", response_model=NoticeOut)
def api_update_notice(
    request: Request,
    notice_id: int,
    payload: NoticeCreate,
    x_role: str | None = Header(default=None),
    x_token: str | None = Header(default=None),
    x_cadre_token: str | None = Header(default=None),
) -> NoticeOut:
    require_cadre(x_role, x_token, x_cadre_token)
    token = require_token(x_token)
    apply_rate_limit(
        request,
        scope="notice_update",
        limit=60,
        window_seconds=600,
        identity=_token_rate_identity(token),
    )
    try:
        row = update_notice(token, notice_id, payload.model_dump())
    except ValueError as exc:
        detail = str(exc)
        raise HTTPException(
            status_code=map_value_error_to_http(detail),
            detail=detail,
        ) from exc
    return NoticeOut(**row)


@app.delete("/api/v1/notices/{notice_id}", response_model=ActionResultOut)
def api_delete_notice(
    notice_id: int,
    x_role: str | None = Header(default=None),
    x_token: str | None = Header(default=None),
    x_cadre_token: str | None = Header(default=None),
) -> ActionResultOut:
    require_cadre(x_role, x_token, x_cadre_token)
    token = require_token(x_token)
    try:
        row = delete_notice(token, notice_id)
    except ValueError as exc:
        detail = str(exc)
        raise HTTPException(
            status_code=map_value_error_to_http(detail),
            detail=detail,
        ) from exc
    return ActionResultOut(**row)


@app.get("/api/v1/training-programs", response_model=list[TrainingProgramOut])
def api_list_training_programs(x_token: str | None = Header(default=None)) -> list[TrainingProgramOut]:
    openid = get_openid_by_token_optional(x_token or "")
    return [TrainingProgramOut(**row) for row in list_training_programs(openid=openid)]


@app.post(
    "/api/v1/training-programs/{program_id}/signup",
    response_model=TrainingSignupOut,
    status_code=201,
)
def api_signup_training_program(
    request: Request,
    program_id: int,
    payload: TrainingSignupCreate,
    x_token: str | None = Header(default=None),
) -> TrainingSignupOut:
    token = require_token(x_token)
    apply_rate_limit(
        request,
        scope="training_signup",
        limit=20,
        window_seconds=600,
        identity=_token_rate_identity(token),
    )
    try:
        row = signup_training_program(token, program_id, payload.model_dump())
    except ValueError as exc:
        detail = str(exc)
        raise HTTPException(
            status_code=map_value_error_to_http(detail),
            detail=detail,
        ) from exc
    return TrainingSignupOut(**row)


@app.get("/api/v1/volunteer-activities", response_model=list[VolunteerActivityOut])
def api_list_volunteer_activities(x_token: str | None = Header(default=None)) -> list[VolunteerActivityOut]:
    openid = get_openid_by_token_optional(x_token or "")
    return [VolunteerActivityOut(**row) for row in list_volunteer_activities(openid=openid)]


@app.post(
    "/api/v1/volunteer-activities/{activity_id}/signup",
    response_model=VolunteerActivitySignupOut,
    status_code=201,
)
def api_signup_volunteer_activity(
    request: Request,
    activity_id: int,
    payload: VolunteerActivitySignupCreate,
    x_token: str | None = Header(default=None),
) -> VolunteerActivitySignupOut:
    token = require_token(x_token)
    apply_rate_limit(
        request,
        scope="volunteer_activity_signup",
        limit=20,
        window_seconds=600,
        identity=_token_rate_identity(token),
    )
    try:
        row = signup_volunteer_activity(token, activity_id, payload.model_dump())
    except ValueError as exc:
        detail = str(exc)
        raise HTTPException(
            status_code=map_value_error_to_http(detail),
            detail=detail,
        ) from exc
    return VolunteerActivitySignupOut(**row)


@app.post("/api/v1/proposal", response_model=ProposalSubmitOut, status_code=201)
def api_create_proposal(
    request: Request,
    payload: ProposalCreateIn,
    x_token: str | None = Header(default=None),
) -> ProposalSubmitOut:
    token = require_token(x_token)
    apply_rate_limit(
        request,
        scope="proposal_submit",
        limit=20,
        window_seconds=600,
        identity=_token_rate_identity(token),
    )
    try:
        row = create_proposal(token, payload.model_dump())
    except ValueError as exc:
        detail = str(exc)
        raise HTTPException(
            status_code=map_value_error_to_http(detail),
            detail=detail,
        ) from exc
    return ProposalSubmitOut(**row)


@app.get("/api/v1/proposal/status", response_model=ProposalStatusOut)
def api_proposal_status(x_token: str | None = Header(default=None)) -> ProposalStatusOut:
    token = require_token(x_token)
    try:
        data = proposal_status(token)
    except ValueError as exc:
        detail = str(exc)
        raise HTTPException(
            status_code=map_value_error_to_http(detail),
            detail=detail,
        ) from exc
    return ProposalStatusOut(**data)


@app.get("/api/v1/products", response_model=list[LocalProductOut])
def api_list_local_products() -> list[LocalProductOut]:
    return [LocalProductOut(**row) for row in list_local_products()]


@app.get("/api/v1/products/{product_id}", response_model=LocalProductOut)
def api_get_local_product(product_id: int) -> LocalProductOut:
    try:
        row = get_local_product(product_id)
    except ValueError as exc:
        detail = str(exc)
        raise HTTPException(
            status_code=map_value_error_to_http(detail),
            detail=detail,
        ) from exc
    return LocalProductOut(**row)


@app.get("/api/v1/ledgers", response_model=list[LedgerOut])
def api_list_ledgers(
    x_role: str | None = Header(default=None),
    x_token: str | None = Header(default=None),
    x_cadre_token: str | None = Header(default=None),
) -> list[LedgerOut]:
    require_cadre(x_role, x_token, x_cadre_token)
    return [LedgerOut(**row) for row in list_ledgers()]


@app.post("/api/v1/ledgers", response_model=LedgerOut, status_code=201)
def api_create_ledger(
    payload: LedgerCreate,
    x_role: str | None = Header(default=None),
    x_token: str | None = Header(default=None),
    x_cadre_token: str | None = Header(default=None),
) -> LedgerOut:
    require_cadre(x_role, x_token, x_cadre_token)
    return LedgerOut(**create_ledger(payload.model_dump()))
