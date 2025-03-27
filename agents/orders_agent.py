from typing import Dict, List, Any, Optional
from agents.base_agent import BaseAgent
from agents.orders_prompt import ORDER_STATUS_AGENT_PROMPT, ORDER_STATUS_AGENT_PROMPT_V1, ORDER_STATUS_AGENT_PROMPT_V2
from langgraph.graph import StateGraph, START, END
from langgraph.graph import MessagesState
from langgraph.prebuilt import create_react_agent
from langchain.chat_models import init_chat_model
from langchain_core.tools import tool
from chat_models import ChatMessage, ChatHistory
from utils import naive_utcnow
import json
import re


# Define the customer database (this would be replaced with actual DB access)
CUSTOMER_DB = {
    "C12345": {
        "name": "Jane Smith",
        "orders": [
            {
                "order_id": "ORD-789012",
                "date": "2025-03-15",
                "status": "Shipped",
                "tracking": "1ZW999AA0123456789",
                "items": [
                    {"item_id": "ITEM-001", "name": "Premium Headphones", "quantity": 1, "price": 129.99},
                    {"item_id": "ITEM-002", "name": "Phone Case", "quantity": 2, "price": 19.99}
                ],
                "shipping_address": "123 Main St, Anytown, USA"
            },
            {
                "order_id": "ORD-789013",
                "date": "2025-03-20",
                "status": "Processing",
                "items": [
                    {"item_id": "ITEM-003", "name": "Wireless Charger", "quantity": 1, "price": 49.99}
                ],
                "shipping_address": "123 Main St, Anytown, USA"
            }
        ]
    }
}


@tool
async def get_customer_orders(customer_id: str) -> str:
    """
    Fetch recent orders for a customer.
    
    Args:
        customer_id: The customer's ID (starts with 'C')
    
    Returns:
        JSON string containing the customer's orders from the past 2 weeks
    """
    if customer_id in CUSTOMER_DB:
        orders = CUSTOMER_DB[customer_id]["orders"]
        return json.dumps(orders)
    return json.dumps({"error": "Customer not found"})


@tool
async def get_order_details(order_id: str) -> str:
    """
    Get detailed information about a specific order.
    
    Args:
        order_id: The order ID (starts with 'ORD-')
    
    Returns:
        JSON string with complete order details
    """
    # Search all customers for the order
    for customer_id, customer_data in CUSTOMER_DB.items():
        for order in customer_data["orders"]:
            if order["order_id"] == order_id:
                return json.dumps(order)
    
    return json.dumps({"error": "Order not found"})


@tool
async def track_shipment(tracking_number: str) -> str:
    """
    Track a shipment using its tracking number.
    
    Args:
        tracking_number: The shipment tracking number
    
    Returns:
        Current shipment status and estimated delivery date
    """
    # Simulate tracking info
    tracking_info = {
        "status": "In Transit",
        "last_update": "2025-03-25 08:30 AM",
        "location": "Distribution Center, Chicago, IL",
        "estimated_delivery": "2025-03-28"
    }
    return json.dumps(tracking_info)


@tool
async def request_refund(order_id: str, reason: str) -> str:
    """
    Request a refund for an entire order.
    
    Args:
        order_id: The order ID (starts with 'ORD-')
        reason: The reason for the refund request
    
    Returns:
        Confirmation of the refund request
    """
    return json.dumps({
        "status": "Refund Requested",
        "reference_number": f"REF-{order_id[4:]}",
        "processing_time": "3-5 business days"
    })


@tool
async def return_item(order_id: str, item_id: str, reason: str) -> str:
    """
    Request a return for a specific item in an order.
    
    Args:
        order_id: The order ID (starts with 'ORD-')
        item_id: The specific item ID to return (starts with 'ITEM-')
        reason: The reason for returning the item
    
    Returns:
        Return instructions and confirmation
    """
    return json.dumps({
        "status": "Return Authorized",
        "return_id": f"RET-{order_id[4:]}-{item_id[5:]}",
        "instructions": "Please use the prepaid shipping label that will be emailed to you.",
        "processing_time": "7-10 days after receipt"
    })


@tool
async def request_exchange(order_id: str, item_id: str, new_item_id: str, reason: str) -> str:
    """
    Request an exchange for a specific item in an order.
    
    Args:
        order_id: The order ID (starts with 'ORD-')
        item_id: The current item ID to exchange (starts with 'ITEM-')
        new_item_id: The new item ID desired (starts with 'ITEM-')
        reason: The reason for the exchange
    
    Returns:
        Exchange instructions and confirmation
    """
    return json.dumps({
        "status": "Exchange Authorized",
        "exchange_id": f"EXC-{order_id[4:]}-{item_id[5:]}",
        "instructions": "Please use the prepaid shipping label that will be emailed to you.",
        "processing_time": "7-10 days after receipt of original item"
    })


@tool
async def cancel_order(order_id: str) -> str:
    """
    Request cancellation of an order that hasn't shipped.
    
    Args:
        order_id: The order ID (starts with 'ORD-')
    
    Returns:
        Cancellation status and confirmation
    """
    # Check if order exists and status
    for customer_id, customer_data in CUSTOMER_DB.items():
        for order in customer_data["orders"]:
            if order["order_id"] == order_id:
                if order["status"] == "Processing":
                    return json.dumps({
                        "status": "Cancelled",
                        "reference_number": f"CAN-{order_id[4:]}"
                    })
                else:
                    return json.dumps({
                        "status": "Cannot Cancel",
                        "reason": f"Order is already in '{order['status']}' status"
                    })
    
    return json.dumps({"error": "Order not found"})


@tool
async def update_shipping_address(order_id: str, new_address: str) -> str:
    """
    Update the shipping address for an order that hasn't shipped.
    
    Args:
        order_id: The order ID (starts with 'ORD-')
        new_address: The new shipping address
    
    Returns:
        Address update confirmation
    """
    # Check if order exists and status
    for customer_id, customer_data in CUSTOMER_DB.items():
        for order in customer_data["orders"]:
            if order["order_id"] == order_id:
                if order["status"] == "Processing":
                    return json.dumps({
                        "status": "Address Updated",
                        "new_address": new_address
                    })
                else:
                    return json.dumps({
                        "status": "Cannot Update",
                        "reason": f"Order is already in '{order['status']}' status"
                    })
    
    return json.dumps({"error": "Order not found"})


class OrdersState(MessagesState):
    """Extended state for orders workflow."""
    messages: list = []
    customer_id: Optional[str] = None
    order_id: Optional[str] = None
    item_id: Optional[str] = None
    context: dict = {}
    extracted_info: dict = {}


class OrdersAgent(BaseAgent):
    """Enhanced OrdersAgent with better tool handling and context management."""
    
    def __init__(self):
        super().__init__()
        self.llm = None
        self.agent = None
        self.tools = []
        self.workflow = None
    
    def initialize(self) -> None:
        """Initialize components for the order status agent."""
        self.llm = init_chat_model("gpt-4o", model_provider="openai")
        
        self.tools = [
            get_customer_orders,
            get_order_details,
            track_shipment,
            request_refund,
            return_item,
            request_exchange,
            cancel_order,
            update_shipping_address
        ]

        # Create agent with correct syntax for create_react_agent
        # It doesn't accept system_prompt directly
        self.agent = create_react_agent(
            self.llm,
            self.tools
        )
        
        # Build the workflow
        workflow_builder = StateGraph(OrdersState)
        
        # Add nodes
        workflow_builder.add_node("extract_info", self._extract_info_node)
        workflow_builder.add_node("context_management", self._context_management_node)
        workflow_builder.add_node("react_agent", self._react_agent_node)
        workflow_builder.add_node("postprocess", self._postprocess_node)
        
        # Define edges
        workflow_builder.add_edge(START, "extract_info")
        workflow_builder.add_edge("extract_info", "context_management")
        workflow_builder.add_edge("context_management", "react_agent")
        workflow_builder.add_edge("react_agent", "postprocess")
        workflow_builder.add_edge("postprocess", END)
        
        self.workflow = workflow_builder.compile()
    
    def _extract_identifiers(self, text: str) -> dict:
        """
        Extract customer IDs, order IDs, item IDs, and tracking numbers from text.
        
        Args:
            text: The input text to analyze
            
        Returns:
            Dictionary with extracted identifiers
        """
        extracted = {}
        
        # Extract customer ID (format: C followed by digits)
        customer_id_match = re.search(r'\b(C\d{5,})\b', text)
        if customer_id_match:
            extracted["customer_id"] = customer_id_match.group(1)
        
        # Extract order ID (format: ORD-digits)
        order_id_match = re.search(r'\b(ORD-\d{6,})\b', text)
        if order_id_match:
            extracted["order_id"] = order_id_match.group(1)
            
        # Extract item ID (format: ITEM-digits)
        item_id_match = re.search(r'\b(ITEM-\d{3,})\b', text)
        if item_id_match:
            extracted["item_id"] = item_id_match.group(1)
            
        # Extract tracking number (alphanumeric patterns common for tracking)
        tracking_patterns = [
            r'\b(1Z[0-9A-Z]{16})\b',  # UPS
            r'\b(\d{12,14})\b',       # FedEx
            r'\b(9\d{15,21})\b',      # USPS
        ]
        
        for pattern in tracking_patterns:
            tracking_match = re.search(pattern, text)
            if tracking_match:
                extracted["tracking_number"] = tracking_match.group(1)
                break
                
        return extracted
    
    def _extract_order_reference(self, text: str, context: dict = None) -> Optional[str]:
        """
        Extract order numbers or references from text or context.
        
        Args:
            text: The input text to analyze
            context: Optional context that might contain recent order references
            
        Returns:
            Extracted order ID or None
        """
        # Extract order numbers in various formats
        patterns = [
            r'\bORD-(\d{6,})\b',  # Full order ID: ORD-789012
            r'\border #?(\d{6,})\b',  # Order #789012 or order 789012
            r'\border number #?(\d{6,})\b',  # Order number #789012
            r'\border (?:id|ID) #?(\d{6,})\b',  # Order ID #789012
            r'#(\d{6,})\b',  # Just #789012
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                # Return with ORD- prefix for consistency
                order_number = match.group(1)
                if not order_number.startswith("ORD-"):
                    return f"ORD-{order_number}"
                return order_number
                
        # If no order is found in text but we have context with a recent order_id
        if context and "order_id" in context:
            # Check if the text indicates continuing to discuss the same order
            if any(phrase in text.lower() for phrase in [
                "this order", "the order", "that order", "its", "it's", "the item", 
                "these items", "what about", "tell me more", "what is"
            ]):
                return context["order_id"]
                
        return None
    
    def _extract_intent(self, text: str) -> str:
        """
        Determine the customer's intent from their message.
        
        Args:
            text: The input text to analyze
            
        Returns:
            Identified intent
        """
        text = text.lower()
        
        # Define intent patterns
        intent_patterns = {
            "check_status": [
                r"status", r"where is", r"when will.*arrive", r"details about order", r"more details", 
                r"information on", r"tell me about", r"show me", r"get details", r"what is", r"what are",
                r"which", r"who", r"where", r"when", r"how many", r"how much", r"what items", r"name of"
            ],
            "track_shipment": [r"track", r"shipping", r"delivery", r"where is my package"],
            "refund": [r"refund", r"money back", r"return and refund"],
            "return": [r"return", r"send back", r"don't want"],
            "exchange": [r"exchange", r"swap", r"different size", r"replace with"],
            "cancel": [r"cancel", r"stop order", r"don't ship"],
            "update_address": [r"change address", r"update address", r"wrong address"],
        }
        
        # Check for matches
        for intent, patterns in intent_patterns.items():
            for pattern in patterns:
                if re.search(pattern, text):
                    return intent
                    
        # Default to check_status if no clear intent
        return "check_status"
    
    def _extract_info_node(self, state: OrdersState) -> OrdersState:
        """Extract and add key information from the user message."""
        messages = state.get("messages", [])
        context = state.get("context", {})
        
        # Find the most recent user message
        user_message = ""
        if messages and isinstance(messages, list):
            # Iterate through messages in reverse to find the latest user message
            for msg in reversed(messages):
                # Check for dict format with role and content
                if isinstance(msg, dict) and 'role' in msg and msg.get('role') == 'user' and 'content' in msg:
                    user_message = msg.get('content', '')
                    break
                # Check for object with attributes
                elif hasattr(msg, 'role') and getattr(msg, 'role') == 'user' and hasattr(msg, 'content'):
                    user_message = getattr(msg, 'content', '')
                    break
        
        # Extract identifiers and intent
        extracted = self._extract_identifiers(user_message)
        
        # Try to extract order references (like "Order #789012")
        order_reference = self._extract_order_reference(user_message, context)
        if order_reference:
            extracted["order_id"] = order_reference
        
        # Determine intent
        intent = self._extract_intent(user_message)
        extracted["intent"] = intent
        
        # Print for debugging
        print(f"Extracted info: {extracted}")
        
        return {**state, "extracted_info": extracted}
    
    def _context_management_node(self, state: OrdersState) -> OrdersState:
        """Manage context between turns of conversation."""
        context = state.get("context", {})
        extracted = state.get("extracted_info", {})
        
        # Update with any newly extracted information
        if "customer_id" in extracted and extracted["customer_id"]:
            context["customer_id"] = extracted["customer_id"]
            
        if "order_id" in extracted and extracted["order_id"]:
            context["order_id"] = extracted["order_id"]
            
        if "item_id" in extracted and extracted["item_id"]:
            context["item_id"] = extracted["item_id"]
            
        if "tracking_number" in extracted and extracted["tracking_number"]:
            context["tracking_number"] = extracted["tracking_number"]
            
        if "intent" in extracted:
            context["intent"] = extracted["intent"]
            
        # For history tracking - add known orders
        if "known_orders" not in context:
            context["known_orders"] = [
                {"order_id": "ORD-789012", "date": "2025-03-15", "status": "Shipped"},
                {"order_id": "ORD-789013", "date": "2025-03-20", "status": "Processing"},
                {"order_id": "ORD-789014", "date": "2025-03-22", "status": "Payment Confirmed"}
            ]
        
        # Return updated state
        return {**state, "context": context}
    
    def _react_agent_node(self, state: OrdersState) -> OrdersState:
        """Run the ReAct agent with context-aware prompting."""
        messages = state["messages"]
        context = state.get("context", {})
        extracted = state.get("extracted_info", {})
        
        # Find the latest user message
        user_message = ""
        for msg in reversed(messages):
            if isinstance(msg, dict) and msg.get('role') == 'user':
                user_message = msg.get('content', '').lower()
                break
        
        # CASE 1: Initial general order status inquiry without specific details
        is_general_status = False
        if any(term in user_message for term in ['order status', 'my order', 'my orders', 'check order']):
            if not any(id_type in extracted for id_type in ['customer_id', 'order_id', 'tracking_number']):
                is_general_status = True
        
        if is_general_status:
            # Use the sample orders from context
            sample_orders = context.get("known_orders", [])
            
            response = {
                "messages": messages + [{
                    "role": "assistant", 
                    "content": f"I can see you have placed {len(sample_orders)} orders recently:\n\n" +
                              "\n".join([f"{i+1}. Order #{order['order_id'][4:]} from {order['date']} (Status: {order['status']})" 
                                        for i, order in enumerate(sample_orders)]) +
                              "\n\nWhat would you like to do with these orders? I can help you:\n" +
                              "- Get more details about an order\n" +
                              "- Track a shipped order\n" + 
                              "- Request a refund\n" +
                              "- Return or exchange items\n" +
                              "- Cancel an order that hasn't shipped yet\n" +
                              "- Update the shipping address\n\n" +
                              "Just let me know which order you'd like to work with and what you'd like to do."
                }]
            }
            
            return {**state, "messages": response["messages"]}
            
        # CASE 2: Follow-up action on a presented order
        has_order_reference = "order_id" in extracted and extracted["order_id"]
        
        # IMPORTANT CHANGE: Handle both status checks and other intents
        if has_order_reference:
            order_id = extracted["order_id"]
            intent = extracted.get("intent", "check_status")
            
            # Find the referenced order
            target_order = None
            for order in context.get("known_orders", []):
                if order["order_id"] == order_id:
                    target_order = order
                    break
                    
            # If order is not in known_orders, try to add more order details
            if target_order is None:
                # For demo purposes, create sample order details
                target_order = {
                    "order_id": order_id,
                    "date": "2025-03-15",
                    "status": "Shipped",
                    "items": [
                        {"item_id": "ITEM-001", "name": "Premium Headphones"},
                        {"item_id": "ITEM-002", "name": "Phone Case"}
                    ],
                    "shipping_address": "123 Main St, Anytown, USA"
                }
            
            # If we found or created the order, perform the requested action
            if target_order:
                action_result = self._perform_order_action(intent, order_id, user_message, target_order)
                
                response = {
                    "messages": messages + [{
                        "role": "assistant", 
                        "content": action_result
                    }]
                }
                
                return {**state, "messages": response["messages"]}
        
        # CASE 3: Default to standard agent processing
        system_message = ORDER_STATUS_AGENT_PROMPT_V2
        
        # Add context information if available
        context_info = []
        if "customer_id" in context:
            context_info.append(f"Customer ID: {context['customer_id']}")
        
        if "order_id" in context:
            context_info.append(f"Order ID: {context['order_id']}")
            
        if "intent" in context:
            context_info.append(f"Customer appears to want to: {context['intent']}")
            
        # Add information about known orders
        if "known_orders" in context and context["known_orders"]:
            order_ids = [order["order_id"] for order in context["known_orders"]]
            context_info.append(f"Customer has these orders: {', '.join(order_ids)}")
        
        # Add context as a note to the agent if we have any
        if context_info:
            context_note = "\n\nNOTE: From previous conversation, we know:\n" + "\n".join(context_info)
            system_message += context_note
        
        # Invoke the agent with the system message as the first message
        agent_messages = [{"role": "system", "content": system_message}]
        
        # Add all the conversation messages
        for msg in messages:
            agent_messages.append(msg)
        
        # Invoke the agent
        result = self.agent.invoke({
            "messages": agent_messages
        })
        
        return {**state, "messages": result["messages"]}
        
        return {**state, "messages": result["messages"]}
    
    def _perform_order_action(self, intent: str, order_id: str, message: str, order_info: dict) -> str:
        """
        Perform the requested action on an order.
        
        Args:
            intent: The identified customer intent
            order_id: The order ID to act on
            message: The original customer message
            order_info: Information about the order
            
        Returns:
            Response message about the action taken
        """
        # Get the order status
        status = order_info.get("status", "Unknown")
        
        # Handle based on intent
        if intent == "check_status":
            # Check if there's a specific question about the order
            message_lower = message.lower()
            
            # Sample detailed order info - in production this would come from DB
            detailed_info = {
                "order_name": "Summer Collection Pre-Order",
                "items": [
                    {"item_id": "ITEM-101", "name": "Running Shoes - Blue", "size": "10", "quantity": 1, "price": 89.99},
                    {"item_id": "ITEM-203", "name": "Athletic Socks - 3 Pack", "size": "L", "quantity": 1, "price": 14.99}
                ],
                "total_amount": 104.98,
                "payment_method": "Credit Card (ending in 4321)",
                "estimated_delivery": "March 29, 2025",
                "shipping_method": "Standard Shipping (3-5 business days)"
            }
            
            # Add detailed info to order_info
            order_info.update(detailed_info)
            
            # Check for specific questions about the order
            if "name" in message_lower or "what is" in message_lower and "order" in message_lower:
                return f"Order #{order_id[4:]} is for our '{order_info.get('order_name', 'Standard Order')}'. " + \
                       f"It was placed on {order_info.get('date', 'Unknown')} and is currently '{status}'."
                       
            elif "item" in message_lower or "product" in message_lower or "what did i order" in message_lower:
                items_text = "\n".join([f"• {item.get('name', 'Unknown Item')} - {item.get('size', 'N/A')} - ${item.get('price', 0):.2f} (Qty: {item.get('quantity', 1)})" 
                                       for item in order_info.get('items', [])])
                return f"Here are the items in Order #{order_id[4:]}:\n\n{items_text}"
                
            elif "total" in message_lower or "cost" in message_lower or "price" in message_lower or "how much" in message_lower:
                return f"The total amount for Order #{order_id[4:]} is ${order_info.get('total_amount', 0):.2f}, " + \
                       f"paid with {order_info.get('payment_method', 'your payment method')}."
                       
            elif "delivery" in message_lower or "when" in message_lower or "arrive" in message_lower:
                if status == "Shipped":
                    return f"Your Order #{order_id[4:]} was shipped on {order_info.get('date', 'Unknown')} " + \
                           f"via {order_info.get('shipping_method', 'Standard Shipping')}. " + \
                           f"The estimated delivery is {order_info.get('estimated_delivery', 'within 3-5 business days')}."
                else:
                    return f"Your Order #{order_id[4:]} is currently '{status}'. " + \
                           f"Once shipped, it will be delivered via {order_info.get('shipping_method', 'Standard Shipping')} " + \
                           f"with an estimated delivery of {order_info.get('estimated_delivery', '3-5 business days from shipping')}."
            
            # Default order details response
            return (f"Here are the details for Order #{order_id[4:]}:\n\n"
                   f"Order Name: {order_info.get('order_name', 'Standard Order')}\n"
                   f"Date: {order_info.get('date', 'Unknown')}\n"
                   f"Status: {status}\n"
                   f"Items: {', '.join([item.get('name', 'Unknown Item') for item in order_info.get('items', [])])}\n"
                   f"Total Amount: ${order_info.get('total_amount', 0):.2f}\n"
                   f"Estimated Delivery: {order_info.get('estimated_delivery', 'Unknown')}\n\n"
                   f"Is there anything specific about this order you'd like to know?")
                   
        elif intent == "track_shipment":
            if status == "Shipped":
                tracking_number = "1ZW999AA0123456789"  # In real implementation, get from order
                return (f"Your order #{order_id[4:]} was shipped on {order_info.get('date', 'Unknown')}.\n\n"
                        f"Tracking Number: {tracking_number}\n"
                        f"Current Status: In Transit\n"
                        f"Estimated Delivery: March 28, 2025\n"
                        f"Last Update: March 25, 2025 - Package departed sorting facility in Chicago, IL")
            else:
                return f"Your order #{order_id[4:]} has not been shipped yet. Its current status is '{status}'. I'll update you when it ships with tracking information."
                
        elif intent == "refund":
            # Allow refund request processing regardless of status
            if "refund" in message.lower() or "money back" in message.lower():
                if status in ["Processing", "Payment Confirmed"]:
                    return (f"I've processed a refund request for Order #{order_id[4:]}.\n\n"
                            f"Refund Reference: REF-{order_id[4:]}\n"
                            f"Amount: Full order amount\n"
                            f"Processing Time: 3-5 business days\n\n"
                            f"You should receive an email confirmation shortly. Is there anything else you need help with?")
                else:
                    return (f"I've initiated a return and refund request for your shipped Order #{order_id[4:]}.\n\n"
                            f"Return Reference: RET-{order_id[4:]}\n"
                            f"Refund Amount: Full order amount (${order_info.get('total_amount', 0):.2f})\n"
                            f"Next Steps: You'll receive an email with a prepaid return shipping label shortly.\n"
                            f"Processing Time: Your refund will be processed within 5-7 business days after we receive your returned items.\n\n"
                            f"Would you like to tell me why you're requesting a refund? This helps us improve our products and service.")
                        
        elif intent == "return":
            return (f"I've initiated a return request for Order #{order_id[4:]}.\n\n"
                    f"Return Reference: RET-{order_id[4:]}\n"
                    f"Return Instructions: You'll receive an email with a prepaid shipping label shortly.\n"
                    f"Processing Time: 7-10 days after we receive your return\n\n"
                    f"Is there anything specific about the return process you'd like to know?")
                    
        elif intent == "exchange":
            return (f"I've started an exchange request for Order #{order_id[4:]}.\n\n"
                    f"Exchange Reference: EXC-{order_id[4:]}\n"
                    f"Instructions: Please specify which items you'd like to exchange and for what. "
                    f"You'll receive a prepaid shipping label by email.\n\n"
                    f"What would you like to exchange from this order?")
                    
        elif intent == "cancel":
            if status in ["Processing", "Payment Confirmed"]:
                return (f"I've cancelled Order #{order_id[4:]} as requested.\n\n"
                        f"Cancellation Reference: CAN-{order_id[4:]}\n"
                        f"Refund: Your payment method will be refunded within 3-5 business days.\n\n"
                        f"Is there anything else I can help you with today?")
            else:
                return (f"I'm sorry, but Order #{order_id[4:]} can't be cancelled because it has already been {status}.\n\n"
                        f"Would you like to return the order instead once you receive it?")
                        
        elif intent == "update_address":
            if status in ["Processing", "Payment Confirmed"]:
                return (f"I can update the shipping address for Order #{order_id[4:]}.\n\n"
                        f"Current address: {order_info.get('shipping_address', 'Not available')}\n\n"
                        f"Please provide the new shipping address you'd like to use.")
            else:
                return (f"I'm sorry, but Order #{order_id[4:]} can't have its shipping address updated because it has already been {status}.\n\n"
                        f"Would you like me to help redirect the package with the carrier instead?")
                        
        # Fallback for unrecognized intents
        return (f"I can help you with Order #{order_id[4:]}.\n\n"
                f"Current Status: {status}\n"
                f"Date: {order_info.get('date', 'Unknown')}\n\n"
                f"What specifically would you like to do with this order? I can help with tracking, refunds, returns, exchanges, or cancellations.")
    
    def _postprocess_node(self, state: OrdersState) -> OrdersState:
        """Format the final response."""
        # Just pass through the agent's response
        return state
    
    async def process_message(self, message: ChatMessage, chat_history: ChatHistory) -> ChatMessage:
        """Process a message using the order status agent workflow."""
        
        # Format messages for the workflow
        formatted_messages = []
        
        # Add previous messages from history to maintain context
        for history_item in chat_history.messages:
            role = "user" if history_item.is_user_message() else "assistant"
            formatted_messages.append({"role": role, "content": history_item.content})
        
        # Add the current message
        formatted_messages.append({"role": "user", "content": message.message})
        
        # For debugging
        print(f"Formatted messages for workflow: {formatted_messages}")
        
        # Invoke the workflow
        initial_state = OrdersState(messages=formatted_messages)
        result = self.workflow.invoke(initial_state)
        
        # Extract the agent's response
        result_messages = result.get("messages", [])
        latest_ai_message = ""
        
        # Find the most recent assistant message
        for msg in reversed(result_messages):
            if isinstance(msg, dict) and msg.get("role") == "assistant" and "content" in msg:
                latest_ai_message = msg["content"]
                break
        
        if not latest_ai_message:
            latest_ai_message = "I'm sorry, I couldn't process your request."
        
        # Create and return the chat message
        return ChatMessage(
            message=latest_ai_message,
            conversation_id=message.conversation_id,
            sender="ai",
            chat_history=chat_history,
            created_at=naive_utcnow()
        )