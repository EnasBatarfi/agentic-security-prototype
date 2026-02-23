# Chat model client for local Ollama models
from langchain_ollama import ChatOllama

# Message types used by LangChain chat models
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, ToolMessage
# Decorator to register normal Python functions as LLM-callable tools
from langchain_core.tools import tool

# Local file-system helper functions (our shared business logic layer)
from .fs_local import list_tree, read_file, write_file

# Permanent instruction for the assistant (always sent first)
SYSTEM_PROMPT = (
    "You are a helpful assistant. "
    "When useful, use available tools to inspect or edit files before answering."
    "If the user asks about files (list/read/write), you MUST call the relevant fs_* tool. "
    "Do not guess."
)





def generate_reply(user_text: str, conversation) -> str:
    # Create a local LLM client.
    # model: model name in Ollama
    # temperature: lower = more stable/deterministic output
    # num_ctx: max context window (how much past text model can consider)
    # num_predict: max tokens to generate for one model turn
    llm = ChatOllama(
        model="llama3.1:8b", #model="llama3.2:3b" - this model wasn't able to list all the users files # smaller/faster while model="llama3.1:8b" was bigger/stronger but slower
        temperature=0.2,
        num_ctx=2048,
        num_predict=256,
    )

    # We bind tools to the current conversation owner only
    # This prevents the assistant from reading/writing another user's files
    user_id = conversation.owner_id

    @tool
    def fs_list(path: str = "") -> str:
        """List files/folders in this user's sandbox at a relative path."""
        return "\n".join(list_tree(user_id, path))

    @tool
    def fs_read(path: str) -> str:
        """Read one text file from this user's sandbox."""
        try:
            return read_file(user_id, path)
        except FileNotFoundError:
            # Return a clean tool error string (instead of crashing the run)
            return "ERROR: file not found"

    @tool
    def fs_write(path: str, content: str) -> str:
        """Create or overwrite a text file in this user's sandbox."""
        write_file(user_id, path, content)
        return f"OK: wrote {path}"

    # Register available tools and attach them to the model
    tools = [fs_list, fs_read, fs_write]
    llm_with_tools = llm.bind_tools(tools)

    # Pull recent chat history from DB to provide context
    # order_by("-created_at"): newest first, then we reverse for chat order
    # [:10]: keep context small for speed and token usage
    history = list(conversation.messages.order_by("-created_at")[:10])

    # Chat models expect chronological order: oldest -> newest.
    history.reverse()

    # Build message list in the format the model expects
    # System prompt first, then user/assistant history
    msgs = [SystemMessage(content=SYSTEM_PROMPT)]

    # Convert DB rows into LangChain message objects.
    for m in history:
        if m.role == "user":
            msgs.append(HumanMessage(content=m.content))
        else:
            # Here, non-user role means assistant.
            msgs.append(AIMessage(content=m.content))

    # Agent loop:
    # 1) Model responds
    # 2) If it requests tools, run them
    # 3) Feed tool output back to model
    # 4) Repeat until model gives final text
    max_steps = 5
    for _ in range(max_steps):
        # Ask model for the next step (text answer or tool call).
        resp = llm_with_tools.invoke(msgs)
        msgs.append(resp)

        # If no tool calls are requested we are done so we will return model response
        tool_calls = getattr(resp, "tool_calls", None) or []
        if not tool_calls:
            return str(resp.content)

        # Execute each requested tool call and attach the result
        for call in tool_calls:
            tool_name = call.get("name")
            tool_args = call.get("args", {})
            tool_id = call.get("id")

            # Find the matching registered tool by name
            selected_tool = next((t for t in tools if t.name == tool_name), None)
            if selected_tool is None:
                tool_output = f"ERROR: unknown tool '{tool_name}'"
            else:
                try:
                    # Run tool with arguments provided by the model
                    tool_output = selected_tool.invoke(tool_args)
                except Exception as exc:
                    # Keep loop alive even if one tool execution fails
                    tool_output = f"ERROR: tool failed: {exc}"

            # ToolMessage connects output to the exact tool call ID
            msgs.append(ToolMessage(content=str(tool_output), tool_call_id=tool_id))

    # Safety stop so the loop cannot run forever
    return "I couldn't finish tool use in time. Please try again."
