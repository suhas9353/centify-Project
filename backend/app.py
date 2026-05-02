import os
import uuid
import logging
from datetime import datetime, timezone

from flask import Flask, request, jsonify
from flask_jwt_extended import (
    create_access_token,
    jwt_required,
    get_jwt_identity,
)

from config import Config
from extensions import db, jwt, bcrypt, cors

# ─── App Factory ────────────────────────────────────────────────────────────

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Init extensions
    db.init_app(app)
    jwt.init_app(app)
    bcrypt.init_app(app)
    cors.init_app(app, resources={r"/*": {"origins": app.config["CORS_ORIGINS"]}})

    # Import models inside factory to avoid circular imports
    from models import Admin, Opportunity, PasswordResetToken  # noqa: F401

    # Create tables
    with app.app_context():
        db.create_all()

    # Register routes
    register_routes(app)

    return app


# ─── Helpers ────────────────────────────────────────────────────────────────

def success(data=None, message="Success", status=200):
    payload = {"success": True, "message": message}
    if data is not None:
        payload["data"] = data
    return jsonify(payload), status


def error(message="An error occurred", status=400):
    return jsonify({"success": False, "message": message}), status


# ─── Route Registration ─────────────────────────────────────────────────────

def register_routes(app):

    # ── Auth ────────────────────────────────────────────────────────────────

    @app.route("/signup", methods=["POST"])
    def signup():
        from models import Admin

        data = request.get_json(silent=True) or {}

        full_name = (data.get("full_name") or "").strip()
        email = (data.get("email") or "").strip().lower()
        password = data.get("password") or ""
        confirm_password = data.get("confirm_password") or ""

        # Validation
        if not full_name:
            return error("Full name is required.")
        if not email:
            return error("Email is required.")
        if "@" not in email or "." not in email.split("@")[-1]:
            return error("Please provide a valid email address.")
        if not password:
            return error("Password is required.")
        if len(password) < 8:
            return error("Password must be at least 8 characters long.")
        if password != confirm_password:
            return error("Passwords do not match.")

        # Uniqueness check
        if Admin.query.filter_by(email=email).first():
            return error("An account with this email already exists.")

        # Create admin
        hashed_pw = bcrypt.generate_password_hash(password).decode("utf-8")
        admin = Admin(full_name=full_name, email=email, password_hash=hashed_pw)
        db.session.add(admin)
        db.session.commit()

        token = create_access_token(identity=str(admin.id))
        return success(
            data={"token": token, "admin": admin.to_dict()},
            message="Account created successfully.",
            status=201,
        )

    @app.route("/login", methods=["POST"])
    def login():
        from models import Admin

        data = request.get_json(silent=True) or {}

        email = (data.get("email") or "").strip().lower()
        password = data.get("password") or ""
        remember_me = bool(data.get("remember_me", False))

        if not email or not password:
            return error("Invalid email or password.")

        admin = Admin.query.filter_by(email=email).first()
        if not admin or not bcrypt.check_password_hash(admin.password_hash, password):
            return error("Invalid email or password.")

        # Extended expiry when "Remember Me" is checked
        expires = (
            app.config["JWT_REMEMBER_ME_EXPIRES"]
            if remember_me
            else app.config["JWT_ACCESS_TOKEN_EXPIRES"]
        )
        token = create_access_token(identity=str(admin.id), expires_delta=expires)

        return success(
            data={"token": token, "admin": admin.to_dict()},
            message="Logged in successfully.",
        )

    @app.route("/forgot-password", methods=["POST"])
    def forgot_password():
        from models import Admin, PasswordResetToken

        data = request.get_json(silent=True) or {}
        email = (data.get("email") or "").strip().lower()

        # Always return the same message to prevent email enumeration
        generic_msg = (
            "If an account with that email exists, "
            "a password reset link has been sent."
        )

        if not email:
            return success(message=generic_msg)

        admin = Admin.query.filter_by(email=email).first()
        if admin:
            token_str = str(uuid.uuid4())
            expires_at = datetime.now(timezone.utc) + app.config["PASSWORD_RESET_TOKEN_EXPIRES"]

            reset_token = PasswordResetToken(
                email=email, token=token_str, expires_at=expires_at
            )
            db.session.add(reset_token)
            db.session.commit()

            reset_link = f"http://localhost:5000/reset-password/{token_str}"
            logging.info(
                "[Forgot Password] Reset link for %s : %s", email, reset_link
            )

        return success(message=generic_msg)

    @app.route("/reset-password/<token>", methods=["POST"])
    def reset_password(token):
        from models import Admin, PasswordResetToken

        data = request.get_json(silent=True) or {}
        new_password = data.get("password") or ""
        confirm_password = data.get("confirm_password") or ""

        if len(new_password) < 8:
            return error("Password must be at least 8 characters long.")
        if new_password != confirm_password:
            return error("Passwords do not match.")

        reset_token = PasswordResetToken.query.filter_by(token=token, used=False).first()
        if not reset_token:
            return error("Invalid or expired reset token.", 400)

        if reset_token.expires_at.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
            return error("This reset link has expired. Please request a new one.", 400)

        admin = Admin.query.filter_by(email=reset_token.email).first()
        if not admin:
            return error("Account not found.", 404)

        admin.password_hash = bcrypt.generate_password_hash(new_password).decode("utf-8")
        reset_token.used = True
        db.session.commit()

        return success(message="Password has been reset successfully. You may now log in.")

    # ── Opportunities ────────────────────────────────────────────────────────

    @app.route("/opportunities", methods=["GET"])
    @jwt_required()
    def get_opportunities():
        from models import Opportunity

        admin_id = int(get_jwt_identity())
        opportunities = (
            Opportunity.query.filter_by(admin_id=admin_id)
            .order_by(Opportunity.created_at.desc())
            .all()
        )
        return success(data=[o.to_dict() for o in opportunities])

    @app.route("/opportunities", methods=["POST"])
    @jwt_required()
    def create_opportunity():
        from models import Opportunity

        admin_id = int(get_jwt_identity())
        data = request.get_json(silent=True) or {}

        title = (data.get("title") or "").strip()
        description = (data.get("description") or "").strip()
        category = (data.get("category") or "").strip()
        location = (data.get("location") or "").strip()
        deadline = (data.get("deadline") or "").strip()
        status = (data.get("status") or "active").strip()

        # Required field validation
        missing = [
            field
            for field, value in {
                "title": title,
                "description": description,
                "category": category,
                "location": location,
                "deadline": deadline,
            }.items()
            if not value
        ]
        if missing:
            return error(f"Missing required fields: {', '.join(missing)}.")

        opportunity = Opportunity(
            title=title,
            description=description,
            category=category,
            location=location,
            deadline=deadline,
            status=status,
            admin_id=admin_id,
        )
        db.session.add(opportunity)
        db.session.commit()

        return success(
            data=opportunity.to_dict(),
            message="Opportunity created successfully.",
            status=201,
        )

    @app.route("/opportunities/<int:opportunity_id>", methods=["PUT"])
    @jwt_required()
    def update_opportunity(opportunity_id):
        from models import Opportunity

        admin_id = int(get_jwt_identity())
        opportunity = Opportunity.query.filter_by(
            id=opportunity_id, admin_id=admin_id
        ).first()

        if not opportunity:
            return error("Opportunity not found or access denied.", 404)

        data = request.get_json(silent=True) or {}

        # Only update provided fields
        if "title" in data:
            title = (data["title"] or "").strip()
            if not title:
                return error("Title cannot be empty.")
            opportunity.title = title

        if "description" in data:
            description = (data["description"] or "").strip()
            if not description:
                return error("Description cannot be empty.")
            opportunity.description = description

        if "category" in data:
            category = (data["category"] or "").strip()
            if not category:
                return error("Category cannot be empty.")
            opportunity.category = category

        if "location" in data:
            location = (data["location"] or "").strip()
            if not location:
                return error("Location cannot be empty.")
            opportunity.location = location

        if "deadline" in data:
            deadline = (data["deadline"] or "").strip()
            if not deadline:
                return error("Deadline cannot be empty.")
            opportunity.deadline = deadline

        if "status" in data:
            status = (data["status"] or "").strip()
            if not status:
                return error("Status cannot be empty.")
            opportunity.status = status

        opportunity.updated_at = datetime.utcnow()
        db.session.commit()

        return success(
            data=opportunity.to_dict(),
            message="Opportunity updated successfully.",
        )

    @app.route("/opportunities/<int:opportunity_id>", methods=["DELETE"])
    @jwt_required()
    def delete_opportunity(opportunity_id):
        from models import Opportunity

        admin_id = int(get_jwt_identity())
        opportunity = Opportunity.query.filter_by(
            id=opportunity_id, admin_id=admin_id
        ).first()

        if not opportunity:
            return error("Opportunity not found or access denied.", 404)

        db.session.delete(opportunity)
        db.session.commit()

        return success(message="Opportunity deleted successfully.")

    # ── Health Check ─────────────────────────────────────────────────────────

    @app.route("/health", methods=["GET"])
    def health():
        return success(message="Qatar Foundation Admin API is running.")

    # ── 404 / 405 Handlers ──────────────────────────────────────────────────

    @app.errorhandler(404)
    def not_found(_):
        return error("The requested resource was not found.", 404)

    @app.errorhandler(405)
    def method_not_allowed(_):
        return error("Method not allowed.", 405)

    @app.errorhandler(422)
    def unprocessable(_):
        return error("Invalid or missing JWT token.", 422)


# ─── Entrypoint ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    app = create_app()
    app.run(debug=True, port=5000)
