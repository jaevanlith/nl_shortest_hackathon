from typing import List, Tuple, Dict, Any, Annotated, Sequence
from datetime import datetime, timedelta
import os
import yaml
from dotenv import load_dotenv
from langgraph.graph import Graph, StateGraph, END
from langchain.tools import Tool
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage
from langchain_groq import ChatGroq
from langchain.agents import AgentExecutor, create_openai_tools_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
import pickle

# Load environment variables
load_dotenv()

# Google Calendar setup
SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']

def get_google_calendar_creds():
    """Get or refresh Google Calendar credentials."""
    creds = None
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=8080)
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)
    
    return creds

def load_config():
    """Load configuration from config.yaml."""
    try:
        with open('config.yaml', 'r') as file:
            return yaml.safe_load(file)
    except Exception as e:
        print(f"\n[bold red]Error loading config.yaml: {str(e)}[/bold red]")
        return None

def get_calendar_events(days: int = 7) -> str:
    """Get calendar events for the next specified number of days."""
    try:
        creds = get_google_calendar_creds()
        service = build('calendar', 'v3', credentials=creds)
        
        now = datetime.utcnow().isoformat() + 'Z'
        end_date = (datetime.utcnow() + timedelta(days=days)).isoformat() + 'Z'
        
        events_result = service.events().list(
            calendarId='primary',
            timeMin=now,
            timeMax=end_date,
            maxResults=10,
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        
        events = events_result.get('items', [])
        
        if not events:
            return "No upcoming events found."
            
        output = "Upcoming events:\n"
        for event in events:
            start = event['start'].get('dateTime', event['start'].get('date'))
            start_time = datetime.fromisoformat(start.replace('Z', '+00:00'))
            output += f"- {start_time.strftime('%Y-%m-%d %H:%M')} - {event['summary']}\n"
            
        return output
        
    except Exception as e:
        return f"Error accessing calendar: {str(e)}"

# Define the calendar tool
calendar_tool = Tool(
    name="get_calendar_events",
    description="Get upcoming calendar events for the next specified number of days",
    func=get_calendar_events
)

# Load configuration
config = load_config()
if not config:
    raise ValueError("Failed to load configuration from config.yaml")

# Initialize the LLM
llm = ChatGroq(
    groq_api_key=os.getenv("GROQ_API_KEY"),
    model_name=config['model']['name']
)

# Create tools list
tools = [calendar_tool]

# Create the prompt template
prompt = ChatPromptTemplate.from_messages([
    ("system", "You are a helpful AI assistant that can access the user's Google Calendar. When asked about calendar events or schedule, use the get_calendar_events tool to retrieve the information."),
    MessagesPlaceholder(variable_name="chat_history"),
    ("human", "{input}"),
    MessagesPlaceholder(variable_name="agent_scratchpad"),
])

# Create the agent
agent = create_openai_tools_agent(llm, tools, prompt)
agent_executor = AgentExecutor(agent=agent, tools=tools)

# Define the state type
class AgentState(dict):
    """State definition for the agent."""
    messages: Annotated[Sequence[BaseMessage], "The messages in the conversation"]

def process_message(state: AgentState) -> AgentState:
    """Process the message using the agent executor."""
    messages = state["messages"]
    last_message = messages[-1]
    
    # Run the agent
    response = agent_executor.invoke({
        "input": last_message.content,
        "chat_history": messages[:-1]  # All messages except the last one
    })
    
    messages.append(AIMessage(content=response["output"]))
    return {"messages": messages}

def define_workflow() -> Graph:
    """Define the agent workflow."""
    # Initialize workflow with state schema
    workflow = StateGraph(state_schema=AgentState)
    
    # Add the agent node
    workflow.add_node("agent", process_message)
    
    # Set the entry point
    workflow.set_entry_point("agent")
    
    # Add edge from agent to end
    workflow.add_edge("agent", END)
    
    # Compile the graph
    return workflow.compile()

def main():
    # Initialize the workflow
    chain = define_workflow()
    
    print("Calendar Agent initialized. Type 'quit' to exit.")
    while True:
        user_input = input("\nYou: ")
        if user_input.lower() == 'quit':
            break
            
        # Run the agent
        result = chain.invoke({
            "messages": [HumanMessage(content=user_input)]
        })
        
        # Print the final response
        final_message = result["messages"][-1]
        print(f"\nAssistant: {final_message.content}")

if __name__ == "__main__":
    main() 