import logging
import os

from firebase_admin import auth


def get_user_email(uid: str) -> str | None:
    """Helper to get user email from Firebase for sharing."""
    if uid == "dev-user" or not os.getenv("K_SERVICE"):
        return os.getenv("DEV_USER_EMAIL")
    try:
        user = auth.get_user(uid)
        return user.email
    except Exception as e:
        logging.warning(f"Failed to get email for user {uid}: {e}")
        return None


def get_data_access_token() -> str:
    """Helper to retrieve the access token, logging an error if fallback is used in production."""
    token = os.getenv("DATA_ACCESS_TOKEN")
    if not token or not token.strip():
        fallback = "mmtools-default-secret-2024"
        if os.getenv("K_SERVICE"):
            logging.error(
                "CRITICAL: DATA_ACCESS_TOKEN is not set in production! Falling back to insecure default secret."
            )
        return fallback
    return token.strip()
