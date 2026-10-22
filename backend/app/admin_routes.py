from __future__ import annotations

import re
from urllib.parse import quote
from uuid import uuid4
from typing import Any

from fastapi import APIRouter, File, Header, HTTPException, Query, Request, UploadFile, status

from .admin_auth import (
    begin_admin_mfa_setup,
    change_admin_password,
    confirm_admin_mfa_setup,
    get_current_admin,
    login_admin,
    logout_admin,
    resolve_client_ip,
)
from .image_validation import matches_image_content_type
from .admin_services import (
    create_admin_notice,
    create_admin_account_for_authorization,
    create_admin_cadre_authorization,
    create_admin_training_program,
    create_admin_volunteer_activity,
    delete_admin_volunteer_activity,
    end_admin_volunteer_activity,
    export_admin_volunteer_activity_signups_csv,
    list_admin_volunteer_activities,
    list_admin_volunteer_activity_signups,
    update_admin_volunteer_activity,
    list_admin_proposals,
    list_admin_local_products,
    create_admin_local_product,
    update_admin_local_product,
    delete_admin_local_product,
    delete_admin_cadre_authorization,
    delete_admin_notice,
    delete_admin_training_program,
    end_admin_training_program,
    get_admin_audit_log_detail,
    get_admin_gov_application_detail,
    get_admin_gov_service_detail,
    get_admin_nav_badges,
    get_admin_notice_detail,
    get_admin_open_profile,
    get_admin_request_detail,
    build_admin_request_materials_zip,
    get_admin_villager_identity_summary,
    list_admin_audit_logs,
    list_admin_cadre_authorizations,
    list_admin_metrics,
    list_admin_notices,
    list_admin_gov_applications,
    list_admin_gov_services,
    list_admin_requests,
    list_admin_training_programs,
    list_admin_training_signups,
    list_admin_villager_identities,
    import_admin_villager_roster,
    rebind_admin_villager_identity,
    reset_admin_account_for_authorization,
    purge_admin_test_data,
    unbind_admin_villager_identity,
    update_admin_cadre_authorization,
    update_admin_metrics,
    update_admin_notice,
    update_admin_open_profile,
    update_admin_gov_application,
    update_admin_gov_service,
    update_admin_request,
    upload_admin_image,
    export_admin_training_signups_csv,
    export_admin_villager_identities_xlsx,
    update_admin_training_program,
)
from .admin_schemas import (
    AdminActionOut,
    AdminAuditLogDetailOut,
    AdminAuditLogOut,
    AdminAuthUserOut,
    AdminCadreAccountCreateIn,
    AdminCadreAccountResetPasswordIn,
    AdminCadreAuthorizationCreateIn,
    AdminCadreAuthorizationOut,
    AdminCadreAuthorizationUpdateIn,
    AdminChangePasswordIn,
    AdminLoginIn,
    AdminLoginOut,
    AdminMfaConfirmIn,
    AdminMfaConfirmOut,
    AdminMfaSetupOut,
    AdminNoticeDetailOut,
    AdminPurgeTestDataIn,
    AdminPurgeTestDataOut,
    AdminVillagerIdentityOut,
    AdminVillagerIdentityRebindIn,
    AdminVillagerIdentitySummaryOut,
    AdminVillagerIdentityUnbindIn,
)
from .schemas import (
    GovServiceDetailOut,
    GovServiceOut,
    GovServiceApplicationOut,
    GovServiceApplicationUpdateIn,
    GovServiceUpdateIn,
    NoticeCreate,
    NoticeOut,
    UploadImageOut,
    TrainingProgramCreate,
    TrainingProgramOut,
    TrainingSignupAdminOut,
    VillageMetricsUpdateIn,
    VillageMetricOut,
    VillageOpenProfileOut,
    VillageOpenProfileUpdateIn,
    VolunteerActivityCreate,
    VolunteerActivityOut,
    VolunteerActivitySignupAdminOut,
    ProposalOut,
    LocalProductCreateIn,
    LocalProductOut,
    VillagerRequestOut,
    VillagerRequestUpdateIn,
    RosterImportOut,
)


router = APIRouter(prefix="/api/v1/admin", tags=["admin"])
ADMIN_UPLOAD_SCENE_WHITELIST = {
    "notice",
    "request_reply",
    "gov_reply",
    "open",
    "gov",
    "gov_service",
    "gov_detail",
    "ledger",
    "shop",
}
ADMIN_ALLOWED_IMAGE_TYPES = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "image/heic": ".heic",
    "image/heif": ".heif",
}
ADMIN_UPLOAD_SCENE_PATTERN = re.compile(r"^[a-z0-9_-]{1,32}$")
ADMIN_MAX_IMAGE_BYTES = 8 * 1024 * 1024


def _request_ip(request: Request) -> str:
    client_host = getattr(request.client, "host", "") if request.client else ""
    return resolve_client_ip(
        peer_ip=str(client_host or ""),
        forwarded_for=str(request.headers.get("x-forwarded-for") or ""),
        real_ip=str(request.headers.get("x-real-ip") or ""),
    )[:64]


def _request_user_agent(request: Request) -> str:
    return str(request.headers.get("user-agent") or "").strip()[:255]


def require_admin_token(x_admin_token: str | None) -> str:
    token = str(x_admin_token or "").strip()
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="login_required")
    return token


def map_admin_error_to_http(detail: str) -> int:
    if detail in {
        "login_required",
        "invalid_admin_token",
        "admin_token_expired",
        "invalid_admin_credentials",
        "admin_mfa_code_required",
        "invalid_admin_mfa_code",
    }:
        return status.HTTP_401_UNAUTHORIZED
    if detail == "admin_ip_rate_limited":
        return status.HTTP_429_TOO_MANY_REQUESTS
    if detail in {"roster_not_ready", "upload_store_failed"}:
        return status.HTTP_503_SERVICE_UNAVAILABLE
    if detail in {
        "admin_account_disabled",
        "admin_authorization_disabled",
        "admin_password_change_required",
        "admin_mfa_setup_required",
        "admin_write_forbidden",
        "admin_super_required",
        "cadre_authorization_default_protected",
    }:
        return status.HTTP_403_FORBIDDEN
    if detail == "admin_account_locked":
        return status.HTTP_423_LOCKED
    if detail in {
        "request_not_found",
        "gov_application_not_found",
        "gov_service_not_found",
        "notice_not_found",
        "cadre_authorization_not_found",
        "audit_log_not_found",
        "admin_account_not_found",
        "training_program_not_found",
        "volunteer_activity_not_found",
        "local_product_not_found",
        "villager_identity_not_found",
    }:
        return status.HTTP_404_NOT_FOUND
    if detail in {"id_card_already_verified", "cadre_authorization_exists", "cadre_authorization_has_account", "admin_login_name_conflict"}:
        return status.HTTP_409_CONFLICT
    if detail == "admin_mfa_already_configured":
        return status.HTTP_409_CONFLICT
    return status.HTTP_400_BAD_REQUEST


@router.post("/auth/login", response_model=AdminLoginOut)
def api_admin_login(request: Request, payload: AdminLoginIn) -> AdminLoginOut:
    try:
        data = login_admin(
            login_name=payload.login_name,
            password=payload.password,
            mfa_code=payload.mfa_code,
            ip=_request_ip(request),
            user_agent=_request_user_agent(request),
        )
    except ValueError as exc:
        detail = str(exc)
        raise HTTPException(status_code=map_admin_error_to_http(detail), detail=detail) from exc
    return AdminLoginOut(**data)


@router.post("/auth/logout", response_model=AdminActionOut)
def api_admin_logout(
    request: Request,
    x_admin_token: str | None = Header(default=None),
) -> AdminActionOut:
    token = require_admin_token(x_admin_token)
    try:
        data = logout_admin(
            token,
            ip=_request_ip(request),
            user_agent=_request_user_agent(request),
        )
    except ValueError as exc:
        detail = str(exc)
        raise HTTPException(status_code=map_admin_error_to_http(detail), detail=detail) from exc
    return AdminActionOut(**data)


@router.get("/auth/me", response_model=AdminAuthUserOut)
def api_admin_me(x_admin_token: str | None = Header(default=None)) -> AdminAuthUserOut:
    token = require_admin_token(x_admin_token)
    try:
        data = get_current_admin(token, allow_incomplete=True)
    except ValueError as exc:
        detail = str(exc)
        raise HTTPException(status_code=map_admin_error_to_http(detail), detail=detail) from exc
    return AdminAuthUserOut(**data)


@router.post("/auth/mfa/setup", response_model=AdminMfaSetupOut)
def api_admin_mfa_setup(
    request: Request,
    x_admin_token: str | None = Header(default=None),
) -> AdminMfaSetupOut:
    token = require_admin_token(x_admin_token)
    try:
        data = begin_admin_mfa_setup(
            token,
            ip=_request_ip(request),
            user_agent=_request_user_agent(request),
        )
    except ValueError as exc:
        detail = str(exc)
        raise HTTPException(status_code=map_admin_error_to_http(detail), detail=detail) from exc
    return AdminMfaSetupOut(**data)


@router.post("/auth/mfa/confirm", response_model=AdminMfaConfirmOut)
def api_admin_mfa_confirm(
    request: Request,
    payload: AdminMfaConfirmIn,
    x_admin_token: str | None = Header(default=None),
) -> AdminMfaConfirmOut:
    token = require_admin_token(x_admin_token)
    try:
        data = confirm_admin_mfa_setup(
            token,
            code=payload.code,
            ip=_request_ip(request),
            user_agent=_request_user_agent(request),
        )
    except ValueError as exc:
        detail = str(exc)
        raise HTTPException(status_code=map_admin_error_to_http(detail), detail=detail) from exc
    return AdminMfaConfirmOut(**data)


@router.post("/roster/import", response_model=RosterImportOut)
async def api_admin_roster_import(
    file: UploadFile = File(...),
    x_admin_token: str | None = Header(default=None),
) -> RosterImportOut:
    token = require_admin_token(x_admin_token)
    try:
        file_bytes = await file.read()
        data = import_admin_villager_roster(token, file.filename or "roster.csv", file_bytes)
    except ValueError as exc:
        detail = str(exc)
        raise HTTPException(status_code=map_admin_error_to_http(detail), detail=detail) from exc
    return RosterImportOut(**data)


@router.post("/auth/change-password", response_model=AdminActionOut)
def api_admin_change_password(
    request: Request,
    payload: AdminChangePasswordIn,
    x_admin_token: str | None = Header(default=None),
) -> AdminActionOut:
    token = require_admin_token(x_admin_token)
    try:
        data = change_admin_password(
            token,
            current_password=payload.current_password,
            new_password=payload.new_password,
            ip=_request_ip(request),
            user_agent=_request_user_agent(request),
        )
    except ValueError as exc:
        detail = str(exc)
        raise HTTPException(status_code=map_admin_error_to_http(detail), detail=detail) from exc
    return AdminActionOut(**data)


@router.post("/maintenance/purge-test-data", response_model=AdminPurgeTestDataOut)
def api_admin_purge_test_data(
    payload: AdminPurgeTestDataIn,
    x_admin_token: str | None = Header(default=None),
) -> AdminPurgeTestDataOut:
    token = require_admin_token(x_admin_token)
    try:
        data = purge_admin_test_data(token, payload.confirm_text)
    except ValueError as exc:
        detail = str(exc)
        raise HTTPException(status_code=map_admin_error_to_http(detail), detail=detail) from exc
    return AdminPurgeTestDataOut(**data)


@router.get("/nav-badges", response_model=dict[str, int])
def api_admin_nav_badges(
    x_admin_token: str | None = Header(default=None),
) -> dict[str, int]:
    token = require_admin_token(x_admin_token)
    try:
        return get_admin_nav_badges(token)
    except ValueError as exc:
        detail = str(exc)
        raise HTTPException(status_code=map_admin_error_to_http(detail), detail=detail) from exc


@router.get("/gov/services", response_model=list[GovServiceOut])
def api_admin_list_gov_services(
    x_admin_token: str | None = Header(default=None),
) -> list[GovServiceOut]:
    token = require_admin_token(x_admin_token)
    try:
        rows = list_admin_gov_services(token)
    except ValueError as exc:
        detail = str(exc)
        raise HTTPException(status_code=map_admin_error_to_http(detail), detail=detail) from exc
    return [GovServiceOut(**row) for row in rows]


@router.get("/gov/services/{service_id}", response_model=GovServiceDetailOut)
def api_admin_get_gov_service(
    service_id: int,
    x_admin_token: str | None = Header(default=None),
) -> GovServiceDetailOut:
    token = require_admin_token(x_admin_token)
    try:
        row = get_admin_gov_service_detail(token, service_id)
    except ValueError as exc:
        detail = str(exc)
        raise HTTPException(status_code=map_admin_error_to_http(detail), detail=detail) from exc
    return GovServiceDetailOut(**row)


@router.put("/gov/services/{service_id}", response_model=GovServiceDetailOut)
def api_admin_update_gov_service(
    service_id: int,
    payload: GovServiceUpdateIn,
    x_admin_token: str | None = Header(default=None),
) -> GovServiceDetailOut:
    token = require_admin_token(x_admin_token)
    try:
        row = update_admin_gov_service(token, service_id, payload.model_dump())
    except ValueError as exc:
        detail = str(exc)
        raise HTTPException(status_code=map_admin_error_to_http(detail), detail=detail) from exc
    return GovServiceDetailOut(**row)


@router.get("/requests", response_model=list[VillagerRequestOut])
def api_admin_list_requests(
    x_admin_token: str | None = Header(default=None),
    status: str = Query(default="", alias="status"),
    request_type: str = "",
    keyword: str = "",
) -> list[VillagerRequestOut]:
    token = require_admin_token(x_admin_token)
    try:
        rows = list_admin_requests(
            token,
            status=status,
            request_type=request_type,
            keyword=keyword,
        )
    except ValueError as exc:
        detail = str(exc)
        raise HTTPException(status_code=map_admin_error_to_http(detail), detail=detail) from exc
    return [VillagerRequestOut(**row) for row in rows]


@router.get("/requests/{request_id}", response_model=VillagerRequestOut)
def api_admin_get_request(
    request_id: int,
    x_admin_token: str | None = Header(default=None),
) -> VillagerRequestOut:
    token = require_admin_token(x_admin_token)
    try:
        row = get_admin_request_detail(token, request_id)
    except ValueError as exc:
        detail = str(exc)
        raise HTTPException(status_code=map_admin_error_to_http(detail), detail=detail) from exc
    return VillagerRequestOut(**row)


@router.get("/requests/{request_id}/materials/export")
def api_admin_export_request_materials(
    request_id: int,
    x_admin_token: str | None = Header(default=None),
) -> Any:
    token = require_admin_token(x_admin_token)
    try:
        content, filename_text = build_admin_request_materials_zip(token, request_id)
    except ValueError as exc:
        detail = str(exc)
        raise HTTPException(status_code=map_admin_error_to_http(detail), detail=detail) from exc
    from fastapi import Response

    filename = quote(filename_text)
    return Response(
        content=content,
        media_type="application/zip",
        headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{filename}",
            "Cache-Control": "no-store",
        },
    )


@router.patch("/requests/{request_id}", response_model=VillagerRequestOut)
def api_admin_update_request(
    request_id: int,
    payload: VillagerRequestUpdateIn,
    x_admin_token: str | None = Header(default=None),
) -> VillagerRequestOut:
    token = require_admin_token(x_admin_token)
    try:
        row = update_admin_request(
            token,
            request_id,
            status=payload.status,
            reply_text=payload.reply_text,
            reply_photo_urls=payload.reply_photo_urls,
        )
    except ValueError as exc:
        detail = str(exc)
        raise HTTPException(status_code=map_admin_error_to_http(detail), detail=detail) from exc
    return VillagerRequestOut(**row)


@router.get("/gov/applications", response_model=list[GovServiceApplicationOut])
def api_admin_list_gov_applications(
    x_admin_token: str | None = Header(default=None),
    status: str = Query(default="", alias="status"),
    service_key: str = "",
    keyword: str = "",
    village_group: str = "",
) -> list[GovServiceApplicationOut]:
    token = require_admin_token(x_admin_token)
    try:
        rows = list_admin_gov_applications(
            token,
            status=status,
            service_key=service_key,
            keyword=keyword,
            village_group=village_group,
        )
    except ValueError as exc:
        detail = str(exc)
        raise HTTPException(status_code=map_admin_error_to_http(detail), detail=detail) from exc
    return [GovServiceApplicationOut(**row) for row in rows]


@router.get("/gov/applications/{application_id}", response_model=GovServiceApplicationOut)
def api_admin_get_gov_application(
    application_id: int,
    x_admin_token: str | None = Header(default=None),
) -> GovServiceApplicationOut:
    token = require_admin_token(x_admin_token)
    try:
        row = get_admin_gov_application_detail(token, application_id)
    except ValueError as exc:
        detail = str(exc)
        raise HTTPException(status_code=map_admin_error_to_http(detail), detail=detail) from exc
    return GovServiceApplicationOut(**row)


@router.patch("/gov/applications/{application_id}", response_model=GovServiceApplicationOut)
def api_admin_update_gov_application(
    application_id: int,
    payload: GovServiceApplicationUpdateIn,
    x_admin_token: str | None = Header(default=None),
) -> GovServiceApplicationOut:
    token = require_admin_token(x_admin_token)
    try:
        row = update_admin_gov_application(
            token,
            application_id,
            status=payload.status,
            cadre_reply=payload.cadre_reply,
            reply_photo_urls=payload.reply_photo_urls,
        )
    except ValueError as exc:
        detail = str(exc)
        raise HTTPException(status_code=map_admin_error_to_http(detail), detail=detail) from exc
    return GovServiceApplicationOut(**row)


@router.get("/notices", response_model=list[NoticeOut])
def api_admin_list_notices(
    x_admin_token: str | None = Header(default=None),
    keyword: str = "",
    home_top_only: bool = False,
) -> list[NoticeOut]:
    token = require_admin_token(x_admin_token)
    try:
        rows = list_admin_notices(token, keyword=keyword, home_top_only=home_top_only)
    except ValueError as exc:
        detail = str(exc)
        raise HTTPException(status_code=map_admin_error_to_http(detail), detail=detail) from exc
    return [NoticeOut(**row) for row in rows]


@router.get("/notices/{notice_id}", response_model=AdminNoticeDetailOut)
def api_admin_get_notice(
    notice_id: int,
    x_admin_token: str | None = Header(default=None),
) -> AdminNoticeDetailOut:
    token = require_admin_token(x_admin_token)
    try:
        row = get_admin_notice_detail(token, notice_id)
    except ValueError as exc:
        detail = str(exc)
        raise HTTPException(status_code=map_admin_error_to_http(detail), detail=detail) from exc
    return AdminNoticeDetailOut(**row)


@router.post("/notices", response_model=NoticeOut)
def api_admin_create_notice(
    payload: NoticeCreate,
    x_admin_token: str | None = Header(default=None),
) -> NoticeOut:
    token = require_admin_token(x_admin_token)
    try:
        row = create_admin_notice(token, payload.model_dump())
    except ValueError as exc:
        detail = str(exc)
        raise HTTPException(status_code=map_admin_error_to_http(detail), detail=detail) from exc
    return NoticeOut(**row)


@router.put("/notices/{notice_id}", response_model=NoticeOut)
def api_admin_update_notice(
    notice_id: int,
    payload: NoticeCreate,
    x_admin_token: str | None = Header(default=None),
) -> NoticeOut:
    token = require_admin_token(x_admin_token)
    try:
        row = update_admin_notice(token, notice_id, payload.model_dump())
    except ValueError as exc:
        detail = str(exc)
        raise HTTPException(status_code=map_admin_error_to_http(detail), detail=detail) from exc
    return NoticeOut(**row)


@router.delete("/notices/{notice_id}", response_model=AdminActionOut)
def api_admin_delete_notice(
    notice_id: int,
    x_admin_token: str | None = Header(default=None),
) -> AdminActionOut:
    token = require_admin_token(x_admin_token)
    try:
        row = delete_admin_notice(token, notice_id)
    except ValueError as exc:
        detail = str(exc)
        raise HTTPException(status_code=map_admin_error_to_http(detail), detail=detail) from exc
    return AdminActionOut(**row)


@router.post("/uploads/images", response_model=UploadImageOut, status_code=201)
async def api_admin_upload_image(
    request: Request,
    file: UploadFile = File(...),
    scene: str = Query(default=""),
    x_admin_token: str | None = Header(default=None),
) -> UploadImageOut:
    token = require_admin_token(x_admin_token)
    content_type = (file.content_type or "").lower().strip()
    suffix = ADMIN_ALLOWED_IMAGE_TYPES.get(content_type)
    if suffix is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="unsupported_image_type")
    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="empty_image_file")
    if len(file_bytes) > ADMIN_MAX_IMAGE_BYTES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="image_file_too_large")
    if not matches_image_content_type(content_type, file_bytes):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="image_content_mismatch")
    scene_text = str(scene or "").strip().lower()
    if not ADMIN_UPLOAD_SCENE_PATTERN.fullmatch(scene_text) or scene_text not in ADMIN_UPLOAD_SCENE_WHITELIST:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="invalid_upload_scene")
    filename = f"{uuid4().hex}{suffix}"
    try:
        data = upload_admin_image(
            token,
            scene=scene_text,
            filename=filename,
            content_type=content_type,
            file_bytes=file_bytes,
            public_origin=str(request.base_url).rstrip("/"),
        )
    except ValueError as exc:
        detail = str(exc)
        raise HTTPException(status_code=map_admin_error_to_http(detail), detail=detail) from exc
    return UploadImageOut(**data)


@router.get("/open/metrics", response_model=list[VillageMetricOut])
def api_admin_list_metrics(
    x_admin_token: str | None = Header(default=None),
) -> list[VillageMetricOut]:
    token = require_admin_token(x_admin_token)
    try:
        rows = list_admin_metrics(token)
    except ValueError as exc:
        detail = str(exc)
        raise HTTPException(status_code=map_admin_error_to_http(detail), detail=detail) from exc
    return [VillageMetricOut(**row) for row in rows]


@router.get("/open/profile", response_model=VillageOpenProfileOut)
def api_admin_get_open_profile(
    x_admin_token: str | None = Header(default=None),
) -> VillageOpenProfileOut:
    token = require_admin_token(x_admin_token)
    try:
        row = get_admin_open_profile(token)
    except ValueError as exc:
        detail = str(exc)
        raise HTTPException(status_code=map_admin_error_to_http(detail), detail=detail) from exc
    return VillageOpenProfileOut(**row)


@router.put("/open/profile", response_model=VillageOpenProfileOut)
def api_admin_update_open_profile(
    payload: VillageOpenProfileUpdateIn,
    x_admin_token: str | None = Header(default=None),
) -> VillageOpenProfileOut:
    token = require_admin_token(x_admin_token)
    try:
        row = update_admin_open_profile(token, payload.model_dump())
    except ValueError as exc:
        detail = str(exc)
        raise HTTPException(status_code=map_admin_error_to_http(detail), detail=detail) from exc
    return VillageOpenProfileOut(**row)


@router.put("/open/metrics", response_model=list[VillageMetricOut])
def api_admin_update_metrics(
    payload: VillageMetricsUpdateIn,
    x_admin_token: str | None = Header(default=None),
) -> list[VillageMetricOut]:
    token = require_admin_token(x_admin_token)
    try:
        rows = update_admin_metrics(token, payload.model_dump())
    except ValueError as exc:
        detail = str(exc)
        raise HTTPException(status_code=map_admin_error_to_http(detail), detail=detail) from exc
    return [VillageMetricOut(**row) for row in rows]


@router.get("/cadre-authorizations", response_model=list[AdminCadreAuthorizationOut])
def api_admin_list_cadre_authorizations(
    x_admin_token: str | None = Header(default=None),
    status: str = "",
    keyword: str = "",
) -> list[AdminCadreAuthorizationOut]:
    token = require_admin_token(x_admin_token)
    try:
        rows = list_admin_cadre_authorizations(token, status=status, keyword=keyword)
    except ValueError as exc:
        detail = str(exc)
        raise HTTPException(status_code=map_admin_error_to_http(detail), detail=detail) from exc
    return [AdminCadreAuthorizationOut(**row) for row in rows]


@router.post("/cadre-authorizations", response_model=AdminCadreAuthorizationOut, status_code=201)
def api_admin_create_cadre_authorization(
    payload: AdminCadreAuthorizationCreateIn,
    x_admin_token: str | None = Header(default=None),
) -> AdminCadreAuthorizationOut:
    token = require_admin_token(x_admin_token)
    try:
        row = create_admin_cadre_authorization(
            token,
            real_name=payload.real_name,
            office_title=payload.office_title,
            role_level=payload.role_level,
            can_export_full_id=payload.can_export_full_id,
            status=payload.status,
            create_account=payload.create_account,
            login_name=payload.login_name,
            password=payload.password,
            admin_role_key=payload.admin_role_key,
            force_reset=payload.force_reset,
        )
    except ValueError as exc:
        detail = str(exc)
        raise HTTPException(status_code=map_admin_error_to_http(detail), detail=detail) from exc
    return AdminCadreAuthorizationOut(**row)


@router.delete("/cadre-authorizations/{authorization_id}", response_model=AdminActionOut)
def api_admin_delete_cadre_authorization(
    authorization_id: int,
    x_admin_token: str | None = Header(default=None),
) -> AdminActionOut:
    token = require_admin_token(x_admin_token)
    try:
        row = delete_admin_cadre_authorization(token, authorization_id)
    except ValueError as exc:
        detail = str(exc)
        raise HTTPException(status_code=map_admin_error_to_http(detail), detail=detail) from exc
    return AdminActionOut(**row)


@router.put("/cadre-authorizations/{authorization_id}", response_model=AdminCadreAuthorizationOut)
def api_admin_update_cadre_authorization(
    authorization_id: int,
    payload: AdminCadreAuthorizationUpdateIn,
    x_admin_token: str | None = Header(default=None),
) -> AdminCadreAuthorizationOut:
    token = require_admin_token(x_admin_token)
    try:
        row = update_admin_cadre_authorization(
            token,
            authorization_id,
            office_title=payload.office_title,
            role_level=payload.role_level,
            can_export_full_id=payload.can_export_full_id,
            status=payload.status,
            admin_role_key=payload.admin_role_key,
        )
    except ValueError as exc:
        detail = str(exc)
        raise HTTPException(status_code=map_admin_error_to_http(detail), detail=detail) from exc
    return AdminCadreAuthorizationOut(**row)


@router.post("/cadre-authorizations/{authorization_id}/create-account", response_model=AdminCadreAuthorizationOut)
def api_admin_create_cadre_account(
    authorization_id: int,
    payload: AdminCadreAccountCreateIn,
    x_admin_token: str | None = Header(default=None),
) -> AdminCadreAuthorizationOut:
    token = require_admin_token(x_admin_token)
    try:
        row = create_admin_account_for_authorization(
            token,
            authorization_id,
            login_name=payload.login_name,
            password=payload.password,
            display_name=payload.display_name,
            role_key=payload.role_key,
            force_reset=payload.force_reset,
        )
    except ValueError as exc:
        detail = str(exc)
        raise HTTPException(status_code=map_admin_error_to_http(detail), detail=detail) from exc
    return AdminCadreAuthorizationOut(**row)


@router.post("/cadre-authorizations/{authorization_id}/reset-password", response_model=AdminActionOut)
def api_admin_reset_cadre_account_password(
    authorization_id: int,
    payload: AdminCadreAccountResetPasswordIn,
    x_admin_token: str | None = Header(default=None),
) -> AdminActionOut:
    token = require_admin_token(x_admin_token)
    try:
        row = reset_admin_account_for_authorization(
            token,
            authorization_id,
            new_password=payload.new_password,
            force_reset=payload.force_reset,
        )
    except ValueError as exc:
        detail = str(exc)
        raise HTTPException(status_code=map_admin_error_to_http(detail), detail=detail) from exc
    return AdminActionOut(**row)


@router.get("/audit-logs", response_model=list[AdminAuditLogOut])
def api_admin_list_audit_logs(
    x_admin_token: str | None = Header(default=None),
    actor_type: str = "",
    action: str = "",
    target_type: str = "",
    keyword: str = "",
    limit: int = Query(default=200, ge=1, le=500),
) -> list[AdminAuditLogOut]:
    token = require_admin_token(x_admin_token)
    try:
        rows = list_admin_audit_logs(
            token,
            actor_type=actor_type,
            action=action,
            target_type=target_type,
            keyword=keyword,
            limit=limit,
        )
    except ValueError as exc:
        detail = str(exc)
        raise HTTPException(status_code=map_admin_error_to_http(detail), detail=detail) from exc
    return [AdminAuditLogOut(**row) for row in rows]


@router.get("/audit-logs/{log_id}", response_model=AdminAuditLogDetailOut)
def api_admin_get_audit_log(
    log_id: int,
    x_admin_token: str | None = Header(default=None),
) -> AdminAuditLogDetailOut:
    token = require_admin_token(x_admin_token)
    try:
        row = get_admin_audit_log_detail(token, log_id)
    except ValueError as exc:
        detail = str(exc)
        raise HTTPException(status_code=map_admin_error_to_http(detail), detail=detail) from exc
    return AdminAuditLogDetailOut(**row)


@router.get("/villager-identities", response_model=list[AdminVillagerIdentityOut])
def api_admin_list_villager_identities(
    x_admin_token: str | None = Header(default=None),
    keyword: str = "",
    limit: int = Query(default=200, ge=1, le=500),
) -> list[AdminVillagerIdentityOut]:
    token = require_admin_token(x_admin_token)
    try:
        rows = list_admin_villager_identities(token, keyword=keyword, limit=limit)
    except ValueError as exc:
        detail = str(exc)
        raise HTTPException(status_code=map_admin_error_to_http(detail), detail=detail) from exc
    return [AdminVillagerIdentityOut(**row) for row in rows]


@router.get("/villager-identities/summary", response_model=AdminVillagerIdentitySummaryOut)
def api_admin_villager_identity_summary(
    x_admin_token: str | None = Header(default=None),
    keyword: str = "",
) -> AdminVillagerIdentitySummaryOut:
    token = require_admin_token(x_admin_token)
    try:
        row = get_admin_villager_identity_summary(token, keyword=keyword)
    except ValueError as exc:
        detail = str(exc)
        raise HTTPException(status_code=map_admin_error_to_http(detail), detail=detail) from exc
    return AdminVillagerIdentitySummaryOut(**row)


@router.get("/villager-identities/export")
def api_admin_export_villager_identities(
    x_admin_token: str | None = Header(default=None),
    keyword: str = "",
) -> Any:
    token = require_admin_token(x_admin_token)
    try:
        content = export_admin_villager_identities_xlsx(token, keyword=keyword)
    except ValueError as exc:
        detail = str(exc)
        raise HTTPException(status_code=map_admin_error_to_http(detail), detail=detail) from exc
    filename = quote("村民脱敏名册.xlsx")
    from fastapi import Response

    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{filename}",
            "Cache-Control": "no-store",
        },
    )


@router.get("/training-programs", response_model=list[TrainingProgramOut])
def api_admin_list_training_programs(
    x_admin_token: str | None = Header(default=None),
    keyword: str = "",
) -> list[TrainingProgramOut]:
    token = require_admin_token(x_admin_token)
    try:
        rows = list_admin_training_programs(token, keyword=keyword)
    except ValueError as exc:
        detail = str(exc)
        raise HTTPException(status_code=map_admin_error_to_http(detail), detail=detail) from exc
    return [TrainingProgramOut(**row) for row in rows]


@router.post("/training-programs", response_model=TrainingProgramOut, status_code=201)
def api_admin_create_training_program(
    payload: TrainingProgramCreate,
    x_admin_token: str | None = Header(default=None),
) -> TrainingProgramOut:
    token = require_admin_token(x_admin_token)
    try:
        row = create_admin_training_program(token, payload.model_dump())
    except ValueError as exc:
        detail = str(exc)
        raise HTTPException(status_code=map_admin_error_to_http(detail), detail=detail) from exc
    return TrainingProgramOut(**row)


@router.put("/training-programs/{program_id}", response_model=TrainingProgramOut)
def api_admin_update_training_program(
    program_id: int,
    payload: TrainingProgramCreate,
    x_admin_token: str | None = Header(default=None),
) -> TrainingProgramOut:
    token = require_admin_token(x_admin_token)
    try:
        row = update_admin_training_program(token, program_id, payload.model_dump())
    except ValueError as exc:
        detail = str(exc)
        raise HTTPException(status_code=map_admin_error_to_http(detail), detail=detail) from exc
    return TrainingProgramOut(**row)


@router.post("/training-programs/{program_id}/end", response_model=TrainingProgramOut)
def api_admin_end_training_program(
    program_id: int,
    x_admin_token: str | None = Header(default=None),
) -> TrainingProgramOut:
    token = require_admin_token(x_admin_token)
    try:
        row = end_admin_training_program(token, program_id)
    except ValueError as exc:
        detail = str(exc)
        raise HTTPException(status_code=map_admin_error_to_http(detail), detail=detail) from exc
    return TrainingProgramOut(**row)


@router.delete("/training-programs/{program_id}", response_model=AdminActionOut)
def api_admin_delete_training_program(
    program_id: int,
    x_admin_token: str | None = Header(default=None),
) -> AdminActionOut:
    token = require_admin_token(x_admin_token)
    try:
        row = delete_admin_training_program(token, program_id)
    except ValueError as exc:
        detail = str(exc)
        raise HTTPException(status_code=map_admin_error_to_http(detail), detail=detail) from exc
    return AdminActionOut(**row)


@router.get("/training-programs/{program_id}/signups", response_model=list[TrainingSignupAdminOut])
def api_admin_list_training_signups(
    program_id: int,
    x_admin_token: str | None = Header(default=None),
) -> list[TrainingSignupAdminOut]:
    token = require_admin_token(x_admin_token)
    try:
        rows = list_admin_training_signups(token, program_id)
    except ValueError as exc:
        detail = str(exc)
        raise HTTPException(status_code=map_admin_error_to_http(detail), detail=detail) from exc
    return [TrainingSignupAdminOut(**row) for row in rows]


@router.get("/training-programs/{program_id}/signups/export")
def api_admin_export_training_signups(
    program_id: int,
    x_admin_token: str | None = Header(default=None),
) -> Any:
    token = require_admin_token(x_admin_token)
    try:
        content = export_admin_training_signups_csv(token, program_id)
    except ValueError as exc:
        detail = str(exc)
        raise HTTPException(status_code=map_admin_error_to_http(detail), detail=detail) from exc
    filename = quote(f"就业培训报名名单_{program_id}.csv")
    from fastapi import Response

    return Response(
        content=content,
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{filename}",
            "Cache-Control": "no-store",
        },
    )


@router.get("/volunteer-activities", response_model=list[VolunteerActivityOut])
def api_admin_list_volunteer_activities(
    x_admin_token: str | None = Header(default=None),
    keyword: str = "",
) -> list[VolunteerActivityOut]:
    token = require_admin_token(x_admin_token)
    try:
        rows = list_admin_volunteer_activities(token, keyword=keyword)
    except ValueError as exc:
        detail = str(exc)
        raise HTTPException(status_code=map_admin_error_to_http(detail), detail=detail) from exc
    return [VolunteerActivityOut(**row) for row in rows]


@router.post("/volunteer-activities", response_model=VolunteerActivityOut, status_code=201)
def api_admin_create_volunteer_activity(
    payload: VolunteerActivityCreate,
    x_admin_token: str | None = Header(default=None),
) -> VolunteerActivityOut:
    token = require_admin_token(x_admin_token)
    try:
        row = create_admin_volunteer_activity(token, payload.model_dump())
    except ValueError as exc:
        detail = str(exc)
        raise HTTPException(status_code=map_admin_error_to_http(detail), detail=detail) from exc
    return VolunteerActivityOut(**row)


@router.put("/volunteer-activities/{activity_id}", response_model=VolunteerActivityOut)
def api_admin_update_volunteer_activity(
    activity_id: int,
    payload: VolunteerActivityCreate,
    x_admin_token: str | None = Header(default=None),
) -> VolunteerActivityOut:
    token = require_admin_token(x_admin_token)
    try:
        row = update_admin_volunteer_activity(token, activity_id, payload.model_dump())
    except ValueError as exc:
        detail = str(exc)
        raise HTTPException(status_code=map_admin_error_to_http(detail), detail=detail) from exc
    return VolunteerActivityOut(**row)


@router.post("/volunteer-activities/{activity_id}/end", response_model=VolunteerActivityOut)
def api_admin_end_volunteer_activity(
    activity_id: int,
    x_admin_token: str | None = Header(default=None),
) -> VolunteerActivityOut:
    token = require_admin_token(x_admin_token)
    try:
        row = end_admin_volunteer_activity(token, activity_id)
    except ValueError as exc:
        detail = str(exc)
        raise HTTPException(status_code=map_admin_error_to_http(detail), detail=detail) from exc
    return VolunteerActivityOut(**row)


@router.delete("/volunteer-activities/{activity_id}", response_model=AdminActionOut)
def api_admin_delete_volunteer_activity(
    activity_id: int,
    x_admin_token: str | None = Header(default=None),
) -> AdminActionOut:
    token = require_admin_token(x_admin_token)
    try:
        row = delete_admin_volunteer_activity(token, activity_id)
    except ValueError as exc:
        detail = str(exc)
        raise HTTPException(status_code=map_admin_error_to_http(detail), detail=detail) from exc
    return AdminActionOut(**row)


@router.get("/volunteer-activities/{activity_id}/signups", response_model=list[VolunteerActivitySignupAdminOut])
def api_admin_list_volunteer_activity_signups(
    activity_id: int,
    x_admin_token: str | None = Header(default=None),
) -> list[VolunteerActivitySignupAdminOut]:
    token = require_admin_token(x_admin_token)
    try:
        rows = list_admin_volunteer_activity_signups(token, activity_id)
    except ValueError as exc:
        detail = str(exc)
        raise HTTPException(status_code=map_admin_error_to_http(detail), detail=detail) from exc
    return [VolunteerActivitySignupAdminOut(**row) for row in rows]


@router.get("/volunteer-activities/{activity_id}/signups/export")
def api_admin_export_volunteer_activity_signups(
    activity_id: int,
    x_admin_token: str | None = Header(default=None),
) -> Any:
    token = require_admin_token(x_admin_token)
    try:
        content = export_admin_volunteer_activity_signups_csv(token, activity_id)
    except ValueError as exc:
        detail = str(exc)
        raise HTTPException(status_code=map_admin_error_to_http(detail), detail=detail) from exc
    filename = quote(f"志愿活动报名名单_{activity_id}.csv")
    from fastapi import Response

    return Response(
        content=content,
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{filename}",
            "Cache-Control": "no-store",
        },
    )


@router.get("/proposals", response_model=list[ProposalOut])
def api_admin_list_proposals(
    x_admin_token: str | None = Header(default=None),
) -> list[ProposalOut]:
    token = require_admin_token(x_admin_token)
    try:
        rows = list_admin_proposals(token)
    except ValueError as exc:
        detail = str(exc)
        raise HTTPException(status_code=map_admin_error_to_http(detail), detail=detail) from exc
    return [ProposalOut(**row) for row in rows]


@router.get("/products", response_model=list[LocalProductOut])
def api_admin_list_local_products(
    x_admin_token: str | None = Header(default=None),
) -> list[LocalProductOut]:
    token = require_admin_token(x_admin_token)
    try:
        rows = list_admin_local_products(token)
    except ValueError as exc:
        detail = str(exc)
        raise HTTPException(status_code=map_admin_error_to_http(detail), detail=detail) from exc
    return [LocalProductOut(**row) for row in rows]


@router.post("/products", response_model=LocalProductOut, status_code=201)
def api_admin_create_local_product(
    payload: LocalProductCreateIn,
    x_admin_token: str | None = Header(default=None),
) -> LocalProductOut:
    token = require_admin_token(x_admin_token)
    try:
        row = create_admin_local_product(token, payload.model_dump())
    except ValueError as exc:
        detail = str(exc)
        raise HTTPException(status_code=map_admin_error_to_http(detail), detail=detail) from exc
    return LocalProductOut(**row)


@router.put("/products/{product_id}", response_model=LocalProductOut)
def api_admin_update_local_product(
    product_id: int,
    payload: LocalProductCreateIn,
    x_admin_token: str | None = Header(default=None),
) -> LocalProductOut:
    token = require_admin_token(x_admin_token)
    try:
        row = update_admin_local_product(token, product_id, payload.model_dump())
    except ValueError as exc:
        detail = str(exc)
        raise HTTPException(status_code=map_admin_error_to_http(detail), detail=detail) from exc
    return LocalProductOut(**row)


@router.delete("/products/{product_id}", response_model=AdminActionOut)
def api_admin_delete_local_product(
    product_id: int,
    x_admin_token: str | None = Header(default=None),
) -> AdminActionOut:
    token = require_admin_token(x_admin_token)
    try:
        row = delete_admin_local_product(token, product_id)
    except ValueError as exc:
        detail = str(exc)
        raise HTTPException(status_code=map_admin_error_to_http(detail), detail=detail) from exc
    return AdminActionOut(**row)


@router.post("/villager-identities/{user_id}/unbind", response_model=AdminActionOut)
def api_admin_unbind_villager_identity(
    user_id: int,
    payload: AdminVillagerIdentityUnbindIn,
    x_admin_token: str | None = Header(default=None),
) -> AdminActionOut:
    token = require_admin_token(x_admin_token)
    try:
        row = unbind_admin_villager_identity(token, user_id, reason=payload.reason)
    except ValueError as exc:
        detail = str(exc)
        raise HTTPException(status_code=map_admin_error_to_http(detail), detail=detail) from exc
    return AdminActionOut(**row)


@router.post("/villager-identities/{user_id}/rebind", response_model=AdminVillagerIdentityOut)
def api_admin_rebind_villager_identity(
    user_id: int,
    payload: AdminVillagerIdentityRebindIn,
    x_admin_token: str | None = Header(default=None),
) -> AdminVillagerIdentityOut:
    token = require_admin_token(x_admin_token)
    try:
        row = rebind_admin_villager_identity(
            token,
            user_id,
            real_name=payload.real_name,
            id_card_number=payload.id_card_number,
        )
    except ValueError as exc:
        detail = str(exc)
        raise HTTPException(status_code=map_admin_error_to_http(detail), detail=detail) from exc
    return AdminVillagerIdentityOut(**row)
