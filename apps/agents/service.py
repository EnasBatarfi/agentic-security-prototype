from django.conf import settings
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage

from .providers import get_chat_model
from .tooling import get_tools_for_context
from .enforcement import authorize_tool_invocation

# MCP tool flow:
# 1. Tool business logic is implemented in:
#    - mcp_server/tools/files.py
#    - mcp_server/tools/profiles.py
# 2. mcp_server/server.py registers these implementations as MCP tools
#    using FastMCP and runs with the stdio transport.
# 3. mcp_client/client.py starts the MCP server as a subprocess using:
#       python -m mcp_server.server
#    It creates an MCP session over stdin/stdout and invokes tools using
#    the MCP JSON-RPC protocol.
# 4. mcp_client/tools.py contains application-level wrapper functions.
#    These wrappers invoke the corresponding MCP tools by name.
# 5. mcp_client/tools.py wraps those functions as LangChain tools using
#    @tool. get_tools() returns them to the agent.
# 6. apps/agents/tooling.py retrieves the tools, and
#    apps/agents/service.py publishes them to the model using bind_tools().
# System prompt for the agent to guide its behavior in the file management application.


SYSTEM_PROMPT = """
You are a helpful assistant for a file management web application.

The application has two chat areas:
- file chat, where users usually ask about uploaded files
- profile chat, where users usually ask profile-related questions

The active chat context is provided as "Current context".
You are operating in only one active context at a time.

Context rules:
- Use only the tools and capabilities available in the current active context.
- Describe capabilities in user-facing language. Do not mention internal tool names to the user.
- If the user asks what tools or capabilities are available, answer only for the current active context.
- If the user asks for an action outside the current context, briefly ask them to switch to the correct chat area.
- If the user asks what is available in another chat area, do not describe that area’s actions.
- Do not describe tools or capabilities from other chat contexts.


Your job is to help the user based on the active context:
- In file chat, help with uploaded files.
- In profile chat, help with profile-related actions such as password reset.

File chat guidelines:
- Use list_files when the user asks to list uploaded files or browse available files. The tool returns the file tree recursively.
- Use search_files when the user asks to find, locate, or search for a specific file.
- Do not call list_files again on subfolders after listing files unless the user asks to inspect a specific folder.
- Prefer active files under users/ over deleted files under _deleted/ unless the user explicitly asks for deleted files.
- If search_files returns both an active file and a deleted copy, use the active file under users/ for read or delete.
- If the user gives a natural file name with spaces, search using simple keywords. For example, for "alice notes", search for "alice" first.
- Users usually provide file names or descriptions, not full paths.
- When the user asks to read or delete a file by name, search for the file first.
- Use read_file with the exact path returned by list_files or search_files.
- Use delete_file with the exact path returned by list_files or search_files.
- Do not invent file names, file paths, or file contents.
- Do not say a file does not exist until search_files has been used.
- If multiple active files match, explain the matches and ask the user which one they mean.
- After using a tool, briefly explain the result in plain language. Do not mention internal tool names.
- If a file read or delete request is not allowed, explain briefly that the file could not be accessed or changed because the application did not permit it.
- Do not claim that a file was read or deleted unless the tool result clearly shows success.

When deleting a file in file chat:
- Only call delete_file if the user clearly asks to delete a file.
- If the user gives only a file name, use search_files first to find the exact path.
- If search_files returns one clear matching file, call delete_file with that exact path.
- If search_files returns multiple matching files, ask which path the user means.
- Do not ask for confirmation after the user has already clearly asked to delete.
- Do not say a file was deleted unless delete_file returned a success message.

Profile chat guidelines:
- If the user asks to change or reset their password and provides an email address, use send_password_reset_email with that email address.
- If the user asks to change or reset their password but does not provide an email address, ask which email address should receive the password reset email.
- Use the email address provided by the user when calling send_password_reset_email.
- The application will only allow a password reset request if the provided email belongs to the signed-in user.
- Do not answer whether an email address is registered in the application.
- Do not guess, imply, or speculate that an email address is registered or not registered.
- After using the tool, briefly explain the result in plain language. Do not mention internal tool names.
- If the reset request is accepted, say that the password reset request was accepted and the user should check their email.
- If the reset request is not allowed, say: "The reset request could not be completed for that email. Please use the email linked to your signed-in account."

Keep answers short and clear unless the user asks for detail.
If the user asks about something unrelated to files or profile actions, answer normally without using tools.
""".strip()


def run_agent(user,context, history):
    """Run one assistant response for the selected chat context."""

    # --- DEBUGGING ---
    print("Current Django user:", user.pk, user.email)

    # get chat model based on the choosen provider 
    model = get_chat_model()

    # --- First PEP: get the allowed tools for the current context ---
    tools = get_tools_for_context(user, context)
    
    # --- DEBUGGING ---
    print("Bound tools:", context, [tool.name for tool in tools])

    # bind the tools to the model so that it can use them when generating responses
    model = model.bind_tools(tools)

    # start the message list with the system prompt and the current context, then add the conversation history
    messages = [
        SystemMessage(content=f"{SYSTEM_PROMPT}\n\nCurrent context: {context}")
    ]

    # add the conversation history to the messages list, converting each message to the appropriate format for the model
    for msg in history:
        if msg.role == "user":
            messages.append(HumanMessage(content=msg.content))
        else:
            messages.append(AIMessage(content=msg.content))

    # create a mapping of tool names to tool instances for easy lookup when the model calls tools by name
    tools_by_name = {tool.name: tool for tool in tools}

    # run a loop where the model generates responses and calls tools until it either stops generating tool calls or reaches a maximum number of steps to prevent infinite loops
    for _ in range(settings.MAX_TOOL_STEPS):
        # invoke the model with the current messages and get the response which may include tool calls
        response = model.invoke(messages)
        # add the model's response to the messages list so that the next iteration includes it in the context for generating the next response
        messages.append(response)

        # check if the model's response includes any tool calls. If not, we can return the content of the response as the final answer. If there are tool calls, we need to execute them and add their results back to the messages list for the next iteration.
        tool_calls = getattr(response, "tool_calls", None) or []

        if not tool_calls:
            return str(response.content)

        # execute each tool call by looking up the tool by name, invoking it with the provided arguments, 
        # and then adding the result as a ToolMessage to the messages list for the next iteration. 
        # If a tool name is unknown, we add a message indicating that.
        for tool_call in tool_calls:
            name = tool_call["name"]
            args = tool_call["args"]
            tool_id = tool_call["id"]

            # --- DEBUGGING ---
            print(f"Agent requested tool: {name}")
            print(f"Tool arguments: {args}")

            selected_tool = tools_by_name.get(name)

            # To prevent the model hallucinated or accessing unauthorized tools, we check if the tool name is in the list of allowed tools
            if selected_tool is None:
                tool_result = f"Unknown tool: {name}"
            else:
                # --- DEBUGGING ---
                print("Selected tool:", context, selected_tool.name, args)

                # --- Second PEP: authorize the selected tool invocation before execution ---
                authorization = authorize_tool_invocation(user=user, context=context, tool_name=name, args=args)

                if not authorization.allowed:
                    tool_result = authorization.message
                else:
                    tool_result = selected_tool.invoke(authorization.safe_args)

            # --- DEBUGGING ---
            print(f"Tool result: {tool_result}")

            # add the result as a ToolMessage to the messages list
            # tool message is a special type of message that includes the tool call id so that the model can associate the result with the correct tool call in its next response
            messages.append(
                ToolMessage(
                    content=str(tool_result),
                    tool_call_id=tool_id,
                )
            )

    return "Stopped because the tool loop reached the step limit."
