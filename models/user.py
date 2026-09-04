from datetime import datetime

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from extensions import db


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    full_name = db.Column(db.String(120), nullable=False)
    role = db.Column(db.String(20), nullable=False, default="doctor")
    password_hash = db.Column(db.String(255), nullable=False)
    preferred_language = db.Column(db.String(10), nullable=False, default="en")
    pref_large_text = db.Column(db.Boolean, nullable=False, default=False)
    pref_high_contrast = db.Column(db.Boolean, nullable=False, default=False)
    pref_large_buttons = db.Column(db.Boolean, nullable=False, default=False)
    pref_simple_language = db.Column(db.Boolean, nullable=False, default=False)
    is_active_account = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    patients = db.relationship("Patient", backref="created_by", lazy=True, foreign_keys="Patient.created_by_id")
    cases = db.relationship("MedicalCase", backref="doctor", lazy=True)
    linked_patient = db.relationship(
        "Patient",
        backref="portal_user",
        uselist=False,
        foreign_keys="Patient.user_id",
    )

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @property
    def is_active(self):
        return bool(self.is_active_account)

    @property
    def is_staff(self):
        return self.role in ("doctor", "admin")

    def __repr__(self):
        return f"<User {self.username}>"
