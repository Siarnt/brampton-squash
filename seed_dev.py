"""Fills the LOCAL dev database with sample data so you can click around the site.

    python seed_dev.py

Creates instance/dev.db with the four leagues, quick links and resources, plus
an admin login:  name 'admin'  password 'admin12345'  secret code 'dev-secret-code'.
It refuses to run if DATABASE_URL is set, so it can never touch the live database.
"""
import os
import sys

if os.getenv("DATABASE_URL"):
    sys.exit("DATABASE_URL is set - refusing to seed. This script is for the local dev database only.")

os.environ.setdefault("secret_code", "dev-secret-code")

from app import app  # noqa: E402
from extensions import db  # noqa: E402
from models import Announcement, League, QuickLink, Resource, User  # noqa: E402
from security import hash_password  # noqa: E402

LEAGUES = [
    (1, "Sunday League", "Sunday Organizer", "sunday@example.com",
     "https://docs.google.com/spreadsheets/d/1hPOlS3ZgDKrHOraFPOksiok6AfH3IxciYU7JkQcWNuw/edit?usp=drive_link", "https://forms.gle/UGeiupP5ZkJX9BW18", ""),
    (2, "Monday League", "Monday Organizer", "monday@example.com",
     "https://docs.google.com/spreadsheets/d/1WHlIcfykb_u-fx2N8mvHe1JZ5OmTwhGXoSAyaceFq3k/edit?usp=sharing", "", ""),
    (3, "Wednesday League", "Wednesday Organizer", "wednesday@example.com",
     "https://docs.google.com/spreadsheets/d/1h6Mu_JoSk4gOqA92mCidGr7J4mFaa59r/edit#gid=153175616", "", ""),
    (4, "Summer League", "Summer Organizer", "summer@example.com",
     "https://docs.google.com/spreadsheets/d/1aXTPrpU9Z7BQwiz00KUDlb8oifwi6FoI/edit?usp=sharing", "", ""),
]

with app.app_context():
    if League.query.count():
        sys.exit("The dev database already has data. Delete instance/dev.db first if you want to start over.")

    for number, name, contact, email, link, score_form, signup_form in LEAGUES:
        db.session.add(League(league_number=number, league_name=name, contact_name=contact, email=email,
                              link=link, score_form_link=score_form, signup_form_link=signup_form))

    db.session.add_all([
        QuickLink(description="Monday League", link="https://docs.google.com/spreadsheets/d/1WHlIcfykb_u-fx2N8mvHe1JZ5OmTwhGXoSAyaceFq3k/edit?usp=sharing", rank=1),
        QuickLink(description="Wednesday League", link="https://docs.google.com/spreadsheets/d/1h6Mu_JoSk4gOqA92mCidGr7J4mFaa59r/edit?usp=drive_link", rank=2),
        QuickLink(description="Sunday League", link="https://docs.google.com/spreadsheets/d/1hPOlS3ZgDKrHOraFPOksiok6AfH3IxciYU7JkQcWNuw/edit?usp=drive_link", rank=3),
        QuickLink(description="Sunday League Score Submission (Google Form)", link="https://forms.gle/UGeiupP5ZkJX9BW18", rank=4),
        Resource(heading="City of Brampton",
                 description="Log in to book a court or buy a membership on the City of Brampton website.",
                 link="https://cityofbrampton.perfectmind.com/Menu/MemberRegistration/MemberSignIn", rank=1),
        Resource(heading="Racquet Stringing", description="Christian Yu: 647-210-8434",
                 link="christian.yu.88@gmail.com", rank=2),
        Resource(heading="", description="Charles Gembes: 416-892-4440", link="cgembes@yahoo.ca", rank=3),
        Announcement(announcement_item="Sample announcement - delete me from the admin page.",
                     date_created="Nov 21, 2026", rank=1),
        User(name="admin", password=hash_password("admin12345")),
    ])
    db.session.commit()
    print("Done. Start the site with:  python app.py   then log in at /admin_login as admin / admin12345")
    print("Secret code for creating more admins locally:", os.environ["secret_code"])
