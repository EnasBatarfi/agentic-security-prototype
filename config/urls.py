"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from django.contrib.auth import views as auth_views
from core.views import home, signup, new_chat, chat, fs_list_api, fs_write_api, fs_read_api, fs_page


urlpatterns = [
    path("admin/", admin.site.urls),

    path("", home, name="home"),

    path("signup/", signup, name="signup"),
    path("login/", auth_views.LoginView.as_view(template_name="login.html"), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("chat/new/", new_chat, name="new_chat"),
    path("chat/<int:conversation_id>/", chat, name="chat"),
    path("api/fs/list/", fs_list_api, name="fs_list_api"),
    path("api/fs/write/", fs_write_api, name="fs_write_api"),
    path("api/fs/read/", fs_read_api, name="fs_read_api"),
    path("fs/", fs_page, name="fs_page"),

]
