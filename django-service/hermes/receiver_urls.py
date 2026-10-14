"""This URL tree never imports private dashboard/admin URL patterns."""
from django.urls import include, path, re_path
from dashboard import receiver_surface as receiver
from dashboard import wallet_views
from django.views.decorators.http import require_http_methods

grant = r"(?P<grant_id>[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})"
routes = [
    re_path(r"^verify/(?P<token>[0-9a-f]{64})/$",
            require_http_methods(["GET", "HEAD", "POST"])(wallet_views.verify), name="verify"),
    re_path(r"^proof-status/" + grant + r"/$", receiver.proof_status, name="proof_status"),
    re_path(r"^proof-download/" + grant + r"/$",
            require_http_methods(["GET", "HEAD"])(wallet_views.proof_download), name="proof_download"),
]
urlpatterns = [
    path("", include((routes, "dashboard"), namespace="dashboard")),
    path("healthz/", receiver.health),
    path("static/<path:asset>", receiver.static_asset),
]
