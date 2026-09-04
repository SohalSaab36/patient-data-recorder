from datetime import date

from extensions import db
from models.records import (
    DocumentExtraction,
    LabResult,
    MedicalDocument,
    Medication,
    TimelineEvent,
)
from services.extraction_service import extract_from_text, parse_date
from services.ocr_service import extract_text


def add_timeline_event(
    patient_id,
    title,
    event_type,
    description="",
    event_date=None,
    document_id=None,
    session_id=None,
    case_id=None,
):
    event = TimelineEvent(
        patient_id=patient_id,
        event_date=event_date or date.today(),
        title=title,
        description=description,
        event_type=event_type,
        document_id=document_id,
        session_id=session_id,
        case_id=case_id,
    )
    db.session.add(event)
    return event


def persist_extraction(document, findings):
    DocumentExtraction.query.filter_by(document_id=document.id).delete()
    for name, value in findings.get("fields") or []:
        db.session.add(
            DocumentExtraction(
                document_id=document.id,
                field_name=name,
                field_value=value,
                needs_review=True,
            )
        )
    if findings.get("document_date"):
        document.document_date = parse_date(findings["document_date"]) or document.document_date
    if findings.get("facility_or_doctor"):
        document.facility_name = findings["facility_or_doctor"]

    for med in findings.get("medications") or []:
        db.session.add(
            Medication(
                patient_id=document.patient_id,
                document_id=document.id,
                name=med["name"],
                dosage=med.get("dosage") or None,
                source="extraction",
            )
        )
    for lab in findings.get("labs") or []:
        db.session.add(
            LabResult(
                patient_id=document.patient_id,
                document_id=document.id,
                test_name=lab["test_name"],
                value=lab.get("value"),
                unit=lab.get("unit"),
                ref_low=lab.get("ref_low"),
                ref_high=lab.get("ref_high"),
                flag=lab.get("flag") or "needs_manual_review",
                collected_on=document.document_date,
            )
        )


def process_document(document: MedicalDocument, filepath: str):
    document.status = "ocr_processing"
    db.session.commit()
    text, message = extract_text(filepath, document.mime_type or "")
    document.ocr_message = message
    if text is None:
        document.status = "needs_manual_review"
        document.ocr_text = ""
        db.session.commit()
        return
    document.ocr_text = text
    if not text:
        document.status = "needs_manual_review"
        db.session.commit()
        return
    findings = extract_from_text(text)
    persist_extraction(document, findings)
    document.status = "ocr_completed"
    if not document.document_date:
        document.document_date = parse_date(text)
    add_timeline_event(
        document.patient_id,
        title=f"{document.category}: {document.original_filename}",
        event_type=document.category,
        description=(document.ocr_text or "")[:400],
        event_date=document.document_date or date.today(),
        document_id=document.id,
    )
    db.session.commit()
