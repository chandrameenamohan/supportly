# Supportly

Supportly is an AI-powered customer support platform that routes customer inquiries to specialized agents based on intent.

## Features

- **Multi-Agent Architecture**: Routes customer inquiries to specialized agents
- **Intent Classification**: Automatically determines customer needs
- **Domain-Specific Agents**: Specialized handling for orders, products, and knowledge base queries
- **Web Client Interface**: User-friendly chat interface

## Installation

### 1. Backend Setup

#### Install Python Dependencies
```bash
pip install -r requirements.txt
```

#### Configure LLM Settings
Edit the `config.py` file to set your LLM vendor and model:
```python
LLM_VENDOR = "openai"  # Options: "openai", "azure", "anthropic"
LLM_MODEL = "gpt-4o"   # Model name for your selected vendor
```

**Note:** You may need to modify `llm_factory.py` to adjust LLM initialization parameters for your specific provider, the Azure initialization is the only one that has been tested.

#### Set API Keys
Create a `.env` file in the project root with your API keys:
```
OPENAI_API_KEY = "your-openai-api-key"
AZURE_OPENAI_API_KEY = "your-azure-openai-api-key"
ANTHROPIC_API_KEY = "your-anthropic-api-key"
```

#### Initialize Database
This creates a SQLite database in the project root, named db.sqlite.
```bash
python initialize_db.py
```

#### Initialize RAG Store
This loads and processes documents in the rag store.
```bash
python initialize_vector_store.py
```

#### Generate fake order data
Run the order_data/generate_fake_order_data.py from command line.

### 2. Frontend Setup

#### Install NPM Dependencies
```bash
cd ai-chat-client
npm install
```

## Running the Application

### Start the Backend Server
```bash
uvicorn api:app --reload
```

### Start the Web Client
```bash
cd ai-chat-client
npm start
```

## Development Guide

### Key Components to Modify

| Component | File | Purpose |
|-----------|------|---------|
| Orchestrator | `agents/orchestrator_agent.py` | Intent classification and routing |
| Greeting Agent | `agents/greeting_agent.py` | Initial customer interaction |
| Orders Agent | `agents/orders_agent.py` | Order-related inquiries |
| Products Agent | `agents/products_agent.py` | Product information requests |
| Knowledge Agent | `agents/knowledge_agent.py` | RAG-based knowledge retrieval |

## Architecture

Supportly uses a multi-agent architecture where the orchestrator classifies user intent and routes to specialized agents:

1. **User Request** → Web Client → API
2. **Orchestrator** determines intent
3. **Specialized Agent** (Orders/Products/Knowledge) handles the request
4. **Response** returned to user

## Debug 
In visual code or cursor we can run and debug the code using Run and Debug Feature of it.
There is launch.json which you can use.
Follow this video to check on how to run: https://www.youtube.com/watch?v=3HiLLByBWkg

## License

[Your license information here]



