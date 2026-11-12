import hashlib
import re
import secrets
import time
import uuid

from werkzeug.security import check_password_hash, generate_password_hash


class AuthService:
    SESSION_TTL_SECONDS = 7 * 24 * 60 * 60
    EMAIL_PATTERN = re.compile(r"^[^@\s]{1,64}@[^@\s.]+(?:\.[^@\s.]+)+$")

    def __init__(self, database, session_ttl_seconds=None):
        self.database = database
        self.session_ttl_seconds = session_ttl_seconds or self.SESSION_TTL_SECONDS

    @staticmethod
    def token_digest(token):
        return hashlib.sha256(token.encode("utf-8")).hexdigest()

    @classmethod
    def normalize_email(cls, email):
        if not isinstance(email, str):
            raise ValueError("Enter a valid email address.")
        normalized = email.strip().lower()
        if len(normalized) > 254 or not cls.EMAIL_PATTERN.fullmatch(normalized):
            raise ValueError("Enter a valid email address.")
        return normalized

    @staticmethod
    def hash_password(password):
        if not isinstance(password, str) or not 12 <= len(password) <= 128:
            raise ValueError("Password must contain 12–128 characters.")
        return generate_password_hash(password)

    def register(self, email, password):
        normalized = self.normalize_email(email)
        password_hash = self.hash_password(password)
        user_id = str(uuid.uuid4())
        if not self.database.create_user(user_id, normalized, password_hash):
            raise FileExistsError("An account with this email already exists.")
        return self._issue_session(self.database.get_user(user_id))

    def login(self, email, password):
        normalized = self.normalize_email(email)
        user = self.database.get_user_by_email(normalized)
        if not isinstance(password, str) or not 12 <= len(password) <= 128:
            raise PermissionError("Email or password is incorrect.")
        if not user or not check_password_hash(user["password_hash"], password):
            raise PermissionError("Email or password is incorrect.")
        return self._issue_session(user)

    def authenticate(self, token):
        if not isinstance(token, str) or not 20 <= len(token) <= 256:
            return None
        return self.database.get_session_user(self.token_digest(token), int(time.time()))

    def revoke(self, token):
        if isinstance(token, str) and 20 <= len(token) <= 256:
            self.database.revoke_auth_session(self.token_digest(token))

    def _issue_session(self, user):
        if not user:
            raise RuntimeError("Account could not be loaded.")
        token = secrets.token_urlsafe(32)
        expires_at = int(time.time()) + self.session_ttl_seconds
        self.database.save_auth_session(self.token_digest(token), user["id"], expires_at)
        return {
            "token": token,
            "expires_at": expires_at,
            "user": {"id": user["id"], "email": user["email"]},
        }
