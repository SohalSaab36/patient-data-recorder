from datetime import datetime

from extensions import db
from models.privacy import Consent

CONSENT_CATALOG = [
    (
        "history_collection",
        "Consent for clinical history collection",
        "Allows a guided interview to record symptoms and history.",
    ),
    (
        "document_processing",
        "Consent for document processing",
        "Allows upload, OCR, and rule-based extraction of medical files.",
    ),
    (
        "share_with_doctor",
        "Consent for sharing with doctor/hospital",
        "Allows clinicians on this system to review your history and files.",
    ),
    (
        "abdm_demo",
        "Demo consent for ABDM/ABHA sandbox",
        "Allows simulated (not real) ABHA verification and FHIR-like export.",
    ),
]


def latest_consent(patient_id, consent_type):
    return (
        Consent.query.filter_by(patient_id=patient_id, consent_type=consent_type)
        .order_by(Consent.id.desc())
        .first()
    )


def has_active_consent(patient_id, consent_type):
    record = latest_consent(patient_id, consent_type)
    return bool(record and record.granted and not record.withdrawn_at)


def set_consent(patient_id, consent_type, granted):
    record = latest_consent(patient_id, consent_type)
    now = datetime.utcnow()
    if record and record.granted and not record.withdrawn_at and granted:
        return record
    if record and record.granted and not record.withdrawn_at and not granted:
        record.withdrawn_at = now
        record.granted = False
        db.session.add(
            Consent(
                patient_id=patient_id,
                consent_type=consent_type,
                granted=False,
                timestamp=now,
                withdrawn_at=now,
            )
        )
        return record
    db.session.add(
        Consent(
            patient_id=patient_id,
            consent_type=consent_type,
            granted=bool(granted),
            timestamp=now,
            withdrawn_at=None if granted else now,
        )
    )
    return latest_consent(patient_id, consent_type)


def consent_state(patient_id):
    rows = []
    for key, title, help_text in CONSENT_CATALOG:
        rec = latest_consent(patient_id, key)
        rows.append(
            {
                "key": key,
                "title": title,
                "help": help_text,
                "granted": bool(rec and rec.granted and not rec.withdrawn_at),
                "timestamp": rec.timestamp if rec else None,
                "withdrawn_at": rec.withdrawn_at if rec else None,
            }
        )
    return rows
