# LangChain wrapper that talks to Ollama running locally on your machine
from langchain_ollama import ChatOllama

# Message classes in the format chat models expect
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

# A fixed instruction that always goes at the start of the conversation
SYSTEM_PROMPT = "You are a helpful assistant."

def generate_reply(user_text: str, conversation) -> str:
    # Create a local chat model client (Ollama must be running)
    # model: which local model to use
    # temperature: randomness (0.2 = mostly stable) (low temp-> stable/predictable answers)
    # num_ctx: max context window (how much text it can consider), smaller = faster
    # num_predict: max tokens to generate in the reply, smaller = faster
    llm = ChatOllama(
        model="llama3.2:3b",  # smaller/faster while model="llama3.1:8b" was bigger/stronger but slower
        temperature=0.2,
        num_ctx=2048,
        num_predict=256,
    )

    # Get the latest N messages from this conversation from the DB and used as context window
    # order_by("-created_at") gets newest messages first
    # [:10] limits to only the last 10 messages to keep prompts short and fast
    history = list(conversation.messages.order_by("-created_at")[:10])

    # Reverse so the messages become oldest -> newest (the natural order for chat models)
    history.reverse()

    # Build the prompt in the chat-message format:
    # start with a System message (instructions), then add the conversation turns.
    msgs = [SystemMessage(content=SYSTEM_PROMPT)]

    # Convert the stored DB messages into LangChain chat message objects
    for m in history:
        if m.role == "user":
            msgs.append(HumanMessage(content=m.content))
        else:
            # Any non-user role you stored (assistant) becomes an AIMessage
            msgs.append(AIMessage(content=m.content))

    # Send the message list to the model and get a response
    resp = llm.invoke(msgs)

    # Return the text content of the model response
    return resp.content