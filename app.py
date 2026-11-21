"""Brampton Squash Leagues website.

Run locally:   python app.py          (uses a throwaway SQLite database)
Run on Heroku: gunicorn app:app       (uses the DATABASE_URL Heroku provides)
"""
import os

from dotenv import load_dotenv
from flask import Flask, flash, redirect, render_template, request
from flask_limiter.errors import RateLimitExceeded
from flask_wtf.csrf import CSRFError
from werkzeug.middleware.proxy_fix import ProxyFix

from extensions import csrf, db, limiter, login_manager
from models import League, User

load_dotenv()

# Shown in the page header and footer. Edit here and both update.
VENUES = [
    {
        "name": "Jim Archdekin Recreation Centre",
        "address": "292 Conestoga Drive",
        "phone": "905-840-1023",
        "url": "https://www.brampton.ca/EN/residents/Recreation/Community-Centres/Pages/Jim-Archdekin.aspx",
    },
    {
        "name": "Riverstone Community Centre",
        "address": "195 Don Minaker Drive",
        "phone": "905-874-3536",
        "url": "https://www.brampton.ca/EN/residents/Recreation/Community-Centres/Pages/Riverstone-Community-Centre.aspx",
    },
    {
        "name": "Paul Palleschi Recreation Centre",
        "address": "30 Loafers Lake Lane",
        "phone": "905-846-2370",
        "url": "https://www.brampton.ca/EN/residents/Recreation/Community-Centres/Pages/Loafers-Lake.aspx",
    },
]


def create_app():
    app = Flask(__name__)

    # Heroku sets DATABASE_URL, so its presence means "live site".
    # Without it we're on a dev machine and use a local SQLite file.
    database_url = os.getenv("DATABASE_URL")
    is_prod = bool(database_url)
    app.config["IS_PROD"] = is_prod

    if is_prod:
        # Heroku hands out postgres:// but SQLAlchemy needs postgresql://
        if database_url.startswith("postgres://"):
            database_url = "postgresql://" + database_url[len("postgres://"):]
        app.config["SQLALCHEMY_DATABASE_URI"] = database_url
        # Heroku drops idle connections; check before reusing one.
        app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {"pool_pre_ping": True, "pool_recycle": 300}
        # Trust Heroku's router for the real client IP and https/http.
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)
    else:
        app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///dev.db"  # stored in instance/dev.db

    secret_key = os.getenv("secret_key")
    if not secret_key:
        if is_prod:
            raise RuntimeError("The secret_key config var is not set")
        secret_key = "dev-only-secret-key"
    app.config["SECRET_KEY"] = secret_key

    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["WTF_CSRF_TIME_LIMIT"] = None  # form tokens last as long as the login session
    # Still requires the secret CSRF token on every form. Only skips the extra "Referer header" check,
    # which breaks for visitors whose browser or privacy tool strips that header.
    app.config["WTF_CSRF_SSL_STRICT"] = False
    app.config["SESSION_COOKIE_HTTPONLY"] = True
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
    app.config["REMEMBER_COOKIE_HTTPONLY"] = True
    app.config["REMEMBER_COOKIE_SAMESITE"] = "Lax"
    app.config["REMEMBER_COOKIE_DURATION"] = 60 * 60 * 24 * 30  # stay logged in 30 days
    force_https = is_prod and os.getenv("FORCE_HTTPS", "1") != "0"
    app.config["SESSION_COOKIE_SECURE"] = force_https
    app.config["REMEMBER_COOKIE_SECURE"] = force_https

    db.init_app(app)
    csrf.init_app(app)
    limiter.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = "admin.admin_login"
    login_manager.login_message = "Please log in to see that page."
    login_manager.login_message_category = "error"

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    from admin import bp as admin_bp
    from public import bp as public_bp

    app.register_blueprint(public_bp)
    app.register_blueprint(admin_bp)

    @app.context_processor
    def inject_globals():
        # Every page's menu needs the league list.
        try:
            nav_leagues = League.query.order_by(League.league_number).all()
        except Exception:
            db.session.rollback()
            nav_leagues = []
        return {"nav_leagues": nav_leagues, "venues": VENUES}

    @app.before_request
    def redirect_to_https():
        if force_https and not request.is_secure:
            return redirect(request.url.replace("http://", "https://", 1), code=301)

    @app.after_request
    def security_headers(response):
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "SAMEORIGIN")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        return response

    @app.errorhandler(CSRFError)
    def csrf_failed(_error):
        flash("That page expired. Please try again.", category="error")
        return redirect(request.referrer or "/")

    @app.errorhandler(404)
    def not_found(_error):
        return render_template("error.html", page_title="Page Not Found", heading="Page not found",
                               message="We couldn't find that page."), 404

    @app.errorhandler(RateLimitExceeded)
    def too_many_requests(_error):
        return render_template("error.html", page_title="Slow Down", heading="Too many attempts",
                               message="Please wait a little while and try again."), 429

    @app.errorhandler(500)
    def server_error(_error):
        db.session.rollback()
        return render_template("error.html", page_title="Error", heading="Something went wrong",
                               message="Please try again in a few minutes."), 500

    if not is_prod:
        from schema import ensure_schema
        with app.app_context():
            ensure_schema()

    return app


app = create_app()

if __name__ == "__main__":
    # Local testing from a phone on the same Wi-Fi:  HOST=0.0.0.0 python app.py
    host = os.getenv("HOST", "127.0.0.1")
    # Debug mode stays off when the site is reachable from other devices.
    app.run(host=host, debug=(not app.config["IS_PROD"]) and host == "127.0.0.1")
