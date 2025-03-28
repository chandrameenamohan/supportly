import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# API configuration
API_HOST = os.getenv("API_HOST") or "127.0.0.1:8000"
API_URL = f"http://{API_HOST}"

# OpenAI configuration
EMBEDDING_MODEL = "text-embedding-3-large"
LLM_MODEL = "gpt-4o"

# Options are "openai", "anthropic", "azure", "dummy"
# If you want to use Azure, you need to set the AZURE_OPENAI_API_KEY, AZURE_OPENAI_API_VERSION, and AZURE_OPENAI_API_BASE environment variables
# If you want to use OpenAI, you need to set the OPENAI_API_KEY environment variable
# If you want to use Anthropic, you need to set the ANTHROPIC_API_KEY environment variable
# "dummy" is for testing without API keys
LLM_VENDOR = "azure"
EMBEDDING_VENDOR = "azure"

# Construct database URL
DB_URL = os.getenv("DB_URL") or "sqlite+aiosqlite:///db.sqlite"
