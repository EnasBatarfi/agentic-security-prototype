from django.contrib import admin

from .models import ChatMessage


@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "context", "role", "created_at")
    search_fields = ("user__username", "content")
    list_filter = ("context", "role")