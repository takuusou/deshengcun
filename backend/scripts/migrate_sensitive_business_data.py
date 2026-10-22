from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path
import sys
from typing import Any


ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.db import DB_BACKEND, get_connection, init_db
from app.secret_protection import keyed_lookup_hash, unprotect_text
from app.services import (
    _build_certificate_application_fingerprint,
    _parse_json_object,
    _protect_gov_application_extra_fields,
    _protected_business_phone_fields,
    _json_text,
    decrypt_id_card_number,
    is_valid_phone,
    mask_id_card,
)


def _migrate_phone_table(
    conn: Any,
    *,
    table_name: str,
    id_column: str,
    phone_column: str,
    ciphertext_column: str,
    hash_column: str,
    masked_column: str,
    purpose: str,
    legacy_value: str,
) -> tuple[int, int]:
    rows = conn.execute(
        f"""
        SELECT {id_column} AS row_id, {phone_column} AS phone
        FROM {table_name}
        WHERE COALESCE({ciphertext_column}, '') = ''
          AND COALESCE({phone_column}, '') != ''
        """
    ).fetchall()
    migrated = 0
    skipped = 0
    for row in rows:
        phone = str(row["phone"] or "").strip()
        if not is_valid_phone(phone):
            skipped += 1
            continue
        protected = _protected_business_phone_fields(phone, purpose=purpose)
        stored_legacy_value = protected[legacy_value]
        conn.execute(
            f"""
            UPDATE {table_name}
            SET {phone_column} = ?, {ciphertext_column} = ?, {hash_column} = ?, {masked_column} = ?
            WHERE {id_column} = ?
            """,
            (
                stored_legacy_value,
                protected["ciphertext"],
                protected["lookup_hash"],
                protected["masked"],
                row["row_id"],
            ),
        )
        migrated += 1
    return migrated, skipped


def _remask_villager_identity_data(conn: Any) -> dict[str, int]:
    rows = conn.execute(
        """
        SELECT id, id_card_masked, id_card_last4, id_card_encrypted
        FROM users
        WHERE COALESCE(id_card_masked, '') != ''
           OR COALESCE(id_card_last4, '') != ''
           OR COALESCE(id_card_encrypted, '') != ''
        ORDER BY id ASC
        """
    ).fetchall()
    user_masks_updated = 0
    registry_masks_updated = 0
    decrypt_failures = 0
    for row in rows:
        stored_mask = str(row["id_card_masked"] or "")
        mask_source = stored_mask
        encrypted_value = str(row["id_card_encrypted"] or "").strip()
        if encrypted_value:
            try:
                mask_source = decrypt_id_card_number(encrypted_value)
            except ValueError:
                decrypt_failures += 1
        expected_mask = mask_id_card(mask_source)
        user_id = int(row["id"] or 0)
        if expected_mask != stored_mask or str(row["id_card_last4"] or ""):
            conn.execute(
                "UPDATE users SET id_card_masked = ?, id_card_last4 = '' WHERE id = ?",
                (expected_mask, user_id),
            )
            user_masks_updated += 1

        registry_row = conn.execute(
            "SELECT id_card_masked, id_card_last4 FROM villager_registry WHERE user_id = ? LIMIT 1",
            (user_id,),
        ).fetchone()
        if registry_row is not None and (
            str(registry_row["id_card_masked"] or "") != expected_mask
            or str(registry_row["id_card_last4"] or "")
        ):
            conn.execute(
                "UPDATE villager_registry SET id_card_masked = ?, id_card_last4 = '' WHERE user_id = ?",
                (expected_mask, user_id),
            )
            registry_masks_updated += 1

    remaining_registry_rows = conn.execute(
        """
        SELECT user_id, id_card_masked, id_card_last4
        FROM villager_registry
        WHERE COALESCE(id_card_masked, '') != '' OR COALESCE(id_card_last4, '') != ''
        """
    ).fetchall()
    for row in remaining_registry_rows:
        stored_mask = str(row["id_card_masked"] or "")
        expected_mask = mask_id_card(stored_mask)
        if expected_mask == stored_mask and not str(row["id_card_last4"] or ""):
            continue
        conn.execute(
            "UPDATE villager_registry SET id_card_masked = ?, id_card_last4 = '' WHERE user_id = ?",
            (expected_mask, int(row["user_id"] or 0)),
        )
        registry_masks_updated += 1

    roster_last4_rows = conn.execute(
        "SELECT COUNT(1) AS cnt FROM villager_roster WHERE COALESCE(id_last4, '') != ''"
    ).fetchone()
    roster_last4_cleared = int(roster_last4_rows["cnt"] or 0) if roster_last4_rows else 0
    if roster_last4_cleared:
        conn.execute("UPDATE villager_roster SET id_last4 = '' WHERE COALESCE(id_last4, '') != ''")

    return {
        "villager_identity_masks_updated": user_masks_updated,
        "villager_registry_masks_updated": registry_masks_updated,
        "villager_identity_decrypt_failures": decrypt_failures,
        "roster_id_last4_cleared": roster_last4_cleared,
    }


def _remove_identity_suffix_from_audit_logs(conn: Any) -> int:
    rows = conn.execute(
        """
        SELECT id, detail_json
        FROM audit_logs
        WHERE detail_json LIKE '%id_last4%' OR detail_json LIKE '%id_card_last4%'
        """
    ).fetchall()
    updated = 0
    for row in rows:
        detail = _parse_json_object(row["detail_json"])
        changed = False
        for key in ("id_last4", "id_card_last4"):
            if key in detail:
                detail.pop(key, None)
                changed = True
        if not changed:
            continue
        conn.execute(
            "UPDATE audit_logs SET detail_json = ? WHERE id = ?",
            (_json_text(detail), row["id"]),
        )
        updated += 1
    return updated


def migrate_sensitive_business_data(*, dry_run: bool = False) -> dict[str, int]:
    init_db()
    conn = get_connection()
    stats: dict[str, int] = {}
    try:
        stats.update(_remask_villager_identity_data(conn))
        stats["audit_identity_suffixes_removed"] = _remove_identity_suffix_from_audit_logs(conn)

        migrated, skipped = _migrate_phone_table(
            conn,
            table_name="villager_requests",
            id_column="id",
            phone_column="contact_phone",
            ciphertext_column="contact_phone_ciphertext",
            hash_column="contact_phone_hash",
            masked_column="contact_phone_masked",
            purpose="villager_request_phone",
            legacy_value="masked",
        )
        stats["villager_request_phones_migrated"] = migrated
        stats["villager_request_phones_skipped"] = skipped

        for table_name, purpose, stat_prefix in (
            ("training_signups", "training_signup_phone", "training_signup"),
            ("volunteer_activity_signups", "volunteer_signup_phone", "volunteer_signup"),
        ):
            migrated, skipped = _migrate_phone_table(
                conn,
                table_name=table_name,
                id_column="id",
                phone_column="phone",
                ciphertext_column="phone_ciphertext",
                hash_column="phone_hash",
                masked_column="phone_masked",
                purpose=purpose,
                legacy_value="legacy_token",
            )
            stats[f"{stat_prefix}_phones_migrated"] = migrated
            stats[f"{stat_prefix}_phones_skipped"] = skipped

        application_rows = conn.execute(
            """
            SELECT
                id, service_id, service_key, selected_option, applicant_phone, extra_fields,
                applicant_phone_ciphertext, applicant_phone_hash, applicant_phone_masked,
                sensitive_extra_fields_encrypted,
                applicant_id_card_hash,
                application_fingerprint_hash
            FROM gov_service_applications
            ORDER BY id ASC
            """
        ).fetchall()
        phone_migrated = 0
        phone_skipped = 0
        extra_migrated = 0
        for row in application_rows:
            phone = str(row["applicant_phone"] or "").strip()
            phone_values = {
                "masked": str(row["applicant_phone_masked"] or "").strip() or phone,
                "ciphertext": str(row["applicant_phone_ciphertext"] or ""),
                "lookup_hash": str(row["applicant_phone_hash"] or "").strip(),
            }
            if not phone_values["ciphertext"] and phone:
                if is_valid_phone(phone):
                    phone_values = _protected_business_phone_fields(
                        phone,
                        purpose="gov_application_phone",
                    )
                    phone_migrated += 1
                else:
                    phone_skipped += 1

            extra_fields = _parse_json_object(row["extra_fields"])
            source_extra_fields = dict(extra_fields)
            existing_encrypted_extra = str(row["sensitive_extra_fields_encrypted"] or "").strip()
            if existing_encrypted_extra:
                decrypted_extra = _parse_json_object(
                    unprotect_text(existing_encrypted_extra, purpose="gov_application_extra")
                )
                source_extra_fields.update(decrypted_extra)
            protected_extra, encrypted_extra, derived_applicant_id_hash = _protect_gov_application_extra_fields(
                source_extra_fields
            )
            applicant_id_hash = (
                str(row["applicant_id_card_hash"] or "").strip()
                or derived_applicant_id_hash
            )
            if existing_encrypted_extra:
                encrypted_extra = existing_encrypted_extra
            elif encrypted_extra:
                extra_migrated += 1

            fingerprint_hash = str(row["application_fingerprint_hash"] or "").strip()
            if not fingerprint_hash and str(row["service_key"] or "") == "certificate":
                fingerprint_hash = keyed_lookup_hash(
                    _build_certificate_application_fingerprint(
                        service_id=int(row["service_id"] or 0),
                        selected_option=str(row["selected_option"] or ""),
                        extra_fields=source_extra_fields,
                    ),
                    purpose="gov_application_fingerprint",
                )

            conn.execute(
                """
                UPDATE gov_service_applications
                SET applicant_phone = ?, applicant_phone_ciphertext = ?, applicant_phone_hash = ?,
                    applicant_phone_masked = ?, extra_fields = ?,
                    sensitive_extra_fields_encrypted = ?, applicant_id_card_hash = ?,
                    application_fingerprint_hash = ?
                WHERE id = ?
                """,
                (
                    phone_values["masked"],
                    phone_values["ciphertext"],
                    phone_values["lookup_hash"],
                    phone_values["masked"],
                    _json_text(protected_extra),
                    encrypted_extra,
                    applicant_id_hash,
                    fingerprint_hash,
                    row["id"],
                ),
            )

        stats["gov_application_phones_migrated"] = phone_migrated
        stats["gov_application_phones_skipped"] = phone_skipped
        stats["gov_application_sensitive_json_migrated"] = extra_migrated

        legacy_admin_rows = conn.execute(
            "SELECT id FROM admin_users WHERE COALESCE(security_policy_version, 0) < 1"
        ).fetchall()
        legacy_admin_ids = [int(row["id"] or 0) for row in legacy_admin_rows if int(row["id"] or 0) > 0]
        now_text = datetime.now(timezone.utc).isoformat()
        for admin_user_id in legacy_admin_ids:
            conn.execute(
                """
                UPDATE admin_users
                SET password_reset_required = 1, security_policy_version = 1, updated_at = ?
                WHERE id = ?
                """,
                (now_text, admin_user_id),
            )
            conn.execute(
                """
                UPDATE admin_sessions SET revoked_at = ?
                WHERE admin_user_id = ? AND revoked_at = ''
                """,
                (now_text, admin_user_id),
            )
        stats["admin_accounts_forced_password_reset"] = len(legacy_admin_ids)

        if dry_run:
            conn.rollback()
        else:
            conn.commit()
        return stats
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Encrypt legacy business phone and identity fields without printing personal data."
    )
    parser.add_argument("--dry-run", action="store_true", help="Validate and report counts, then roll back.")
    args = parser.parse_args()
    stats = migrate_sensitive_business_data(dry_run=bool(args.dry_run))
    mode = "dry-run" if args.dry_run else "committed"
    print(f"sensitive business data migration {mode}; backend={DB_BACKEND}")
    for key in sorted(stats):
        print(f"{key}={stats[key]}")


if __name__ == "__main__":
    main()
