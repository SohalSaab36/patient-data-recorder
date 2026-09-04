from datetime import datetime

from extensions import db


class MedicalHistory(db.Model):
    __tablename__ = "medical_histories"

    id = db.Column(db.Integer, primary_key=True)
    case_id = db.Column(
        db.Integer,
        db.ForeignKey("medical_cases.id"),
        nullable=False,
        unique=True,
    )
    previous_diseases = db.Column(db.Text, nullable=False)
    previous_surgeries = db.Column(db.Text, nullable=False)
    hospitalizations = db.Column(db.Text, nullable=False)
    current_medications = db.Column(db.Text, nullable=False)
    allergies = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<MedicalHistory case={self.case_id}>"
