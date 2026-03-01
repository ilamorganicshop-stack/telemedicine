from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    # Room IDs are UUID strings (contain hyphens), so allow "-" in the route.
    re_path(r'ws/video-call/(?P<room_id>[-\w]+)/$', consumers.VideoCallConsumer.as_asgi()),
    re_path(r'ws/call-invite/(?P<appointment_id>\d+)/$', consumers.CallInviteConsumer.as_asgi()),
    re_path(r'ws/chat/(?P<appointment_id>\d+)/$', consumers.ChatConsumer.as_asgi()),
]
