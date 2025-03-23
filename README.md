# Supportly README

## Installation

### Install the python libraries:
> pip install -r requirements.txt

### Set your LLM vendor and model in the config.py file:
**Note that you may need to edit the llm_factory.py file to edit the llm initialization paremeters for openai and anthropic, I've only tested it with azure so far.**
> LLM_VENDOR = "openai"
> LLM_MODEL = "gpt-4o"

### Set your API Keys in your .env file:
> OPENAI_API_KEY = "your-openai-api-key"
> AZURE_OPENAI_API_KEY = "your-azure-openai-api-key"

### Install the database:
**This will create a sqlite database in the root directory of the project.**
> python initialize_db.py

### Install npm libraries for client:
> cd ai-chat-client
> npm install

## Run the python server
uvicorn api:app --reload

## Run the web client
> cd ai-chat-client
> npm start

## Files to modify
- agents/orders_agent.py (Where you will implement the order assistant functionality)
- agents/products_agent.py (Where you will implement the product assistant functionality)
- agents/orchestrator_agent.py (Where you will implement the classifier/intent routing functionality)
- agents/greeting_agent.py (Where you will implement the greeting functionality)
- agents/knowledge_agent.py (Where you will implement the rag/knowledge assistant functionality)



