import os

from dotenv import load_dotenv

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

# Read the local .env file (if it exists).
# On Render there is no .env file - Render's own environment
# variables are used instead, and they are never overwritten here.
load_dotenv(os.path.join(BASE_DIR, ".env"))


def get_database_url():
    """
    Pick the database:
    - If DATABASE_URL is set  -> use PostgreSQL (Neon)
    - If it is not set        -> use local SQLite (fallback)
    """
    url = os.environ.get("DATABASE_URL", "").strip()

    if not url:
        return "sqlite:///" + os.path.join(
            BASE_DIR, "instance", "queueless.db"
        )

    # Make sure SQLAlchemy uses the psycopg (version 3) driver,
    # even if the URL starts with a shorter prefix.
    if url.startswith("postgres://"):
        url = "postgresql+psycopg://" + url[len("postgres://"):]
    elif url.startswith("postgresql://"):
        url = "postgresql+psycopg://" + url[len("postgresql://"):]

    return url


DATABASE_URL = get_database_url()


class Config:
    SECRET_KEY = os.environ.get(
        "SECRET_KEY",
        "queueless-development-secret-key"
    )

    SQLALCHEMY_DATABASE_URI = DATABASE_URL

    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Neon can close idle connections. These settings make Flask
    # check a connection before using it, and refresh old ones.
    if DATABASE_URL.startswith("postgresql"):
        SQLALCHEMY_ENGINE_OPTIONS = {
            "pool_pre_ping": True,
            "pool_recycle": 280,
        }

    DEBUG = False
