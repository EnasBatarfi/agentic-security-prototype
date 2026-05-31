from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render, get_object_or_404

from .forms import UploadedFileForm
from .models import UploadedFile
from apps.mcp_tools.tools import delete_file as mcp_delete_file


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

@login_required
def file_delete(request, file_id):
    """Delete a file from the UI using the same MCP delete tool."""

    # If the request is a POST the user wants to delete the file
    if request.method == "POST":
        uploaded_file = get_object_or_404(
            UploadedFile,
            id=file_id,
            owner=request.user,
        )

        mcp_delete_file(uploaded_file.file.name)

    return redirect("file_list")