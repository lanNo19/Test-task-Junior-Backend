"""
Django settings for instagram_sync project.

Uses python-decouple to read configuration from environment variables
or a .env file.
"""

from pathlib import Path
from typing import Any, Final

from decouple import Csv, config

BASE_DIR: Final[Path] = Path(__file__).resolve().parent.parent

# ---------------------------------------------------------------------------
# Security
# ---------------------------------------------------------------------------

SECRET_KEY: str = config("SECRET_KEY", default="dev-secret-key-change-in-production")
DEBUG: bool = config("DEBUG", default=True, cast=bool)
ALLOWED_HOSTS: list[str] = config(
    "ALLOWED_HOSTS", default="localhost,127.0.0.1", cast=Csv()
)

# ---------------------------------------------------------------------------
# Applications
# ---------------------------------------------------------------------------

INSTALLED_APPS: Final[list[str]] = [
    "django.contrib.contenttypes",
    "django.contrib.auth",
    "rest_framework",
    "posts",
]

MIDDLEWARE: Final[list[str]] = [
    "django.middleware.security.SecurityMiddleware",
    "django.middleware.common.CommonMiddleware",
]

ROOT_URLCONF: Final[str] = "config.urls"
WSGI_APPLICATION: Final[str] = "config.wsgi.application"

# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------

DATABASE_URL: str = config(
    "DATABASE_URL",
    default="postgres://postgres:postgres@localhost:5432/instagram_sync",
)

DATABASES: dict[str, Any] = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": "instagram_sync",
        "USER": "postgres",
        "PASSWORD": "postgres",
        "HOST": "localhost",
        "PORT": "5432",
    }
}

# Parse DATABASE_URL if provided (used in Docker).
# dj_database_url is optional — fall back to manual URL parsing if absent.
try:
    import dj_database_url as _dj
    DATABASES["default"] = _dj.parse(DATABASE_URL)
except ImportError:
    import urllib.parse as _up
    _u = _up.urlparse(DATABASE_URL)
    DATABASES["default"] = {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": _u.path.lstrip("/"),
        "USER": _u.username,
        "PASSWORD": _u.password,
        "HOST": _u.hostname,
        "PORT": str(_u.port or 5432),
    }

# ---------------------------------------------------------------------------
# Internationalisation
# ---------------------------------------------------------------------------

LANGUAGE_CODE: Final[str] = "en-us"
TIME_ZONE: Final[str] = "UTC"
USE_TZ: Final[bool] = True

# ---------------------------------------------------------------------------
# Django REST Framework
# ---------------------------------------------------------------------------

REST_FRAMEWORK: Final[dict[str, Any]] = {
    "DEFAULT_PAGINATION_CLASS": "posts.pagination.PostCursorPagination",
    "PAGE_SIZE": 20,
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
}

# ---------------------------------------------------------------------------
# Instagram API (accessed via InstagramClient, not directly in views)
# ---------------------------------------------------------------------------

INSTAGRAM_ACCESS_TOKEN: str = config("INSTAGRAM_ACCESS_TOKEN", default="")
INSTAGRAM_USER_ID: str = config("INSTAGRAM_USER_ID", default="")
INSTAGRAM_API_VERSION: str = config("INSTAGRAM_API_VERSION", default="v21.0")

DEFAULT_AUTO_FIELD: Final[str] = "django.db.models.BigAutoField"