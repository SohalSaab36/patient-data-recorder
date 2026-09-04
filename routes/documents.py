import os
import uuid

from flask import (
    Blueprint,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    send_from_directory,
    url_for,
)
from flask_login import current_user, login_required
from werkzeug.utils import secure_filename

from extensions import db
from models.records import LabResult, MedicalDocument, Medication
from services.consent_service import has_active_consent
from services.document_pipeline import process_document
from utils.helpers import current_patient_record, staff_required, write_audit

documents_bp = Blueprint("documents", __name__)

CATEGORIES = [
    ("Prescription", "Prescription"),
    ("Laboratory Report", "Laboratory Report"),
    ("Discharge Summary", "Discharge Summary"),
    ("Medical Image/Other", "Medical Image/Other"),
]


def _allowed(filename):
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    return ext in current_app.config["ALLOWED_DOC_EXTENSIONS"]


def _can_access(doc):
    if current_user.role in ("doctor", "admin"):
        return True
    patient = current_patient_record()
    return bool(patient and patient.id == doc.patient_id)


@documents_bp.route("/portal/documents", methods=["GET", "POST"])
@login_required
def portal_documents():
    if current_user.role != "patient":
        return redirect(url_for("dashboard.index"))
    patient = current_patient_record()
    if not patient:
        flash("No patient record linked.", "danger")
        return redirect(url_for("auth.logout"))
    if request.method == "POST":
        if not has_active_consent(patient.id, "document_processing"):
            flash("Grant document processing consent before uploading.", "warning")
            return redirect(url_for("portal.consent"))
        return _handle_upload(patient, url_for("documents.portal_documents"))
    docs = (
        MedicalDocument.query.filter_by(patient_id=patient.id)
        .order_by(MedicalDocument.created_at.desc())
        .all()
    )
    return render_template(
        "portal/documents.html",
        patient=patient,
        documents=docs,
        categories=CATEGORIES,
    )


@documents_bp.route("/patients/<int:patient_id>/documents", methods=["POST"])
@login_required
@staff_required
def staff_upload(patient_id):
    from models.patient import Patient

    patient = Patient.query.get_or_404(patient_id)
    return _handle_upload(patient, url_for("patients.detail", patient_id=patient.id))


def _handle_upload(patient, redirect_to):
    file = request.files.get("file")
    category = request.form.get("category") or "Medical Image/Other"
    if not file or not file.filename:
        flash("Choose a PDF, JPG, JPEG, or PNG file.", "danger")
        return redirect(redirect_to)
    if not _allowed(file.filename):
        flash("That file type is not allowed.", "danger")
        return redirect(redirect_to)
    os.makedirs(current_app.config["UPLOAD_FOLDER"], exist_ok=True)
    original = secure_filename(file.filename)
    stored = f"{uuid.uuid4().hex}_{original}"
    path = os.path.join(current_app.config["UPLOAD_FOLDER"], stored)
    file.save(path)
    doc = MedicalDocument(
        patient_id=patient.id,
        original_filename=original,
        stored_name=stored,
        category=category,
        mime_type=file.mimetype,
        status="uploaded",
        uploaded_by_id=current_user.id,
    )
    db.session.add(doc)
    db.session.commit()
    process_document(doc, path)
    write_audit("upload_document", "document", doc.id, patient_id=patient.id)
    db.session.commit()
    flash(f"Document stored. Status: {doc.status.replace('_', ' ')}.", "success")
    return redirect(url_for("documents.review", document_id=doc.id))


@documents_bp.route("/documents/<int:document_id>")
@login_required
def review(document_id):
    doc = MedicalDocument.query.get_or_404(document_id)
    if not _can_access(doc):
        flash("You cannot open this document.", "danger")
        return redirect(url_for("portal.home") if current_user.role == "patient" else url_for("dashboard.index"))
    meds = Medication.query.filter_by(document_id=doc.id).all()
    labs = LabResult.query.filter_by(document_id=doc.id).all()
    return render_template("documents/review.html", doc=doc, meds=meds, labs=labs)


@documents_bp.route("/documents/<int:document_id>/file")
@login_required
def file_download(document_id):
    doc = MedicalDocument.query.get_or_404(document_id)
    if not _can_access(doc):
        flash("You cannot open this document.", "danger")
        return redirect(url_for("portal.home"))
    return send_from_directory(
        current_app.config["UPLOAD_FOLDER"],
        doc.stored_name,
        as_attachment=False,
        download_name=doc.original_filename,
    )


@documents_bp.route("/documents/<int:document_id>/ocr", methods=["POST"])
@login_required
def save_ocr(document_id):
    doc = MedicalDocument.query.get_or_404(document_id)
    if not _can_access(doc):
        flash("You cannot edit this document.", "danger")
        return redirect(url_for("portal.home"))
    doc.ocr_text = request.form.get("ocr_text") or ""
    doc.facility_name = (request.form.get("facility_name") or "").strip() or None
    if request.form.get("document_date"):
        from datetime import datetime

        try:
            doc.document_date = datetime.strptime(request.form.get("document_date"), "%Y-%m-%d").date()
        except ValueError:
            pass
    for extraction in doc.extractions:
        extraction.field_value = request.form.get(f"ex_{extraction.id}", extraction.field_value)
        extraction.needs_review = bool(request.form.get(f"rev_{extraction.id}"))
    for lab in LabResult.query.filter_by(document_id=doc.id).all():
        lab.value = request.form.get(f"lab_value_{lab.id}", lab.value)
        lab.unit = request.form.get(f"lab_unit_{lab.id}", lab.unit)
        lab.flag = request.form.get(f"lab_flag_{lab.id}", lab.flag)
    write_audit("edit_extraction", "document", doc.id, patient_id=doc.patient_id)
    db.session.commit()
    flash("Extracted fields updated. Automated extraction is for review only.", "success")
    return redirect(url_for("documents.review", document_id=doc.id))
