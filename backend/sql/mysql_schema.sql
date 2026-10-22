CREATE TABLE IF NOT EXISTS notices (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    title VARCHAR(255) NOT NULL,
    content LONGTEXT NOT NULL,
    publisher VARCHAR(120) NOT NULL,
    photo_urls LONGTEXT NULL,
    is_home_top TINYINT(1) NOT NULL DEFAULT 0,
    created_at VARCHAR(40) NOT NULL,
    KEY idx_notices_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS meetings (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    topic VARCHAR(255) NOT NULL,
    summary LONGTEXT NOT NULL,
    owner VARCHAR(120) NOT NULL,
    meeting_time VARCHAR(40) NOT NULL,
    photo_urls LONGTEXT NULL,
    created_at VARCHAR(40) NOT NULL,
    KEY idx_meetings_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS volunteer_events (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    title VARCHAR(255) NOT NULL,
    detail LONGTEXT NOT NULL,
    event_time VARCHAR(40) NOT NULL,
    quota INT NOT NULL,
    created_by VARCHAR(120) NOT NULL,
    photo_urls LONGTEXT NULL,
    created_at VARCHAR(40) NOT NULL,
    KEY idx_volunteer_events_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS volunteer_signups (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    event_id BIGINT NOT NULL,
    participant_openid VARCHAR(120) NOT NULL,
    participant_name VARCHAR(60) NOT NULL DEFAULT '',
    created_at VARCHAR(40) NOT NULL,
    UNIQUE KEY uq_volunteer_signups_event_openid (event_id, participant_openid),
    KEY idx_volunteer_signups_event_openid (event_id, participant_openid)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS training_programs (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    title VARCHAR(120) NOT NULL,
    schedule_text VARCHAR(160) NOT NULL DEFAULT '',
    location VARCHAR(160) NOT NULL DEFAULT '',
    target VARCHAR(255) NOT NULL DEFAULT '',
    signup_deadline VARCHAR(20) NOT NULL DEFAULT '',
    end_date VARCHAR(20) NOT NULL DEFAULT '',
    contact_phone VARCHAR(32) NOT NULL DEFAULT '',
    status VARCHAR(20) NOT NULL DEFAULT 'open',
    created_at VARCHAR(40) NOT NULL,
    updated_at VARCHAR(40) NOT NULL,
    KEY idx_training_programs_dates (status, signup_deadline, end_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS training_signups (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    program_id BIGINT NOT NULL,
    name VARCHAR(60) NOT NULL DEFAULT '',
    phone VARCHAR(32) NOT NULL DEFAULT '',
    phone_ciphertext LONGTEXT NULL,
    phone_hash CHAR(64) NOT NULL DEFAULT '',
    phone_masked VARCHAR(32) NOT NULL DEFAULT '',
    openid VARCHAR(120) NOT NULL DEFAULT '',
    created_at VARCHAR(40) NOT NULL,
    UNIQUE KEY uq_training_signups_program_phone (program_id, phone),
    UNIQUE KEY uq_training_signups_openid_program (openid, program_id),
    KEY idx_training_signups_program_phone (program_id, phone)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS volunteer_activities (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    title VARCHAR(120) NOT NULL,
    schedule_text VARCHAR(160) NOT NULL DEFAULT '',
    location VARCHAR(160) NOT NULL DEFAULT '',
    target VARCHAR(255) NOT NULL DEFAULT '',
    detail LONGTEXT NULL,
    signup_deadline VARCHAR(20) NOT NULL DEFAULT '',
    end_date VARCHAR(20) NOT NULL DEFAULT '',
    contact_phone VARCHAR(32) NOT NULL DEFAULT '',
    status VARCHAR(20) NOT NULL DEFAULT 'open',
    created_at VARCHAR(40) NOT NULL,
    updated_at VARCHAR(40) NOT NULL,
    KEY idx_volunteer_activities_dates (status, signup_deadline, end_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS volunteer_activity_signups (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    activity_id BIGINT NOT NULL,
    name VARCHAR(60) NOT NULL DEFAULT '',
    phone VARCHAR(32) NOT NULL DEFAULT '',
    phone_ciphertext LONGTEXT NULL,
    phone_hash CHAR(64) NOT NULL DEFAULT '',
    phone_masked VARCHAR(32) NOT NULL DEFAULT '',
    openid VARCHAR(120) NOT NULL DEFAULT '',
    created_at VARCHAR(40) NOT NULL,
    UNIQUE KEY uq_volunteer_activity_signups_activity_phone (activity_id, phone),
    UNIQUE KEY uq_volunteer_activity_signups_openid_activity (openid, activity_id),
    KEY idx_volunteer_activity_signups_activity_phone (activity_id, phone)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS proposals (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    content LONGTEXT NOT NULL,
    user_openid VARCHAR(120) NOT NULL DEFAULT '',
    villager_name VARCHAR(60) NOT NULL DEFAULT '',
    created_at VARCHAR(40) NOT NULL,
    KEY idx_proposals_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS local_product (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(120) NOT NULL,
    subtitle VARCHAR(255) NOT NULL DEFAULT '',
    cover_url LONGTEXT NULL,
    detail_img_url LONGTEXT NULL,
    history LONGTEXT NULL,
    craft LONGTEXT NULL,
    flavor LONGTEXT NULL,
    sort_order INT NOT NULL DEFAULT 0,
    created_at VARCHAR(40) NOT NULL,
    updated_at VARCHAR(40) NOT NULL,
    KEY idx_local_product_sort (sort_order, id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS users (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    openid VARCHAR(120) NOT NULL,
    unionid VARCHAR(120) NOT NULL DEFAULT '',
    nickname VARCHAR(120) NOT NULL DEFAULT '',
    avatar_url VARCHAR(500) NOT NULL DEFAULT '',
    phone VARCHAR(32) NOT NULL DEFAULT '',
    phone_ciphertext LONGTEXT NULL,
    phone_hash CHAR(64) NOT NULL DEFAULT '',
    phone_masked VARCHAR(32) NOT NULL DEFAULT '',
    phone_last4 VARCHAR(8) NOT NULL DEFAULT '',
    phone_bound TINYINT(1) NOT NULL DEFAULT 0,
    phone_verified_at VARCHAR(40) NOT NULL DEFAULT '',
    real_name VARCHAR(60) NOT NULL DEFAULT '',
    gender VARCHAR(12) NOT NULL DEFAULT '',
    id_card_masked VARCHAR(40) NOT NULL DEFAULT '',
    id_card_last4 VARCHAR(8) NOT NULL DEFAULT '',
    id_card_hash CHAR(64) NOT NULL DEFAULT '',
    id_card_encrypted LONGTEXT NULL,
    face_photo_url VARCHAR(500) NOT NULL DEFAULT '',
    face_verified_at VARCHAR(40) NOT NULL DEFAULT '',
    role VARCHAR(20) NOT NULL DEFAULT 'villager',
    role_request VARCHAR(20) NOT NULL DEFAULT 'villager',
    realname_status VARCHAR(20) NOT NULL DEFAULT 'unsubmitted',
    face_status VARCHAR(20) NOT NULL DEFAULT 'unsubmitted',
    auth_status VARCHAR(20) NOT NULL DEFAULT 'unverified',
    roster_match_status VARCHAR(20) NOT NULL DEFAULT 'unmatched',
    village_group VARCHAR(80) NOT NULL DEFAULT '',
    created_at VARCHAR(40) NOT NULL,
    updated_at VARCHAR(40) NOT NULL,
    UNIQUE KEY uq_users_openid (openid),
    KEY idx_users_unionid (unionid),
    KEY idx_users_phone_hash (phone_hash),
    KEY idx_users_id_card_hash (id_card_hash)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS notice_subscriptions (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    user_id BIGINT NOT NULL,
    openid VARCHAR(120) NOT NULL DEFAULT '',
    template_id VARCHAR(120) NOT NULL DEFAULT '',
    subscription_status VARCHAR(32) NOT NULL DEFAULT 'unknown',
    is_enabled TINYINT(1) NOT NULL DEFAULT 0,
    last_request_scene VARCHAR(40) NOT NULL DEFAULT '',
    last_request_result_json LONGTEXT NULL,
    last_error_code VARCHAR(40) NOT NULL DEFAULT '',
    last_error_message VARCHAR(255) NOT NULL DEFAULT '',
    last_requested_at VARCHAR(40) NOT NULL DEFAULT '',
    last_subscribed_at VARCHAR(40) NOT NULL DEFAULT '',
    last_unsubscribed_at VARCHAR(40) NOT NULL DEFAULT '',
    created_at VARCHAR(40) NOT NULL,
    updated_at VARCHAR(40) NOT NULL,
    UNIQUE KEY uq_notice_subscriptions_user (user_id),
    KEY idx_notice_subscriptions_enabled (is_enabled, template_id, updated_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS notice_delivery_logs (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    notice_id BIGINT NOT NULL,
    user_id BIGINT NOT NULL,
    openid VARCHAR(120) NOT NULL DEFAULT '',
    template_id VARCHAR(120) NOT NULL DEFAULT '',
    delivery_status VARCHAR(20) NOT NULL DEFAULT 'pending',
    errcode INT NOT NULL DEFAULT 0,
    errmsg VARCHAR(255) NOT NULL DEFAULT '',
    response_json LONGTEXT NULL,
    sent_at VARCHAR(40) NOT NULL DEFAULT '',
    created_at VARCHAR(40) NOT NULL,
    updated_at VARCHAR(40) NOT NULL,
    UNIQUE KEY uq_notice_delivery_logs_notice_user_template (notice_id, user_id, template_id),
    KEY idx_notice_delivery_logs_notice_user (notice_id, user_id, template_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS ledgers (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    category VARCHAR(80) NOT NULL,
    content LONGTEXT NOT NULL,
    status VARCHAR(20) NOT NULL,
    owner VARCHAR(120) NOT NULL,
    photo_urls LONGTEXT NULL,
    created_at VARCHAR(40) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS auth_sessions (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    user_id BIGINT NOT NULL,
    token VARCHAR(128) NOT NULL,
    created_at VARCHAR(40) NOT NULL,
    expires_at VARCHAR(40) NOT NULL,
    UNIQUE KEY uq_auth_sessions_token (token),
    KEY idx_auth_sessions_expires_at (expires_at),
    KEY idx_auth_sessions_user_id (user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS cadre_managers (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    manager_name VARCHAR(120) NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    password_salt VARCHAR(255) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'active',
    created_at VARCHAR(40) NOT NULL,
    updated_at VARCHAR(40) NOT NULL,
    UNIQUE KEY uq_cadre_managers_name (manager_name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS cadre_authorizations (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    real_name VARCHAR(60) NOT NULL,
    office_title VARCHAR(60) NOT NULL DEFAULT '',
    user_id BIGINT NULL,
    openid VARCHAR(120) NULL,
    unionid VARCHAR(120) NULL,
    role_level VARCHAR(20) NOT NULL DEFAULT 'cadre',
    can_export_full_id TINYINT(1) NOT NULL DEFAULT 0,
    status VARCHAR(20) NOT NULL DEFAULT 'active',
    last_bound_at VARCHAR(40) NOT NULL DEFAULT '',
    created_at VARCHAR(40) NOT NULL,
    updated_at VARCHAR(40) NOT NULL,
    UNIQUE KEY uq_cadre_auth_real_name (real_name),
    UNIQUE KEY uq_cadre_auth_user_id (user_id),
    UNIQUE KEY uq_cadre_auth_openid (openid),
    UNIQUE KEY uq_cadre_auth_unionid (unionid),
    KEY idx_cadre_authorizations_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS admin_users (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    login_name VARCHAR(50) NOT NULL,
    display_name VARCHAR(50) NOT NULL,
    real_name VARCHAR(50) NOT NULL,
    cadre_authorization_id BIGINT NOT NULL,
    role_key VARCHAR(20) NOT NULL DEFAULT 'cadre',
    password_hash VARCHAR(255) NOT NULL,
    password_algorithm VARCHAR(20) NOT NULL DEFAULT 'argon2id',
    status VARCHAR(20) NOT NULL DEFAULT 'active',
    password_reset_required TINYINT(1) NOT NULL DEFAULT 0,
    security_policy_version INT NOT NULL DEFAULT 1,
    mfa_secret_encrypted LONGTEXT NULL,
    mfa_enabled TINYINT(1) NOT NULL DEFAULT 0,
    mfa_enrolled_at VARCHAR(40) NOT NULL DEFAULT '',
    mfa_recovery_codes_hashes LONGTEXT NULL,
    mfa_last_counter BIGINT NOT NULL DEFAULT 0,
    failed_login_count INT NOT NULL DEFAULT 0,
    locked_until VARCHAR(40) NOT NULL DEFAULT '',
    last_login_at VARCHAR(40) NOT NULL DEFAULT '',
    last_login_ip VARCHAR(64) NOT NULL DEFAULT '',
    last_login_user_agent VARCHAR(255) NOT NULL DEFAULT '',
    password_changed_at VARCHAR(40) NOT NULL DEFAULT '',
    created_by_admin_user_id BIGINT NULL,
    updated_by_admin_user_id BIGINT NULL,
    created_at VARCHAR(40) NOT NULL,
    updated_at VARCHAR(40) NOT NULL,
    UNIQUE KEY uq_admin_users_login_name (login_name),
    UNIQUE KEY uq_admin_users_cadre_auth (cadre_authorization_id),
    KEY idx_admin_users_status_role (status, role_key)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS admin_sessions (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    admin_user_id BIGINT NOT NULL,
    token_hash CHAR(64) NOT NULL,
    session_type VARCHAR(20) NOT NULL DEFAULT 'password',
    login_ip VARCHAR(64) NOT NULL DEFAULT '',
    login_user_agent VARCHAR(255) NOT NULL DEFAULT '',
    created_at VARCHAR(40) NOT NULL,
    expires_at VARCHAR(40) NOT NULL,
    last_seen_at VARCHAR(40) NOT NULL,
    revoked_at VARCHAR(40) NOT NULL DEFAULT '',
    UNIQUE KEY uq_admin_sessions_token_hash (token_hash),
    KEY idx_admin_sessions_user_expires (admin_user_id, expires_at),
    KEY idx_admin_sessions_revoked (revoked_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS cadre_stepup_secrets (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    user_id BIGINT NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    password_algorithm VARCHAR(20) NOT NULL DEFAULT 'argon2id',
    failed_count INT NOT NULL DEFAULT 0,
    locked_until VARCHAR(40) NOT NULL DEFAULT '',
    created_at VARCHAR(40) NOT NULL,
    updated_at VARCHAR(40) NOT NULL,
    UNIQUE KEY uq_cadre_stepup_secrets_user (user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS cadre_stepup_sessions (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    user_id BIGINT NOT NULL,
    token VARCHAR(128) NOT NULL,
    created_at VARCHAR(40) NOT NULL,
    expires_at VARCHAR(40) NOT NULL,
    last_used_at VARCHAR(40) NOT NULL,
    revoked_at VARCHAR(40) NOT NULL DEFAULT '',
    UNIQUE KEY uq_cadre_stepup_sessions_token (token),
    KEY idx_cadre_stepup_sessions_expires_at (expires_at),
    KEY idx_cadre_stepup_sessions_user_id (user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS roster_import_batches (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    filename VARCHAR(255) NOT NULL,
    imported_by VARCHAR(120) NOT NULL,
    imported_count INT NOT NULL,
    skipped_count INT NOT NULL,
    created_at VARCHAR(40) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS villager_roster (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    batch_id BIGINT NOT NULL,
    full_name VARCHAR(60) NOT NULL,
    id_last4 VARCHAR(8) NOT NULL,
    id_hash CHAR(64) NOT NULL DEFAULT '',
    group_name VARCHAR(80) NOT NULL DEFAULT '',
    status VARCHAR(20) NOT NULL DEFAULT 'active',
    created_at VARCHAR(40) NOT NULL,
    KEY idx_villager_roster_match (status, full_name, id_hash)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS privacy_consents (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    user_id BIGINT NOT NULL,
    policy_version VARCHAR(40) NOT NULL,
    consent_type VARCHAR(40) NOT NULL,
    status VARCHAR(20) NOT NULL,
    created_at VARCHAR(40) NOT NULL,
    updated_at VARCHAR(40) NOT NULL,
    withdrawn_at VARCHAR(40) NOT NULL DEFAULT '',
    UNIQUE KEY uq_privacy_consents_user_policy_type (user_id, policy_version, consent_type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS audit_logs (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    actor_user_id BIGINT NULL,
    actor_admin_user_id BIGINT NULL,
    actor_type VARCHAR(20) NOT NULL DEFAULT 'villager',
    action VARCHAR(80) NOT NULL,
    target_type VARCHAR(80) NOT NULL,
    target_id VARCHAR(120) NOT NULL DEFAULT '',
    detail_json LONGTEXT NULL,
    ip VARCHAR(64) NOT NULL DEFAULT '',
    user_agent VARCHAR(255) NOT NULL DEFAULT '',
    created_at VARCHAR(40) NOT NULL,
    KEY idx_audit_logs_actor_action (actor_user_id, action, created_at),
    KEY idx_audit_logs_admin_action (actor_admin_user_id, action, created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS village_metrics (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    metric_key VARCHAR(60) NOT NULL,
    metric_label VARCHAR(120) NOT NULL,
    metric_value VARCHAR(255) NOT NULL,
    sort_order INT NOT NULL DEFAULT 0,
    updated_by VARCHAR(120) NOT NULL DEFAULT '',
    created_at VARCHAR(40) NOT NULL,
    updated_at VARCHAR(40) NOT NULL,
    UNIQUE KEY uq_village_metrics_key (metric_key)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS open_profile (
    id BIGINT PRIMARY KEY,
    village_intro LONGTEXT NULL,
    village_photo_url VARCHAR(1000) NOT NULL DEFAULT '',
    updated_by VARCHAR(120) NOT NULL DEFAULT '',
    created_at VARCHAR(40) NOT NULL,
    updated_at VARCHAR(40) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS open_items (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    section_key VARCHAR(40) NOT NULL,
    title VARCHAR(255) NOT NULL,
    summary VARCHAR(500) NOT NULL DEFAULT '',
    fields_json LONGTEXT NULL,
    content LONGTEXT NULL,
    photo_urls LONGTEXT NULL,
    sort_order INT NOT NULL DEFAULT 0,
    created_at VARCHAR(40) NOT NULL,
    updated_at VARCHAR(40) NOT NULL,
    KEY idx_open_items_section_sort (section_key, sort_order, id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS villager_requests (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    user_id BIGINT NOT NULL,
    request_type VARCHAR(40) NOT NULL,
    title VARCHAR(255) NOT NULL,
    content LONGTEXT NOT NULL,
    contact_phone VARCHAR(32) NOT NULL DEFAULT '',
    contact_phone_ciphertext LONGTEXT NULL,
    contact_phone_hash CHAR(64) NOT NULL DEFAULT '',
    contact_phone_masked VARCHAR(32) NOT NULL DEFAULT '',
    reporter_name VARCHAR(60) NOT NULL DEFAULT '',
    reporter_real_name VARCHAR(60) NOT NULL DEFAULT '',
    reporter_id_card_hash CHAR(64) NOT NULL DEFAULT '',
    photo_urls LONGTEXT NULL,
    reply_photo_urls LONGTEXT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    reply_text LONGTEXT NULL,
    handled_by VARCHAR(120) NOT NULL DEFAULT '',
    created_at VARCHAR(40) NOT NULL,
    updated_at VARCHAR(40) NOT NULL,
    handled_at VARCHAR(40) NOT NULL DEFAULT '',
    KEY idx_villager_requests_user_status_created (user_id, status, created_at),
    KEY idx_villager_requests_identity_created (reporter_id_card_hash, reporter_real_name, created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS request_rate_limits (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    scope VARCHAR(80) NOT NULL,
    bucket_key VARCHAR(180) NOT NULL,
    window_start VARCHAR(40) NOT NULL,
    request_count INT NOT NULL DEFAULT 0,
    created_at VARCHAR(40) NOT NULL,
    updated_at VARCHAR(40) NOT NULL,
    UNIQUE KEY uq_request_rate_limits_scope_bucket_window (scope, bucket_key, window_start),
    KEY idx_request_rate_limits_scope_bucket_window (scope, bucket_key, window_start)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS gov_services (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    service_key VARCHAR(80) NOT NULL,
    title VARCHAR(255) NOT NULL,
    subtitle VARCHAR(255) NOT NULL DEFAULT '',
    category VARCHAR(60) NOT NULL DEFAULT 'government',
    icon_emoji VARCHAR(32) NOT NULL DEFAULT '',
    theme_color VARCHAR(32) NOT NULL DEFAULT '',
    contact_name VARCHAR(120) NOT NULL DEFAULT '',
    contact_phone VARCHAR(32) NOT NULL DEFAULT '',
    intro LONGTEXT NULL,
    action_label VARCHAR(80) NOT NULL DEFAULT '',
    detail_type VARCHAR(40) NOT NULL DEFAULT 'info_apply',
    detail_payload LONGTEXT NULL,
    is_enabled TINYINT(1) NOT NULL DEFAULT 1,
    sort_order INT NOT NULL DEFAULT 0,
    created_at VARCHAR(40) NOT NULL,
    updated_at VARCHAR(40) NOT NULL,
    UNIQUE KEY uq_gov_services_service_key (service_key)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS gov_service_applications (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    service_id BIGINT NOT NULL,
    user_id BIGINT NOT NULL,
    service_key VARCHAR(80) NOT NULL,
    service_title VARCHAR(255) NOT NULL,
    applicant_name VARCHAR(60) NOT NULL,
    applicant_phone VARCHAR(32) NOT NULL DEFAULT '',
    applicant_phone_ciphertext LONGTEXT NULL,
    applicant_phone_hash CHAR(64) NOT NULL DEFAULT '',
    applicant_phone_masked VARCHAR(32) NOT NULL DEFAULT '',
    selected_option VARCHAR(255) NOT NULL DEFAULT '',
    note LONGTEXT NULL,
    extra_fields LONGTEXT NULL,
    sensitive_extra_fields_encrypted LONGTEXT NULL,
    applicant_id_card_hash CHAR(64) NOT NULL DEFAULT '',
    application_fingerprint_hash CHAR(64) NOT NULL DEFAULT '',
    reply_photo_urls LONGTEXT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    cadre_reply LONGTEXT NULL,
    handled_by VARCHAR(120) NOT NULL DEFAULT '',
    created_at VARCHAR(40) NOT NULL,
    updated_at VARCHAR(40) NOT NULL,
    handled_at VARCHAR(40) NOT NULL DEFAULT '',
    KEY idx_gov_service_apps_user_status_created (user_id, status, created_at),
    KEY idx_gov_service_apps_service_status_created (service_id, status, created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS villager_registry (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    user_id BIGINT NOT NULL,
    village_name VARCHAR(60) NOT NULL DEFAULT '得胜村',
    group_name VARCHAR(80) NOT NULL DEFAULT '',
    real_name VARCHAR(60) NOT NULL DEFAULT '',
    gender VARCHAR(12) NOT NULL DEFAULT '',
    phone VARCHAR(32) NOT NULL DEFAULT '',
    phone_ciphertext LONGTEXT NULL,
    phone_hash CHAR(64) NOT NULL DEFAULT '',
    phone_masked VARCHAR(32) NOT NULL DEFAULT '',
    phone_last4 VARCHAR(8) NOT NULL DEFAULT '',
    id_card_masked VARCHAR(40) NOT NULL DEFAULT '',
    id_card_last4 VARCHAR(8) NOT NULL DEFAULT '',
    id_card_hash CHAR(64) NOT NULL DEFAULT '',
    id_card_encrypted LONGTEXT NULL,
    face_photo_url VARCHAR(500) NOT NULL DEFAULT '',
    realname_submitted_at VARCHAR(40) NOT NULL DEFAULT '',
    face_verified_at VARCHAR(40) NOT NULL DEFAULT '',
    auth_status VARCHAR(20) NOT NULL DEFAULT 'unverified',
    created_at VARCHAR(40) NOT NULL,
    updated_at VARCHAR(40) NOT NULL,
    UNIQUE KEY uq_villager_registry_user_id (user_id),
    KEY idx_villager_registry_phone_hash (phone_hash)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS stored_files (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    scene VARCHAR(40) NOT NULL,
    filename VARCHAR(180) NOT NULL,
    storage_provider VARCHAR(20) NOT NULL DEFAULT 'local',
    bucket_name VARCHAR(120) NOT NULL DEFAULT '',
    object_key VARCHAR(500) NOT NULL DEFAULT '',
    content_type VARCHAR(120) NOT NULL DEFAULT '',
    size_bytes BIGINT NOT NULL DEFAULT 0,
    sha256_hex CHAR(64) NOT NULL DEFAULT '',
    uploaded_by_user_id BIGINT NULL,
    is_private TINYINT(1) NOT NULL DEFAULT 1,
    source_path VARCHAR(500) NOT NULL DEFAULT '',
    status VARCHAR(20) NOT NULL DEFAULT 'active',
    created_at VARCHAR(40) NOT NULL,
    updated_at VARCHAR(40) NOT NULL,
    UNIQUE KEY uq_stored_files_scene_filename (scene, filename),
    KEY idx_stored_files_scene_filename (scene, filename)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
