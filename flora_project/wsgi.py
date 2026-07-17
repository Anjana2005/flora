"""
WSGI config for Flora project.
"""

import os
from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'flora_project.settings')

application = get_wsgi_application()