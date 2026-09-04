"""Layered summarization: rule-based by default, optional HTTP AI if configured."""

import json
import urllib.error
import urllib.request

from flask import current_app

from models.records import LabResult, MedicalDocument, Medication, TimelineEvent
from models.privacy import RedFlagAlert
from services.interview_engine import get_question, pick_text


SECTION_TITLES = [
    ("chief_complaint", "Chief Complaint"),
    ("hpi", "History of Present Illness"),
    ("past_medical", "Past Medical History"),
    ("past_surgical", "Past Surgical History"),
    ("drug_history", "Drug & Medication History"),
    ("allergy_history", "Allergies"),
    ("family_history", "Family History"),
    ("personal_history", "Personal History"),
    ("review_of_systems", "Review of Systems"),
    ("prior_investigations", "Prior Investigations Summary"),
]


def _join_answers(answers, section):
    lines = []
    for ans in answers:
        if ans.section != section:
            continue
        q = get_question(ans.question_id)
        label = ans.question_text
        if q:
            label = pick_text(q.get("text"), "en") or label
        lines.append(f"{label} {ans.answer_text}".strip())
    return " ".join(lines).strip() or "Not elicited in this session."


def _document_timeline_text(patient_id):
    events = (
        TimelineEvent.query.filter_by(patient_id=patient_id)
        .order_by(TimelineEvent.event_date.desc(), TimelineEvent.id.desc())
        .limit(20)
        .all()
    )
    if not events:
        return "No timeline events recorded yet."
    return "\n".join(
        f"{ev.event_date.isoformat()} — {ev.event_type}: {ev.title}"
        for ev in events
    )


def _meds_text(patient_id):
    meds = Medication.query.filter_by(patient_id=patient_id).all()
    if not meds:
        return ""
    return "Extracted from documents (unverified): " + "; ".join(
        f"{m.name}" + (f" {m.dosage}" if m.dosage else "") for m in meds
    )


def _labs_text(patient_id):
    labs = LabResult.query.filter_by(patient_id=patient_id).order_by(LabResult.id.desc()).limit(15).all()
    if not labs:
        return ""
    parts = []
    for lab in labs:
        flag = lab.flag.replace("_", " ")
        parts.append(f"{lab.test_name} {lab.value or ''} {lab.unit or ''} ({flag})")
    return "Extracted lab values (for review only): " + "; ".join(parts)


def _red_flag_text(session_id):
    alerts = RedFlagAlert.query.filter_by(session_id=session_id).all()
    if not alerts:
        return "No predefined red-flag phrases matched. This does not rule out emergency conditions."
    return "Priority phrases matched (not a diagnosis): " + " | ".join(
        f"{a.matched_phrase} — {a.message}" for a in alerts
    )


def build_rule_based_summary(session, answers, patient):
    chief = _join_answers(answers, "chief_complaint")
    hpi = _join_answers(answers, "hpi")
    drugs = _join_answers(answers, "drug_history")
    extra_meds = _meds_text(patient.id)
    if extra_meds:
        drugs = f"{drugs}\n{extra_meds}"
    investigations = _join_answers(answers, "prior_investigations")
    extra_labs = _labs_text(patient.id)
    if extra_labs:
        investigations = f"{investigations}\n{extra_labs}"

    docs = MedicalDocument.query.filter_by(patient_id=patient.id).count()
    doc_note = f"Uploaded documents on file: {docs}."

    return {
        "chief_complaint": chief,
        "hpi": hpi,
        "past_medical": _join_answers(answers, "past_medical"),
        "past_surgical": _join_answers(answers, "past_surgical"),
        "drug_history": drugs,
        "allergy_history": _join_answers(answers, "allergy_history"),
        "family_history": _join_answers(answers, "family_history"),
        "personal_history": _join_answers(answers, "personal_history"),
        "review_of_systems": _join_answers(answers, "review_of_systems"),
        "prior_investigations": investigations,
        "document_timeline": f"{doc_note}\n{_document_timeline_text(patient.id)}",
        "red_flag_notes": _red_flag_text(session.id),
        "important_notes": (
            "Automated clinical history assistance only. Not a diagnosis, "
            "not a treatment plan, and not a certified medical device. "
            "A qualified clinician must review and confirm."
        ),
        "generator_mode": "rule-based",
    }


def _try_external_polish(payload):
    key = current_app.config.get("AI_API_KEY") or ""
    provider = (current_app.config.get("AI_PROVIDER") or "none").lower()
    if not key or provider in ("none", "", "off"):
        return None
    body = {
        "model": current_app.config.get("AI_MODEL"),
        "messages": [
            {
                "role": "system",
                "content": (
                    "You rewrite clinical history notes to be concise and structured. "
                    "Do not diagnose. Do not add facts that are not in the source."
                ),
            },
            {"role": "user", "content": json.dumps(payload)},
        ],
        "temperature": 0.1,
    }
    request = urllib.request.Request(
        current_app.config.get("AI_API_URL"),
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {key}",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            data = json.loads(response.read().decode("utf-8"))
        text = data["choices"][0]["message"]["content"]
        parsed = json.loads(text)
        parsed["generator_mode"] = "external-ai-optional"
        return parsed
    except (urllib.error.URLError, KeyError, json.JSONDecodeError, TimeoutError, ValueError):
        return None


def generate_summary(session, answers, patient):
    base = build_rule_based_summary(session, answers, patient)
    polished = _try_external_polish(base)
    return polished or base
