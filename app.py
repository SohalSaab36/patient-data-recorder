import os

from flask import Flask, render_template
from flask_login import current_user
from sqlalchemy.exc import OperationalError

from config import Config
from extensions import db, login_manager
from models.clinical import AyushAssessment, ClinicalAnswer, ClinicalSession, ClinicalSummary  # noqa: F401
from models.medical_case import MedicalCase  # noqa: F401
from models.medical_history import MedicalHistory  # noqa: F401
from models.patient import Patient
from models.privacy import AuditLog, Consent, RedFlagAlert  # noqa: F401
from models.records import DocumentExtraction, LabResult, MedicalDocument, Medication, TimelineEvent  # noqa: F401
from models.user import User
from utils.helpers import generate_patient_id


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    db.init_app(app)
    login_manager.init_app(app)

    from routes.admin import admin_bp
    from routes.auth import auth_bp
    from routes.cases import cases_bp
    from routes.clinical import clinical_bp
    from routes.dashboard import dashboard_bp
    from routes.documents import documents_bp
    from routes.patients import patients_bp
    from routes.portal import portal_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(patients_bp)
    app.register_blueprint(cases_bp)
    app.register_blueprint(portal_bp)
    app.register_blueprint(documents_bp)
    app.register_blueprint(clinical_bp)
    app.register_blueprint(admin_bp)

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    @app.context_processor
    def inject_ui():
        classes = []
        if current_user.is_authenticated:
            if getattr(current_user, "pref_large_text", False):
                classes.append("a11y-large-text")
            if getattr(current_user, "pref_high_contrast", False):
                classes.append("a11y-contrast")
            if getattr(current_user, "pref_large_buttons", False):
                classes.append("a11y-large-buttons")
            if getattr(current_user, "pref_simple_language", False):
                classes.append("a11y-simple")
        return {"a11y_classes": " ".join(classes), "attr": getattr}

    @app.errorhandler(403)
    def forbidden(_error):
        return (
            render_template(
                "errors/simple.html",
                title="Not allowed",
                heading="You do not have access",
                message="This area is limited to another role. Sign in with the correct account.",
            ),
            403,
        )

    @app.errorhandler(404)
    def not_found(_error):
        return (
            render_template(
                "errors/simple.html",
                title="Not found",
                heading="Page not found",
                message="The page you requested does not exist.",
            ),
            404,
        )

    @app.errorhandler(500)
    def server_error(_error):
        return (
            render_template(
                "errors/simple.html",
                title="Server error",
                heading="Something went wrong",
                message="Please try again. If the problem continues, check the application logs.",
            ),
            500,
        )

    with app.app_context():
        try:
            from database.migrate import upgrade_schema

            upgrade_schema()
            _seed_accounts()
        except OperationalError as exc:
            print("\nCould not connect to the configured database.")
            print("Check DATABASE_URL or the MySQL settings in .env. See README.md.")
            print(f"Details: {exc}\n")

    return app


def _seed_accounts():
    if not User.query.filter_by(username="admin").first():
        admin = User(
            username="admin",
            email="admin@clinic.local",
            full_name="Clinic Administrator",
            role="admin",
        )
        admin.set_password("admin123")
        db.session.add(admin)
        db.session.commit()
        print("Default admin account created: username=admin  password=admin123")

    if not User.query.filter_by(username="doctor").first():
        doctor = User(
            username="doctor",
            email="doctor@clinic.local",
            full_name="Demo Doctor",
            role="doctor",
        )
        doctor.set_password("doctor123")
        db.session.add(doctor)
        db.session.commit()
        print("Demo doctor created: username=doctor  password=doctor123")

    if not User.query.filter_by(username="patient").first():
        doctor = User.query.filter_by(role="doctor").first() or User.query.filter_by(role="admin").first()
        user = User(
            username="patient",
            email="patient@clinic.local",
            full_name="Demo Patient",
            role="patient",
            preferred_language="en",
        )
        user.set_password("patient123")
        db.session.add(user)
        db.session.flush()
        patient = Patient(
            patient_id=generate_patient_id(),
            full_name="Demo Patient",
            age=42,
            gender="Female",
            phone="9999900001",
            address="Demo Nagar, Ward 1",
            preferred_language="en",
            emergency_contact_name="Demo Relative",
            emergency_contact_phone="9999900002",
            abha_id="12-3456-7890-1234",
            user_id=user.id,
            created_by_id=doctor.id if doctor else user.id,
        )
        db.session.add(patient)
        db.session.commit()
        print("Demo patient created: username=patient  password=patient123")


app = create_app()

if __name__ == "__main__":
    app.run(debug=True)
