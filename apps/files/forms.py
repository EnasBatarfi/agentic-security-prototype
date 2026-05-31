from django import forms

from .models import UploadedFile


class UploadedFileForm(forms.ModelForm):
    """Form for uploading a file."""

    title = forms.CharField(max_length=255, required=False)
    class Meta:
        model = UploadedFile
        fields = ["title", "file"]