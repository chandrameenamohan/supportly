import logging
import uuid
from datetime import datetime
from typing import List

import enum
from pydantic import BaseModel
from sqlalchemy import Column, DateTime, Enum, Float, ForeignKey, Integer, String
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.future import select
from sqlalchemy.orm import relationship, selectinload, sessionmaker

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
_message_logger = None

# Database configuration
Base = declarative_base()

_orders_db = None


class OrderStatus(enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class Product(Base):
    __tablename__ = 'products'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    description = Column(String(500))
    price = Column(Float, nullable=False)
    sku = Column(String(50), unique=True)
    stock_quantity = Column(Integer, default=0)
    
    # Relationship with OrderItem
    order_items = relationship("OrderItem", back_populates="product")


class Order(Base):
    __tablename__ = 'orders'
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), nullable=False)  # Foreign key to users table
    status = Column(Enum(OrderStatus), default=OrderStatus.PENDING)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    total_amount = Column(Float, nullable=False)
    
    # Relationship with OrderItem
    items = relationship("OrderItem", back_populates="order")


class OrderItem(Base):
    __tablename__ = 'order_items'
    
    id = Column(Integer, primary_key=True)
    order_id = Column(String(36), ForeignKey('orders.id'), nullable=False)
    product_id = Column(Integer, ForeignKey('products.id'), nullable=False)
    quantity = Column(Integer, nullable=False)
    unit_price = Column(Float, nullable=False)
    
    # Relationships
    order = relationship("Order", back_populates="items")
    product = relationship("Product", back_populates="order_items")


class OrderItemData(BaseModel):
    id: int
    order_id: str
    product_id: int
    quantity: int
    unit_price: float

    class Config:
        from_attributes = True


class OrderData(BaseModel):
    id: str
    user_id: str
    status: OrderStatus
    created_at: datetime
    updated_at: datetime
    total_amount: float
    items: List[OrderItemData] = []

    class Config:
        from_attributes = True


class OrdersDB:
    def __init__(self, db_url: str):
        try:
            self.db_url = db_url
            self.engine = create_async_engine(db_url)
            self.async_session = sessionmaker(
                self.engine, expire_on_commit=False, class_=AsyncSession
            )
        except Exception as e:
            logger.error(f"Failed to initialize OrdersDB: {str(e)}")
            raise

    async def initialize(self):
        try:
            async with self.engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            logger.info("Orders database initialized")
        except Exception as e:
            logger.error(f"Failed to initialize database tables: {str(e)}")
            raise
    
    async def get_orders(self, user_id: str = "demo_user") -> List[OrderData]:
        """
        Retrieve all orders for a specific user.
        Also fetches the order items for each order.
        
        Args:
            user_id: The ID of the user to retrieve orders for
            
        Returns:
            List[OrderData]: A list of orders with their items
        """
        try:
            async with self.async_session() as session:
                query = (
                    select(Order)
                    .where(Order.user_id == user_id)
                    .options(selectinload(Order.items))
                )
                orders = await session.execute(query)
                return [OrderData.model_validate(order) for order in orders.scalars().all()]
        except Exception as e:
            logger.error(f"Failed to fetch orders for user {user_id}: {str(e)}")
            raise
    
    async def get_order_items(self, order_id: str) -> List[OrderItemData]:
        """
        Retrieve all order items for a specific order.
        
        Args:
            order_id: The ID of the order to retrieve items for
            
        Returns:
            List[OrderItemData]: A list of order items
        """
        try:
            async with self.async_session() as session:
                query = select(OrderItem).where(OrderItem.order_id == order_id)
                order_items = await session.execute(query)
                return [OrderItemData.model_validate(item) for item in order_items.scalars().all()]
        except Exception as e:
            logger.error(f"Failed to fetch order items for order {order_id}: {str(e)}")
            raise


async def get_orders_db(db_url: str):
    try:
        global _orders_db
        if _orders_db is None:
            _orders_db = OrdersDB(db_url)
        return _orders_db
    except Exception as e:
        logger.error(f"Failed to get orders database instance: {str(e)}")
        raise