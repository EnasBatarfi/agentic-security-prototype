from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from .forms import UploadedFileForm
from .models import UploadedFile


@login_required
def file_list(request):
    """Show uploaded files."""

    # List all uploaded files for the current user ordered by creation date (newest first)
    files = UploadedFile.objects.filter(owner=request.user).order_by("-created_at")
    return render(request, "files/list.html", {"files": files})


@login_required
def file_upload(request):
    """Upload a file and save the current user as owner."""

    # If the request is a POST the user uploaded new file
    if request.method == "POST":
        form = UploadedFileForm(request.POST, request.FILES)

        # If the form is valid, save the uploaded file and set the current user as owner
        if form.is_valid():
            uploaded_file = form.save(commit=False)
            uploaded_file.owner = request.user
            uploaded_file.save()
            return redirect("file_list")
    # If the request is get show the upload form
    else:
        form = UploadedFileForm()

    return render(request, "files/upload.html", {"form": form})