import asyncio
from datetime import datetime, timedelta
from db import OrdersDB, Product, Order, OrderItem, OrderStatus
from config import DB_URL
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Sample shoe data
SHOES = [
    {
        "name": "Nike Air Max 270",
        "description": "The Nike Air Max 270 delivers unrivaled comfort with its large Air unit.",
        "price": 150.00,
        "sku": "NIKE-AM270-001",
        "stock_quantity": 50
    },
    {
        "name": "Adidas Ultra Boost 21",
        "description": "Experience ultimate comfort with the responsive Boost technology.",
        "price": 180.00,
        "sku": "ADID-UB21-001",
        "stock_quantity": 45
    },
    {
        "name": "New Balance 990v5",
        "description": "Premium comfort and stability in a classic design.",
        "price": 200.00,
        "sku": "NB-990V5-001",
        "stock_quantity": 30
    },
    {
        "name": "Puma RS-X",
        "description": "Retro-inspired design with modern comfort.",
        "price": 120.00,
        "sku": "PUMA-RSX-001",
        "stock_quantity": 40
    },
    {
        "name": "Reebok Classic Leather",
        "description": "Timeless style meets everyday comfort.",
        "price": 80.00,
        "sku": "REEB-CL-001",
        "stock_quantity": 60
    },
    {
        "name": "Asics Gel-Nimbus 23",
        "description": "Premium cushioning for long-distance running.",
        "price": 160.00,
        "sku": "ASIC-GN23-001",
        "stock_quantity": 35
    },
    {
        "name": "Under Armour HOVR",
        "description": "Energy return technology for maximum comfort.",
        "price": 130.00,
        "sku": "UA-HOVR-001",
        "stock_quantity": 55
    },
    {
        "name": "Brooks Ghost 14",
        "description": "Smooth ride with DNA LOFT cushioning.",
        "price": 140.00,
        "sku": "BROO-GH14-001",
        "stock_quantity": 40
    },
    {
        "name": "Saucony Ride 15",
        "description": "Balanced cushioning for everyday running.",
        "price": 120.00,
        "sku": "SAUC-RD15-001",
        "stock_quantity": 45
    },
    {
        "name": "Mizuno Wave Rider 25",
        "description": "Advanced wave technology for optimal performance.",
        "price": 130.00,
        "sku": "MIZU-WR25-001",
        "stock_quantity": 30
    }
]

async def populate_database():
    """Populate the database with sample shoe products and order history."""
    db = OrdersDB(DB_URL)
    await db.initialize()
    
    async with db.async_session() as session:
        # Add products
        products = []
        for shoe in SHOES:
            product = Product(**shoe)
            session.add(product)
            products.append(product)
        await session.commit()
        
        # Create 5 orders with random items
        user_id = "demo_user"
        for i in range(5):
            # Create order with random date within last 30 days
            order_date = datetime.utcnow() - timedelta(days=i*7)
            order = Order(
                user_id=user_id,
                status=OrderStatus.COMPLETED,
                created_at=order_date,
                updated_at=order_date,
                total_amount=0.0
            )
            session.add(order)
            await session.flush()  # Get the order ID
            
            # Add 1-2 random items to the order
            num_items = 2 if i % 2 == 0 else 1
            order_total = 0.0
            
            for _ in range(num_items):
                product = products[i % len(products)]  # Cycle through products
                quantity = 1
                unit_price = product.price
                order_total += unit_price * quantity
                
                order_item = OrderItem(
                    order_id=order.id,
                    product_id=product.id,
                    quantity=quantity,
                    unit_price=unit_price
                )
                session.add(order_item)
            
            order.total_amount = order_total
            await session.commit()
        
        logger.info("Database populated successfully with sample data")

if __name__ == "__main__":
    asyncio.run(populate_database()) 