from django import template
from dashboard.verification import recognized_threshold

register = template.Library()
register.filter('recognized_threshold', recognized_threshold)
