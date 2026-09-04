from datetime import datetime

from extensions import db


class Consent(db.Model):
    __tablename__ = "consents"

    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey("patients.id"), nullable=False)
    consent_type = db.Column(db.String(50), nullable=False)
    granted = db.Column(db.Boolean, nullable=False, default=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    withdrawn_at = db.Column(db.DateTime, nullable=True)

    patient = db.relationship("Patient", backref="consents")


class RedFlagAlert(db.Model):
    __tablename__ = "red_flag_alerts"

    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey("patients.id"), nullable=False)
    session_id = db.Column(db.Integer, db.ForeignKey("clinical_sessions.id"), nullable=True)
    matched_phrase = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    acknowledged = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    patient = db.relationship("Patient", backref="red_flag_alerts")
    session = db.relationship("ClinicalSession", backref="red_flag_alerts")


class AuditLog(db.Model):
    __tablename__ = "audit_logs"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    patient_id = db.Column(db.Integer, db.ForeignKey("patients.id"), nullable=True)
    action = db.Column(db.String(80), nullable=False)
    entity_type = db.Column(db.String(50), nullable=True)
    entity_id = db.Column(db.Integer, nullable=True)
    details = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship("User")
