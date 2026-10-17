"""Stub URLconf for the offline preview: the real route names, no views behind them."""
from django.http import HttpResponse
from django.urls import include, path


def stub(request, *args, **kwargs):
    return HttpResponse(status=204)


dashboard = ([
    path("intake/pair/", stub, name="intake-pair"),
    path("intake/sessions/", stub, name="intake-sessions"),
    path("intake/files/", stub, name="intake-files"),
    path("intake/files/import/", stub, name="intake-file-import"),
    path("intake/documents/<str:credential_id>/", stub, name="intake-analysis"),
    path("intake/documents/<str:credential_id>/retry/", stub, name="intake-retry"),
    path("", stub, name="index"),
    path("login/", stub, name="login"),
    path("register/", stub, name="register"),
    path("logout/", stub, name="logout"),
    path("ask-foli/", stub, name="foli"),
    path("wallet/enroll/", stub, name="enroll"),
    path("wallet/<str:credential_id>/", stub, name="detail"),
    path("wallet/<str:credential_id>/share/", stub, name="compose"),
    path("wallet/<str:credential_id>/file/", stub, name="original"),
    path("wallet/<str:credential_id>/signature/", stub, name="signature-inspect"),
    path("wallet/<str:credential_id>/scan/", stub, name="scan_fields"),
    path("wallet/<str:credential_id>/<str:action>/", stub, name="document_action"),
    path("versions/<str:previous_id>/", stub, name="version"),
    path("sharing/", stub, name="sharing"),
    path("sharing/<str:grant_id>/revoke/", stub, name="revoke_share"),
    path("integrity/", stub, name="integrity"),
    path("integrity/<str:agent_id>/revoke/", stub, name="revoke_agent"),
    path("verify/<str:token>/", stub, name="verify"),
    path("proof-status/<str:grant_id>/", stub, name="proof_status"),
    path("proof-download/<str:grant_id>/", stub, name="proof_download"),
], "dashboard")

urlpatterns = [path("", include(dashboard))]
