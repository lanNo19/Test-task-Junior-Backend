"""Root URL configuration."""

from typing import Final

from django.urls import URLPattern, include, path

urlpatterns: Final[list[URLPattern]] = [
    path("api/", include("posts.urls")),
]