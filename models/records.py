from datetime import datetime

from extensions import db


class MedicalDocument(db.Model):
    __tablename__ = "medical_documents"

    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey("patients.id"), nullable=False)
    session_id = db.Column(db.Integer, db.ForeignKey("clinical_sessions.id"), nullable=True)
    original_filename = db.Column(db.String(255), nullable=False)
    stored_name = db.Column(db.String(255), nullable=False)
    category = db.Column(db.String(50), nullable=False)
    mime_type = db.Column(db.String(80), nullable=True)
    status = db.Column(db.String(40), nullable=False, default="uploaded")
    ocr_text = db.Column(db.Text, nullable=True)
    ocr_message = db.Column(db.String(255), nullable=True)
    document_date = db.Column(db.Date, nullable=True)
    facility_name = db.Column(db.String(200), nullable=True)
    uploaded_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    patient = db.relationship("Patient", backref="documents")
    uploaded_by = db.relationship("User")
    extractions = db.relationship(
        "DocumentExtraction",
        backref="document",
        cascade="all, delete-orphan",
        lazy=True,
    )


class DocumentExtraction(db.Model):
    __tablename__ = "document_extractions"

    id = db.Column(db.Integer, primary_key=True)
    document_id = db.Column(db.Integer, db.ForeignKey("medical_documents.id"), nullable=False)
    field_name = db.Column(db.String(80), nullable=False)
    field_value = db.Column(db.Text, nullable=False)
    needs_review = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Medication(db.Model):
    __tablename__ = "medications"

    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey("patients.id"), nullable=False)
    document_id = db.Column(db.Integer, db.ForeignKey("medical_documents.id"), nullable=True)
    name = db.Column(db.String(150), nullable=False)
    dosage = db.Column(db.String(80), nullable=True)
    frequency = db.Column(db.String(80), nullable=True)
    source = db.Column(db.String(40), nullable=False, default="extraction")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    patient = db.relationship("Patient", backref="medications")


class LabResult(db.Model):
    __tablename__ = "lab_results"

    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey("patients.id"), nullable=False)
    document_id = db.Column(db.Integer, db.ForeignKey("medical_documents.id"), nullable=True)
    test_name = db.Column(db.String(150), nullable=False)
    value = db.Column(db.String(50), nullable=True)
    unit = db.Column(db.String(40), nullable=True)
    ref_low = db.Column(db.String(40), nullable=True)
    ref_high = db.Column(db.String(40), nullable=True)
    flag = db.Column(db.String(40), nullable=False, default="needs_manual_review")
    collected_on = db.Column(db.Date, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    patient = db.relationship("Patient", backref="lab_results")
    document = db.relationship("MedicalDocument", backref="lab_results")


class TimelineEvent(db.Model):
    __tablename__ = "medical_timeline"

    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey("patients.id"), nullable=False)
    event_date = db.Column(db.Date, nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    event_type = db.Column(db.String(40), nullable=False)
    document_id = db.Column(db.Integer, db.ForeignKey("medical_documents.id"), nullable=True)
    session_id = db.Column(db.Integer, db.ForeignKey("clinical_sessions.id"), nullable=True)
    case_id = db.Column(db.Integer, db.ForeignKey("medical_cases.id"), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    patient = db.relationship("Patient", backref="timeline_events")
    document = db.relationship("MedicalDocument")
    session = db.relationship("ClinicalSession")
    case = db.relationship("MedicalCase")
