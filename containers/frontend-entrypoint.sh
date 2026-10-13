#!/bin/sh
set -eu
python manage.py migrate --noinput
python manage.py collectstatic --noinput
exec gunicorn hermes.wsgi:application --bind 0.0.0.0:8000 --workers 2 --threads 4 --timeout 120
