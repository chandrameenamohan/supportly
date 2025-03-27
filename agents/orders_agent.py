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
import sqlite3
import os
import asyncio
from datetime import datetime, timedelta
import random
import threading

# Define a class to handle the database operations
class OrdersDatabase:
    def __init__(self, db_path="orders.db"):
        self.db_path = db_path
        self.local = threading.local()  # Add thread-local storage
        self.initialize_database()
        
    def get_connection(self):
        # Check if this thread has a connection
        if not hasattr(self.local, 'conn'):
            # Create a new connection for this thread
            self.local.conn = sqlite3.connect(self.db_path)
            self.local.conn.row_factory = sqlite3.Row
        return self.local.conn
        
    def initialize_database(self):
        """Create the database and tables if they don't exist, and populate with initial data."""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Create tables
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS customers (
            customer_id TEXT PRIMARY KEY,
            name TEXT,
            email TEXT,
            address TEXT
        )
        ''')
        
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS products (
            product_id TEXT PRIMARY KEY,
            name TEXT,
            category TEXT,
            price REAL,
            description TEXT
        )
        ''')
        
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS orders (
            order_id TEXT PRIMARY KEY,
            customer_id TEXT,
            date TEXT,
            status TEXT,
            total REAL,
            FOREIGN KEY (customer_id) REFERENCES customers (customer_id)
        )
        ''')
        
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS order_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id TEXT,
            product_id TEXT,
            quantity INTEGER,
            price REAL,
            FOREIGN KEY (order_id) REFERENCES orders (order_id),
            FOREIGN KEY (product_id) REFERENCES products (product_id)
        )
        ''')
        
        # Check if data already exists
        cursor.execute("SELECT COUNT(*) FROM customers")
        customer_count = cursor.fetchone()[0]
        
        # Populate with initial data if empty
        if customer_count == 0:
            self.populate_initial_data()
            
        conn.commit()
    
    def populate_initial_data(self):
        """Populate the database with initial sample data."""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Sample customers
        customers = [
            ("CUST-001", "John Smith", "john.smith@example.com", "123 Main St, Anytown, USA"),
            ("CUST-002", "Jane Doe", "jane.doe@example.com", "456 Oak Ave, Somewhere, USA"),
            ("CUST-003", "Bob Johnson", "bob.johnson@example.com", "789 Pine Rd, Elsewhere, USA"),
        ]
        cursor.executemany("INSERT INTO customers VALUES (?, ?, ?, ?)", customers)
        
        # Sample shoe products
        products = [
            ("PROD-001", "Running Shoes - Blue", "Athletic", 89.99, "Lightweight running shoes with extra cushioning"),
            ("PROD-002", "Leather Oxford - Brown", "Formal", 129.99, "Classic leather oxford shoes for formal occasions"),
            ("PROD-003", "Canvas Sneakers - White", "Casual", 49.99, "Comfortable everyday canvas sneakers"),
            ("PROD-004", "Hiking Boots - Green", "Outdoor", 159.99, "Waterproof hiking boots with ankle support"),
            ("PROD-005", "Basketball Shoes - Red", "Athletic", 119.99, "High-top basketball shoes with extra ankle support"),
            ("PROD-006", "Sandals - Beige", "Casual", 39.99, "Comfortable summer sandals"),
            ("PROD-007", "Dress Shoes - Black", "Formal", 109.99, "Elegant dress shoes for formal events"),
            ("PROD-008", "Trail Runners - Grey", "Athletic", 99.99, "Durable trail running shoes with grip"),
            ("PROD-009", "Loafers - Navy", "Casual", 79.99, "Slip-on loafers for casual wear"),
            ("PROD-010", "Work Boots - Tan", "Work", 149.99, "Steel-toe work boots for job site protection"),
        ]
        cursor.executemany("INSERT INTO products VALUES (?, ?, ?, ?, ?)", products)
        
        # Generate sample orders
        today = datetime.now()
        statuses = ["Delivered", "Shipped", "Processing", "Cancelled"]
        
        for i in range(1, 21):  # Generate 20 orders
            order_id = f"ORD-{100 + i}"
            customer_id = f"CUST-{(i % 3) + 1:03d}"  # Distribute among 3 customers
            days_ago = random.randint(0, 30)
            order_date = (today - timedelta(days=days_ago)).strftime("%Y-%m-%d")
            status = statuses[i % 4]
            
            # Add order
            cursor.execute(
                "INSERT INTO orders VALUES (?, ?, ?, ?, ?)",
                (order_id, customer_id, order_date, status, 0)  # Initial total is 0
            )
            
            # Add 1-3 items to each order
            total = 0
            for j in range(random.randint(1, 3)):
                product_id = f"PROD-{(random.randint(1, 10)):03d}"
                quantity = random.randint(1, 2)
                
                # Get product price
                cursor.execute("SELECT price FROM products WHERE product_id = ?", (product_id,))
                price = cursor.fetchone()[0]
                
                # Add order item
                cursor.execute(
                    "INSERT INTO order_items (order_id, product_id, quantity, price) VALUES (?, ?, ?, ?)",
                    (order_id, product_id, quantity, price)
                )
                
                total += price * quantity
            
            # Update order total
            cursor.execute("UPDATE orders SET total = ? WHERE order_id = ?", (total, order_id))
        
        conn.commit()
    
    def get_recent_orders(self, customer_id, limit=5):
        """Fetch recent orders for a customer from the database."""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Get total order count for this customer
            cursor.execute("SELECT COUNT(*) FROM orders WHERE customer_id = ?", (customer_id,))
            total_orders = cursor.fetchone()[0]
            
            # Get the recent orders
            cursor.execute("""
                SELECT o.order_id, o.date, o.status, o.total 
                FROM orders o
                WHERE o.customer_id = ?
                ORDER BY o.date DESC
                LIMIT ?
            """, (customer_id, limit))
            
            orders = []
            for row in cursor.fetchall():
                try:
                    # Get items for this order
                    cursor.execute("""
                        SELECT p.name
                        FROM order_items oi
                        JOIN products p ON oi.product_id = p.product_id
                        WHERE oi.order_id = ?
                    """, (row['order_id'],))
                    
                    items = [item[0] for item in cursor.fetchall()]
                    
                    orders.append({
                        "order_id": row['order_id'],
                        "date": row['date'],
                        "status": row['status'],
                        "items": items,
                        "total": f"${row['total']:.2f}"
                    })
                except Exception as e:
                    print(f"Error processing order items for {row['order_id']}: {str(e)}")
                    # Still add the order but with empty items
                    orders.append({
                        "order_id": row['order_id'],
                        "date": row['date'],
                        "status": row['status'],
                        "items": ["Error retrieving items"],
                        "total": f"${row['total']:.2f}"
                    })
            
            return orders, total_orders
        except Exception as e:
            print(f"Database error in get_recent_orders: {str(e)}")
            return [], 0
    
    def cancel_order(self, order_id, customer_id):
        """Cancel an order if it's eligible for cancellation."""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Get the order
            cursor.execute(
                "SELECT * FROM orders WHERE order_id = ? AND customer_id = ?", 
                (order_id, customer_id)
            )
            order = cursor.fetchone()
            
            if order is None:
                return {"success": False, "message": f"Order {order_id} not found for customer {customer_id}."}
            
            # Check if order can be cancelled
            if order['status'] == "Processing":
                try:
                    cursor.execute(
                        "UPDATE orders SET status = 'Cancelled' WHERE order_id = ?",
                        (order_id,)
                    )
                    conn.commit()
                    return {"success": True, "message": f"Order {order_id} has been successfully cancelled. Your refund will be processed within 3-5 business days."}
                except Exception as e:
                    conn.rollback()
                    print(f"Error cancelling order {order_id}: {str(e)}")
                    return {"success": False, "message": f"There was an error cancelling order {order_id}. Please try again later."}
            elif order['status'] == "Shipped":
                return {"success": False, "message": f"Order {order_id} has already been shipped. Please initiate a return once you receive it."}
            elif order['status'] == "Cancelled":
                return {"success": False, "message": f"Order {order_id} has already been cancelled."}
            else:  # Delivered
                return {"success": False, "message": f"Order {order_id} has already been delivered. Please initiate a return process instead of cancellation."}
        except Exception as e:
            print(f"Database error in cancel_order: {str(e)}")
            return {"success": False, "message": "There was an error processing your request. Please try again later."}

    def close_connections(self):
        """Close connection if it exists in current thread"""
        if hasattr(self.local, 'conn'):
            self.local.conn.close()
            del self.local.conn

# Initialize the database
db = OrdersDatabase()

# Define tool for fetching orders
@tool
def get_recent_orders(customer_id: str = "CUST-001", limit: int = 5) -> str:
    """Fetch the most recent orders for a customer."""
    try:
        # Get a fresh connection for this thread
        orders, total_orders = db.get_recent_orders(customer_id, limit)
        
        if not orders:
            return f"No orders found for customer {customer_id}."
        
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
    except Exception as e:
        print(f"Error in get_recent_orders tool: {str(e)}")
        return "I'm sorry, I couldn't retrieve your orders at this time. Please try again later."

# Add a new tool for canceling orders
@tool
def cancel_order(order_id: str, customer_id: str = "CUST-001") -> str:
    """Cancel an order if it's eligible for cancellation."""
    try:
        result = db.cancel_order(order_id, customer_id)
        return result["message"]
    except Exception as e:
        print(f"Error in cancel_order tool: {str(e)}")
        return "I'm sorry, I couldn't process your cancellation request at this time. Please try again later."

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
    agent = OrdersAgent()
    agent.initialize()
    
    # Create empty chat history
    chat_history = ChatHistory(messages=[])
    conversation_id = "test-conversation-123"
    
    try:
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
    finally:
        # Clean up database connections
        db.close_connections()

if __name__ == "__main__":
    asyncio.run(main())