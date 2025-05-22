# Command Line Chat Application

A simple command-line chat application built with Langchain and Groq.

## Setup

1. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Paste your API key in the `.env.example` and change the name of the file to `.env`
```
GROQ_API_KEY=your_api_key_here
```

## Usage

Run the chat application:
```bash
python main.py
```

Type your messages and press Enter to chat. Type 'quit' or 'exit' to end the conversation. 