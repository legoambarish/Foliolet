"""Live Spring API bridge. This domain deliberately has no stub or fallback credentials."""
import requests
from django.conf import settings


class WalletAPIError(Exception):
    def __init__(self, message, status=503):
        super().__init__(message)
        self.status = status


def call(method, path, auth=None, *, data=None, files=None, payload=None, binary=False):
    try:
        response = requests.request(
            method, f"{settings.SPRING_BOOT_API_BASE_URL}{path}",
            auth=tuple(auth) if auth else None, data=data, files=files,
            json=payload, timeout=(5, 65),
        )
    except requests.RequestException as exc:
        raise WalletAPIError("The document service is unavailable. No verification was completed.") from exc
    if not response.ok:
        try:
            body = response.json()
            message = body.get("message", "The request could not be completed.")
        except (ValueError, AttributeError):
            message = response.text[:200] if response.status_code == 400 else "The request could not be completed."
        if response.status_code == 401:
            message = "Your credentials were not accepted. Please sign in again."
        raise WalletAPIError(message, response.status_code)
    if binary:
        return response.content, response.headers.get("Content-Disposition", "attachment")
    try:
        return response.json()
    except ValueError:
        return response.text
