"""Creates missing tables and adds the few columns added since the first version.

Safe to run any number of times. Heroku runs it on every deploy (see Procfile),
and the app runs it by itself when started locally with SQLite.
"""
from sqlalchemy import inspect, text

from extensions import db
from models import League, User

NEW_LEAGUE_COLUMNS = {
    "score_form_link": "VARCHAR(2000)",
    "signup_form_link": "VARCHAR(2000)",
}


def ensure_schema():
    db.create_all()  # creates any table that doesn't exist yet
    engine = db.engine
    inspector = inspect(engine)
    changes = []

    league_cols = {c["name"] for c in inspector.get_columns(League.__tablename__)}
    user_cols = {c["name"]: c for c in inspector.get_columns(User.__tablename__)}

    with engine.begin() as conn:
        for name, ddl in NEW_LEAGUE_COLUMNS.items():
            if name not in league_cols:
                conn.execute(text(f"ALTER TABLE {League.__tablename__} ADD COLUMN {name} {ddl}"))
                changes.append(f"added {League.__tablename__}.{name}")

        # Modern password hashes are longer than the original 100-character column.
        # (SQLite doesn't enforce lengths, so this only matters on Postgres.)
        if engine.dialect.name == "postgresql":
            length = getattr(user_cols["password"]["type"], "length", None) or 0
            if length < 255:
                conn.execute(text(f'ALTER TABLE "{User.__tablename__}" ALTER COLUMN password TYPE VARCHAR(255)'))
                changes.append("widened user.password to 255")

    return changes
