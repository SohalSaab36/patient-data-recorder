from flask import Blueprint, flash, redirect, render_template, url_for
from flask_login import login_required
from sqlalchemy.exc import SQLAlchemyError

from extensions import db
from models.clinical import ClinicalSession
from models.patient import Patient
from models.privacy import AuditLog, RedFlagAlert
from models.records import MedicalDocument
from models.user import User
from utils.helpers import roles_required, write_audit

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


@admin_bp.route("/")
@login_required
@roles_required("admin")
def home():
    stats = {
        "users": User.query.count(),
        "patients": Patient.query.count(),
        "sessions": ClinicalSession.query.count(),
        "documents": MedicalDocument.query.count(),
        "open_alerts": RedFlagAlert.query.filter_by(acknowledged=False).count(),
    }
    users = User.query.order_by(User.created_at.desc()).limit(50).all()
    logs = AuditLog.query.order_by(AuditLog.created_at.desc()).limit(40).all()
    return render_template("admin/home.html", stats=stats, users=users, logs=logs)


@admin_bp.route("/users/<int:user_id>/toggle", methods=["POST"])
@login_required
@roles_required("admin")
def toggle_user(user_id):
    user = User.query.get_or_404(user_id)
    if user.role == "admin":
        flash("The primary admin account cannot be disabled from here.", "warning")
        return redirect(url_for("admin.home"))
    user.is_active_account = not user.is_active_account
    write_audit("toggle_user", "user", user.id, details=str(user.is_active_account))
    try:
        db.session.commit()
    except SQLAlchemyError:
        db.session.rollback()
        flash("Could not update user.", "danger")
    return redirect(url_for("admin.home"))
