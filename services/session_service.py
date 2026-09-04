from datetime import datetime

from extensions import db
from models.clinical import ClinicalAnswer, ClinicalSession, ClinicalSummary
from models.privacy import RedFlagAlert
from services.ai_service import generate_summary
from services.document_pipeline import add_timeline_event
from services.interview_engine import get_question, progress_for, resolve_next, scan_red_flags


def apply_red_flags(session, *texts):
    hits = scan_red_flags(*texts)
    created = []
    for hit in hits:
        existing = RedFlagAlert.query.filter_by(
            session_id=session.id, matched_phrase=hit["phrase"]
        ).first()
        if existing:
            continue
        alert = RedFlagAlert(
            patient_id=session.patient_id,
            session_id=session.id,
            matched_phrase=hit["phrase"],
            message=hit["message"],
        )
        db.session.add(alert)
        created.append(alert)
        session.is_priority = True
    return created


def record_answer(session, question, localized, answer_text, answer_type):
    db.session.add(
        ClinicalAnswer(
            session_id=session.id,
            question_id=session.current_question_id,
            question_text=localized["text"],
            section=question.get("section", "general"),
            answer_text=answer_text,
            answer_type=answer_type,
        )
    )
    if question.get("section") == "chief_complaint" and not session.flow_category:
        session.flow_category = answer_text[:50]
    apply_red_flags(session, localized["text"], answer_text)
    nxt = resolve_next(question, answer_text)
    if nxt == "END":
        complete_session(session)
        return None
    session.current_question_id = nxt
    session.progress_pct = progress_for(nxt)
    return nxt


def complete_session(session):
    db.session.flush()
    answers = (
        ClinicalAnswer.query.filter_by(session_id=session.id).order_by(ClinicalAnswer.id).all()
    )
    payload = generate_summary(session, answers, session.patient)
    summary = session.summary
    if not summary:
        summary = ClinicalSummary(session_id=session.id, patient_id=session.patient_id)
        db.session.add(summary)
    summary.status = "draft"
    summary.chief_complaint = payload.get("chief_complaint")
    summary.hpi = payload.get("hpi")
    summary.past_medical = payload.get("past_medical")
    summary.past_surgical = payload.get("past_surgical")
    summary.drug_history = payload.get("drug_history")
    summary.allergy_history = payload.get("allergy_history")
    summary.family_history = payload.get("family_history")
    summary.personal_history = payload.get("personal_history")
    summary.review_of_systems = payload.get("review_of_systems")
    summary.prior_investigations = payload.get("prior_investigations")
    summary.document_timeline = payload.get("document_timeline")
    summary.red_flag_notes = payload.get("red_flag_notes")
    summary.important_notes = payload.get("important_notes")
    summary.generator_mode = payload.get("generator_mode") or "rule-based"
    session.current_question_id = "END"
    session.progress_pct = 100
    session.completed_at = datetime.utcnow()
    session.status = "priority" if session.is_priority else "pending_review"
    add_timeline_event(
        session.patient_id,
        title=f"Clinical interview {session.session_number}",
        event_type="case",
        description=(summary.chief_complaint or "")[:300],
        session_id=session.id,
    )


def apply_summary_form(summary, form):
    fields = [
        "chief_complaint",
        "hpi",
        "past_medical",
        "past_surgical",
        "drug_history",
        "allergy_history",
        "family_history",
        "personal_history",
        "review_of_systems",
        "prior_investigations",
        "document_timeline",
        "red_flag_notes",
        "important_notes",
    ]
    for name in fields:
        setattr(summary, name, (form.get(name) or "").strip())
