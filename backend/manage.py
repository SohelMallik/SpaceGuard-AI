#!/usr/bin/env python
"""Django's command-line utility for administrative tasks.

This is the `manage.py` file you use for EVERY Django command, e.g.:

    python manage.py runserver      # start the development web server
    python manage.py migrate        # apply database migrations
    python manage.py createsuperuser# create an admin login
    python manage.py test           # run the test suite

It simply sets up Django's environment and forwards your arguments to
Django's command dispatcher. It is standard boilerplate in every project.
"""
import os
import sys


def main():
    """Run administrative tasks."""
    # Point Django at this project's settings file (backend/spaceguard/settings.py)
    # unless DJANGO_SETTINGS_MODULE was already set in the environment.
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'spaceguard.settings')
    try:
        # The actual command runner: parses sys.argv and runs the requested
        # subcommand (runserver, migrate, shell, ...).
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        # The classic failure mode: Django isn't installed in the current
        # Python environment (usually a forgotten/missing virtualenv).
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    # Hand control over to Django with whatever command the user typed.
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()
