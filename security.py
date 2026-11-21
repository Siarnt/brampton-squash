"""Password hashing helpers.

The three existing admin accounts were created with an old Werkzeug call
(method='sha256') that current Werkzeug can no longer verify. verify_password()
still accepts that old format so nobody is locked out, and tells the caller to
re-save the password in the modern format after a successful login.
"""
import hmac

from werkzeug.security import check_password_hash, generate_password_hash


def hash_password(password):
    # PBKDF2 rather than Werkzeug's newer default (scrypt) so that, if a release is ever
    # rolled back on Heroku, the older code can still read these hashes.
    return generate_password_hash(password, method="pbkdf2:sha256")


def _check_legacy_sha256(stored, password):
    # Old format: sha256$<salt>$<hexdigest>, the digest being HMAC-SHA256
    # keyed with the salt.
    try:
        _method, salt, digest = stored.split("$", 2)
    except ValueError:
        return False
    expected = hmac.new(salt.encode("utf-8"), password.encode("utf-8"), "sha256").hexdigest()
    return hmac.compare_digest(expected, digest)


def verify_password(stored, password):
    """Return (password_is_correct, should_rehash)."""
    if not stored:
        return False, False
    if stored.startswith("sha256$"):
        ok = _check_legacy_sha256(stored, password)
        return ok, ok
    try:
        return check_password_hash(stored, password), False
    except ValueError:
        return False, False
