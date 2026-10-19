#!/usr/bin/env bash

pip install -r requirements.txt
python manage.py collectstatic --noinput
MY_DEBUG=False python manage.py check_production_static
python manage.py migrate