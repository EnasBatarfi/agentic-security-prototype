from django.conf import settings
from django.db import models

def uploaded_file_path(instance, filename):
    """Save each user's uploaded files in their own folder."""

    return f"users/{instance.owner_id}/{filename}"

class UploadedFile(models.Model):
    """File uploaded through the normal web UI."""

    # The owner represents the user who uploaded the file
    # This is used to determine where to save the file and to allow users to view their own uploaded files
    # If the user is deleted we also want to delete their uploaded files so we use on delete cascade
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="uploaded_files",
    )
    # The necessary fields to store the file and its metadata
    # The file will be stored in the local filesystem under uploads/users/<owner_id>/<filename> 
    # and the metadata will be stored in the database
    title = models.CharField(max_length=255)
    file = models.FileField(upload_to=uploaded_file_path)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title