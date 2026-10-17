"""Render Foliolet's wallet templates offline with fictional data, for design review.

This never contacts Spring Boot, PostgreSQL, Ganache, Ollama or a running Django
service, and never reads sessions or documents. It configures a throwaway Django
template engine, resolves `{% url %}` against a stub URLconf with the same route
names, renders each screen with the fixtures in fixtures.py, and writes static
HTML plus a copy of the static assets to an output folder.

Usage (from the repository root, with Django installed in any virtualenv):
    python tools/frontend-preview/render.py [OUT_DIR]
    python -m http.server 8765 --bind 127.0.0.1 --directory OUT_DIR

Scripts that call backend endpoints (Ask Foli, intake polling) find nothing to
talk to in this static preview and show their offline states; that is expected.
"""
import json
import os
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
# FOLIOLET_PREVIEW_SERVICE renders another copy of django-service (for example an exported
# `main`) with the same fixtures, which is how the before/after comparison is produced.
SERVICE = Path(os.environ.get("FOLIOLET_PREVIEW_SERVICE", ROOT / "django-service")).resolve()
OUT = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path(__file__).resolve().parent / "out"
sys.path.insert(0, str(SERVICE))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import django  # noqa: E402
from django.conf import settings  # noqa: E402

settings.configure(
    DEBUG=True,
    SECRET_KEY="frontend-preview-only",
    ROOT_URLCONF="preview_urls",
    ALLOWED_HOSTS=["*"],
    INSTALLED_APPS=["django.contrib.staticfiles"],
    STATIC_URL="/static/",
    STATICFILES_DIRS=[str(SERVICE / "dashboard" / "static")],
    USE_TZ=True,
    TIME_ZONE="Asia/Kolkata",
    TEMPLATES=[{
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [str(SERVICE / "dashboard" / "templates")],
        "OPTIONS": {"context_processors": ["django.template.context_processors.request"], "libraries": {
            "wallet_ui": "dashboard.templatetags.wallet_ui",
            "wallet_time": "dashboard.templatetags.wallet_time",
            "claim_kind": "dashboard.templatetags.claim_kind",
        }},
    }],
)
django.setup()

from django.template.loader import render_to_string  # noqa: E402
from django.test import RequestFactory  # noqa: E402
from django.urls import resolve  # noqa: E402

import fixtures as fx  # noqa: E402

factory = RequestFactory()


def render(url, template, out_path, **context):
    request = factory.get(url)
    try:
        request.resolver_match = resolve(url.split("?")[0])
    except Exception:  # pages whose real route is POST-only still render
        request.resolver_match = None
    context.setdefault("product_label", "Foliolet")
    context.setdefault("csrf_token", "preview-token")
    html = render_to_string("wallet/" + template + ".html", context, request=request)
    target = OUT / out_path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(html, encoding="utf-8")
    return target


def main():
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir(parents=True)
    shutil.copytree(SERVICE / "dashboard" / "static", OUT / "static")
    user = {"current_username": "ananya.rao"}
    pages = [
        ("/", "home", "index.html", dict(user, **fx.home())),
        ("/?q=marksheet", "home", "search/index.html", dict(user, **fx.home(query="marksheet"))),
        ("/", "home", "first-run/index.html", dict(user, **fx.home(empty=True))),
        ("/wallet/enroll/", "enroll", "wallet/enroll/index.html", dict(user, **fx.enroll())),
        ("/wallet/doc-draft-7f2a/", "detail", "wallet/doc-draft-7f2a/index.html", dict(user, **fx.detail("draft"))),
        ("/wallet/doc-active-31c9/", "detail", "wallet/doc-active-31c9/index.html", dict(user, **fx.detail("active"))),
        ("/wallet/doc-revoked-0b44/", "detail", "wallet/doc-revoked-0b44/index.html", dict(user, **fx.detail("revoked"))),
        ("/wallet/doc-active-31c9/share/", "compose", "wallet/doc-active-31c9/share/index.html", dict(user, **fx.compose())),
        ("/sharing/", "sharing", "sharing/index.html", dict(user, **fx.sharing())),
        ("/sharing/", "share_ready", "sharing/ready/index.html", dict(user, **fx.share_ready())),
        ("/integrity/", "integrity", "integrity/index.html", dict(user, **fx.integrity())),
        ("/ask-foli/", "foli", "ask-foli/index.html", dict(user)),
        ("/wallet/doc-active-31c9/signature/", "signature_report", "wallet/doc-active-31c9/signature/index.html", dict(user, **fx.signature())),
        ("/login/", "login", "login/index.html", {}),
        ("/register/", "register", "register/index.html", {}),
        ("/verify/demo-token/", "verify", "verify/demo-token/index.html", fx.verify(result=True)),
        ("/verify/gate-token/", "verify", "verify/gate-token/index.html", fx.verify(result=False)),
    ]
    for url, template, out_path, context in pages:
        print("rendered", render(url, template, out_path, **context).relative_to(OUT))
    # Static JSON so client scripts show populated states instead of offline errors.
    # http.server answers a trailing-slash path with index.html; fetch() parses it as JSON.
    for path, body in fx.api_stubs().items():
        target = OUT / path.strip("/") / "index.html"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(body), encoding="utf-8")
    print("preview ready in", OUT)


if __name__ == "__main__":
    main()
