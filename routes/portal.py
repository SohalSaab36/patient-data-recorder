from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy.exc import SQLAlchemyError

from extensions import db
from models.clinical import AyushAssessment, ClinicalSession, ClinicalSummary
from models.records import MedicalDocument, TimelineEvent
from services.abdm_service import generate_fhir_like_payload, link_health_record_demo, verify_abha_demo
from services.consent_service import consent_state, has_active_consent, set_consent
from services.interview_engine import get_flow, get_question, localize_question, progress_for
from services.session_service import record_answer
from utils.helpers import (
    current_patient_record,
    generate_session_number,
    patient_required,
    write_audit,
)

portal_bp = Blueprint("portal", __name__, url_prefix="/portal")


def _patient():
    patient = current_patient_record()
    if not patient:
        flash("No patient record is linked to this account.", "danger")
        return None
    return patient


@portal_bp.route("/")
@login_required
@patient_required
def home():
    patient = _patient()
    if not patient:
        return redirect(url_for("auth.logout"))
    sessions = (
        ClinicalSession.query.filter_by(patient_id=patient.id)
        .order_by(ClinicalSession.created_at.desc())
        .limit(8)
        .all()
    )
    summaries = (
        ClinicalSummary.query.filter_by(patient_id=patient.id)
        .order_by(ClinicalSummary.updated_at.desc())
        .limit(8)
        .all()
    )
    docs = (
        MedicalDocument.query.filter_by(patient_id=patient.id)
        .order_by(MedicalDocument.created_at.desc())
        .limit(6)
        .all()
    )
    return render_template(
        "portal/home.html",
        patient=patient,
        sessions=sessions,
        summaries=summaries,
        docs=docs,
        consents=consent_state(patient.id),
    )


@portal_bp.route("/consent", methods=["GET", "POST"])
@login_required
@patient_required
def consent():
    patient = _patient()
    if not patient:
        return redirect(url_for("auth.logout"))
    if request.method == "POST":
        for key, _title, _help in [
            ("history_collection", "", ""),
            ("document_processing", "", ""),
            ("share_with_doctor", "", ""),
            ("abdm_demo", "", ""),
        ]:
            granted = request.form.get(key) == "on"
            set_consent(patient.id, key, granted)
        write_audit("update_consent", "patient", patient.id, patient_id=patient.id)
        try:
            db.session.commit()
        except SQLAlchemyError:
            db.session.rollback()
            flash("Could not save consent choices.", "danger")
            return redirect(url_for("portal.consent"))
        flash("Consent preferences updated. Withdrawal stops new processing of that type.", "success")
        return redirect(url_for("portal.consent"))
    return render_template("portal/consent.html", patient=patient, consents=consent_state(patient.id))


@portal_bp.route("/interview/start", methods=["POST"])
@login_required
@patient_required
def start_interview():
    patient = _patient()
    if not patient:
        return redirect(url_for("auth.logout"))
    if not has_active_consent(patient.id, "history_collection"):
        flash("Please grant consent for clinical history collection first.", "warning")
        return redirect(url_for("portal.consent"))
    if not has_active_consent(patient.id, "share_with_doctor"):
        flash("Sharing consent is required so a doctor can review your summary.", "warning")
        return redirect(url_for("portal.consent"))

    open_session = ClinicalSession.query.filter_by(
        patient_id=patient.id, status="in_progress"
    ).first()
    if open_session:
        return redirect(url_for("portal.interview", session_id=open_session.id))

    flow = get_flow()
    session = ClinicalSession(
        session_number=generate_session_number(),
        patient_id=patient.id,
        status="in_progress",
        current_question_id=flow["start"],
        language=patient.preferred_language or current_user.preferred_language or "en",
        ayush_enabled=bool(request.form.get("ayush_enabled")),
        progress_pct=progress_for(flow["start"]),
    )
    db.session.add(session)
    write_audit("start_interview", "clinical_session", patient_id=patient.id)
    db.session.commit()
    return redirect(url_for("portal.interview", session_id=session.id))


@portal_bp.route("/interview/<int:session_id>", methods=["GET", "POST"])
@login_required
@patient_required
def interview(session_id):
    patient = _patient()
    if not patient:
        return redirect(url_for("auth.logout"))
    session = ClinicalSession.query.get_or_404(session_id)
    if session.patient_id != patient.id:
        flash("You can only open your own interview.", "danger")
        return redirect(url_for("portal.home"))
    if session.status != "in_progress":
        return redirect(url_for("portal.summary_view", summary_id=session.summary.id) if session.summary else url_for("portal.home"))

    lang = session.language or "en"
    simple = current_user.pref_simple_language
    question = get_question(session.current_question_id)
    if not question:
        from services.session_service import complete_session

        complete_session(session)
        db.session.commit()
        flash("Interview closed. Review the generated summary.", "info")
        return redirect(url_for("portal.home"))
    localized = localize_question(question, lang, simple=simple)

    if request.method == "POST":
        if question["type"] == "choice":
            answer = (request.form.get("choice") or "").strip()
        else:
            answer = (request.form.get("answer") or "").strip()
        if not answer:
            flash("Please answer before continuing.", "warning")
        else:
            record_answer(session, question, localized, answer, question.get("type", "text"))
            try:
                db.session.commit()
            except SQLAlchemyError:
                db.session.rollback()
                flash("Could not save that answer. Try again.", "danger")
                return redirect(url_for("portal.interview", session_id=session.id))
            if session.status != "in_progress":
                flash(
                    "Interview complete. A structured summary was prepared for doctor review. This is not a diagnosis.",
                    "success",
                )
                if session.is_priority:
                    flash(
                        "Priority notice: some answers matched predefined urgent phrases. Please seek in-person care if you feel unwell. Staff have been notified on the doctor dashboard.",
                        "danger",
                    )
                return redirect(url_for("portal.summary_view", summary_id=session.summary.id))
            return redirect(url_for("portal.interview", session_id=session.id))

        question = get_question(session.current_question_id)
        if not question:
            from services.session_service import complete_session

            complete_session(session)
            db.session.commit()
            flash("Interview closed. Review the generated summary.", "info")
            return redirect(url_for("portal.home"))
        localized = localize_question(question, lang, simple=simple)

    recent = list(session.answers)[-6:]
    return render_template(
        "portal/interview.html",
        patient=patient,
        session=session,
        question=localized,
        recent=recent,
        speech_lang="hi-IN" if lang == "hi" else "en-IN",
    )


@portal_bp.route("/summaries")
@login_required
@patient_required
def summaries():
    patient = _patient()
    if not patient:
        return redirect(url_for("auth.logout"))
    items = (
        ClinicalSummary.query.filter_by(patient_id=patient.id)
        .order_by(ClinicalSummary.updated_at.desc())
        .all()
    )
    return render_template("portal/summaries.html", patient=patient, summaries=items)


@portal_bp.route("/summaries/<int:summary_id>")
@login_required
@patient_required
def summary_view(summary_id):
    patient = _patient()
    if not patient:
        return redirect(url_for("auth.logout"))
    summary = ClinicalSummary.query.get_or_404(summary_id)
    if summary.patient_id != patient.id:
        flash("You can only view your own summaries.", "danger")
        return redirect(url_for("portal.home"))
    return render_template("portal/summary.html", patient=patient, summary=summary, editable=False)


@portal_bp.route("/timeline")
@login_required
@patient_required
def timeline():
    patient = _patient()
    if not patient:
        return redirect(url_for("auth.logout"))
    event_filter = (request.args.get("type") or "").strip()
    query = TimelineEvent.query.filter_by(patient_id=patient.id)
    if event_filter:
        query = query.filter_by(event_type=event_filter)
    events = query.order_by(TimelineEvent.event_date.desc(), TimelineEvent.id.desc()).all()
    return render_template(
        "portal/timeline.html",
        patient=patient,
        events=events,
        event_filter=event_filter,
    )


@portal_bp.route("/ayush", methods=["GET", "POST"])
@login_required
@patient_required
def ayush():
    patient = _patient()
    if not patient:
        return redirect(url_for("auth.logout"))
    if request.method == "POST":
        assessment = AyushAssessment(
            patient_id=patient.id,
            prakriti=request.form.get("prakriti") or None,
            vikriti=request.form.get("vikriti") or None,
            agni=request.form.get("agni") or None,
            koshta=request.form.get("koshta") or None,
            ahara=request.form.get("ahara") or None,
            vihara=request.form.get("vihara") or None,
            nidana=request.form.get("nidana") or None,
            sara=request.form.get("sara") or None,
            samhanana=request.form.get("samhanana") or None,
            pramana=request.form.get("pramana") or None,
            satmya=request.form.get("satmya") or None,
            sattva=request.form.get("sattva") or None,
            ahara_shakti=request.form.get("ahara_shakti") or None,
            vyayama_shakti=request.form.get("vyayama_shakti") or None,
            vaya=request.form.get("vaya") or None,
            notes=request.form.get("notes") or None,
        )
        db.session.add(assessment)
        write_audit("ayush_assessment", "ayush", patient_id=patient.id)
        db.session.commit()
        flash("AYUSH / Ayurvedic assessment saved separately from allopathic history.", "success")
        return redirect(url_for("portal.ayush"))
    items = (
        AyushAssessment.query.filter_by(patient_id=patient.id)
        .order_by(AyushAssessment.created_at.desc())
        .all()
    )
    return render_template("portal/ayush.html", patient=patient, items=items)


@portal_bp.route("/abha", methods=["GET", "POST"])
@login_required
@patient_required
def abha():
    patient = _patient()
    if not patient:
        return redirect(url_for("auth.logout"))
    if not has_active_consent(patient.id, "abdm_demo"):
        flash("Grant the ABDM/ABHA demo consent to use the sandbox tools.", "warning")
        return redirect(url_for("portal.consent"))
    result = None
    bundle = None
    if request.method == "POST":
        action = request.form.get("action")
        if action == "verify":
            abha_id = request.form.get("abha_id") or patient.abha_id
            result = verify_abha_demo(abha_id)
            if result.get("ok"):
                patient.abha_id = result.get("abha_id")
                db.session.commit()
        elif action == "link":
            latest = (
                ClinicalSummary.query.filter_by(patient_id=patient.id)
                .order_by(ClinicalSummary.id.desc())
                .first()
            )
            result = link_health_record_demo(patient, latest)
        elif action == "fhir":
            from models.records import LabResult

            docs = MedicalDocument.query.filter_by(patient_id=patient.id).all()
            labs = LabResult.query.filter_by(patient_id=patient.id).all()
            session = (
                ClinicalSession.query.filter_by(patient_id=patient.id)
                .order_by(ClinicalSession.id.desc())
                .first()
            )
            bundle = generate_fhir_like_payload(patient, session, docs, labs)
            result = {"ok": True, "banner": bundle["meta"]["tag"][0]["display"]}
    return render_template("portal/abha.html", patient=patient, result=result, bundle=bundle)
