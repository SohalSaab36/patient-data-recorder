from flask import Blueprint, render_template, redirect, request, url_for
from flask_login import current_user, login_required
from sqlalchemy import or_

from models.clinical import ClinicalSession
from models.medical_case import MedicalCase
from models.patient import Patient
from models.privacy import RedFlagAlert
from models.records import MedicalDocument

dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.route("/")
@dashboard_bp.route("/dashboard")
@login_required
def index():
    if current_user.role == "patient":
        return redirect(url_for("portal.home"))
    if current_user.role not in ("doctor", "admin"):
        from flask import abort

        abort(403)
    q = (request.args.get("q") or "").strip()
    search_results = []
    if q:
        like = f"%{q}%"
        search_results = (
            Patient.query.filter(
                or_(
                    Patient.full_name.ilike(like),
                    Patient.patient_id.ilike(like),
                    Patient.phone.ilike(like),
                )
            )
            .order_by(Patient.created_at.desc())
            .limit(20)
            .all()
        )

    total_patients = Patient.query.count()
    total_cases = MedicalCase.query.count()
    pending_interviews = ClinicalSession.query.filter(
        ClinicalSession.status.in_(["pending_review", "priority", "sent_back"])
    ).count()
    priority_cases = ClinicalSession.query.filter_by(is_priority=True).filter(
        ClinicalSession.status != "confirmed"
    ).count()
    recent_patients = Patient.query.order_by(Patient.created_at.desc()).limit(6).all()
    recent_cases = MedicalCase.query.order_by(MedicalCase.created_at.desc()).limit(6).all()
    recent_sessions = (
        ClinicalSession.query.filter(ClinicalSession.status != "in_progress")
        .order_by(ClinicalSession.updated_at.desc())
        .limit(6)
        .all()
    )
    recent_docs = MedicalDocument.query.order_by(MedicalDocument.created_at.desc()).limit(6).all()
    open_alerts = (
        RedFlagAlert.query.filter_by(acknowledged=False)
        .order_by(RedFlagAlert.created_at.desc())
        .limit(8)
        .all()
    )

    return render_template(
        "dashboard.html",
        total_patients=total_patients,
        total_cases=total_cases,
        pending_interviews=pending_interviews,
        priority_cases=priority_cases,
        recent_patients=recent_patients,
        recent_cases=recent_cases,
        recent_sessions=recent_sessions,
        recent_docs=recent_docs,
        open_alerts=open_alerts,
        search_query=q,
        search_results=search_results,
    )
