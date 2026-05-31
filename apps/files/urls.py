from django.urls import path

from . import views


# URL patterns for the files app
# We have two views here one for listing files and another for uploading files
urlpatterns = [
    path("", views.file_list, name="file_list"),
    path("files/upload/", views.file_upload, name="file_upload"),
]