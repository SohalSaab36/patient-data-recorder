from datetime import datetime

from extensions import db


class MedicalCase(db.Model):
    __tablename__ = "medical_cases"

    id = db.Column(db.Integer, primary_key=True)
    case_number = db.Column(db.String(30), unique=True, nullable=False)
    patient_id = db.Column(db.Integer, db.ForeignKey("patients.id"), nullable=False)
    doctor_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    main_symptoms = db.Column(db.Text, nullable=False)
    duration = db.Column(db.String(100), nullable=False)
    severity = db.Column(db.String(20), nullable=False)

    present_illness_description = db.Column(db.Text, nullable=False)
    symptoms_started = db.Column(db.String(150), nullable=False)
    progression = db.Column(db.Text, nullable=False)

    family_history = db.Column(db.Text, nullable=False)

    diet = db.Column(db.Text, nullable=False)
    sleep = db.Column(db.Text, nullable=False)
    lifestyle = db.Column(db.Text, nullable=False)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    history = db.relationship(
        "MedicalHistory",
        backref="medical_case",
        uselist=False,
        cascade="all, delete-orphan",
    )

    def __repr__(self):
        return f"<MedicalCase {self.case_number}>"
