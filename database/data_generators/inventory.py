#!/usr/bin/env python
"""
Generate synthetic inventory data for the shoe store database.
"""

import random
from typing import List, Dict, Any
from .utils import get_sizes_by_gender, get_random_colors

def generate_inventory(products: List[Dict]) -> List[Dict]:
    """
    Generate inventory data for products with variations by size and color.
    
    Args:
        products: List of product dictionaries
        
    Returns:
        List of inventory dictionaries
    """
    inventory_items = []
    inventory_id = 1
    
    for product in products:
        # Get product details
        product_id = product["id"]
        attributes = product["attributes"]
        gender = attributes.get("gender", "Men")
        
        # Get appropriate sizes based on gender
        sizes = get_sizes_by_gender(gender)
        
        # Get available colors (3-6 colors per product)
        color_count = random.randint(3, 6)
        colors = get_random_colors(color_count)
        
        # Generate inventory items for each size and color combination
        for size in sizes:
            for color in colors:
                # Generate random stock quantity
                # Popular sizes (middle range) have more stock
                mid_index = len(sizes) // 2
                size_index = sizes.index(size)
                
                # Calculate distance from middle size
                distance_from_mid = abs(size_index - mid_index)
                max_distance = max(mid_index, len(sizes) - mid_index - 1)
                
                # Normalize distance to a 0-1 scale and invert (closer to middle = higher stock)
                popularity_factor = 1 - (distance_from_mid / max_distance)
                
                # Base quantity with randomness
                base_quantity = random.randint(3, 20)
                
                # Apply popularity factor (middle sizes get up to 2x more stock)
                quantity = round(base_quantity * (1 + popularity_factor))
                
                # 10% chance for a size/color to be out of stock
                if random.random() < 0.1:
                    quantity = 0
                
                # Create inventory item
                inventory_item = {
                    "id": inventory_id,
                    "product_id": product_id,
                    "size": str(size),
                    "color": color["name"],
                    "quantity": quantity,
                    "location_data": {
                        "warehouse": random.choice(["main", "east", "west"]),
                        "aisle": random.choice(["A", "B", "C", "D"]) + str(random.randint(1, 20)),
                        "shelf": random.randint(1, 5),
                        "color_hex": color["hex"]
                    }
                }
                
                inventory_items.append(inventory_item)
                inventory_id += 1
    
    return inventory_items 