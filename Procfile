web: gunicorn mwami.wsgi
worker: celery -A mwami worker --loglevel=info
worker: celery -A mwami beat --loglevel=info