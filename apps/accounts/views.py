from django.contrib.auth import login
from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.shortcuts import redirect, render

class SignUpForm(UserCreationForm):
    """Form for creating a new user account."""
    email = forms.EmailField(required=True)

def signup(request):
    """Create a user account, then log the user in."""

    # If the request is a POST then the user has signed up
    if request.method == "POST":
        form = SignUpForm(request.POST)

        # Check if the form is valid and if so save the user and log them in
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect("file_list")
    # Otherwise, the user is just viewing the signup page so show them the form
    else:
        form = SignUpForm()

    return render(request, "accounts/signup.html", {"form": form})