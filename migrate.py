"""Run by Heroku before each new release goes live (Procfile 'release:' line)."""
from app import app
from schema import ensure_schema

if __name__ == "__main__":
    with app.app_context():
        changes = ensure_schema()
    print("Database changes:", "; ".join(changes) if changes else "none needed")
