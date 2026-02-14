from django.contrib.auth import login
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.shortcuts import get_object_or_404
from .models import Conversation, Message
from .assistant import generate_reply
import logging

# Add the logger so we can add admin audit
logger = logging.getLogger(__name__)


@login_required
def home(request):
    conversations = Conversation.objects.filter(owner=request.user).order_by("-created_at")
    return render(request, "home.html", {"conversations": conversations})


def signup(request):
    if request.method == "POST":
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect("home")
    else:
        form = UserCreationForm()
    return render(request, "signup.html", {"form": form})


@login_required
def new_chat(request):
    conv = Conversation.objects.create(owner=request.user)
    return redirect("chat", conversation_id=conv.id)

@login_required
def chat(request, conversation_id):
    conv = get_object_or_404(Conversation, id=conversation_id, owner=request.user)

    if request.method == "POST":
        user_text = request.POST.get("message", "").strip()
        if user_text:
            Message.objects.create(conversation=conv, role="user", content=user_text)


            logger.info(
                "chat_message user=%s conv_id=%s session_id=%s text_len=%s",
                request.user.username,
                conv.id,
                conv.session_id,
                len(user_text),
            )


            # Dummy assistant reply for now
            assistant_text = generate_reply(user_text, conv)
            Message.objects.create(conversation=conv, role="assistant", content=assistant_text)


            logger.info(
                "assistant_reply user=%s conv_id=%s session_id=%s reply_len=%s",
                request.user.username,
                conv.id,
                conv.session_id,
                len(assistant_text),
            )



        return redirect("chat", conversation_id=conv.id)

    msgs = conv.messages.order_by("created_at")
    return render(request, "chat.html", {"conversation": conv, "messages": msgs})
