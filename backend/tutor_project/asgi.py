"""
ASGI config for tutor_project project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.2/howto/deployment/asgi/
"""

# tutor_project/asgi.py
# tutor_project/asgi.py

# --- Add these lines START ---
import asyncio
import sys

# Set the event loop policy for Windows if applicable
# --- Temporarily COMMENT OUT these two lines ---
# if sys.platform == 'win32':
#     asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
# --- END comment out ---
# --- Add these lines END ---


import os
from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tutor_project.settings')

application = get_asgi_application()

# --- Add these lines START ---
# import asyncio
# import sys

# # Set the event loop policy for Windows if applicable
# if sys.platform == 'win32':
#     asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
# # --- Add these lines END ---


# import os
# from django.core.asgi import get_asgi_application

# os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tutor_project.settings')

# application = get_asgi_application()

# Optional: If you were using Channels routing, that would go here.
# For now, just the default Django ASGI application is fine.