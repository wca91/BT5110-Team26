#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys
from example.models import Models
from example import utils


def main():
    """Run administrative tasks."""
    models = Models()
    models.createModels()
    utils.readDbFile("example/fact_table.sql", models)
    utils.readDbFile("example/crane.sql", models)
    utils.readDbFile("example/verifier.sql", models)
    #utils.readDbFile("example/date.sql", models)
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'portfolio.settings')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)



if __name__ == '__main__':
    main()

