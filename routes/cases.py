from flask import Blueprint, flash, redirect, render_template, request, send_file, url_for
from flask_login import current_user, login_required
from sqlalchemy.exc import SQLAlchemyError

from extensions import db
from models.medical_case import MedicalCase
from models.medical_history import MedicalHistory
from models.patient import Patient
from services.document_pipeline import add_timeline_event
from utils.helpers import generate_case_number, staff_required
from utils.pdf import build_case_sheet_pdf

cases_bp = Blueprint("cases", __name__)

REQUIRED_FIELDS = [
    "main_symptoms",
    "duration",
    "severity",
    "present_illness_description",
    "symptoms_started",
    "progression",
    "previous_diseases",
    "previous_surgeries",
    "hospitalizations",
    "current_medications",
    "allergies",
    "family_history",
    "diet",
    "sleep",
    "lifestyle",
]

SEVERITIES = ("Mild", "Moderate", "Severe")


def _clean(form):
    return {key: (form.get(key) or "").strip() for key in REQUIRED_FIELDS}


def _validate(data):
    errors = []
    for key in REQUIRED_FIELDS:
        if not data[key]:
            errors.append("Please complete every field in the case-taking form.")
            break
    if data["severity"] not in SEVERITIES:
        errors.append("Select a valid severity: Mild, Moderate, or Severe.")
    return errors


def _apply_case_fields(case, data):
    case.main_symptoms = data["main_symptoms"]
    case.duration = data["duration"]
    case.severity = data["severity"]
    case.present_illness_description = data["present_illness_description"]
    case.symptoms_started = data["symptoms_started"]
    case.progression = data["progression"]
    case.family_history = data["family_history"]
    case.diet = data["diet"]
    case.sleep = data["sleep"]
    case.lifestyle = data["lifestyle"]


def _apply_history_fields(history, data):
    history.previous_diseases = data["previous_diseases"]
    history.previous_surgeries = data["previous_surgeries"]
    history.hospitalizations = data["hospitalizations"]
    history.current_medications = data["current_medications"]
    history.allergies = data["allergies"]


@cases_bp.route("/patients/<int:patient_id>/cases/new", methods=["GET", "POST"])
@login_required
@staff_required
def new_case(patient_id):
    patient = Patient.query.get_or_404(patient_id)
    if request.method == "POST":
        data = _clean(request.form)
        errors = _validate(data)
        if errors:
            for err in errors:
                flash(err, "danger")
            return render_template(
                "cases/form.html",
                patient=patient,
                case=None,
                form=request.form,
            )

        case = MedicalCase(
            case_number=generate_case_number(),
            patient_id=patient.id,
            doctor_id=current_user.id,
        )
        _apply_case_fields(case, data)
        history = MedicalHistory(medical_case=case)
        _apply_history_fields(history, data)
        db.session.add(case)
        try:
            db.session.flush()
            add_timeline_event(
                patient.id,
                title=f"Classic case sheet {case.case_number}",
                event_type="case",
                description=case.main_symptoms[:300],
                case_id=case.id,
            )
            db.session.commit()
        except SQLAlchemyError:
            db.session.rollback()
            flash("Could not save the case sheet. Please try again.", "danger")
            return render_template(
                "cases/form.html",
                patient=patient,
                case=None,
                form=request.form,
            )

        flash("Case sheet created successfully.", "success")
        return redirect(url_for("cases.view_case", case_id=case.id))

    return render_template("cases/form.html", patient=patient, case=None, form={})


@cases_bp.route("/cases/<int:case_id>")
@login_required
@staff_required
def view_case(case_id):
    case = MedicalCase.query.get_or_404(case_id)
    return render_template("cases/view.html", case=case)


@cases_bp.route("/cases/<int:case_id>/edit", methods=["GET", "POST"])
@login_required
@staff_required
def edit_case(case_id):
    case = MedicalCase.query.get_or_404(case_id)
    if request.method == "POST":
        data = _clean(request.form)
        errors = _validate(data)
        if errors:
            for err in errors:
                flash(err, "danger")
            return render_template(
                "cases/form.html",
                patient=case.patient,
                case=case,
                form=request.form,
            )

        _apply_case_fields(case, data)
        if case.history:
            _apply_history_fields(case.history, data)
        else:
            history = MedicalHistory(medical_case=case)
            _apply_history_fields(history, data)
            db.session.add(history)

        try:
            db.session.commit()
        except SQLAlchemyError:
            db.session.rollback()
            flash("Could not update the case sheet. Please try again.", "danger")
            return render_template(
                "cases/form.html",
                patient=case.patient,
                case=case,
                form=request.form,
            )

        flash("Case sheet updated.", "success")
        return redirect(url_for("cases.view_case", case_id=case.id))

    return render_template(
        "cases/form.html",
        patient=case.patient,
        case=case,
        form=None,
    )


@cases_bp.route("/cases/<int:case_id>/pdf")
@login_required
@staff_required
def export_pdf(case_id):
    case = MedicalCase.query.get_or_404(case_id)
    try:
        pdf_buffer = build_case_sheet_pdf(case)
    except Exception:
        flash("Could not generate the PDF. Please try again.", "danger")
        return redirect(url_for("cases.view_case", case_id=case.id))

    filename = f"{case.case_number}_case_sheet.pdf"
    return send_file(
        pdf_buffer,
        mimetype="application/pdf",
        as_attachment=True,
        download_name=filename,
    )
