from typing import Annotated, List, TypedDict, Sequence, Literal
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage, AIMessage
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent
from langgraph.graph import StateGraph, END
from langchain.chat_models import init_chat_model
from agents.base_agent import BaseAgent
from chat_models import ChatMessage, ChatHistory, ChatHistoryItem
from textwrap import dedent
from utils import naive_utcnow
from llm_factory import LLMFactory
from config import LLM_MODEL, LLM_VENDOR
import re

# Define tool for fetching orders
@tool
def get_recent_orders(customer_id: str = "CUST-001", limit: int = 5) -> str:
    """Fetch the most recent orders for a customer."""
    total_orders = 8  # Total orders for this customer
    
    # Generate sample orders
    orders = []
    for i in range(min(limit, total_orders)):
        order = {
            "order_id": f"ORD-{100 + i}",
            "date": f"2023-03-{20 - i}",
            "status": ["Delivered", "Shipped", "Processing"][i % 3],
            "items": [f"Product {i+1}"],
            "total": f"${50 + i*10}.00"
        }
        orders.append(order)
    
    # Format the response
    response = f"Found {total_orders} orders for customer {customer_id}. Here are the {len(orders)} most recent:\n\n"
    for order in orders:
        response += f"Order ID: {order['order_id']}\n"
        response += f"Date: {order['date']}\n"
        response += f"Status: {order['status']}\n"
        response += f"Items: {', '.join(order['items'])}\n"
        response += f"Total: {order['total']}\n\n"
    
    if total_orders > limit:
        response += f"There are {total_orders - limit} more orders not shown."
    
    return response

# Add a new tool for canceling orders
@tool
def cancel_order(order_id: str, customer_id: str = "CUST-001") -> str:
    """Cancel an order if it's eligible for cancellation."""
    # In a real system, you would check the database if this order exists and is cancellable
    # For this example, let's assume orders with "Processing" status can be cancelled
    
    # Check if the order exists (simplified example)
    orders = []
    for i in range(8):  # We have 8 total orders in our demo
        order = {
            "order_id": f"ORD-{100 + i}",
            "date": f"2023-03-{20 - i}",
            "status": ["Delivered", "Shipped", "Processing"][i % 3],
            "items": [f"Product {i+1}"],
            "total": f"${50 + i*10}.00"
        }
        orders.append(order)
    
    # Find the order
    order = next((o for o in orders if o["order_id"] == order_id), None)
    
    if not order:
        return f"Order {order_id} not found for customer {customer_id}."
    
    # Check if order can be cancelled
    if order["status"] == "Processing":
        return f"Order {order_id} has been successfully cancelled. Your refund will be processed within 3-5 business days."
    elif order["status"] == "Shipped":
        return f"Order {order_id} has already been shipped. Please initiate a return once you receive it."
    else:  # Delivered
        return f"Order {order_id} has already been delivered. Please initiate a return process instead of cancellation."

# Define the agent state
class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], "Chat history"]
    query_type: Annotated[str, "Type of query detected"]

# Initialize the LLM and tools
# llm = ChatOpenAI(temperature=0)
llm = init_chat_model("gpt-4o", model_provider="openai")
tools = [get_recent_orders, cancel_order]  # Update tools list
react_agent = create_react_agent(llm, tools)

def classify_query(query: str) -> str:
    """
    Classify the customer query based on keywords.
    For now, if it contains phrases like 'order status', 'orders', etc.,
    we label it as an 'order_query'. Otherwise, it's classified as 'other'.
    """
    query_lower = query.lower()
    if any(phrase in query_lower for phrase in ["order status", "orders", "latest orders", "my order", "cancel", "cancellation"]):
        return "order_query"
    # Additional classifications (like cancellation or tracking) can be added here.
    return "other"

class OrdersAgent(BaseAgent):
    """
    The orders agent is responsible for handling order-related queries from users,
    such as order status, cancellations, and retrievals.
    """

    def __init__(self):
        super().__init__()
        self.llm = None
        self.current_order_context = None
        self.multiple_orders_in_context = False
        # Tools will be initialized in the initialize method
        self.tools = []
        
    def initialize(self):
        self.llm = LLMFactory.create_llm(LLM_MODEL, LLM_VENDOR)
        # Initialize the agent-specific LLM for ReAct pattern
        self.agent_llm = init_chat_model("gpt-4o", model_provider="openai")
        
        # Use the global tool functions instead of class methods
        # This ensures proper tool registration
        self.tools = [get_recent_orders, cancel_order]
        self.react_agent = self.create_react_agent()
        
    @tool
    def get_recent_orders(self, customer_id: str = "CUST-001", limit: int = 5) -> str:
        """Fetch the most recent orders for a customer."""
        total_orders = 8  # Total orders for this customer
        
        # Generate sample orders - this would be replaced with actual DB calls
        orders = []
        for i in range(min(limit, total_orders)):
            order = {
                "order_id": f"ORD-{100 + i}",
                "date": f"2023-03-{20 - i}",
                "status": ["Delivered", "Shipped", "Processing"][i % 3],
                "items": [f"Product {i+1}"],
                "total": f"${50 + i*10}.00"
            }
            orders.append(order)
        
        # Format the response
        response = f"Found {total_orders} orders for customer {customer_id}. Here are the {len(orders)} most recent:\n\n"
        for order in orders:
            response += f"Order ID: {order['order_id']}\n"
            response += f"Date: {order['date']}\n"
            response += f"Status: {order['status']}\n"
            response += f"Items: {', '.join(order['items'])}\n"
            response += f"Total: {order['total']}\n\n"
        
        if total_orders > limit:
            response += f"There are {total_orders - limit} more orders not shown."
        
        return response

    @tool
    def cancel_order(self, order_id: str, customer_id: str = "CUST-001") -> str:
        """Cancel an order if it's eligible for cancellation."""
        # In a real system, you would check the database
        # For this example, let's assume orders with "Processing" status can be cancelled
        
        # Generate sample orders for verification
        orders = []
        for i in range(8):  # We have 8 total orders in our demo
            order = {
                "order_id": f"ORD-{100 + i}",
                "date": f"2023-03-{20 - i}",
                "status": ["Delivered", "Shipped", "Processing"][i % 3],
                "items": [f"Product {i+1}"],
                "total": f"${50 + i*10}.00"
            }
            orders.append(order)
        
        # Find the order
        order = next((o for o in orders if o["order_id"] == order_id), None)
        
        if not order:
            return f"Order {order_id} not found for customer {customer_id}."
        
        # Check if order can be cancelled
        if order["status"] == "Processing":
            return f"Order {order_id} has been successfully cancelled. Your refund will be processed within 3-5 business days."
        elif order["status"] == "Shipped":
            return f"Order {order_id} has already been shipped. Please initiate a return once you receive it."
        else:  # Delivered
            return f"Order {order_id} has already been delivered. Please initiate a return process instead of cancellation."
    
    def create_react_agent(self):
        """Create a ReAct agent with the order tools."""
        from langgraph.prebuilt import create_react_agent
        return create_react_agent(self.agent_llm, self.tools)
    
    def classify_query(self, query: str) -> str:
        """Classify the customer query based on keywords."""
        query_lower = query.lower()
        if any(phrase in query_lower for phrase in ["order status", "orders", "latest orders", "my order", "cancel", "cancellation"]):
            return "order_query"
        return "other"
    
    def convert_chat_history_to_langchain(self, chat_history: ChatHistory):
        """Convert ChatHistory object to langchain message format."""
        lc_messages = []
        
        # Add system message first
        system_prompt = """You are a helpful customer support bot for Acme Shoe, Inc. An online retailer of shoes of all types.
        
When a customer asks about their orders, use the get_recent_orders tool to fetch their recent orders.
By default, show the latest 5 orders. If there are more orders, ask if they want to see more.

When a customer wants to cancel an order, first check which order they want to cancel. 
If they don't specify which order to cancel, ask them to provide the order ID.
Then use the cancel_order tool with the order_id to attempt cancellation.

The customer ID is automatically provided in the system.

Respond to queries like:
- "Order Status"
- "What are my Orders"
- "Give me latest orders"
- "My Order"
- "Cancel my order"
"""
        lc_messages.append(SystemMessage(content=system_prompt))
        
        # Convert existing chat history
        for msg in chat_history.messages:
            if msg.is_user_message():
                lc_messages.append(HumanMessage(content=f"{msg.content} [Customer ID: CUST-001]"))
            elif msg.is_assistant_message():
                lc_messages.append(AIMessage(content=msg.content))
        
        return lc_messages

    async def process_message(self, message: ChatMessage, chat_history: ChatHistory) -> ChatMessage:
        query = message.message
        query_lower = query.lower()
        
        # Update context tracking based on message content
        self.update_order_context(query, chat_history)
        
        # Handle context-dependent queries like "cancel it"
        if any(phrase in query_lower for phrase in ["cancel it", "cancel this order", "i want to cancel"]):
            if self.current_order_context and not self.multiple_orders_in_context:
                # We have a specific order in context, so proceed with cancellation
                query = f"cancel order {self.current_order_context}"
            else:
                # We don't have a specific order or have multiple orders in context
                # Let the agent ask for clarification naturally
                query = "I want to cancel an order but I'm not sure which one"
        
        # Convert chat history to langchain format and add the current query
        lc_messages = self.convert_chat_history_to_langchain(chat_history)
        lc_messages.append(HumanMessage(content=f"{query} [Customer ID: CUST-001]"))
        
        # Invoke the ReAct agent
        result = self.react_agent.invoke({"messages": lc_messages})
        
        # Extract the latest AI response
        ai_messages = [msg for msg in result["messages"] if isinstance(msg, AIMessage)]
        if not ai_messages:
            response_text = "I'm having trouble processing your order query. Can you please try again?"
        else:
            response_text = ai_messages[-1].content
            
            # Update order context after processing
            self.update_order_context_from_response(query, response_text)
        
        # Create suggestions based on the current context
        suggestions = self.generate_suggestions()
        
        return ChatMessage(
            message=response_text,
            conversation_id=message.conversation_id,
            sender="ai",
            chat_history=chat_history,
            suggestions=suggestions,
            created_at=naive_utcnow()
        )
    
    def update_order_context(self, query: str, chat_history: ChatHistory):
        """Update the order context based on the query and chat history."""
        # Check if we're showing recent orders
        if "recent orders" in query.lower() or "order status" in query.lower():
            self.multiple_orders_in_context = True
            self.current_order_context = None
            return
            
        # Look for order IDs in the query
        import re
        order_ids = re.findall(r'ORD-\d+', query)
        if order_ids:
            self.current_order_context = order_ids[0]
            self.multiple_orders_in_context = False
            return
            
        # Check for "order N" pattern
        order_num_match = re.search(r'order (\d+)', query.lower())
        if order_num_match:
            try:
                order_num = int(order_num_match.group(1))
                self.current_order_context = f"ORD-{order_num}"
                self.multiple_orders_in_context = False
                return
            except ValueError:
                pass
    
    def update_order_context_from_response(self, query: str, response: str):
        """Update order context based on the response."""
        # If showing orders, we have multiple in context
        if "Found" in response and "orders" in response:
            self.multiple_orders_in_context = True
            
        # If a specific order was mentioned in the response, update context
        import re
        order_ids = re.findall(r'ORD-\d+', response)
        if len(order_ids) == 1:
            self.current_order_context = order_ids[0]
            self.multiple_orders_in_context = False
    
    def generate_suggestions(self) -> List[str]:
        """Generate contextual suggestions based on the current state."""
        suggestions = []
        
        # Basic suggestions
        suggestions.append("Show my recent orders")
        
        # If we have a specific order in context, add relevant suggestions
        if self.current_order_context:
            suggestions.append(f"Cancel order {self.current_order_context}")
            suggestions.append(f"Track order {self.current_order_context}")
        
        # If we have multiple orders in context, add general suggestions
        if self.multiple_orders_in_context:
            suggestions.append("Show more orders")
        
        return suggestions[:3]  # Limit to 3 suggestions

# Keep only the new main program
async def main():
    print("Welcome to the Acme Shoe Customer Support! Type 'exit' to quit.")
    
    # Initialize the agent
    agent = OrdersAgentV1()
    agent.initialize()
    
    # Create empty chat history
    chat_history = ChatHistory(messages=[])
    conversation_id = "test-conversation-123"
    
    # Chat loop
    while True:
        # Get user input
        user_input = input("\nHow can I help you with your orders? ")
        
        # Check if user wants to exit
        if user_input.lower() in ["exit", "quit", "bye"]:
            print("Thank you for using our service. Goodbye!")
            break
        
        # Create user message and add to history
        user_message = ChatHistoryItem(
            role="user",
            content=user_input,
            created_at=naive_utcnow()
        )
        chat_history.add_message(user_message)
        
        # Create message object for processing
        message = ChatMessage(
            message=user_input,
            conversation_id=conversation_id,
            sender="user",
            created_at=naive_utcnow()
        )
        
        # Process message through agent
        response = await agent.process_message(message, chat_history)
        
        # Add assistant response to history
        assistant_message = ChatHistoryItem(
            role="assistant",
            content=response.message,
            created_at=naive_utcnow()
        )
        chat_history.add_message(assistant_message)
        
        # Print response
        print(f"\nAssistant: {response.message}")
        
        # Show suggestions if available
        if response.suggestions and len(response.suggestions) > 0:
            print("\nSuggestions:")
            for i, suggestion in enumerate(response.suggestions, 1):
                print(f"{i}. {suggestion}")

if __name__ == "__main__":
    asyncio.run(main())