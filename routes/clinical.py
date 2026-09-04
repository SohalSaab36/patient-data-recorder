from datetime import datetime

from flask import Blueprint, flash, redirect, render_template, request, send_file, url_for
from flask_login import current_user, login_required
from sqlalchemy.exc import SQLAlchemyError

from extensions import db
from models.clinical import ClinicalSummary
from models.privacy import RedFlagAlert
from services.session_service import apply_summary_form
from utils.helpers import staff_required, write_audit
from utils.pdf import build_clinical_summary_pdf

clinical_bp = Blueprint("clinical", __name__)


@clinical_bp.route("/summaries/<int:summary_id>", methods=["GET", "POST"])
@login_required
@staff_required
def review_summary(summary_id):
    summary = ClinicalSummary.query.get_or_404(summary_id)
    session = summary.session
    patient = summary.patient
    alerts = RedFlagAlert.query.filter_by(session_id=session.id).all()
    if request.method == "POST":
        action = request.form.get("action") or "draft"
        apply_summary_form(summary, request.form)
        if action == "confirm":
            summary.status = "confirmed"
            summary.confirmed_by_id = current_user.id
            summary.confirmed_at = datetime.utcnow()
            session.status = "confirmed"
            session.doctor_id = current_user.id
            flash("Summary confirmed by clinician. Still not a stand-alone diagnosis.", "success")
        elif action == "reject":
            summary.status = "sent_back"
            session.status = "sent_back"
            session.doctor_feedback = (request.form.get("doctor_feedback") or "").strip()
            flash("Sent back. The patient can see that review is incomplete.", "info")
        else:
            summary.status = "draft"
            flash("Draft saved.", "success")
        write_audit(f"summary_{action}", "summary", summary.id, patient_id=patient.id)
        try:
            db.session.commit()
        except SQLAlchemyError:
            db.session.rollback()
            flash("Could not save the summary.", "danger")
        return redirect(url_for("clinical.review_summary", summary_id=summary.id))

    return render_template(
        "clinical/review.html",
        summary=summary,
        session=session,
        patient=patient,
        alerts=alerts,
        editable=True,
    )


@clinical_bp.route("/summaries/<int:summary_id>/pdf")
@login_required
@staff_required
def summary_pdf(summary_id):
    summary = ClinicalSummary.query.get_or_404(summary_id)
    try:
        pdf = build_clinical_summary_pdf(summary, summary.patient, summary.session)
    except Exception:
        flash("Could not generate PDF.", "danger")
        return redirect(url_for("clinical.review_summary", summary_id=summary.id))
    return send_file(
        pdf,
        mimetype="application/pdf",
        as_attachment=True,
        download_name=f"{summary.session.session_number}_summary.pdf",
    )


@clinical_bp.route("/alerts/<int:alert_id>/ack", methods=["POST"])
@login_required
@staff_required
def ack_alert(alert_id):
    alert = RedFlagAlert.query.get_or_404(alert_id)
    alert.acknowledged = True
    db.session.commit()
    return redirect(request.referrer or url_for("dashboard.index"))
