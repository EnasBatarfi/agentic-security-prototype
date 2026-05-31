from django.urls import path

from . import views

# URL patterns for the conversations app
# For conversation we have two urls one for file chat and one for profile chat
urlpatterns = [
    path("files/", views.file_chat, name="file_chat"),
    path("profile/", views.profile_chat, name="profile_chat"),
]