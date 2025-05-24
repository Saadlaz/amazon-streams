from django.urls import path
from .consumers import ReviewConsumer

websocket_urlpatterns = [
    path("ws/reviews/", ReviewConsumer.as_asgi()),
]
