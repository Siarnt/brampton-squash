"""Flask extensions, created once here and attached to the app in app.py."""
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFProtect

db = SQLAlchemy()
login_manager = LoginManager()
csrf = CSRFProtect()
# In-memory counters are fine here: the site runs a single gunicorn worker.
limiter = Limiter(key_func=get_remote_address, storage_uri="memory://")
