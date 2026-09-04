from datetime import datetime
from functools import wraps

from flask import abort, flash, redirect, url_for
from flask_login import current_user

from models.privacy import AuditLog
from models.clinical import ClinicalSession
from models.patient import Patient
from models.medical_case import MedicalCase
from extensions import db


def generate_patient_id():
    today = datetime.utcnow().strftime("%Y%m%d")
    prefix = f"PAT-{today}-"
    last = (
        Patient.query.filter(Patient.patient_id.like(f"{prefix}%"))
        .order_by(Patient.id.desc())
        .first()
    )
    if last:
        try:
            seq = int(last.patient_id.split("-")[-1]) + 1
        except ValueError:
            seq = 1
    else:
        seq = 1
    return f"{prefix}{seq:04d}"


def generate_case_number():
    today = datetime.utcnow().strftime("%Y%m%d")
    prefix = f"CS-{today}-"
    last = (
        MedicalCase.query.filter(MedicalCase.case_number.like(f"{prefix}%"))
        .order_by(MedicalCase.id.desc())
        .first()
    )
    if last:
        try:
            seq = int(last.case_number.split("-")[-1]) + 1
        except ValueError:
            seq = 1
    else:
        seq = 1
    return f"{prefix}{seq:04d}"


def generate_session_number():
    today = datetime.utcnow().strftime("%Y%m%d")
    prefix = f"INT-{today}-"
    last = (
        ClinicalSession.query.filter(ClinicalSession.session_number.like(f"{prefix}%"))
        .order_by(ClinicalSession.id.desc())
        .first()
    )
    if last:
        try:
            seq = int(last.session_number.split("-")[-1]) + 1
        except ValueError:
            seq = 1
    else:
        seq = 1
    return f"{prefix}{seq:04d}"


def roles_required(*roles):
    def decorator(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            if not current_user.is_authenticated:
                return redirect(url_for("auth.login"))
            if current_user.role not in roles:
                abort(403)
            return view(*args, **kwargs)

        return wrapped

    return decorator


def staff_required(view):
    return roles_required("doctor", "admin")(view)


def patient_required(view):
    return roles_required("patient")(view)


def current_patient_record():
    if not current_user.is_authenticated or current_user.role != "patient":
        return None
    return Patient.query.filter_by(user_id=current_user.id).first()


def write_audit(action, entity_type=None, entity_id=None, details=None, patient_id=None):
    log = AuditLog(
        user_id=current_user.id if current_user.is_authenticated else None,
        patient_id=patient_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        details=details,
    )
    db.session.add(log)


def post_login_redirect():
    if current_user.role == "patient":
        return url_for("portal.home")
    if current_user.role == "admin":
        return url_for("admin.home")
    return url_for("dashboard.index")


def deny_if_wrong_patient(patient):
    if current_user.role == "patient":
        record = current_patient_record()
        if not record or record.id != patient.id:
            abort(403)


def flash_consent_block(kind):
    flash(
        f"This action needs the “{kind}” consent to be granted in Consent Settings.",
        "warning",
    )
