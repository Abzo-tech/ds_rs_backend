#!/bin/bash
set -e

echo "Running migrations..."
python manage.py migrate --noinput

echo "Starting daphne..."
daphne -b 0.0.0.0 -p 8000 config.asgi:application
