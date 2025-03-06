web: python manage.py migrate && gunicorn mwami.wsgi
worker: celery -A mwami worker --loglevel=info
beat: celery -A mwami beat --loglevel=info