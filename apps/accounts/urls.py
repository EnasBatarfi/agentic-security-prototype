from django.urls import path

from . import views

# URL patterns for the accounts app 
# This includes the signup view which allows users to create an account
urlpatterns = [
    path("signup/", views.signup, name="signup"),
]