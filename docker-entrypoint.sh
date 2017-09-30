#!/bin/sh
cd /src/
python manage.py collectstatic --noinput
python manage.py makemigrations
python manage.py migrate
gunicorn -t 200 cgran.wsgi -b 0.0.0.0:80 --access-logfile - --error-logfile - --log-level info --reload
