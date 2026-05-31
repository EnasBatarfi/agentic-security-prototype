from django import forms

from .models import UploadedFile


class UploadedFileForm(forms.ModelForm):
    """Form for uploading a file."""

    class Meta:
        model = UploadedFile
        fields = ["title", "file"]