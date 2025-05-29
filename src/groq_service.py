import logging
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_community.chat_message_histories import ChatMessageHistory

logger = logging.getLogger(__name__)

class GroqChatService:
    """Handles interactions with the Groq API via Langchain."""
    def __init__(self, api_key: str, model_name: str):
        if not api_key:
            raise ValueError("Groq API key must be provided.")
        if not model_name:
            raise ValueError("Groq model name must be provided.")
            
        logger.info(f"Initializing GroqChatService with model: {model_name}")
        self._chat_model = ChatGroq(groq_api_key=api_key, model_name=model_name)
        self._prompt = ChatPromptTemplate.from_messages([
            ("system", "You are a helpful AI assistant."),
            MessagesPlaceholder(variable_name="history"),
            ("human", "{input}")
        ])
        
        # Store for message histories, keyed by session_id
        self.message_histories = {}

        # The lambda now uses self.message_histories to ensure the same
        # ChatMessageHistory object is used for the same session_id.
        self._chain_with_history = RunnableWithMessageHistory(
            self._prompt | self._chat_model,
            # self.get_session_history, # This is an alternative if you prefer a method
            lambda session_id: self.message_histories.setdefault(session_id, ChatMessageHistory()),
            input_messages_key="input",
            history_messages_key="history"
        )
        logger.info("GroqChatService initialized successfully with in-memory session history.")

    # Optional: If you prefer a method for the lambda:
    # def get_session_history(self, session_id):
    #     return self.message_histories.setdefault(session_id, ChatMessageHistory())

    def invoke(self, user_input: str, session_id: str):
        logger.info(f"Invoking Groq LLM for session_id: {session_id} with input: '{user_input[:50]}...'")
        try:
            response = self._chain_with_history.invoke(
                {"input": user_input},
                config={"configurable": {"session_id": session_id}}
            )
            llm_response_content = response.content 
            logger.info(f"Received response from Groq LLM: '{llm_response_content[:50]}...'")
            return llm_response_content
        except Exception as e:
            logger.error(f"Error invoking Groq LLM: {e}", exc_info=True)
            raise 