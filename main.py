import os
import yaml
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_community.chat_message_histories import ChatMessageHistory
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

# Load environment variables
load_dotenv()

# Initialize Slack App
app = App(token=os.environ.get("SLACK_BOT_TOKEN"))

def load_config():
    """Load configuration from config.yaml."""
    try:
        with open('config.yaml', 'r') as file:
            return yaml.safe_load(file)
    except Exception as e:
        print(f"Error loading config.yaml: {str(e)}")
        return None

def initialize_chat():
    """Initialize the chat model and conversation chain."""
    config = load_config()
    if not config:
        raise ValueError("Failed to load configuration")

    chat = ChatGroq(
        groq_api_key=os.getenv("GROQ_API_KEY"),
        model_name=config['model']['name']
    )
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", "You are a helpful AI assistant."),
        MessagesPlaceholder(variable_name="history"),
        ("human", "{input}")
    ])
    
    chain = prompt | chat
    
    chain_with_history = RunnableWithMessageHistory(
        chain,
        lambda session_id: ChatMessageHistory(), # Use a more persistent store for production
        input_messages_key="input",
        history_messages_key="history"
    )
    
    return chain_with_history

# Initialize chat chain globally
try:
    chat_chain = initialize_chat()
except ValueError as e:
    print(f"Failed to initialize chat: {e}")
    print("Please make sure you have set up your GROQ_API_KEY in the .env file and config.yaml is correct.")
    exit(1) # Exit if chat initialization fails

@app.event("app_mention")
def handle_app_mention_events(body, say, logger):
    """Handles mentions of the bot in Slack."""
    print("\n--- App Mention Event Received ---")
    print(f"Body: {body}")
    logger.info(f"Received app_mention event: {body}")
    try:
        user_query = body["event"]["text"]
        print(f"User query: {user_query}")
        # The user ID is part of the mention, e.g. "<@U0XXXXXXX> your query"
        # We need to remove the bot's mention from the query
        bot_user_id = body["authorizations"][0]["user_id"]
        print(f"Bot user ID: {bot_user_id}")
        clean_query = user_query.replace(f"<@{bot_user_id}>", "").strip()
        print(f"Cleaned query: {clean_query}")

        if not clean_query:
            say("It looks like you mentioned me but didn't ask anything!")
            return

        # Use channel ID as session_id for conversation history
        # For threads, use thread_ts if available, otherwise channel_id
        session_id = body["event"].get("thread_ts", body["event"]["channel"])
        print(f"Session ID: {session_id}")
        
        # Get AI response
        print("Invoking chat_chain...")
        response = chat_chain.invoke(
            {"input": clean_query},
            config={"configurable": {"session_id": session_id}}
        )
        print(f"Chat chain response: {response.content}")
        
        # Send response to Slack
        # If the original message was in a thread, reply in that thread
        thread_ts = body["event"].get("ts") # 'ts' is the timestamp of the original message
        print(f"Replying to thread_ts: {thread_ts}")
        say(text=response.content, thread_ts=thread_ts)
        print("--- Event Handled Successfully ---")

    except Exception as e:
        logger.error(f"Error handling app_mention: {e}")
        print(f"Error in handle_app_mention_events: {e}")
        say("Sorry, I encountered an error while processing your request.")

def main():
    """Start the Slack app using Socket Mode."""
    # Check for essential tokens
    slack_app_token = os.environ.get("SLACK_APP_TOKEN")
    slack_bot_token = os.environ.get("SLACK_BOT_TOKEN")

    if not slack_app_token:
        print("SLACK_APP_TOKEN not found. Please set it in your .env file.")
        return
    if not slack_bot_token:
        print("SLACK_BOT_TOKEN not found. Please set it in your .env file.")
        return
        
    # Initialize handler first, so app.client is configured for startup message
    handler = SocketModeHandler(app, slack_app_token) # app is already initialized globally

    # Attempt to send a startup message
    test_channel_id = os.environ.get("SLACK_TEST_CHANNEL_ID")
    if test_channel_id:
        try:
            app.client.chat_postMessage(
                channel=test_channel_id,
                text="Hello! I'm awake."
            )
            print(f"Sent startup message to channel ID: {test_channel_id}")
        except Exception as e:
            print(f"Error sending startup message to {test_channel_id}: {e}")
            print("Please ensure the SLACK_TEST_CHANNEL_ID is correct and the bot has permissions to post in it.")
    else:
        print("SLACK_TEST_CHANNEL_ID not found in .env. Skipping startup message.")

    print("⚡️ Slack app is running in Socket Mode!")
    handler.start() # This call blocks

if __name__ == "__main__":
    main()
