"""
ASGI config for spaceguard project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/6.0/howto/deployment/asgi/

WHAT THIS FILE IS FOR
---------------------
ASGI = "Asynchronous Server Gateway Interface", the modern successor to
WSGI. It supports async handling, WebSockets, and long-lived connections,
in addition to everything WSGI does. This file is the entry point for
ASGI servers such as uvicorn or daphne, e.g.:

    uvicorn spaceguard.asgi:application

SpaceGuard currently serves plain request/response traffic, so either
wsgi.py or asgi.py works for deployment; asgi.py leaves the door open for
future real-time features (e.g. live telemetry streaming over WebSockets).
"""

import os

from django.core.asgi import get_asgi_application

# Tell Django which settings module to use, unless the server already set
# DJANGO_SETTINGS_MODULE itself in the environment.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'spaceguard.settings')

# Create and expose the ASGI application object the server will call for
# every request (also initialises Django: settings, apps, logging).
application = get_asgi_application()
