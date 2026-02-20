"""WSGI entry point for the instagram_sync project."""

import os
from typing import Final

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

application: Final = get_wsgi_application()