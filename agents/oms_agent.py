from typing import Annotated, List, TypedDict, Sequence, Literal
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage, AIMessage
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent
from langgraph.graph import StateGraph, END
from langchain.chat_models import init_chat_model

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

def reach_agent(query: str, customer_id: str = "CUST-001"):
    """
    Create and invoke a ReAct agent with properly formatted messages.
    The query is classified to determine if it is order-related.
    """
    # Classify the query to determine intent
    query_type = classify_query(query)
    
    # Define the system prompt
    system_prompt = """You are an e-commerce customer service assistant.
    
When a customer asks about their orders, use the get_recent_orders tool to fetch their recent orders.
By default, show the latest 5 orders. If there are more orders, ask if they want to see more.

When a customer wants to cancel an order, first check which order they want to cancel. 
Then use the cancel_order tool with the order_id to attempt cancellation.

The customer ID is automatically provided in the system.

Respond to queries like:
- "Order Status"
- "What are my Orders"
- "Give me latest orders"
- "My Order"
- "Cancel my order"
"""
    
    # Create properly formatted messages, including the customer ID in the context
    agent_messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=f"{query} [Customer ID: {customer_id}]")
    ]
    
    # Pass the classified query type along with messages
    result = react_agent.invoke({"messages": agent_messages, "query_type": query_type})
    return result["messages"]

def route_query(state: AgentState) -> Literal["react", "other"]:
    """Route the query based on its classification."""
    return "react" if state["query_type"] == "order_query" else "other"

def handle_other_queries(state: AgentState) -> AgentState:
    """Handle non-order queries."""
    messages = state["messages"]
    response = AIMessage(content="I can help with order-related queries. For other assistance, please specify what you need help with regarding your orders.")
    return {
        "messages": list(messages) + [response],
        "query_type": state["query_type"]
    }

def build_order_agent():
    # Define the LLM and tools
    llm = ChatOpenAI(temperature=0)
    tools = [get_recent_orders, cancel_order]  # Update tools list
    
    # Define the system prompt
    system_prompt = """You are an e-commerce customer service assistant.
    
When a customer asks about their orders, use the get_recent_orders tool to fetch their recent orders.
By default, show the latest 5 orders. If there are more orders, ask if they want to see more.

When a customer wants to cancel an order, first check which order they want to cancel. 
Then use the cancel_order tool with the order_id to attempt cancellation.

The customer ID is automatically provided in the system.

Respond to queries like:
- "Order Status"
- "What are my Orders"
- "Give me latest orders"
- "My Order"
- "Cancel my order"
"""
    
    # Create the state graph
    graph = StateGraph(AgentState)
    graph.add_node("reach", reach_agent)
    graph.add_node("other", handle_other_queries)
    graph.add_edge("reach", route_query)
    graph.add_edge("react", END)
    graph.add_edge("other", END)
    graph.set_entry_point("reach")
    return graph.compile()

def run_order_agent(query: str, customer_id: str = "CUST-001"):
    """
    Build the agent and execute it using an initial state that includes
    the classified query type.
    """
    agent = build_order_agent()
    
    # Hard-code customer ID into the query for simplicity
    query_with_context = f"{query} [Customer ID: {customer_id}]"
    query_type = classify_query(query)
    initial_state = {
        "messages": [HumanMessage(content=query_with_context)],
        "query_type": query_type
    }
    
    result = agent.invoke(initial_state)
    return result["messages"]

# Example usage
if __name__ == "__main__":
    print("Welcome to the Order Management System! Type 'exit' to quit.")
    
    # Initialize conversation history to maintain context between interactions
    conversation_history = []
    system_message = SystemMessage(content="""You are an e-commerce customer service assistant.
    
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
""")
    conversation_history.append(system_message)
    
    # Track the current order being discussed for context
    current_order_context = None
    # Track if we have multiple orders in context
    multiple_orders_in_context = False
    
    while True:
        query = input("\nHow can I help you with your orders? ")
        
        # Check if user wants to exit
        if query.lower() in ["exit", "quit", "bye"]:
            print("Thank you for using our service. Goodbye!")
            break
        
        # Check for context-dependent queries and resolve references
        query_lower = query.lower()
        
        # When cancellation is requested
        if any(phrase in query_lower for phrase in ["cancel it", "cancel this order", "i want to cancel"]):
            # Check if we have a specific order in context
            if current_order_context and not multiple_orders_in_context:
                # We have a specific order in context, so proceed with cancellation
                query = f"cancel order {current_order_context}"
                print(f"(I understand you want to cancel order {current_order_context})")
            else:
                # We don't have a specific order or have multiple orders in context
                # Let the agent ask for clarification naturally
                query = "I want to cancel an order but I'm not sure which one"
        
        # Add user message to conversation history
        user_message = HumanMessage(content=f"{query} [Customer ID: CUST-001]")
        conversation_history.append(user_message)
        
        # Process query with full conversation history
        result = react_agent.invoke({"messages": conversation_history})
        
        # Extract the response and update conversation history
        ai_messages = [msg for msg in result["messages"] if isinstance(msg, AIMessage)]
        if ai_messages:
            latest_ai_message = ai_messages[-1]
            conversation_history.append(latest_ai_message)
        
        # Print the response
        print("\nResponse:")
        for msg in result["messages"]:
            if not isinstance(msg, SystemMessage) and msg not in conversation_history[:-2]:  # Skip previously shown messages
                print(f"{msg.type}: {msg.content}")
        
        # Update order context by checking if an order ID was mentioned
        import re
        
        # Get recent orders - this indicates multiple orders are being shown
        if "get_recent_orders" in query_lower or any(tool_msg.content.startswith("Found") for tool_msg in result["messages"] if hasattr(tool_msg, 'content')):
            multiple_orders_in_context = True
            current_order_context = None
        
        # Look for order IDs in the user's message
        order_ids = re.findall(r'ORD-\d+', query)
        if order_ids:
            # User mentioned a specific order
            current_order_context = order_ids[0]
            multiple_orders_in_context = False
        
        # If user explicitly mentions an order number, update the context
        if re.search(r'order (\d+)', query_lower):
            order_num = re.search(r'order (\d+)', query_lower).group(1)
            try:
                order_num = int(order_num)
                current_order_context = f"ORD-{order_num}"
                multiple_orders_in_context = False
            except ValueError:
                pass
