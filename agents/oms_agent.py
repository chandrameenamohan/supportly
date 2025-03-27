from typing import Annotated, List, TypedDict, Sequence, Literal
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage, AIMessage
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent
from langgraph.graph import StateGraph, END

# Define tool for fetching orders
@tool
def get_recent_orders(customer_id: str = "CUST-001", limit: int = 5) -> str:
    """Fetch the most recent orders for a customer."""
    # Mock implementation - would call your order API in production
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

# Define the state
class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], "Chat history"]
    query_type: Annotated[str, "Type of query detected"]
    # Define the LLM
llm = ChatOpenAI(temperature=0)
    
    # Define tools
tools = [get_recent_orders]  
react_agent = create_react_agent(llm, tools)
# Reach agent function
def reach_agent(query: str, customer_id: str = "CUST-001"):
    """
    Create and invoke a ReAct agent with properly formatted messages.
    
    Args:
        query: The user's query text
        customer_id: Customer identifier
        
    Returns:
        The agent's response
    """
  
    
    # Define the system prompt
    system_prompt = """You are an e-commerce customer service assistant.
    
    When a customer asks about their orders, use the get_recent_orders tool to fetch their recent orders.
    By default, show the latest 5 orders. If there are more orders, ask if they want to see more.
    
    The customer ID is automatically provided in the system.
    
    Respond to queries like:
    - "Order Status"
    - "What are my Orders"
    - "Give me latest orders"
    - "My Order"
    """
    
    # Create properly formatted messages
    agent_messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=f"{query} [Customer ID: {customer_id}]")
    ]
    
    # Invoke the agent directly with the messages
    result = react_agent.invoke({"messages": agent_messages})
    
    return result["messages"]

# Edge function
def route_query(state: AgentState) -> Literal["react", "other"]:
    """Route the query based on classification."""
    return "react" if state["query_type"] == "order_query" else "other"

# Other queries handler
def handle_other_queries(state: AgentState) -> AgentState:
    """Handle non-order queries."""
    messages = state["messages"]
    
    response = AIMessage(content="I can help with order-related queries. For other assistance, please specify what you need help with regarding your orders.")
    
    return {
        "messages": list(messages) + [response],
        "query_type": state["query_type"]
    }

# Build the order agent
def build_order_agent():
    # Define the LLM
    llm = ChatOpenAI(temperature=0)
    
    # Define tools
    tools = [get_recent_orders]
    
    # Define the system prompt
    system_prompt = """You are an e-commerce customer service assistant.
    
    When a customer asks about their orders, use the get_recent_orders tool to fetch their recent orders.
    By default, show the latest 5 orders. If there are more orders, ask if they want to see more.
    
    The customer ID is automatically provided in the system.
    
    Respond to queries like:
    - "Order Status"
    - "What are my Orders"
    - "Give me latest orders"
    - "My Order"
    """
    
    # Create the ReAct agent
    # react_agent = create_react_agent(llm, tools, system_prompt)
    
    # Create the graph
    graph = StateGraph(AgentState)
    
    # Add nodes
    graph.add_node("reach", reach_agent)
    # graph.add_node("react", react_agent)
    graph.add_node("other", handle_other_queries)
    
    # Add edges
    graph.add_edge("reach", route_query)
    graph.add_edge("react", END)
    graph.add_edge("other", END)
    
    # Set the entry point
    graph.set_entry_point("reach")
    
    return graph.compile()

# Run the agent
def run_order_agent(query: str, customer_id: str = "CUST-001"):
    agent = build_order_agent()
    
    # Hard-code customer ID into the query for simplicity
    query_with_context = f"{query} [Customer ID: {customer_id}]"
    
    initial_state = {
        "messages": [HumanMessage(content=query_with_context)],
        "query_type": ""
    }
    
    result = agent.invoke(initial_state)
    return result["messages"]

# Example usage
if __name__ == "__main__":
    query = "What are my recent orders?"
    response = reach_agent(query)
    
    # Print the response
    for msg in response:
        if not isinstance(msg, SystemMessage):
            print(f"{msg.type}: {msg.content}")