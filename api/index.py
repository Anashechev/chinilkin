import os
import sys

# Add the project directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'chinilkin.settings')

import django
django.setup()

from django.core.wsgi import get_wsgi_application
from django.http import HttpResponse

# WSGI application
application = get_wsgi_application()

# Vercel serverless function handler
def handler(event, context):
    """
    Vercel serverless function handler for Django
    """
    # This is a simple wrapper that passes the request to Django
    # In a real deployment, you'd need to handle the event properly
    return HttpResponse("Django app is running", status=200)
