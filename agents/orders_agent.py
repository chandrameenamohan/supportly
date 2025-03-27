<<<<<<< HEAD
from typing import Dict, List, Any
=======
from datetime import datetime, timedelta, date
from typing import Dict, List, Optional, Any
>>>>>>> refs/remotes/origin/cm/orderstatus/first-interaction
from agents.base_agent import BaseAgent
from agents.orders_prompt import ORDER_STATUS_AGENT_PROMPT
from langgraph.graph import StateGraph, START, END, MessagesState
from langgraph.prebuilt import create_react_agent
from langchain.chat_models import init_chat_model
from langchain_core.tools import tool
<<<<<<< HEAD
from chat_models import ChatMessage, ChatHistory
from utils import naive_utcnow
=======
from langchain_community.tools.tavily_search import TavilySearchResults
from opik import Opik, track
from opik.integrations.langchain import OpikTracer
import calendar
import pytz
from dateutil.relativedelta import relativedelta
from dateutil.parser import parse
import holidays
import ephem
from chat_models import ChatMessage, ChatHistory
>>>>>>> refs/remotes/origin/cm/orderstatus/first-interaction


# Dummy asynchronous tool implementations.
# Replace these with your actual business logic.
@tool
async def fetch_customer_orders(customer_id: str):
    """
    Fetch customer orders given a customer id.
    """
    return f"Fetched orders for customer {customer_id}."

@tool
async def refund(order_id: str):
    """
    Process a refund for a given order id.
    """
    return f"Refund processed for order {order_id}."

@tool
async def return_item(order_id: str, item_id: str):
    """
    Initiate a return for an item in an order.
    """
    return f"Return initiated for item {item_id} on order {order_id}."

@tool
async def replace_item(order_id: str, item_id: str):
    """
    Initiate a replacement for an item in an order.
    """
    return f"Replacement initiated for item {item_id} on order {order_id}."

@tool
async def cancel_order(order_id: str):
    """
    Cancel an order given an order id.
    """
    return f"Order {order_id} has been cancelled."

@tool
async def change_shipping_address(order_id: str, new_address: str):
    """
    Change the shipping address for an order.
    """
    return f"Shipping address for order {order_id} updated to {new_address}."

# Prepare a list of tools with metadata.
tools = [
    fetch_customer_orders,
    refund,
    return_item,
    replace_item,
    cancel_order,
    change_shipping_address
]


class WorkflowState(MessagesState):
    """State for our workflow."""
    messages: str = ""
    response: str = ""
    chat_history: List[Dict[str, str]] = []


class OrdersAgent(BaseAgent):
    """Week 3 Part 1 implementation focusing on tool-using agents."""
    
    def __init__(self):
        super().__init__()
        self.llm = None
        self.agent = None
        self.tools = []
        self.workflow = None
    
    def initialize(self) -> None:
        """Initialize components for the tool-using agent.
        
        Students should:
        - Initialize the chat model
        - Define tools for calculator, DateTime, and weather
        - Create the ReAct agent using LangGraph
        """
        self.llm = init_chat_model("gpt-4o", model_provider="openai")
        
        self.tools = self._create_tools()

        self.agent = self._create_agent()
        workflow_builder = StateGraph(WorkflowState)
        workflow_builder.add_node("preprocess", self._preprocess_node)
        workflow_builder.add_node("react_agent", self._react_agent_node)
        workflow_builder.add_node("postprocess", self._postprocess_node)
        workflow_builder.add_edge(START, "preprocess")
        workflow_builder.add_edge("preprocess", "react_agent")
        workflow_builder.add_conditional_edges(
            "react_agent",
            self._should_end,
            {"postprocess": "postprocess", "react_agent": "react_agent"}
        )
        workflow_builder.add_edge("postprocess", END)
        self.workflow = workflow_builder.compile()
    
    def _create_tools(self) -> List[Any]:
        """Create and return the list of tools for the agent.
        Returns:
            List: List of tool objects
        """
        return tools
    
    def _create_agent(self) -> Any:
        """Create and return the ReAct agent executor.
        
        Returns:
            Any: The agent executor graph or callable
        """
        agent = create_react_agent(
            self.llm,
            tools=self.tools,
        )
        return agent
    
    async def process_message(self, message: ChatMessage, chat_history: ChatHistory) -> ChatMessage:
        """Process a message using the tool-using agent."""
        
        user_message = message.message
                
        state = WorkflowState(messages=user_message)
        result = self.workflow.invoke(state)

        ai_message = result["messages"]
        
        chat_message = ChatMessage(
            message=ai_message[2].content,
            conversation_id=message.conversation_id,
            sender="ai",
            chat_history=chat_history,
            created_at=naive_utcnow()
        )
          
        return chat_message
    
    def _preprocess_node(self, state: WorkflowState) -> WorkflowState:
        """Preprocess the message for the agent."""
        messages = state["messages"]
        # We only need to preprocess the latest message
        user_query = messages
        
        # Don't modify the query with calculation-specific text
        # This was causing the agent to focus only on calculations
        preprocessed_query = user_query
        
        # Update the last message with preprocessed content
        messages = preprocessed_query
        
        return {"messages": messages}
    
    def _react_agent_node(self, state: WorkflowState) -> WorkflowState:
        """Run the agent for the agent."""
        # Get the user message from the state
        user_message = state["messages"]
        
        # Define the system prompt
        system_prompt = ORDER_STATUS_AGENT_PROMPT
        # Pass the system prompt and user message to the agent
        result = self.agent.invoke({
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ]
        })
        
        return {"messages": result["messages"]}
    
    def _postprocess_node(self, state: WorkflowState) -> WorkflowState:
        """Postprocess the message for the agent."""
        agent_response = state["messages"]
        return {"response": agent_response}
    
    def _should_end(self, state: WorkflowState) -> str:
        """Check if the agent should end."""
        if state["messages"] and state["messages"][-1].content:
            return "postprocess"
        return "react_agent"
