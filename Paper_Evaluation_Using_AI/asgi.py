import os

from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Paper_Evaluation_Using_AI.settings')

application = get_asgi_application()
