# Standard library imports
import asyncio
import os
import random
import re
import sqlite3
import threading
from datetime import datetime, timedelta
from textwrap import dedent
from typing import Annotated, List, TypedDict, Sequence, Literal
import json
import urllib.parse
import urllib.request
import base64
from io import BytesIO

"""
Shoe Store Agent with Image Search Support

This agent integrates with Tavily API for searching shoe images online.
To enable image search, follow these steps:

1. Install the Tavily Python client:
   pip install tavily-python

2. Set your Tavily API key as an environment variable:
   export TAVILY_API_KEY=tvly-YOUR_API_KEY

3. Get your API key from: https://tavily.com/ by signing up for a free account

When customers ask to see what shoes look like, the agent will use Tavily's
search API to find relevant images online.
"""

# Third-party imports
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage, AIMessage
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent
from langgraph.graph import StateGraph, END
from langchain.chat_models import init_chat_model

# For Tavily search API
try:
    from tavily import TavilyClient
except ImportError:
    TavilyClient = None

# Local/First-party imports
from agents.base_agent import BaseAgent
from chat_models import ChatMessage, ChatHistory, ChatHistoryItem
from utils import naive_utcnow
from llm_factory import LLMFactory
from config import LLM_MODEL, LLM_VENDOR

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
        
        # Sample shoe products with popular, recognizable brands that have images readily available online
        products = [
            ("PROD-001", "Nike Air Max 90", "Athletic", 129.99, "Iconic Nike Air Max 90 running shoes with visible air cushioning"),
            ("PROD-002", "Adidas Ultraboost", "Athletic", 179.99, "Adidas Ultraboost with responsive Boost midsole technology"),
            ("PROD-003", "Converse Chuck Taylor All Star", "Casual", 59.99, "Classic Converse Chuck Taylor high-top canvas sneakers"),
            ("PROD-004", "Timberland Premium 6-Inch", "Outdoor", 199.99, "Waterproof Timberland 6-inch boots with premium leather"),
            ("PROD-005", "Jordan 1 Retro High", "Athletic", 169.99, "Iconic Air Jordan 1 Retro High basketball shoes"),
            ("PROD-006", "Birkenstock Arizona", "Casual", 99.99, "Comfortable Birkenstock Arizona sandals with contoured footbed"),
            ("PROD-007", "Dr. Martens 1460", "Casual", 149.99, "Classic Dr. Martens 1460 8-eye leather boots"),
            ("PROD-008", "New Balance 574", "Athletic", 89.99, "Versatile New Balance 574 sneakers with ENCAP cushioning"),
            ("PROD-009", "Vans Old Skool", "Casual", 69.99, "Vans Old Skool skate shoes with signature side stripe"),
            ("PROD-010", "Red Wing Iron Ranger", "Work", 329.99, "Red Wing Iron Ranger cap-toe boots with Goodyear welt construction"),
        ]
        cursor.executemany("INSERT INTO products VALUES (?, ?, ?, ?, ?)", products)
        
        # Create more specific orders to showcase different shoes
        # This will make the orders more realistic and demonstrate different shoe types
        orders_data = [
            # Customer 1 - John Smith: Athletic shoes buyer
            {"order_id": "ORD-101", "customer_id": "CUST-001", "days_ago": 5, "status": "Delivered", "products": ["PROD-001", "PROD-008"]},  # Nike Air Max 90 + New Balance 574
            {"order_id": "ORD-102", "customer_id": "CUST-001", "days_ago": 12, "status": "Delivered", "products": ["PROD-002"]},  # Adidas Ultraboost
            {"order_id": "ORD-103", "customer_id": "CUST-001", "days_ago": 25, "status": "Delivered", "products": ["PROD-005"]},  # Jordan 1 Retro High
            
            # Customer 2 - Jane Doe: Casual and trendy shoes
            {"order_id": "ORD-104", "customer_id": "CUST-002", "days_ago": 3, "status": "Shipped", "products": ["PROD-003", "PROD-009"]},  # Converse + Vans
            {"order_id": "ORD-105", "customer_id": "CUST-002", "days_ago": 10, "status": "Delivered", "products": ["PROD-006"]},  # Birkenstock Arizona
            {"order_id": "ORD-106", "customer_id": "CUST-002", "days_ago": 2, "status": "Processing", "products": ["PROD-002"]},  # Adidas Ultraboost
            {"order_id": "ORD-107", "customer_id": "CUST-002", "days_ago": 1, "status": "Processing", "products": ["PROD-007"]},  # Dr. Martens
            
            # Customer 3 - Bob Johnson: Practical and work shoes
            {"order_id": "ORD-108", "customer_id": "CUST-003", "days_ago": 7, "status": "Delivered", "products": ["PROD-004"]},  # Timberland
            {"order_id": "ORD-109", "customer_id": "CUST-003", "days_ago": 15, "status": "Delivered", "products": ["PROD-010"]},  # Red Wing Iron Ranger
            {"order_id": "ORD-110", "customer_id": "CUST-003", "days_ago": 0, "status": "Cancelled", "products": ["PROD-004", "PROD-010"]},  # Timberland + Red Wing (cancelled)
        ]
        
        today = datetime.now()
        for order_info in orders_data:
            order_id = order_info["order_id"]
            customer_id = order_info["customer_id"]
            days_ago = order_info["days_ago"]
            status = order_info["status"]
            
            order_date = (today - timedelta(days=days_ago)).strftime("%Y-%m-%d")
            
            # Add order with initial total of 0
            cursor.execute(
                "INSERT INTO orders VALUES (?, ?, ?, ?, ?)",
                (order_id, customer_id, order_date, status, 0)
            )
            
            # Add specific products to the order
            total = 0
            for product_id in order_info["products"]:
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

    def get_order_details(self, order_id, customer_id=None):
        """Get detailed information about a specific order."""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Base query to get order details
            query = """
                SELECT o.order_id, o.date, o.status, o.total, o.customer_id,
                       c.name as customer_name, c.email, c.address
                FROM orders o
                JOIN customers c ON o.customer_id = c.customer_id
                WHERE o.order_id = ?
            """
            
            params = [order_id]
            
            # If customer_id is provided, add it to the query
            if customer_id:
                query += " AND o.customer_id = ?"
                params.append(customer_id)
            
            cursor.execute(query, params)
            order = cursor.fetchone()
            
            if not order:
                if customer_id:
                    return {"success": False, "message": f"Order {order_id} not found for customer {customer_id}."}
                else:
                    return {"success": False, "message": f"Order {order_id} not found."}
            
            # Get items for this order
            cursor.execute("""
                SELECT p.name, oi.quantity, oi.price
                FROM order_items oi
                JOIN products p ON oi.product_id = p.product_id
                WHERE oi.order_id = ?
            """, (order_id,))
            
            items = []
            for item in cursor.fetchall():
                items.append({
                    "name": item['name'],
                    "quantity": item['quantity'],
                    "price": item['price']
                })
            
            # Format the result
            result = {
                "success": True,
                "order": {
                    "order_id": order['order_id'],
                    "date": order['date'],
                    "status": order['status'],
                    "total": order['total'],
                    "customer_id": order['customer_id'],
                    "customer_name": order['customer_name'],
                    "email": order['email'],
                    "address": order['address'],
                    "items": items
                }
            }
            
            return result
        except Exception as e:
            print(f"Database error in get_order_details: {str(e)}")
            return {"success": False, "message": f"Error retrieving details for order {order_id}: {str(e)}"}

    def get_product_details(self, product_id=None, product_name=None):
        """Get details about a specific product by ID or name"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            if product_id:
                cursor.execute("SELECT * FROM products WHERE product_id = ?", (product_id,))
            elif product_name:
                cursor.execute("SELECT * FROM products WHERE name LIKE ?", (f"%{product_name}%",))
            else:
                return {"success": False, "message": "No product ID or name provided."}
                
            products = []
            for row in cursor.fetchall():
                products.append({
                    "product_id": row['product_id'],
                    "name": row['name'],
                    "category": row['category'],
                    "price": row['price'],
                    "description": row['description']
                })
                
            if not products:
                return {"success": False, "message": "No products found matching the criteria."}
                
            return {"success": True, "products": products}
        except Exception as e:
            print(f"Database error in get_product_details: {str(e)}")
            return {"success": False, "message": f"Error retrieving product details: {str(e)}"}

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

# Add a new tool for getting order details
@tool
def get_order_details(order_id: str, customer_id: str = "CUST-001") -> str:
    """
    Get detailed information about a specific order, including customer details and delivery address.
    """
    try:
        result = db.get_order_details(order_id, customer_id)
        
        if not result["success"]:
            return result["message"]
            
        order = result["order"]
        
        # Format the response
        response = f"Order Details for {order_id}:\n\n"
        response += f"Date: {order['date']}\n"
        response += f"Status: {order['status']}\n"
        response += f"Customer: {order['customer_name']} (ID: {order['customer_id']})\n"
        response += f"Email: {order['email']}\n"
        response += f"Delivery Address: {order['address']}\n\n"
        
        response += "Items:\n"
        for item in order['items']:
            response += f"- {item['name']} (Qty: {item['quantity']}) - ${item['price']:.2f} each\n"
            
        response += f"\nTotal: ${order['total']:.2f}"
        
        return response
    except Exception as e:
        print(f"Error in get_order_details tool: {str(e)}")
        return f"I'm sorry, I couldn't retrieve the details for order {order_id} at this time. Please try again later."

def search_for_shoe_image(query):
    """
    Search for an image of shoes online using Tavily API and return the URL.
<<<<<<< HEAD
    Tries to find medium-sized, web-friendly images.
=======
>>>>>>> main
    
    Args:
        query: The search term for the shoes
        
    Returns:
        A URL to an image if found, None otherwise
    """
    try:
        # Check if Tavily is available
        if TavilyClient is None:
            print("Tavily client not installed. Install with: pip install tavily-python")
            return None
            
        # Get API key from environment variable
        api_key = os.environ.get("TAVILY_API_KEY")
        if not api_key:
            print("TAVILY_API_KEY environment variable not set")
            return None
            
        # Initialize Tavily client
        client = TavilyClient(api_key=api_key)
        
        # Enhance query to improve image search results
        # Add size specifications to help find smaller, web-friendly images
        terms = query.split()
        if len(terms) >= 2:
            brand = terms[0]
            model = " ".join(terms[1:])
            enhanced_query = f"{brand} {model} shoes product photo medium size"
        else:
            enhanced_query = f"{query} shoes product photo medium size"
            
        print(f"Searching for: {enhanced_query}")
        
        # Execute search with images enabled
        response = client.search(query=enhanced_query, 
                                include_images=True,
                                search_depth="advanced")
        
        # Check if we have any images in the response and filter large ones
        if response and 'images' in response and response['images']:
            # Basic heuristic: URLs with "thumb" or "small" or "medium" are typically smaller
            # This is just a simple filter - not 100% reliable
            for image_url in response['images']:
                # Skip URLs that might be very large or contain "full" or "large" in the URL path
                if any(term in image_url.lower() for term in ["full", "large", "original", "high-res"]):
                    continue
                
                # Prefer URLs that contain terms suggesting smaller images
                if any(term in image_url.lower() for term in ["thumb", "small", "medium", "preview", "product"]):
                    print(f"Found preferred smaller image: {image_url}")
                    return image_url
            
            # If no preferred smaller images, return the first one
            print(f"Found image: {response['images'][0]}")
            return response['images'][0]
        
        # If no images were found, try a more generic search with size specifications
        if not (response and 'images' in response and response['images']):
            backup_query = f"{query} shoes product photo small size"
            print(f"No images found, trying backup query: {backup_query}")
            
            response = client.search(query=backup_query, 
                                    include_images=True,
                                    search_depth="advanced")
                                    
            if response and 'images' in response and response['images']:
                print(f"Found image with backup query: {response['images'][0]}")
                return response['images'][0]
        
        # If still no images were found
        print(f"No images found for query: {query}")
        return None
    except Exception as e:
        print(f"Error searching for image with Tavily: {str(e)}")
        return None

@tool
def show_shoe_image(product_id: str = None, product_name: str = None) -> str:
    """
    Fetch an image of shoes based on product ID or product name using Tavily search.
    Tries to find web-friendly sized images that load quickly.
    """
    try:
        # First get product details from our database
        result = db.get_product_details(product_id, product_name)
        
        if not result["success"]:
            return result["message"]
            
        products = result["products"]
        
        # Get the first matching product
        product = products[0]
        product_name = product["name"]
        category = product["category"]
        description = product["description"]
        
        # Try to search for an image online
        search_query = f"{product_name} {category} shoes"
        image_url = None
        try:
            print(f"Searching for web-friendly images of {product_name}...")
            image_url = search_for_shoe_image(search_query)
        except Exception as e:
            print(f"Error searching for image: {str(e)}")
        
        if image_url:
            # In a real implementation with a UI, you would display the image
            # For this demo, we'll return the URL and a description
            response = f"Here's the image for {product_name}:\n\n"
            response += f"Image URL: {image_url}\n\n"
            response += f"Product ID: {product['product_id']}\n"
            response += f"Category: {product['category']}\n"
            response += f"Price: ${product['price']:.2f}\n"
            response += f"Description: {product['description']}"
            
            return response
            
        # Fallback: provide a descriptive placeholder for the image
        image_description = f"[Image of {product_name} - {category} shoe: {description}]"
        
        response = f"I couldn't find an image for {product_name}. Here's a description instead:\n\n"
        response += f"{image_description}\n\n"
        response += f"Product ID: {product['product_id']}\n"
        response += f"Category: {product['category']}\n"
        response += f"Price: ${product['price']:.2f}\n"
        response += f"Description: {product['description']}\n\n"
        response += "To see images, please make sure the Tavily API key is properly configured."
        
        return response
    except Exception as e:
        print(f"Error in show_shoe_image tool: {str(e)}")
        return "I'm sorry, I couldn't retrieve the shoe image at this time. Please try again later."

# Define the agent state
class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], "Chat history"]
    query_type: Annotated[str, "Type of query detected"]

# Initialize the LLM and tools
# llm = ChatOpenAI(temperature=0)
llm = init_chat_model("gpt-4o", model_provider="openai")
tools = [get_recent_orders, cancel_order, get_order_details, show_shoe_image]  # Update tools list
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
    if any(phrase in query_lower for phrase in ["image", "picture", "photo", "see the", "show me", "what does it look like"]):
        return "image_query"
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
        self.agent_llm = init_chat_model("gpt-4o-mini", model_provider="openai")
        
        # Use the global tool functions instead of class methods
        # This ensures proper tool registration
        self.tools = [get_recent_orders, cancel_order, get_order_details, show_shoe_image]
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
        if any(phrase in query_lower for phrase in ["image", "picture", "photo", "see the", "show me", "what does it look like"]):
            return "image_query"
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

When a customer asks for specific details about an order, such as delivery address, 
customer information, or specific item details, use the get_order_details tool.

When a customer asks to see images or pictures of shoes, or asks what a product looks like,
use the show_shoe_image tool to retrieve images of the shoes using Tavily search.
The system will search the web for web-friendly sized images of the requested shoes and 
provide a URL if found. We prioritize small to medium sized images that load quickly.
If no images are found, a descriptive text will be provided instead.

Note that to enable image search, the system requires a Tavily API key to be set.
If images aren't showing, it may be because the API key hasn't been configured.

The customer can ask for images by product ID or by product name/description.

The customer ID is automatically provided in the system.

Respond to queries like:
- "Order Status"
- "What are my Orders"
- "Give me latest orders"
- "My Order"
- "Cancel my order"
- "Who is the customer for this order"
- "What address was this delivered to"
- "Show me details of order ORD-123"
- "Show me Nike Air Max 90"
- "What do Adidas Ultraboost look like"
- "Can I see a picture of the Jordan 1 Retro High"
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
            suggestions.append(f"Show details for {self.current_order_context}")
        
        # If we have multiple orders in context, add general suggestions
        if self.multiple_orders_in_context:
            suggestions.append("Show more orders")
        
        # Add suggestions for viewing images of popular shoe brands
        popular_shoe_suggestions = [
            "Show me Nike Air Max 90",
            "Show me Adidas Ultraboost",
            "What do Jordan 1 Retro High look like?",
            "Show me Converse Chuck Taylor",
            "Can I see Dr. Martens 1460 boots?",
            "Show me Vans Old Skool"
        ]
        
        # Add a random selection of popular shoe suggestions
        import random
        random.shuffle(popular_shoe_suggestions)
        suggestions.extend(popular_shoe_suggestions[:3])
        
        # Return a mix of suggestions, but limit to 3
        # First prioritize context-specific suggestions, then general ones
        context_suggestions = [s for s in suggestions[:4]]  # First 4 are context-specific
        general_suggestions = [s for s in suggestions[4:]]  # Rest are general
        
        # Randomize the general suggestions to provide variety
        random.shuffle(general_suggestions)
        
        # Combine context suggestions with some general ones
        result = context_suggestions + general_suggestions
        return result[:3]  # Limit to 3 suggestions

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