from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class AdminAuthUserOut(BaseModel):
    id: int
    login_name: str
    display_name: str
    real_name: str
    office_title: str = ""
    role_key: str
    status: str
    password_reset_required: bool
    mfa_enabled: bool = False
    mfa_setup_required: bool = False
    cadre_authorization_id: int
    cadre_role_level: str
    can_export_full_id: bool
    last_login_at: str


class AdminLoginIn(BaseModel):
    login_name: str = Field(min_length=1, max_length=50)
    password: str = Field(min_length=1, max_length=128)
    mfa_code: str = Field(default="", max_length=32)


class AdminLoginOut(BaseModel):
    token: str
    expires_at: str
    user: AdminAuthUserOut


class AdminChangePasswordIn(BaseModel):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=12, max_length=128)


class AdminMfaSetupOut(BaseModel):
    secret: str
    otpauth_uri: str
    account_label: str
    issuer: str


class AdminMfaConfirmIn(BaseModel):
    code: str = Field(min_length=6, max_length=32)


class AdminMfaConfirmOut(BaseModel):
    status: str
    message: str
    recovery_codes: list[str]
    user: AdminAuthUserOut


class AdminActionOut(BaseModel):
    status: str
    message: str


class AdminPurgeTestDataIn(BaseModel):
    confirm_text: str = Field(min_length=1, max_length=64)


class AdminPurgeTestDataOut(BaseModel):
    status: str
    message: str
    notices_deleted: int = 0
    notice_subscriptions_deleted: int = 0
    notice_delivery_logs_deleted: int = 0
    villager_requests_deleted: int = 0
    gov_service_applications_deleted: int = 0
    meetings_deleted: int = 0
    volunteer_events_deleted: int = 0
    volunteer_signups_deleted: int = 0
    auth_sessions_deleted: int = 0
    privacy_consents_deleted: int = 0
    villager_registry_deleted: int = 0
    villager_users_deleted: int = 0
    villager_users_scrubbed: int = 0
    stored_files_deleted: int = 0
    audit_logs_deleted: int = 0
    preserved_cadre_user_ids: list[int] = Field(default_factory=list)


class AdminNoticeDetailOut(BaseModel):
    id: int
    title: str
    content: str
    publisher: str
    photo_urls: list[str]
    is_home_top: bool
    created_at: str


class AdminOpenItemFieldIn(BaseModel):
    label: str = Field(min_length=1, max_length=40)
    value: str = Field(default="", max_length=500)


class AdminOpenItemUpsertIn(BaseModel):
    section_key: str = Field(min_length=1, max_length=32)
    title: str = Field(min_length=1, max_length=100)
    summary: str = Field(default="", max_length=300)
    content: str = Field(default="", max_length=5000)
    fields: list[AdminOpenItemFieldIn] = Field(default_factory=list, max_length=60)
    photo_urls: list[str] = Field(default_factory=list)
    sort_order: int = Field(default=0, ge=0, le=1000)


class AdminCadreAuthorizationOut(BaseModel):
    id: int
    real_name: str
    office_title: str = ""
    user_id: int
    openid_bound: bool
    unionid_bound: bool
    role_level: str
    can_export_full_id: bool
    is_default: bool = False
    status: str
    last_bound_at: str
    admin_account_exists: bool
    admin_login_name: str
    admin_display_name: str
    admin_role_key: str
    admin_status: str
    admin_locked_until: str
    admin_last_login_at: str


class AdminCadreAuthorizationUpdateIn(BaseModel):
    office_title: str = Field(default="", max_length=60)
    role_level: Literal["super_admin", "cadre"] = "cadre"
    can_export_full_id: bool = False
    status: Literal["active", "disabled"] = "active"
    admin_role_key: Literal["super_admin", "cadre", "readonly"] = "cadre"


class AdminCadreAuthorizationCreateIn(BaseModel):
    real_name: str = Field(min_length=1, max_length=50)
    office_title: str = Field(default="", max_length=60)
    role_level: Literal["super_admin", "cadre"] = "cadre"
    can_export_full_id: bool = False
    status: Literal["active", "disabled"] = "active"
    # 可选：登记的同时为该干部创建后台登录账号
    create_account: bool = False
    login_name: str = Field(default="", max_length=50)
    password: str = Field(default="", max_length=128)
    admin_role_key: Literal["super_admin", "cadre", "readonly"] = "cadre"
    force_reset: bool = True


class AdminCadreAccountCreateIn(BaseModel):
    login_name: str = Field(min_length=1, max_length=50)
    password: str = Field(min_length=12, max_length=128)
    display_name: str = Field(default="", max_length=50)
    role_key: Literal["super_admin", "cadre", "readonly"] = "cadre"
    force_reset: bool = False


class AdminCadreAccountResetPasswordIn(BaseModel):
    new_password: str = Field(min_length=12, max_length=128)
    force_reset: bool = True


class AdminAuditLogOut(BaseModel):
    id: int
    actor_type: str
    actor_user_id: int | None = None
    actor_admin_user_id: int | None = None
    actor_display_name: str
    action: str
    target_type: str
    target_id: str
    detail_preview: str
    ip: str
    user_agent: str
    created_at: str


class AdminAuditLogDetailOut(BaseModel):
    id: int
    actor_type: str
    actor_user_id: int | None = None
    actor_admin_user_id: int | None = None
    actor_display_name: str
    action: str
    target_type: str
    target_id: str
    detail_json: dict[str, Any]
    ip: str
    user_agent: str
    created_at: str


class AdminVillagerIdentityOut(BaseModel):
    user_id: int
    real_name: str
    gender: str = ""
    phone_masked: str
    id_card_masked: str
    auth_status: str
    realname_status: str
    roster_match_status: str
    village_group: str
    age: int | None = None
    is_turning_60_this_year: bool = False
    is_age_60_plus: bool = False
    is_age_80_plus: bool = False
    updated_at: str
    realname_submitted_at: str = ""


class AdminVillagerIdentitySummaryOut(BaseModel):
    total_count: int
    matched_count: int
    grouped_count: int
    turning_60_this_year_count: int = 0
    age_60_plus_count: int
    age_80_plus_count: int


class AdminVillagerIdentityUnbindIn(BaseModel):
    reason: str = Field(default="", max_length=200)


class AdminVillagerIdentityRebindIn(BaseModel):
    real_name: str = Field(min_length=1, max_length=50)
    id_card_number: str = Field(min_length=8, max_length=32)
