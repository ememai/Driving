web: python manage.py collectstatic --noinput && MY_DEBUG=False python manage.py check_production_static && exec daphne -b 0.0.0.0 -p 8000 mwami.asgi:application
