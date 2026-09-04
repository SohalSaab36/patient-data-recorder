from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user
from sqlalchemy.exc import SQLAlchemyError

from extensions import db
from models.patient import Patient
from models.user import User
from utils.helpers import generate_patient_id, post_login_redirect, write_audit

auth_bp = Blueprint("auth", __name__)


def _age_from_dob(dob_str):
    if not dob_str:
        return None
    from datetime import date, datetime

    try:
        dob = datetime.strptime(dob_str, "%Y-%m-%d").date()
    except ValueError:
        return None
    today = date.today()
    return today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(post_login_redirect())

    if request.method == "POST":
        username = (request.form.get("username") or "").strip()
        password = request.form.get("password") or ""

        if not username or not password:
            flash("Username and password are required.", "danger")
            return render_template("login.html")

        user = User.query.filter(
            (User.username == username) | (User.email == username)
        ).first()

        if user and user.is_active_account and user.check_password(password):
            login_user(user)
            write_audit("login", "user", user.id)
            db.session.commit()
            next_page = request.args.get("next")
            flash(f"Welcome back, {user.full_name}.", "success")
            if next_page:
                return redirect(next_page)
            return redirect(post_login_redirect())

        flash("Invalid username or password.", "danger")

    return render_template("login.html")


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(post_login_redirect())

    if request.method == "POST":
        username = (request.form.get("username") or "").strip()
        email = (request.form.get("email") or "").strip().lower()
        password = request.form.get("password") or ""
        full_name = (request.form.get("full_name") or "").strip()
        phone = (request.form.get("phone") or "").strip()
        address = (request.form.get("address") or "").strip()
        gender = (request.form.get("gender") or "").strip()
        language = (request.form.get("preferred_language") or "en").strip()
        dob = (request.form.get("date_of_birth") or "").strip()
        age_raw = (request.form.get("age") or "").strip()
        emergency_name = (request.form.get("emergency_contact_name") or "").strip()
        emergency_phone = (request.form.get("emergency_contact_phone") or "").strip()
        abha_id = (request.form.get("abha_id") or "").strip()
        aadhaar_demo = (request.form.get("aadhaar_demo") or "").strip()

        errors = []
        if len(username) < 3:
            errors.append("Username must be at least 3 characters.")
        if "@" not in email:
            errors.append("A valid email is required.")
        if len(password) < 6:
            errors.append("Password must be at least 6 characters.")
        if len(full_name) < 2:
            errors.append("Full name is required.")
        if gender not in ("Male", "Female", "Other"):
            errors.append("Select a valid gender.")
        if len(phone) < 8:
            errors.append("Phone number is required.")
        if len(address) < 5:
            errors.append("Address is required.")
        age = _age_from_dob(dob)
        if age is None:
            try:
                age = int(age_raw)
            except ValueError:
                age = None
        if age is None or age < 0 or age > 130:
            errors.append("Enter a valid age or date of birth.")
        if language not in ("en", "hi"):
            language = "en"
        if User.query.filter((User.username == username) | (User.email == email)).first():
            errors.append("That username or email is already registered.")
        if Patient.query.filter_by(phone=phone).first():
            errors.append("A patient with this phone number already exists. Ask staff to link a portal login.")

        if errors:
            for err in errors:
                flash(err, "danger")
            return render_template("register.html", form=request.form)

        user = User(
            username=username,
            email=email,
            full_name=full_name,
            role="patient",
            preferred_language=language,
        )
        user.set_password(password)
        db.session.add(user)
        try:
            db.session.flush()
            from datetime import datetime as dt

            dob_val = None
            if dob:
                try:
                    dob_val = dt.strptime(dob, "%Y-%m-%d").date()
                except ValueError:
                    dob_val = None
            patient = Patient(
                patient_id=generate_patient_id(),
                full_name=full_name,
                age=age,
                date_of_birth=dob_val,
                gender=gender,
                phone=phone,
                address=address,
                preferred_language=language,
                emergency_contact_name=emergency_name or None,
                emergency_contact_phone=emergency_phone or None,
                abha_id=abha_id or None,
                aadhaar_demo=aadhaar_demo or None,
                user_id=user.id,
                created_by_id=user.id,
            )
            db.session.add(patient)
            write_audit("register_patient", "user", user.id, patient_id=None)
            db.session.commit()
        except SQLAlchemyError:
            db.session.rollback()
            flash("Could not complete registration. Please try again.", "danger")
            return render_template("register.html", form=request.form)

        login_user(user)
        flash("Account created. Please review consent before starting an interview.", "success")
        return redirect(url_for("portal.consent"))

    return render_template("register.html", form={})


@auth_bp.route("/accessibility", methods=["POST"])
@login_required
def accessibility():
    current_user.pref_large_text = bool(request.form.get("pref_large_text"))
    current_user.pref_high_contrast = bool(request.form.get("pref_high_contrast"))
    current_user.pref_large_buttons = bool(request.form.get("pref_large_buttons"))
    current_user.pref_simple_language = bool(request.form.get("pref_simple_language"))
    lang = request.form.get("preferred_language") or current_user.preferred_language
    if lang in ("en", "hi"):
        current_user.preferred_language = lang
        from models.patient import Patient

        linked = Patient.query.filter_by(user_id=current_user.id).first()
        if linked:
            linked.preferred_language = lang
    db.session.commit()
    flash("Accessibility preferences saved.", "success")
    return redirect(request.referrer or post_login_redirect())


@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for("auth.login"))
