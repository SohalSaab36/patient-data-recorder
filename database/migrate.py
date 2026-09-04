"""Add missing columns on existing MySQL databases without wiping data."""

from sqlalchemy import inspect, text

from extensions import db


PATIENT_COLUMNS = {
    "date_of_birth": "DATE NULL",
    "preferred_language": "VARCHAR(10) NOT NULL DEFAULT 'en'",
    "emergency_contact_name": "VARCHAR(150) NULL",
    "emergency_contact_phone": "VARCHAR(20) NULL",
    "abha_id": "VARCHAR(20) NULL",
    "aadhaar_demo": "VARCHAR(20) NULL",
    "user_id": "INT NULL",
}

USER_COLUMNS = {
    "preferred_language": "VARCHAR(10) NOT NULL DEFAULT 'en'",
    "pref_large_text": "TINYINT(1) NOT NULL DEFAULT 0",
    "pref_high_contrast": "TINYINT(1) NOT NULL DEFAULT 0",
    "pref_large_buttons": "TINYINT(1) NOT NULL DEFAULT 0",
    "pref_simple_language": "TINYINT(1) NOT NULL DEFAULT 0",
    "is_active_account": "TINYINT(1) NOT NULL DEFAULT 1",
}


def _existing_columns(table_name):
    inspector = inspect(db.engine)
    if table_name not in inspector.get_table_names():
        return set()
    return {col["name"] for col in inspector.get_columns(table_name)}


def _add_columns(table_name, columns):
    existing = _existing_columns(table_name)
    for name, ddl in columns.items():
        if name in existing:
            continue
        db.session.execute(text(f"ALTER TABLE `{table_name}` ADD COLUMN `{name}` {ddl}"))
        db.session.commit()


def upgrade_schema():
    db.create_all()
    _add_columns("users", USER_COLUMNS)
    _add_columns("patients", PATIENT_COLUMNS)

    inspector = inspect(db.engine)
    if "patients" in inspector.get_table_names():
        indexes = {idx["name"] for idx in inspector.get_indexes("patients")}
        fks = {fk["name"] for fk in inspector.get_foreign_keys("patients")}
        cols = _existing_columns("patients")
        if "user_id" in cols and "uq_patients_user_id" not in indexes:
            try:
                db.session.execute(text("ALTER TABLE patients ADD UNIQUE INDEX uq_patients_user_id (user_id)"))
                db.session.commit()
            except Exception:
                db.session.rollback()
        if "user_id" in cols and "fk_patients_portal_user" not in fks:
            try:
                db.session.execute(
                    text(
                        "ALTER TABLE patients ADD CONSTRAINT fk_patients_portal_user "
                        "FOREIGN KEY (user_id) REFERENCES users(id)"
                    )
                )
                db.session.commit()
            except Exception:
                db.session.rollback()
