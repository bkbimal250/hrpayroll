"""
WebSocket routing configuration for Django Channels.
Defines the URL patterns for WebSocket connections.
"""

from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r'ws/attendance/$', consumers.AttendanceConsumer.as_asgi()),
    re_path(r'ws/resignations/$', consumers.ResignationConsumer.as_asgi()),
]
