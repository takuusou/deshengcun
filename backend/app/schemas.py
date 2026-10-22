from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class NoticeCreate(BaseModel):
    title: str = Field(min_length=1, max_length=100)
    content: str = Field(min_length=1, max_length=5000)
    publisher: str = Field(min_length=1, max_length=50)
    photo_urls: list[str] = Field(default_factory=list)
    is_home_top: bool = False


class NoticeOut(BaseModel):
    id: int
    title: str
    content: str
    publisher: str
    photo_urls: list[str]
    is_home_top: bool
    created_at: str


class NoticeSubscriptionStatusOut(BaseModel):
    available: bool
    is_enabled: bool
    template_id: str = ""
    template_title: str = ""
    current_status: str = "unknown"
    button_text: str = "订阅服务消息"
    prompt_title: str = "开启村务通知提醒"
    prompt_content: str = ""
    updated_at: str = ""


class NoticeSubscriptionRecordIn(BaseModel):
    scene: str = Field(default="manual", max_length=40)
    template_statuses: dict[str, str] = Field(default_factory=dict)
    err_msg: str = Field(default="", max_length=200)


class NoticeDetailOut(BaseModel):
    id: int
    title: str
    content: str
    publisher: str
    photo_urls: list[str]
    is_home_top: bool
    created_at: str


class OpenItemFieldOut(BaseModel):
    label: str
    value: str


class OpenItemOut(BaseModel):
    id: int
    section_key: str
    title: str
    summary: str
    sort_order: int
    photo_urls: list[str]
    updated_at: str


class OpenItemDetailOut(BaseModel):
    id: int
    section_key: str
    title: str
    summary: str
    content: str
    sort_order: int
    photo_urls: list[str]
    updated_at: str
    fields: list[OpenItemFieldOut]


class GovServiceOut(BaseModel):
    id: int
    service_key: str
    title: str
    subtitle: str
    category: str
    icon_emoji: str
    theme_color: str
    detail_type: str
    action_label: str
    is_enabled: bool
    sort_order: int


class GovServiceDetailOut(BaseModel):
    id: int
    service_key: str
    title: str
    subtitle: str
    category: str
    icon_emoji: str
    theme_color: str
    contact_name: str
    contact_phone: str
    intro: str
    detail_type: str
    detail_payload: dict[str, Any]
    action_label: str
    is_enabled: bool
    sort_order: int
    updated_at: str


class GovServiceUpdateIn(BaseModel):
    title: str = Field(min_length=1, max_length=60)
    subtitle: str = Field(default="", max_length=120)
    category: str = Field(default="government", max_length=40)
    icon_emoji: str = Field(default="", max_length=20)
    theme_color: str = Field(default="", max_length=20)
    contact_name: str = Field(default="", max_length=50)
    contact_phone: str = Field(default="", max_length=20)
    intro: str = Field(default="", max_length=2000)
    detail_type: str = Field(default="info_apply", max_length=40)
    detail_payload: dict[str, Any] = Field(default_factory=dict)
    action_label: str = Field(default="", max_length=30)
    is_enabled: bool = True
    sort_order: int = Field(default=0, ge=0, le=1000)


class GovServiceApplicationCreateIn(BaseModel):
    service_id: int = Field(gt=0)
    applicant_name: str = Field(default="", max_length=50)
    applicant_phone: str = Field(default="", max_length=20)
    selected_option: str = Field(default="", max_length=120)
    note: str = Field(default="", max_length=2000)
    supporting_photo_urls: list[str] = Field(default_factory=list)
    extra_fields: dict[str, Any] = Field(default_factory=dict)


class GovServiceApplicationUpdateIn(BaseModel):
    status: Literal["pending", "processing", "resolved", "rejected", "closed"]
    cadre_reply: str = Field(default="", max_length=2000)
    reply_photo_urls: list[str] = Field(default_factory=list)


class GovServiceApplicationOut(BaseModel):
    id: int
    service_id: int
    service_key: str
    service_title: str
    user_id: int
    applicant_name: str
    applicant_phone: str
    selected_option: str
    note: str
    supporting_photo_urls: list[str]
    extra_fields: dict[str, Any]
    reply_photo_urls: list[str]
    status: str
    cadre_reply: str
    handled_by: str
    created_at: str
    updated_at: str
    handled_at: str
    village_group: str = ""


class TrainingProgramCreate(BaseModel):
    title: str = Field(min_length=1, max_length=100)
    schedule_text: str = Field(default="", max_length=120)
    location: str = Field(default="", max_length=120)
    target: str = Field(default="", max_length=200)
    signup_deadline: str = Field(default="", max_length=20)
    end_date: str = Field(default="", max_length=20)
    contact_phone: str = Field(default="", max_length=20)
    status: Literal["open", "ended"] = "open"


class TrainingProgramOut(BaseModel):
    id: int
    title: str
    schedule_text: str
    location: str
    target: str
    signup_deadline: str
    end_date: str
    contact_phone: str
    status: str
    status_label: str
    is_open: bool
    is_ended: bool
    days_remaining: int | None = None
    deadline_text: str
    created_at: str
    updated_at: str
    signup_count: int
    signed_up: bool = False


class TrainingSignupCreate(BaseModel):
    name: str = Field(min_length=1, max_length=50)
    phone: str = Field(min_length=1, max_length=20)


class TrainingSignupOut(BaseModel):
    id: int
    program_id: int
    created_at: str


class TrainingSignupAdminOut(BaseModel):
    id: int
    program_id: int
    name: str
    phone: str
    openid: str
    created_at: str


class VolunteerActivityCreate(BaseModel):
    title: str = Field(min_length=1, max_length=100)
    schedule_text: str = Field(default="", max_length=120)
    location: str = Field(default="", max_length=120)
    target: str = Field(default="", max_length=200)
    detail: str = Field(default="", max_length=2000)
    signup_deadline: str = Field(default="", max_length=20)
    end_date: str = Field(default="", max_length=20)
    contact_phone: str = Field(default="", max_length=20)
    status: Literal["open", "ended"] = "open"


class VolunteerActivityOut(BaseModel):
    id: int
    title: str
    schedule_text: str
    location: str
    target: str
    detail: str
    signup_deadline: str
    end_date: str
    contact_phone: str
    status: str
    status_label: str
    is_open: bool
    is_ended: bool
    days_remaining: int | None = None
    deadline_text: str
    created_at: str
    updated_at: str
    signup_count: int
    signed_up: bool = False


class VolunteerActivitySignupCreate(BaseModel):
    name: str = Field(min_length=1, max_length=50)
    phone: str = Field(min_length=1, max_length=20)


class VolunteerActivitySignupOut(BaseModel):
    id: int
    activity_id: int
    created_at: str


class VolunteerActivitySignupAdminOut(BaseModel):
    id: int
    activity_id: int
    name: str
    phone: str
    openid: str
    created_at: str


class ProposalCreateIn(BaseModel):
    content: str = Field(min_length=1, max_length=500)


class ProposalSubmitOut(BaseModel):
    id: int
    created_at: str


class ProposalStatusOut(BaseModel):
    submitted_today: bool


class LocalProductCreateIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    subtitle: str = Field(default="", max_length=255)
    cover_url: str = Field(default="", max_length=2048)
    detail_img_url: str = Field(default="", max_length=2048)
    history: str = Field(default="", max_length=5000)
    craft: str = Field(default="", max_length=5000)
    flavor: str = Field(default="", max_length=5000)
    sort_order: int = Field(default=0, ge=0, le=9999)


class LocalProductOut(BaseModel):
    id: int
    name: str
    subtitle: str
    cover_url: str
    detail_img_url: str
    history: str
    craft: str
    flavor: str
    sort_order: int
    created_at: str
    updated_at: str


class ProposalOut(BaseModel):
    id: int
    content: str
    villager_name: str
    user_openid: str
    created_at: str


class LedgerCreate(BaseModel):
    category: str = Field(min_length=1, max_length=50)
    content: str = Field(min_length=1, max_length=5000)
    status: str = Field(min_length=1, max_length=30)
    owner: str = Field(min_length=1, max_length=50)
    photo_urls: list[str] = Field(default_factory=list)


class LedgerOut(BaseModel):
    id: int
    category: str
    content: str
    status: str
    owner: str
    photo_urls: list[str]
    created_at: str


class WechatLoginIn(BaseModel):
    code: str = Field(min_length=1, max_length=256)
    nickname: str = Field(default="", max_length=64)
    avatar_url: str = Field(default="", max_length=512)


class CadreLoginIn(BaseModel):
    manager_name: str = Field(min_length=1, max_length=64)
    manager_password: str = Field(min_length=6, max_length=128)


class BindPhoneIn(BaseModel):
    phone_code: str = Field(default="", max_length=256)


class RealnameSubmitIn(BaseModel):
    real_name: str = Field(min_length=1, max_length=50)
    id_card_number: str = Field(min_length=8, max_length=32)


class UploadImageInlineIn(BaseModel):
    scene: str = Field(default="", max_length=32)
    content_type: str = Field(default="", max_length=64)
    data_base64: str = Field(min_length=1, max_length=16_000_000)


class UploadImageCloudFileIn(BaseModel):
    scene: str = Field(default="", max_length=32)
    source_url: str = Field(min_length=1, max_length=4096)
    content_type: str = Field(default="", max_length=64)


class UploadImageOut(BaseModel):
    url: str
    filename: str
    size: int
    content_type: str


class VillageMetricIn(BaseModel):
    metric_key: str = Field(default="", max_length=64)
    metric_label: str = Field(min_length=1, max_length=40)
    metric_value: str = Field(min_length=1, max_length=40)


class VillageMetricOut(BaseModel):
    metric_key: str
    metric_label: str
    metric_value: str
    sort_order: int
    updated_at: str


class VillageMetricsUpdateIn(BaseModel):
    items: list[VillageMetricIn] = Field(min_length=1, max_length=30)


class VillageOpenProfileUpdateIn(BaseModel):
    village_intro: str = Field(default="", max_length=2000)
    village_photo_url: str = Field(default="", max_length=1000)


class VillageOpenProfileOut(BaseModel):
    village_groups: str
    households: str
    population: str
    party_members: str
    village_intro: str
    village_photo_url: str


class VillagerRequestCreateIn(BaseModel):
    request_type: Literal["complaint", "service", "dibao", "tekun"] = "service"
    title: str = Field(min_length=1, max_length=100)
    content: str = Field(min_length=1, max_length=3000)
    contact_phone: str = Field(default="", max_length=20)
    photo_urls: list[str] = Field(default_factory=list)


class VillagerRequestUpdateIn(BaseModel):
    status: Literal["pending", "processing", "resolved", "closed"]
    reply_text: str = Field(default="", max_length=2000)
    reply_photo_urls: list[str] = Field(default_factory=list)


class VillagerRequestOut(BaseModel):
    id: int
    user_id: int
    request_type: Literal["complaint", "service", "dibao", "tekun"]
    title: str
    content: str
    contact_phone: str
    reporter_name: str
    photo_urls: list[str]
    reply_photo_urls: list[str]
    status: str
    reply_text: str
    handled_by: str
    village_group: str = ""
    created_at: str
    updated_at: str
    handled_at: str


class AuthUserOut(BaseModel):
    id: int
    nickname: str
    avatar_url: str
    phone: str
    phone_masked: str = ""
    phone_bound: bool
    phone_verified_at: str
    real_name: str
    gender: str
    id_card_masked: str
    id_card_number: str = ""
    birth_date: str = ""
    age: int | None = None
    role: Literal["villager", "cadre"]
    cadre_eligible: bool
    cadre_role_level: str
    cadre_password_set: bool
    realname_status: str
    auth_status: str
    roster_match_status: str
    village_group: str
    created_at: str
    updated_at: str

class LoginOut(BaseModel):
    token: str
    expires_at: str
    user: AuthUserOut


class CadreAccessStatusOut(BaseModel):
    cadre_eligible: bool
    cadre_role_level: str
    password_set: bool
    session_active: bool
    session_expires_at: str = ""
    locked_until: str = ""


class CadreAccessPasswordIn(BaseModel):
    password: str = Field(min_length=8, max_length=128)


class CadreAccessVerifyIn(BaseModel):
    password: str = Field(min_length=1, max_length=128)


class CadreAccessVerifyOut(BaseModel):
    token: str
    expires_at: str
    status: Literal["ok"] = "ok"


class PrivacyPolicyOut(BaseModel):
    version: str
    title: str
    content: str
    updated_at: str
    required_consents: list[str]


class PrivacyConsentIn(BaseModel):
    policy_version: str = Field(min_length=3, max_length=40)
    consent_types: list[
        Literal["privacy_policy", "sensitive_identity"]
    ] = Field(min_length=1)


class PrivacyConsentItemOut(BaseModel):
    consent_type: str
    status: str
    policy_version: str
    updated_at: str


class PrivacyConsentOut(BaseModel):
    items: list[PrivacyConsentItemOut]


class PrivacyWithdrawIn(BaseModel):
    reason: str = Field(default="", max_length=200)


class ActionResultOut(BaseModel):
    status: str
    message: str


class RosterImportOut(BaseModel):
    batch_id: int
    filename: str
    imported_count: int
    skipped_count: int
    created_at: str


class RosterImportBatchOut(BaseModel):
    id: int
    filename: str
    imported_by: str
    imported_count: int
    skipped_count: int
    created_at: str
