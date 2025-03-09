web: gunicorn mwami.wsgi:application
worker: celery -A mwami worker --loglevel=info
beat: celery -A mwami beat --loglevel=info