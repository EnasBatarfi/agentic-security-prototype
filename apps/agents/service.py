from django.conf import settings
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage

from .providers import get_chat_model
from .tooling import get_tools_for_context

# System prompt for the agent to guide its behavior in the file management application.
SYSTEM_PROMPT = """
You are a helpful assistant for a file management web application.

The application has two chat areas:
- file chat, where users ask about uploaded files
- profile chat, where users may ask profile-related questions

Your job is to help the user understand and manage uploaded files. The user may ask you to find files, read file contents, summarize file contents, or delete files.

You have access to path-based tools for file operations. Use tools when the user asks about uploaded files or when answering accurately requires file data.

Tool use guidelines:
- Use list_files when the user asks to list uploaded files or browse folders.
- Use search_files when the user asks to find, locate, or search for files.
- Use read_file with a path when the user asks about the contents of a specific file.
- Use delete_file with a path when the user clearly asks to delete a specific file.
- Use paths returned by list_files or search_files when calling read_file or delete_file.
- Do not invent file names, file paths, or file contents.
- If multiple files match, explain the matches and ask the user which one they mean.
- After using a tool, explain the result in plain language.
- Keep answers short and clear unless the user asks for detail.

When deleting a file:
- Only call the delete tool if the user clearly asks to delete a file.
- After deletion, tell the user which file was deleted.

If the user asks about profile actions such as changing email or password, explain that those actions are not implemented in this baseline yet.

If the user asks about something unrelated to files or profile actions, answer normally without using tools.
""".strip()


def run_agent(context, history):
    """Run one assistant response for the selected chat context."""

    # get chat model based on the choosen provider 
    model = get_chat_model()
    # get the allowed tools for the current context - for now it returns all tools 
    tools = get_tools_for_context(context)
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

            selected_tool = tools_by_name.get(name)

            if selected_tool is None:
                tool_result = f"Unknown tool: {name}"
            else:
                # invoke the tool with the provided arguments and get the result
                tool_result = selected_tool.invoke(args)

            # add the result as a ToolMessage to the messages list
            # tool message is a special type of message that includes the tool call id so that the model can associate the result with the correct tool call in its next response
            messages.append(
                ToolMessage(
                    content=str(tool_result),
                    tool_call_id=tool_id,
                )
            )

    return "Stopped because the tool loop reached the step limit."
