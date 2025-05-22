import os
import yaml
from dotenv import load_dotenv
from rich.console import Console
from rich.markdown import Markdown
from rich.style import Style
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_core.messages import AIMessage, HumanMessage
from langchain_community.chat_message_histories import ChatMessageHistory

# Load environment variables
load_dotenv()

# Initialize Rich console with custom styles
console = Console()
user_style = Style(color="green", bold=True)
assistant_style = Style(color="blue", bold=True)
info_style = Style(color="yellow", bold=True)

def load_config():
    """Load configuration from config.yaml."""
    try:
        with open('config.yaml', 'r') as file:
            return yaml.safe_load(file)
    except Exception as e:
        console.print(f"\n[bold red]Error loading config.yaml: {str(e)}[/bold red]")
        return None

def initialize_chat():
    """Initialize the chat model and conversation chain."""
    # Load configuration
    config = load_config()
    if not config:
        raise ValueError("Failed to load configuration")

    # Initialize the chat model
    chat = ChatGroq(
        groq_api_key=os.getenv("GROQ_API_KEY"),
        model_name=config['model']['name']
    )
    
    # Create the prompt template
    prompt = ChatPromptTemplate.from_messages([
        ("system", "You are a helpful AI assistant."),
        MessagesPlaceholder(variable_name="history"),
        ("human", "{input}")
    ])
    
    # Create the chain
    chain = prompt | chat
    
    # Add message history
    chain_with_history = RunnableWithMessageHistory(
        chain,
        lambda session_id: ChatMessageHistory(),
        input_messages_key="input",
        history_messages_key="history"
    )
    
    return chain_with_history

def main():
    """Main chat loop."""
    console.print("Welcome to the Command Line Chat!", style=info_style)
    console.print("Type 'quit' or 'exit' to end the conversation.\n")
    
    try:
        chat_chain = initialize_chat()
        session_id = "default"  # You could generate unique session IDs for multiple users
        
        while True:
            # Get user input with styled prompt
            console.print("You:", style=user_style, end=" ")
            user_input = input()
            
            # Check if user wants to quit
            if user_input.lower() in ['quit', 'exit']:
                console.print("\nGoodbye!", style=info_style)
                break
            
            # Get AI response
            with console.status("[yellow]Thinking...[/yellow]"):
                response = chat_chain.invoke(
                    {"input": user_input},
                    config={"configurable": {"session_id": session_id}}
                )
            
            # Display AI response
            console.print("\nAssistant:", style=assistant_style)
            console.print(Markdown(response.content))
            console.print()  # Empty line for better readability
            
    except Exception as e:
        console.print(f"\n[bold red]An error occurred: {str(e)}[/bold red]")
        console.print("\nPlease make sure you have set up your GROQ_API_KEY in the .env file.")

if __name__ == "__main__":
    main()
