"""Point d'entrée WSGI (utilisé en production par Gunicorn ou PythonAnywhere)."""
import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "aerotrack.settings")

application = get_wsgi_application()
