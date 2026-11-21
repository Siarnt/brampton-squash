"""Database tables.

__tablename__ is set explicitly so the names always match the tables that
already exist in the live Heroku Postgres database.
"""
from flask_login import UserMixin

from extensions import db


class User(db.Model, UserMixin):
    __tablename__ = "user"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True)
    # 255 so modern password hashes fit (the old column was 100).
    password = db.Column(db.String(255))


class Announcement(db.Model):
    __tablename__ = "announcements"
    id = db.Column(db.Integer, primary_key=True)
    announcement_item = db.Column(db.String(2000))
    date_created = db.Column(db.String(1000))
    rank = db.Column(db.Integer)


class League(db.Model):
    __tablename__ = "league__information"
    id = db.Column(db.Integer, primary_key=True)
    league_number = db.Column(db.Integer, unique=True)
    league_name = db.Column(db.String(500))
    contact_name = db.Column(db.String(500))
    email = db.Column(db.String(500))
    # Link to the standings/schedule spreadsheet.
    link = db.Column(db.String(2000))
    # Optional Google Form links. When set, the site sends players there
    # instead of showing its own on-site form.
    score_form_link = db.Column(db.String(2000))
    signup_form_link = db.Column(db.String(2000))

    @property
    def has_score_form(self):
        return bool((self.score_form_link or "").strip())

    @property
    def has_signup_form(self):
        return bool((self.signup_form_link or "").strip())


class Resource(db.Model):
    __tablename__ = "resources"
    id = db.Column(db.Integer, primary_key=True)
    heading = db.Column(db.String(1000))
    description = db.Column(db.String(2000))
    link = db.Column(db.String(2000))
    rank = db.Column(db.Integer)


class QuickLink(db.Model):
    __tablename__ = "quick__links"
    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.String(2000))
    link = db.Column(db.String(2000))
    rank = db.Column(db.Integer)
