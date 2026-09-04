import re
from datetime import datetime

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy import or_
from sqlalchemy.exc import SQLAlchemyError

from extensions import db
from models.clinical import ClinicalSession, ClinicalSummary
from models.patient import Patient
from models.privacy import RedFlagAlert
from models.records import LabResult, MedicalDocument, TimelineEvent
from utils.helpers import generate_patient_id, staff_required, write_audit

patients_bp = Blueprint("patients", __name__, url_prefix="/patients")

PHONE_RE = re.compile(r"^[0-9+\-\s]{8,20}$")


def _parse_dob(raw):
    raw = (raw or "").strip()
    if not raw:
        return None
    try:
        return datetime.strptime(raw, "%Y-%m-%d").date()
    except ValueError:
        return None


def _validate_patient_form(form, patient_id=None):
    errors = []
    full_name = (form.get("full_name") or "").strip()
    age_raw = (form.get("age") or "").strip()
    gender = (form.get("gender") or "").strip()
    phone = (form.get("phone") or "").strip()
    address = (form.get("address") or "").strip()
    language = (form.get("preferred_language") or "en").strip()
    dob = _parse_dob(form.get("date_of_birth"))
    emergency_contact_name = (form.get("emergency_contact_name") or "").strip() or None
    emergency_contact_phone = (form.get("emergency_contact_phone") or "").strip() or None
    abha_id = (form.get("abha_id") or "").strip() or None
    aadhaar_demo = (form.get("aadhaar_demo") or "").strip() or None

    if len(full_name) < 2:
        errors.append("Full name is required.")

    try:
        age = int(age_raw)
        if age < 0 or age > 130:
            errors.append("Age must be between 0 and 130.")
    except ValueError:
        age = None
        errors.append("Age must be a valid number.")

    if gender not in ("Male", "Female", "Other"):
        errors.append("Please select a valid gender.")

    if not PHONE_RE.match(phone):
        errors.append("Enter a valid phone number.")

    if len(address) < 5:
        errors.append("Address is required.")

    if language not in ("en", "hi"):
        language = "en"

    existing = Patient.query.filter_by(phone=phone).first()
    if existing and existing.id != patient_id:
        errors.append("Another patient is already registered with this phone number.")

    return errors, {
        "full_name": full_name,
        "age": age,
        "gender": gender,
        "phone": phone,
        "address": address,
        "preferred_language": language,
        "date_of_birth": dob,
        "emergency_contact_name": emergency_contact_name,
        "emergency_contact_phone": emergency_contact_phone,
        "abha_id": abha_id,
        "aadhaar_demo": aadhaar_demo,
    }


@patients_bp.route("/")
@login_required
@staff_required
def list_patients():
    q = (request.args.get("q") or "").strip()
    query = Patient.query
    if q:
        like = f"%{q}%"
        query = query.filter(
            or_(
                Patient.full_name.ilike(like),
                Patient.patient_id.ilike(like),
                Patient.phone.ilike(like),
            )
        )
    patients = query.order_by(Patient.created_at.desc()).all()
    return render_template("patients/list.html", patients=patients, search_query=q)


@patients_bp.route("/add", methods=["GET", "POST"])
@login_required
@staff_required
def add_patient():
    if request.method == "POST":
        errors, data = _validate_patient_form(request.form)
        if errors:
            for err in errors:
                flash(err, "danger")
            return render_template("patients/form.html", patient=None, form=request.form)

        patient = Patient(
            patient_id=generate_patient_id(),
            created_by_id=current_user.id,
            **data,
        )
        db.session.add(patient)
        try:
            write_audit("create_patient", "patient", details=patient.patient_id)
            db.session.commit()
        except SQLAlchemyError:
            db.session.rollback()
            flash("Could not save the patient. Please try again.", "danger")
            return render_template("patients/form.html", patient=None, form=request.form)

        flash(f"Patient {patient.full_name} registered as {patient.patient_id}.", "success")
        return redirect(url_for("patients.detail", patient_id=patient.id))

    return render_template("patients/form.html", patient=None, form={})


@patients_bp.route("/<int:patient_id>")
@login_required
@staff_required
def detail(patient_id):
    patient = Patient.query.get_or_404(patient_id)
    cases = sorted(patient.cases, key=lambda c: c.created_at or 0, reverse=True)
    sessions = (
        ClinicalSession.query.filter_by(patient_id=patient.id)
        .order_by(ClinicalSession.created_at.desc())
        .all()
    )
    summaries = (
        ClinicalSummary.query.filter_by(patient_id=patient.id)
        .order_by(ClinicalSummary.updated_at.desc())
        .all()
    )
    documents = (
        MedicalDocument.query.filter_by(patient_id=patient.id)
        .order_by(MedicalDocument.created_at.desc())
        .all()
    )
    event_filter = (request.args.get("type") or "").strip()
    timeline_q = TimelineEvent.query.filter_by(patient_id=patient.id)
    if event_filter:
        timeline_q = timeline_q.filter_by(event_type=event_filter)
    timeline = timeline_q.order_by(TimelineEvent.event_date.desc(), TimelineEvent.id.desc()).all()
    labs = (
        LabResult.query.filter_by(patient_id=patient.id)
        .order_by(LabResult.id.desc())
        .limit(12)
        .all()
    )
    alerts = (
        RedFlagAlert.query.filter_by(patient_id=patient.id)
        .order_by(RedFlagAlert.created_at.desc())
        .limit(10)
        .all()
    )
    latest_summary = summaries[0] if summaries else None
    return render_template(
        "patients/detail.html",
        patient=patient,
        cases=cases,
        sessions=sessions,
        summaries=summaries,
        latest_summary=latest_summary,
        documents=documents,
        timeline=timeline,
        event_filter=event_filter,
        labs=labs,
        alerts=alerts,
    )


@patients_bp.route("/<int:patient_id>/edit", methods=["GET", "POST"])
@login_required
@staff_required
def edit_patient(patient_id):
    patient = Patient.query.get_or_404(patient_id)
    if request.method == "POST":
        errors, data = _validate_patient_form(request.form, patient_id=patient.id)
        if errors:
            for err in errors:
                flash(err, "danger")
            return render_template("patients/form.html", patient=patient, form=request.form)

        for key, value in data.items():
            setattr(patient, key, value)
        try:
            write_audit("edit_patient", "patient", patient.id, patient_id=patient.id)
            db.session.commit()
        except SQLAlchemyError:
            db.session.rollback()
            flash("Could not update the patient. Please try again.", "danger")
            return render_template("patients/form.html", patient=patient, form=request.form)

        flash("Patient information updated.", "success")
        return redirect(url_for("patients.detail", patient_id=patient.id))

    return render_template("patients/form.html", patient=patient, form=None)
