from datetime import datetime
from django import template
from django.utils import timezone

register = template.Library()


@register.filter
def wallet_time(value):
    """Format API clocks for humans without changing the signed JSON presentation."""
    if not value:
        return "—"
    try:
        clock = datetime.fromisoformat(value.replace("Z", "+00:00")) if isinstance(value, str) else value
        if timezone.is_naive(clock):
            # Audit clocks are server-local without an offset; show them as-is rather than guess a zone.
            return clock.strftime("%d %b %Y, %H:%M")
        return timezone.localtime(clock).strftime("%d %b %Y, %H:%M %Z")
    except (TypeError, ValueError, AttributeError):
        return value
