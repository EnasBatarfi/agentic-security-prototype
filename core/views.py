from django.contrib.auth import login
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.shortcuts import get_object_or_404
from .models import Conversation, Message
from .assistant import generate_reply
import logging

# File system imports
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from .fs_local import list_dir, read_file, write_file


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

# Show what files are in the user folder
@login_required
def fs_list_api(request):
    items = list_dir(request.user.id, "")
    return JsonResponse({"items": items})

# Create or overwrite a file inside the user folder
@require_POST
@login_required
def fs_write_api(request):
    path = (request.POST.get("path") or "").strip()
    content = request.POST.get("content") or ""
    if not path:
        return JsonResponse({"error": "missing path"}, status=400)

    write_file(request.user.id, path, content)
    return JsonResponse({"ok": True})

# Read a text file from the user folder
@require_POST
@login_required
def fs_read_api(request):
    path = (request.POST.get("path") or "").strip()
    if not path:
        return JsonResponse({"error": "missing path"}, status=400)

    try:
        content = read_file(request.user.id, path)
        return JsonResponse({"ok": True, "content": content})
    except FileNotFoundError:
        return JsonResponse({"ok": False, "error": "not found"}, status=404)


# UI FS for testing 
@login_required
def fs_page(request):
    result = None
    items = None

    if request.method == "POST":
        action = request.POST.get("action")

        if action == "write":
            path = (request.POST.get("path") or "").strip()
            content = request.POST.get("content") or ""
            if not path:
                result = "Missing path"
            else:
                write_file(request.user.id, path, content)
                result = f"Wrote: {path}"

        elif action == "read":
            path = (request.POST.get("path") or "").strip()
            if not path:
                result = "Missing path"
            else:
                try:
                    result = read_file(request.user.id, path)
                except FileNotFoundError:
                    result = "File not found"

    items = list_dir(request.user.id, "")
    return render(request, "fs.html", {"result": result, "items": items})