#!/bin/sh
cd /src/
python manage.py collectstatic --noinput
python manage.py makemigrations
python manage.py migrate
if [ "x$PORT" = "x" ]; then
  PORT=8000
fi
gunicorn -t 200 cgran.wsgi -b 0.0.0.0:$PORT --access-logfile - --error-logfile - --log-level info --reload
