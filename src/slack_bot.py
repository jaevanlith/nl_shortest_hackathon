import logging
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
# Use relative imports for sibling modules within the 'src' package
from .config_manager import ConfigManager 
from .groq_service import GroqChatService

logger = logging.getLogger(__name__)

class SlackBot:
    """Manages the Slack Bolt App, event handling, and Socket Mode."""
    def __init__(self, config: ConfigManager, chat_service: GroqChatService):
        self.config = config
        self.chat_service = chat_service
        self.app = App(token=self.config.slack_bot_token)
        self._register_event_handlers()
        logger.info("SlackBot initialized.")

    def _register_event_handlers(self):
        self.app.event("app_mention")(self._handle_app_mention)
        logger.info("Registered app_mention event handler.")

    def _handle_app_mention(self, body, say, logger): 
        logger.info(f"Received app_mention event (raw body keys): {list(body.keys())}")
        
        try:
            event_data = body.get("event", {})
            user_query = event_data.get("text", "")
            authorizations = body.get("authorizations", [])
            bot_user_id = None
            if authorizations and isinstance(authorizations, list) and len(authorizations) > 0:
                 bot_user_id = authorizations[0].get("user_id")

            if not bot_user_id:
                logger.error("Could not determine bot_user_id from event body.")
                clean_query = user_query.strip() 
            else:
                clean_query = user_query.replace(f"<@{bot_user_id}>", "").strip()

            if not clean_query:
                say("It looks like you mentioned me but didn't ask anything! Try asking a question.")
                return

            session_id = event_data.get("thread_ts", event_data.get("channel", "default_session"))
            if not session_id: 
                session_id = "unknown_session_" + event_data.get("ts", "fallback_ts")
            
            logger.info(f"Cleaned query for chat service: '{clean_query}', session_id: {session_id}")
            ai_response = self.chat_service.invoke(clean_query, session_id)
            
            thread_ts = event_data.get("ts") 
            say(text=ai_response, thread_ts=thread_ts)
            logger.info("Successfully handled app_mention and responded.")

        except Exception as e:
            logger.error(f"Error in _handle_app_mention: {e}", exc_info=True)
            try:
                say("Sorry, I encountered an internal error while processing your request. Please try again later.")
            except Exception as say_e:
                logger.error(f"Failed to send error message to Slack: {say_e}", exc_info=True)

    def start(self):
        handler = SocketModeHandler(self.app, self.config.slack_app_token)
        
        if self.config.slack_test_channel_id:
            try:
                self.app.client.chat_postMessage(
                    channel=self.config.slack_test_channel_id,
                    text="Hello! SlackBot is now online."
                )
                logger.info(f"Sent startup message to channel ID: {self.config.slack_test_channel_id}")
            except Exception as e:
                logger.error(f"Error sending startup message to {self.config.slack_test_channel_id}: {e}", exc_info=True)
                logger.warning("Please ensure the SLACK_TEST_CHANNEL_ID is correct and the bot has permissions to post in it.")
        else:
            logger.info("SLACK_TEST_CHANNEL_ID not found in config. Skipping startup message.")

        logger.info("⚡️ SlackBot is starting in Socket Mode...")
        handler.start() 