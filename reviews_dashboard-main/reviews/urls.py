from django.urls import path
from .views import dashboard, online, push_review ,auto_refresh_dashboard

urlpatterns = [
    path("", dashboard,   name="dashboard"),   # offline
    path("online/", auto_refresh_dashboard,   name="auto_refresh_dashboard"),  # live
    path("api/push/", push_review, name="push_review"),
]
