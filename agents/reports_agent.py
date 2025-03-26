from .base_agent import BaseAgent
from chat_models import ChatMessage, ChatHistory
from textwrap import dedent
from utils import naive_utcnow
from llm_factory import LLMFactory
from config import LLM_MODEL, LLM_VENDOR
import logging
import json
import traceback
from typing import Dict, List, Optional

# Configure logging
logger = logging.getLogger(__name__)

class ReportsAgent(BaseAgent):
    """
    The reports agent is responsible for generating reports about the inventory,
    pricing, and other store analytics.
    """
    agent_name: str = "reports"

    def __init__(self):
        super().__init__()
        self.llm = None

    def initialize(self):
        """Initialize the reports agent with LLM and database tool"""
        self.llm = LLMFactory.create_llm(LLM_MODEL, LLM_VENDOR)

    async def process_message(self, message: ChatMessage, chat_history: ChatHistory) -> ChatMessage:
        """
        Process the message and generate appropriate reports.
        """
        try:
            # Extract report type and parameters from the message
            report_params = await self._extract_report_parameters(message.message)
            
            # Generate the requested report
            report_result = await self._generate_report(report_params)
            
            # Format the response
            response_text = self._format_report_response(report_result)
            
            # Return the ChatMessage with the report
            return ChatMessage(
                message=response_text,
                conversation_id=message.conversation_id,
                sender="ai",
                suggestions=self._generate_suggestions(report_params["report_type"]),
                created_at=naive_utcnow()
            )
        except Exception as e:
            logger.error(f"Error in reports agent: {str(e)}\n{traceback.format_exc()}")
            
            # Fall back to a simple response
            response = await self.llm.ainvoke(dedent(f"""
                You are a helpful customer support bot for our shoe store.
                You need to provide reports about our inventory and products.
                An error occurred while trying to generate the report.
                Apologize for this error and offer general assistance.
                ---
                User message: {message.message}
                ---
                """))
                
            return ChatMessage(
                message=response.content,
                conversation_id=message.conversation_id,
                sender="ai",
                suggestions=["Show inventory report", "Show price analysis", "What are your most discounted products?"],
                created_at=naive_utcnow()
            )

    async def _extract_report_parameters(self, message: str) -> Dict:
        """
        Extract report parameters from the user message.
        
        Args:
            message: The user message
            
        Returns:
            Dictionary with report type and parameters
        """
        # Use LLM to extract parameters
        prompt = dedent(f"""
            You are a helpful assistant that extracts report parameters from user messages.
            You need to identify the type of report the user is asking for and any relevant parameters.
            
            The available report types are:
            - inventory: A report showing all inventory with details
            - price_analysis: A report analyzing product pricing and discounts
            - most_discounted: A list of the most discounted products
            
            For inventory reports, extract these optional parameters:
            - category_id: The category ID to filter by (if mentioned)
            - brand_id: The brand ID to filter by (if mentioned)
            
            For price analysis reports, extract these optional parameters:
            - min_discount_percent: The minimum discount percentage to include (default: 0)
            - category_id: The category ID to filter by (if mentioned)
            
            For most discounted products, extract these optional parameters:
            - limit: The number of products to include (default: 5)
            - category_id: The category ID to filter by (if mentioned)
            
            Return a JSON object with the report_type and any parameters.
            If the user doesn't specify a report type, default to "inventory".
            
            Example response format:
            ```json
            {{{{
                "report_type": "inventory",
                "category_id": null,
                "brand_id": null
            }}}}
            ```
            
            User message: {message}
        """)
        
        try:
            response = await self.llm.ainvoke(prompt)
            logger.info(f"Extracted report parameters: {response.content}")
            
            # Look for JSON in the response
            import re
            json_match = re.search(r'```json\s*(.*?)\s*```', response.content, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                # Try to find any JSON-like structure
                json_match = re.search(r'{.*}', response.content, re.DOTALL)
                if json_match:
                    json_str = json_match.group(0)
                else:
                    # No JSON found, use default parameters
                    logger.warning(f"No JSON found in LLM response: {response.content}")
                    return {
                        "report_type": "inventory",
                        "category_id": None,
                        "brand_id": None
                    }
            
            # Parse the JSON
            import json
            try:
                params = json.loads(json_str)
                return params
            except json.JSONDecodeError as e:
                logger.error(f"Error parsing JSON from LLM response: {e}, JSON string: {json_str}")
                # Fall back to default parameters
                return {
                    "report_type": "inventory",
                    "category_id": None,
                    "brand_id": None
                }
                
        except Exception as e:
            logger.error(f"Error extracting report parameters: {str(e)}")
            # Default to inventory report
            return {
                "report_type": "inventory",
                "category_id": None,
                "brand_id": None
            }

    async def _generate_report(self, params: Dict) -> Dict:
        """
        Generate the requested report.
        
        Args:
            params: Dictionary with report type and parameters
            
        Returns:
            Report data
        """
        report_type = params.get("report_type", "inventory")
        
        try:
            # Import the ProductsRepository here to avoid circular imports
            from database.products_repository import ProductsRepository
            
            if report_type == "inventory":
                category_id = params.get("category_id")
                brand_id = params.get("brand_id")
                
                return await ProductsRepository.get_inventory_report(
                    category_id=category_id,
                    brand_id=brand_id
                )
            
            elif report_type == "price_analysis":
                min_discount_percent = params.get("min_discount_percent", 0)
                category_id = params.get("category_id")
                
                return await ProductsRepository.get_product_price_analysis(
                    min_discount_percent=min_discount_percent,
                    category_id=category_id
                )
            
            elif report_type == "most_discounted":
                limit = params.get("limit", 5)
                category_id = params.get("category_id")
                
                # Call the API directly or use the repository method
                from database.db_connection import db
                
                sql = """
                SELECT 
                    p.id, p.name,
                    b.name as brand_name,
                    p.price, p.sale_price,
                    (p.price - p.sale_price) / p.price * 100 as discount_percentage
                FROM 
                    products p
                JOIN 
                    brands b ON p.brand_id = b.id
                WHERE 
                    p.is_active = TRUE
                    AND p.is_on_sale = TRUE
                    AND p.sale_price IS NOT NULL
                """
                
                params = []
                param_count = 0
                
                # Add category filter if provided
                if category_id is not None:
                    param_count += 1
                    sql += f" AND p.category_id = ${param_count}"
                    params.append(category_id)
                
                # Add sorting and limit
                sql += """
                ORDER BY 
                    discount_percentage DESC
                """
                
                param_count += 1
                sql += f" LIMIT ${param_count}"
                params.append(limit)
                
                # Execute query
                results = await db.execute_query(sql, *params)
                return {"products": results}
            
            else:
                # Unknown report type
                return {
                    "error": f"Unknown report type: {report_type}",
                    "available_reports": ["inventory", "price_analysis", "most_discounted"]
                }
        except Exception as e:
            logger.error(f"Error generating report: {str(e)}")
            return {"error": str(e)}

    def _format_report_response(self, report_data: Dict) -> str:
        """
        Format the report data into a user-friendly response.
        
        Args:
            report_data: The report data
            
        Returns:
            Formatted response
        """
        if "error" in report_data:
            return f"I'm sorry, but I encountered an error while generating the report: {report_data['error']}"
        
        # Check if it's an inventory report
        if "total_products" in report_data:
            # Format inventory report
            total_products = report_data["total_products"]
            total_quantity = report_data.get("total_quantity", 0)
            total_value = report_data["total_value"]
            discounted_value = report_data["discounted_value"]
            total_discount = report_data["total_discount"]
            
            brand_summary = report_data.get("brand_summary", {})
            category_summary = report_data.get("category_summary", {})
            
            response = f"## Inventory Report\n\n"
            response += f"### Summary\n"
            response += f"- Total Product Models: {total_products}\n"
            response += f"- Total Inventory Items: {total_quantity}\n"
            response += f"- Total Value: ${total_value:.2f}\n"
            response += f"- Discounted Value: ${discounted_value:.2f}\n"
            response += f"- Total Discount: ${total_discount:.2f}\n\n"
            
            if brand_summary:
                response += f"### Brand Summary\n"
                for brand, data in brand_summary.items():
                    response += f"- {brand}: {data['count']} product models, {data['total_quantity']} items, value: ${data['total_value']:.2f}\n"
                response += "\n"
            
            if category_summary:
                response += f"### Category Summary\n"
                for category, data in category_summary.items():
                    response += f"- {category}: {data['count']} product models, {data['total_quantity']} items, value: ${data['total_value']:.2f}\n"
                response += "\n"
            
            # Add sample of inventory items
            inventory_data = report_data.get("inventory_data", [])
            if inventory_data:
                response += f"### Sample Products (showing {min(5, len(inventory_data))} of {len(inventory_data)} product models)\n"
                for i, product in enumerate(inventory_data[:5]):
                    response += f"{i+1}. **{product['name']}** ({product['brand']})\n"
                    response += f"   Price: ${product['price']:.2f}"
                    if product['is_on_sale'] and product.get('sale_price'):
                        response += f" Sale: ${product['sale_price']:.2f} ({product.get('discount_percentage', 0):.0f}% off)\n"
                    else:
                        response += "\n"
                    response += f"   Quantity: {product.get('total_quantity', 0)} items | Sizes: {', '.join(product.get('available_sizes', []))[:30]}... | Colors: {', '.join(product.get('available_colors', []))[:30]}...\n"
            
            return response
        
        # Check if it's a price analysis report
        elif "discount_summary" in report_data:
            # Format price analysis report
            discount_summary = report_data["discount_summary"]
            price_ranges = report_data.get("price_ranges", {})
            discounted_products = report_data.get("discounted_products", [])
            
            response = f"## Price Analysis Report\n\n"
            response += f"### Discount Summary\n"
            response += f"- Average Discount: {discount_summary.get('average_discount', 0):.1f}%\n"
            response += f"- Max Discount: {discount_summary.get('max_discount', 0):.1f}%\n"
            response += f"- Products on Sale: {discount_summary.get('products_on_sale', 0)}\n\n"
            
            if price_ranges:
                response += f"### Price Ranges\n"
                for price_range, count in price_ranges.items():
                    response += f"- {price_range}: {count} products\n"
                response += "\n"
            
            # Add sample of discounted products
            if discounted_products:
                response += f"### Top Discounted Products (showing {min(5, len(discounted_products))} of {len(discounted_products)} products)\n"
                for i, product in enumerate(discounted_products[:5]):
                    response += f"{i+1}. **{product['name']}** ({product.get('brand_name', 'Unknown')})\n"
                    response += f"   Price: ${product['price']:.2f} Sale: ${product['sale_price']:.2f} ({product.get('discount_percentage', 0):.0f}% off)\n"
            
            return response
        
        # Check if it's a most discounted products report
        elif "products" in report_data:
            products = report_data["products"]
            
            response = f"## Most Discounted Products\n\n"
            if not products:
                response += "We don't currently have any products on sale.\n"
                return response
            
            response += f"Here are our most discounted products (showing {len(products)} products):\n\n"
            for i, product in enumerate(products):
                response += f"{i+1}. **{product['name']}** ({product.get('brand_name', 'Unknown')})\n"
                response += f"   Price: ${product['price']:.2f} Sale: ${product['sale_price']:.2f} ({product.get('discount_percentage', 0):.0f}% off)\n"
            
            return response
        
        # Unknown report type
        return "I'm sorry, but I don't know how to format this type of report. Here's the raw data:\n\n" + str(report_data)

    def _generate_suggestions(self, report_type: str) -> List[str]:
        """
        Generate suggestions for the next user message based on the report type.
        
        Args:
            report_type: The type of report generated
            
        Returns:
            A list of suggestions
        """
        if report_type == "inventory":
            return [
                "Show me a price analysis report",
                "What are your most discounted products?",
                "Show me Nike inventory only"
            ]
        elif report_type == "price_analysis":
            return [
                "Show me inventory report",
                "What are your most discounted products?",
                "Show price analysis for running shoes"
            ]
        elif report_type == "most_discounted":
            return [
                "Show me inventory report",
                "Show me a price analysis report",
                "Tell me more about the first product"
            ]
        else:
            return [
                "Show inventory report",
                "Show price analysis",
                "What are your most discounted products?"
            ] 