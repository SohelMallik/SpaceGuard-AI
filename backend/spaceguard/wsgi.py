"""
WSGI config for spaceguard project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/6.0/howto/deployment/wsgi/

WHAT THIS FILE IS FOR
---------------------
WSGI = "Web Server Gateway Interface", the traditional standard for running
Python web apps synchronously (one request handled at a time per worker).
This file is the entry point used by production WSGI servers such as
gunicorn or uWSGI, e.g.:

    gunicorn spaceguard.wsgi:application

Browsers/clients -> web server (nginx) -> WSGI server (gunicorn) -> this
`application` callable -> Django. You never edit this file for normal
development (`runserver` works without it); it only matters at deployment.
"""

import os

from django.core.wsgi import get_wsgi_application

# Tell Django which settings module to use, unless the server already set
# DJANGO_SETTINGS_MODULE itself in the environment.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'spaceguard.settings')

# Create and expose the WSGI application object the server will call for
# every request. Side effect: this also initialises Django (loads settings,
# sets up app registry and logging).
application = get_wsgi_application()
