"""Admin login, account creation, and the editable content on the home page."""
import hmac
import os
import re
from dataclasses import dataclass

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError

from extensions import db, limiter
from models import Announcement, League, QuickLink, Resource, User
from security import hash_password, verify_password

bp = Blueprint("admin", __name__)

EMAIL_RE = re.compile(r"^[^@\s,;<>]+@[^@\s,;<>]+\.[^@\s,;<>]+$")
URL_RE = re.compile(r"^https?://\S+$", re.IGNORECASE)
MIN_PASSWORD_LENGTH = 8


# ---------------------------------------------------------------------------
# The four editable sections share one add / edit / delete implementation.
# To add a field later, add it to the model and to the list below.
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Field:
    name: str
    label: str
    kind: str = "text"      # text | textarea | int | rank | email | url
    required: bool = False
    max_len: int = 500
    help: str = ""


@dataclass(frozen=True)
class Section:
    slug: str
    model: type
    title: str
    singular: str
    fields: tuple
    order: tuple            # column names to sort by


SECTIONS = {
    s.slug: s
    for s in (
        Section("quick-links", QuickLink, "Quick Links", "Quick Link", (
            Field("description", "Description", "textarea", required=True, max_len=2000),
            Field("link", "Link", "url", required=True, max_len=2000),
            Field("rank", "Rank", "rank", help="Lower numbers show first. Leave blank to add at the end."),
        ), ("rank", "id")),
        Section("announcements", Announcement, "Announcements", "Announcement", (
            Field("announcement_item", "Announcement", "textarea", required=True, max_len=2000),
            Field("date_created", "Date Posted", "text", max_len=1000),
            Field("rank", "Rank", "rank", help="Lower numbers show first. Leave blank to add at the end."),
        ), ("rank", "id")),
        Section("resources", Resource, "Resources", "Resource", (
            Field("heading", "Heading", "text", max_len=1000),
            Field("description", "Description", "textarea", required=True, max_len=2000),
            Field("link", "Link or email address", "text", max_len=2000,
                  help="A web address (https://...) or an email address."),
            Field("rank", "Rank", "rank", help="Lower numbers show first. Leave blank to add at the end."),
        ), ("rank", "id")),
        Section("leagues", League, "Squash Leagues", "League", (
            Field("league_number", "League Number", "int", required=True,
                  help="Used in the page addresses (e.g. 1 gives /1-submit_scores). Must be unique."),
            Field("league_name", "League Name", "text", required=True),
            Field("contact_name", "Contact Name"),
            Field("email", "Contact Email", "email", required=True,
                  help="Score and sign-up messages are sent here. Separate several addresses with commas."),
            Field("link", "Standings & Schedule Link", "url", max_len=2000,
                  help="The spreadsheet with standings and schedule."),
            Field("score_form_link", "Score Form Link (optional)", "url", max_len=2000,
                  help="Google Form for submitting scores. If set, 'Submit a Score' goes straight to it."),
            Field("signup_form_link", "Sign-Up Form Link (optional)", "url", max_len=2000,
                  help="Google Form for signing up. If set, 'Sign Up for League' goes straight to it."),
        ), ("league_number", "id")),
    )
}


def _get_section(slug):
    section = SECTIONS.get(slug)
    if section is None:
        abort(404)
    return section


def _ordered(section):
    return section.model.query.order_by(*(getattr(section.model, c) for c in section.order))


def _parse(section, form, item_id=None):
    """Validate submitted form values. Returns (values, errors)."""
    values, errors = {}, []
    for f in section.fields:
        raw = (form.get(f.name) or "").strip()

        if not raw:
            if f.kind == "rank":
                values[f.name] = None        # filled in below
            elif f.required:
                errors.append(f"{f.label} is required.")
            else:
                values[f.name] = ""
            continue

        if len(raw) > f.max_len:
            errors.append(f"{f.label} is too long (maximum {f.max_len} characters).")
        elif f.kind in ("int", "rank"):
            if raw.isdigit() and int(raw) < 1_000_000:
                values[f.name] = int(raw)
            else:
                errors.append(f"{f.label} must be a whole number.")
        elif f.kind == "email":
            addresses = [a.strip() for a in re.split(r"[;,]", raw) if a.strip()]
            if addresses and all(EMAIL_RE.match(a) for a in addresses):
                values[f.name] = ", ".join(addresses)
            else:
                errors.append(f"{f.label} must be a valid email address.")
        elif f.kind == "url":
            if URL_RE.match(raw):
                values[f.name] = raw
            else:
                errors.append(f"{f.label} must start with http:// or https://")
        else:
            values[f.name] = raw

    if section.slug == "leagues" and isinstance(values.get("league_number"), int):
        clash = League.query.filter(League.league_number == values["league_number"], League.id != item_id).first()
        if clash:
            errors.append(f"League number {values['league_number']} is already used by {clash.league_name}.")

    if "rank" in values and values["rank"] is None and not errors:
        values["rank"] = (db.session.query(func.max(section.model.rank)).scalar() or 0) + 1

    return values, errors


def _commit(success_message):
    try:
        db.session.commit()
        flash(success_message, category="success")
        return True
    except IntegrityError:
        db.session.rollback()
        flash("That couldn't be saved because it clashes with an existing entry.", category="error")
        return False


# ---------------------------------------------------------------------------
# Login / logout / account creation
# ---------------------------------------------------------------------------

@bp.route("/admin_login")
def admin_login():
    if current_user.is_authenticated:
        return redirect(url_for("admin.admin_page"))
    return render_template("admin_login.html", page_title="Brampton Squash - Admin Login")


@bp.post("/login")
@limiter.limit("10 per minute; 60 per hour")
def login():
    name = (request.form.get("name") or "").strip()
    password = request.form.get("password") or ""
    user = User.query.filter_by(name=name).first()

    if user:
        ok, needs_rehash = verify_password(user.password, password)
        if ok:
            if needs_rehash:
                user.password = hash_password(password)  # upgrade an old-style hash
                db.session.commit()
            login_user(user, remember=True)
            return redirect(url_for("admin.admin_page"))

    flash("Incorrect name or password.", category="error")
    return redirect(url_for("admin.admin_login"))


@bp.post("/logout")
@login_required
def logout():
    logout_user()
    return redirect("/")


@bp.route("/create_admin", methods=["GET", "POST"])
@limiter.limit("10 per hour", methods=["POST"])
def create_admin():
    page_title = "Brampton Squash - Create Admin"
    if request.method == "GET":
        return render_template("create_admin.html", page_title=page_title, name="")

    name = (request.form.get("name") or "").strip()
    password1 = request.form.get("password1") or ""
    password2 = request.form.get("password2") or ""
    secret_code = request.form.get("secret_code") or ""
    expected_code = os.getenv("secret_code") or ""

    error = None
    # The secret code is checked first so strangers learn nothing else about the site.
    if not expected_code or not hmac.compare_digest(secret_code.encode(), expected_code.encode()):
        error = "That secret code isn't correct. Ask an existing admin for it."
    elif not name or len(name) > 50:
        error = "Please enter a name (up to 50 characters)."
    elif User.query.filter_by(name=name).first():
        error = "That name already exists."
    elif password1 != password2:
        error = "The passwords didn't match."
    elif len(password1) < MIN_PASSWORD_LENGTH:
        error = f"The password is too short. It must be at least {MIN_PASSWORD_LENGTH} characters."

    if error:
        flash(error, category="error")
        return render_template("create_admin.html", page_title=page_title, name=name)

    db.session.add(User(name=name, password=hash_password(password1)))
    if _commit("Account created! Please remember your password. There is currently no way to look it up if it's forgotten."):
        return redirect(url_for("admin.admin_login"))
    return render_template("create_admin.html", page_title=page_title, name=name)


@bp.post("/admin/users/<int:user_id>/delete")
@login_required
def delete_user(user_id):
    user = db.get_or_404(User, user_id)
    if user.id == current_user.id:
        flash("You can't delete the account you're logged in with.", category="error")
    elif User.query.count() <= 1:
        flash("You can't delete the last admin account.", category="error")
    else:
        db.session.delete(user)
        _commit(f"Admin user {user.name} deleted.")
    return redirect(url_for("admin.admin_page"))


# ---------------------------------------------------------------------------
# Admin page and the add / edit / delete routes
# ---------------------------------------------------------------------------

@bp.route("/admin_page")
@login_required
def admin_page():
    return render_template(
        "admin_page.html",
        page_title="Brampton Squash - Admin Page",
        sections=[(s, _ordered(s).all()) for s in SECTIONS.values()],
        all_users=User.query.order_by(User.name).all(),
    )


@bp.post("/admin/<slug>/add")
@login_required
def add_item(slug):
    section = _get_section(slug)
    values, errors = _parse(section, request.form)
    if errors:
        for message in errors:
            flash(message, category="error")
    else:
        db.session.add(section.model(**values))
        _commit(f"{section.singular} added.")
    return redirect(url_for("admin.admin_page") + f"#{slug}")


@bp.route("/admin/<slug>/<int:item_id>/edit", methods=["GET", "POST"])
@login_required
def edit_item(slug, item_id):
    section = _get_section(slug)
    item = db.get_or_404(section.model, item_id)
    page_title = f"Brampton Squash - Update {section.singular}"

    if request.method == "POST":
        values, errors = _parse(section, request.form, item_id=item.id)
        if not errors:
            for name, value in values.items():
                setattr(item, name, value)
            if _commit(f"{section.singular} updated."):
                return redirect(url_for("admin.admin_page") + f"#{slug}")
        else:
            for message in errors:
                flash(message, category="error")
        current = request.form
    else:
        current = {f.name: getattr(item, f.name) for f in section.fields}

    return render_template("admin_edit.html", page_title=page_title, section=section, item=item,
                           current=current)


@bp.post("/admin/<slug>/<int:item_id>/delete")
@login_required
def delete_item(slug, item_id):
    section = _get_section(slug)
    item = db.get_or_404(section.model, item_id)
    db.session.delete(item)
    _commit(f"{section.singular} deleted.")
    return redirect(url_for("admin.admin_page") + f"#{slug}")
