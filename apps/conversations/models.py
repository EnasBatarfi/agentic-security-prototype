from django.conf import settings
from django.db import models

from apps.authorization.actions import FILE_CONTEXT, PROFILE_CONTEXT


class ChatMessage(models.Model):
    """One saved message from file chat or profile chat."""

    # Class for context choices
    class Context(models.TextChoices):
        FILE = FILE_CONTEXT, "File Chat"
        PROFILE = PROFILE_CONTEXT, "Profile Chat"

    # Class for role choices
    class Role(models.TextChoices):
        USER = "user", "User"
        ASSISTANT = "assistant", "Assistant"

    # The user who sent the message
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="chat_messages",
    )
    # The context of the message (file chat or profile chat based on the choices defined in Context)
    context = models.CharField(
        max_length=20,
        choices=Context.choices,
    )
    # The role of the message (user or assistant based on the choices defined in Role)
    role = models.CharField(
        max_length=20,
        choices=Role.choices,
    )
    # The actual content of the message
    content = models.TextField()
    # Timestamp when the message was created
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.context}: {self.role}"
