"""
WSGI config for gcpcul project.
"""
import os
import sys

# Vercel Fix: Add the root directory to Python's system path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gcpcul.settings')

application = get_wsgi_application()

# Vercel requires the WSGI application to be named 'app'
app = application