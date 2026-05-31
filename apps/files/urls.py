from django.urls import path

from . import views


# URL patterns for the files app
# We have three urls one for file list, file upload and file delete
urlpatterns = [
    path("", views.file_list, name="file_list"),
    path("files/upload/", views.file_upload, name="file_upload"),
    path("files/<int:file_id>/delete/", views.file_delete, name="file_delete"),
]