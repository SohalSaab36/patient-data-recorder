from datetime import datetime

from extensions import db


class ClinicalSession(db.Model):
    __tablename__ = "clinical_sessions"

    id = db.Column(db.Integer, primary_key=True)
    session_number = db.Column(db.String(30), unique=True, nullable=False)
    patient_id = db.Column(db.Integer, db.ForeignKey("patients.id"), nullable=False)
    doctor_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    status = db.Column(db.String(30), nullable=False, default="in_progress")
    current_question_id = db.Column(db.String(80), nullable=False, default="q_category")
    flow_category = db.Column(db.String(50), nullable=True)
    language = db.Column(db.String(10), nullable=False, default="en")
    ayush_enabled = db.Column(db.Boolean, nullable=False, default=False)
    is_priority = db.Column(db.Boolean, nullable=False, default=False)
    progress_pct = db.Column(db.Integer, nullable=False, default=0)
    doctor_feedback = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime, nullable=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    patient = db.relationship("Patient", backref="clinical_sessions")
    reviewer = db.relationship("User", foreign_keys=[doctor_id])
    answers = db.relationship(
        "ClinicalAnswer",
        backref="session",
        lazy=True,
        cascade="all, delete-orphan",
        order_by="ClinicalAnswer.id",
    )
    summary = db.relationship(
        "ClinicalSummary",
        backref="session",
        uselist=False,
        cascade="all, delete-orphan",
    )


class ClinicalAnswer(db.Model):
    __tablename__ = "clinical_answers"

    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey("clinical_sessions.id"), nullable=False)
    question_id = db.Column(db.String(80), nullable=False)
    question_text = db.Column(db.Text, nullable=False)
    section = db.Column(db.String(50), nullable=False, default="general")
    answer_text = db.Column(db.Text, nullable=False)
    answer_type = db.Column(db.String(20), nullable=False, default="text")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class ClinicalSummary(db.Model):
    __tablename__ = "clinical_summaries"

    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey("clinical_sessions.id"), nullable=False, unique=True)
    patient_id = db.Column(db.Integer, db.ForeignKey("patients.id"), nullable=False)
    status = db.Column(db.String(30), nullable=False, default="draft")
    chief_complaint = db.Column(db.Text, nullable=True)
    hpi = db.Column(db.Text, nullable=True)
    past_medical = db.Column(db.Text, nullable=True)
    past_surgical = db.Column(db.Text, nullable=True)
    drug_history = db.Column(db.Text, nullable=True)
    allergy_history = db.Column(db.Text, nullable=True)
    family_history = db.Column(db.Text, nullable=True)
    personal_history = db.Column(db.Text, nullable=True)
    review_of_systems = db.Column(db.Text, nullable=True)
    prior_investigations = db.Column(db.Text, nullable=True)
    document_timeline = db.Column(db.Text, nullable=True)
    red_flag_notes = db.Column(db.Text, nullable=True)
    important_notes = db.Column(db.Text, nullable=True)
    generator_mode = db.Column(db.String(30), nullable=False, default="rule-based")
    confirmed_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    confirmed_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    patient = db.relationship("Patient", backref="clinical_summaries")
    confirmed_by = db.relationship("User", foreign_keys=[confirmed_by_id])


class AyushAssessment(db.Model):
    __tablename__ = "ayush_assessments"

    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey("patients.id"), nullable=False)
    session_id = db.Column(db.Integer, db.ForeignKey("clinical_sessions.id"), nullable=True)
    prakriti = db.Column(db.String(50), nullable=True)
    vikriti = db.Column(db.String(50), nullable=True)
    agni = db.Column(db.String(50), nullable=True)
    koshta = db.Column(db.String(50), nullable=True)
    ahara = db.Column(db.Text, nullable=True)
    vihara = db.Column(db.Text, nullable=True)
    nidana = db.Column(db.Text, nullable=True)
    sara = db.Column(db.String(50), nullable=True)
    samhanana = db.Column(db.String(50), nullable=True)
    pramana = db.Column(db.String(50), nullable=True)
    satmya = db.Column(db.String(80), nullable=True)
    sattva = db.Column(db.String(50), nullable=True)
    ahara_shakti = db.Column(db.String(50), nullable=True)
    vyayama_shakti = db.Column(db.String(50), nullable=True)
    vaya = db.Column(db.String(50), nullable=True)
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    patient = db.relationship("Patient", backref="ayush_assessments")
