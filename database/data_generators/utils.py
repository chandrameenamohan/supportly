#!/usr/bin/env python
"""
Utility functions for generating synthetic data.
"""

import random
import uuid
from datetime import datetime, timedelta
from typing import List, Dict, Any, Tuple

# Common shoe sizes
MEN_SIZES = [6, 6.5, 7, 7.5, 8, 8.5, 9, 9.5, 10, 10.5, 11, 11.5, 12, 12.5, 13, 14, 15]
WOMEN_SIZES = [5, 5.5, 6, 6.5, 7, 7.5, 8, 8.5, 9, 9.5, 10, 10.5, 11]
KIDS_SIZES = [1, 1.5, 2, 2.5, 3, 3.5, 4, 4.5, 5, 5.5, 6, 6.5]

# Common shoe colors with hex codes
COLORS = [
    {"name": "Black", "hex": "#000000"},
    {"name": "White", "hex": "#FFFFFF"},
    {"name": "Red", "hex": "#FF0000"},
    {"name": "Blue", "hex": "#0000FF"},
    {"name": "Navy", "hex": "#000080"},
    {"name": "Grey", "hex": "#808080"},
    {"name": "Green", "hex": "#008000"},
    {"name": "Yellow", "hex": "#FFFF00"},
    {"name": "Purple", "hex": "#800080"},
    {"name": "Pink", "hex": "#FFC0CB"},
    {"name": "Orange", "hex": "#FFA500"},
    {"name": "Brown", "hex": "#A52A2A"},
    {"name": "Tan", "hex": "#D2B48C"},
    {"name": "Teal", "hex": "#008080"},
    {"name": "Olive", "hex": "#808000"},
    {"name": "Beige", "hex": "#F5F5DC"}
]

# Common shoe materials
MATERIALS = [
    "Leather",
    "Synthetic Leather",
    "Canvas",
    "Mesh",
    "Knit",
    "Suede",
    "Nylon",
    "Polyester",
    "Gore-Tex",
    "Rubber",
    "Cotton",
    "Neoprene",
    "Wool",
    "Fleece"
]

# Customer names for reviews
CUSTOMER_NAMES = [
    "John S.", "Emma W.", "Michael T.", "Sarah L.", "David B.",
    "Jessica H.", "Daniel K.", "Rachel G.", "Robert F.", "Lisa M.",
    "Chris P.", "Olivia N.", "James O.", "Sophia R.", "Thomas S.",
    "Emily T.", "William H.", "Ava J.", "Joseph C.", "Madison D.",
    "Alexander K.", "Chloe L.", "Ryan M.", "Grace N.", "Noah P.", 
    "Hannah Q.", "Ethan R.", "Lily S.", "Kevin T.", "Zoe U."
]

def generate_sku(brand_prefix: str, category_id: int, product_id: int) -> str:
    """Generate a SKU (Stock Keeping Unit) for a product."""
    # Format: BRAND-CATID-PRODID (e.g., NIKE-06-0123)
    return f"{brand_prefix}-{category_id:02d}-{product_id:04d}"

def generate_price(category_id: int) -> float:
    """Generate a realistic price based on the category."""
    # Different price ranges for different categories
    price_ranges = {
        # Athletic
        1: (80, 200),
        6: (100, 180),  # Running
        7: (120, 220),  # Basketball
        8: (80, 180),   # Soccer
        9: (70, 150),   # Training
        10: (90, 160),  # Tennis
        
        # Casual
        2: (50, 150),
        11: (60, 120),  # Sneakers
        12: (40, 100),  # Slip-Ons
        13: (30, 80),   # Sandals
        14: (70, 140),  # Loafers
        
        # Formal
        3: (100, 300),
        15: (150, 350), # Oxfords
        16: (120, 280), # Derbies
        17: (130, 290), # Monk Straps
        18: (160, 380), # Dress Boots
        
        # Outdoor
        4: (90, 250),
        19: (120, 280), # Hiking Boots
        20: (110, 250), # Work Boots
        21: (110, 220), # Trail Running
        22: (130, 300), # Winter Boots
        
        # Special Purpose
        5: (80, 200),
        23: (120, 300), # Cycling
        24: (100, 220), # Golf
        25: (70, 150),  # Skateboarding
        26: (60, 140),  # Dance
    }
    
    # Default price range if category not found
    default_range = (60, 180)
    min_price, max_price = price_ranges.get(category_id, default_range)
    
    # Generate a price with cents
    price = round(random.uniform(min_price, max_price), 2)
    return price

def generate_sale_price(original_price: float) -> Tuple[float, bool]:
    """Generate a sale price and determine if the item is on sale."""
    # 30% chance the item is on sale
    is_on_sale = random.random() < 0.3
    
    if is_on_sale:
        # Discount between 10% and 40%
        discount = random.uniform(0.1, 0.4)
        sale_price = round(original_price * (1 - discount), 2)
        return sale_price, True
    else:
        return None, False

def generate_uuid() -> str:
    """Generate a UUID for product IDs."""
    return str(uuid.uuid4())

def random_date(start_date: datetime, end_date: datetime) -> datetime:
    """Generate a random date between start_date and end_date."""
    time_between_dates = end_date - start_date
    days_between_dates = time_between_dates.days
    random_days = random.randrange(days_between_dates)
    return start_date + timedelta(days=random_days)

def get_random_materials(count: int = None) -> List[str]:
    """Get a list of random materials."""
    if count is None:
        count = random.randint(1, 3)
    return random.sample(MATERIALS, min(count, len(MATERIALS)))

def get_random_colors(count: int = None) -> List[Dict]:
    """Get a list of random colors."""
    if count is None:
        count = random.randint(3, 6)
    return random.sample(COLORS, min(count, len(COLORS)))

def get_sizes_by_gender(gender: str) -> List[float]:
    """Get appropriate sizes based on gender."""
    if gender == "Men":
        return MEN_SIZES
    elif gender == "Women":
        return WOMEN_SIZES
    elif gender == "Kids":
        return KIDS_SIZES
    else:
        return MEN_SIZES  # Default to men's sizes

def get_random_customer_name() -> str:
    """Get a random customer name for reviews."""
    return random.choice(CUSTOMER_NAMES)

def generate_random_review_text(product_name: str, rating: int) -> str:
    """Generate a random review text based on the rating."""
    positive_reviews = [
        f"Love these {product_name}! They are so comfortable and stylish.",
        f"Best shoes I've ever owned. The {product_name} exceeded my expectations.",
        f"Great quality and fit perfectly. Would definitely buy the {product_name} again.",
        f"These {product_name} are amazing for the price. Highly recommend!",
        f"Super comfortable from day one. No breaking in needed for these {product_name}.",
        f"The {product_name} look even better in person than in the photos.",
        f"Perfect fit and very durable. These {product_name} are worth every penny.",
        f"I get compliments every time I wear these {product_name}."
    ]
    
    neutral_reviews = [
        f"The {product_name} are decent. Not amazing but good for the price.",
        f"Comfortable but not as durable as I'd hoped the {product_name} would be.",
        f"Good looking shoes but took some time to break in.",
        f"The {product_name} fit as expected but the color is slightly different than pictured.",
        f"Satisfied with my purchase but nothing exceptional about these {product_name}.",
        f"Good everyday shoes. The {product_name} serve their purpose well."
    ]
    
    negative_reviews = [
        f"Disappointed with these {product_name}. They started falling apart after just a few weeks.",
        f"The fit is off on these {product_name}. Had to return them.",
        f"Not comfortable at all. Wouldn't recommend these {product_name}.",
        f"The quality doesn't match the price. Expected better from these {product_name}.",
        f"The color of the {product_name} was completely different than what was shown online.",
        f"These run much smaller than expected. Size up if you buy the {product_name}."
    ]
    
    if rating >= 4:
        return random.choice(positive_reviews)
    elif rating >= 3:
        return random.choice(neutral_reviews)
    else:
        return random.choice(negative_reviews) 