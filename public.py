"""Pages everyone can see: the home page and the per-league forms."""
import re

from flask import Blueprint, flash, redirect, render_template, request

from emailer import send_email
from extensions import limiter
from models import Announcement, League, QuickLink, Resource

bp = Blueprint("public", __name__)

EMAIL_RE = re.compile(r"^[^@\s,;<>]+@[^@\s,;<>]+\.[^@\s,;<>]+$")

# Generous because a whole club night can share one Wi-Fi address.
SCORE_LIMIT = "30 per hour"
SIGNUP_LIMIT = "10 per hour"


def _get_league(league_number):
    return League.query.filter_by(league_number=league_number).first_or_404()


def _field(name, max_len):
    return (request.form.get(name) or "").strip()[:max_len]


def _is_bot():
    # Real visitors never see this hidden field; spam bots tend to fill it in.
    return bool(request.form.get("trap_field_x"))


@bp.route("/")
def home():
    return render_template(
        "home.html",
        page_title="Brampton Squash",
        announcements=Announcement.query.order_by(Announcement.rank, Announcement.id).all(),
        resources=Resource.query.order_by(Resource.rank, Resource.id).all(),
        quick_links=QuickLink.query.order_by(QuickLink.rank, QuickLink.id).all(),
    )


# The URLs keep their old shape (/1-submit_scores) so existing links and bookmarks still work.
@bp.route("/<int:league_number>-submit_scores", methods=["GET", "POST"])
@limiter.limit(SCORE_LIMIT, methods=["POST"])
def submit_scores(league_number):
    league = _get_league(league_number)

    # A Google Form link, if the league has one, replaces the on-site form.
    if league.has_score_form:
        return redirect(league.score_form_link.strip())

    page = dict(page_title=f"{league.league_name} - Submit a Score", league=league)

    if request.method == "GET":
        return render_template("submit_scores.html", form={}, **page)

    if _is_bot():
        flash("Score submitted successfully!", category="success")
        return redirect(request.path)

    data = {
        "p1_name": _field("p1_name", 100),
        "p1_score": _field("p1_score", 20),
        "p2_name": _field("p2_name", 100),
        "p2_score": _field("p2_score", 20),
        "email": _field("email", 200),
        "comments": _field("comments", 2000),
    }
    required = ("p1_name", "p1_score", "p2_name", "p2_score", "email")
    if any(not data[name] for name in required):
        flash("Please fill in all the fields marked with *.", category="error")
        return render_template("submit_scores.html", form=data, **page)
    if not EMAIL_RE.match(data["email"]):
        flash("Please enter a valid email address.", category="error")
        return render_template("submit_scores.html", form=data, **page)
    if not league.email:
        flash("This league doesn't have a contact email set up yet. Please contact the league organizer.",
              category="error")
        return render_template("submit_scores.html", form=data, **page)

    body = (
        f"Player 1 - Name: {data['p1_name']}\nPlayer 1 - Score: {data['p1_score']}\n"
        f"Player 2 - Name: {data['p2_name']}\nPlayer 2 - Score: {data['p2_score']}\n"
        f"Your Email: {data['email']}\nComments: {data['comments']}"
    )
    if send_email(f"{league.league_name} - Score Submission", body, league.email, reply_to=data["email"]):
        flash("Score submitted successfully!", category="success")
        return redirect(request.path)

    flash("Sorry, your score couldn't be sent. Please try again, or contact the league organizer.",
          category="error")
    return render_template("submit_scores.html", form=data, **page)


@bp.route("/<int:league_number>-sign_up", methods=["GET", "POST"])
@limiter.limit(SIGNUP_LIMIT, methods=["POST"])
def sign_up(league_number):
    league = _get_league(league_number)

    if league.has_signup_form:
        return redirect(league.signup_form_link.strip())

    page = dict(page_title=f"{league.league_name} - Sign Up", league=league)

    if request.method == "GET":
        return render_template("sign_up.html", form={}, **page)

    if _is_bot():
        flash("Message sent successfully!", category="success")
        return redirect(request.path)

    data = {
        "name": _field("name", 100),
        "phone_number": _field("phone_number", 40),
        "email": _field("email", 200),
        "comments": _field("comments", 2000),
    }
    if not data["name"] or not data["email"]:
        flash("Please fill in all the fields marked with *.", category="error")
        return render_template("sign_up.html", form=data, **page)
    if not EMAIL_RE.match(data["email"]):
        flash("Please enter a valid email address.", category="error")
        return render_template("sign_up.html", form=data, **page)
    if not league.email:
        flash("This league doesn't have a contact email set up yet. Please contact the league organizer.",
              category="error")
        return render_template("sign_up.html", form=data, **page)

    body = (
        f"Full Name: {data['name']}\nPhone Number: {data['phone_number']}\n"
        f"Email: {data['email']}\nComments: {data['comments']}"
    )
    if send_email(f"{league.league_name} - Sign Up Inquiry", body, league.email, reply_to=data["email"]):
        flash("Message sent successfully!", category="success")
        return redirect(request.path)

    flash("Sorry, your message couldn't be sent. Please try again, or contact the league organizer.",
          category="error")
    return render_template("sign_up.html", form=data, **page)
