from django.contrib.auth import login
from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm
from django.shortcuts import redirect, render

class SignUpForm(UserCreationForm):
    """Signup form with email and clear field errors."""

    email = forms.EmailField(required=True)

    class Meta(UserCreationForm.Meta):
        fields = ("username", "email", "password1", "password2")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.order_fields(["username", "email", "password1", "password2"])

        self.fields["username"].label = "Username"
        self.fields["email"].label = "Email"
        self.fields["password1"].label = "Password"
        self.fields["password2"].label = "Password confirmation"

    def clean_username(self):
        username = self.cleaned_data["username"].strip().lower()

        User = get_user_model()
        if User.objects.filter(username__iexact=username).exists():
            raise forms.ValidationError("This username is already in use.")

        return username

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()

        User = get_user_model()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("This email is already in use.")

        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]

        if commit:
            user.save()

        return user

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