#!/usr/bin/env python
"""
Generate synthetic category data for the shoe store database.
"""

from typing import List, Dict, Optional

def generate_categories() -> List[Dict]:
    """
    Generate a list of shoe categories with hierarchical structure.
    
    Returns:
        List[Dict]: A list of category dictionaries
    """
    categories = [
        # Main categories
        {
            "id": 1,
            "name": "Athletic",
            "description": "Shoes designed for sports and athletic activities",
            "parent_id": None
        },
        {
            "id": 2,
            "name": "Casual",
            "description": "Everyday comfortable shoes for casual wear",
            "parent_id": None
        },
        {
            "id": 3,
            "name": "Formal",
            "description": "Elegant shoes for formal occasions and business wear",
            "parent_id": None
        },
        {
            "id": 4,
            "name": "Outdoor",
            "description": "Durable shoes for outdoor activities and adventures",
            "parent_id": None
        },
        {
            "id": 5,
            "name": "Special Purpose",
            "description": "Shoes designed for specific activities or environments",
            "parent_id": None
        },
        
        # Athletic subcategories
        {
            "id": 6,
            "name": "Running",
            "description": "Shoes designed for running with cushioning and support",
            "parent_id": 1
        },
        {
            "id": 7,
            "name": "Basketball",
            "description": "High-top shoes with ankle support for basketball",
            "parent_id": 1
        },
        {
            "id": 8,
            "name": "Soccer",
            "description": "Cleats and shoes designed for soccer play",
            "parent_id": 1
        },
        {
            "id": 9,
            "name": "Training",
            "description": "Versatile shoes for gym workouts and cross-training",
            "parent_id": 1
        },
        {
            "id": 10,
            "name": "Tennis",
            "description": "Shoes with lateral support for tennis courts",
            "parent_id": 1
        },
        
        # Casual subcategories
        {
            "id": 11,
            "name": "Sneakers",
            "description": "Casual athletic-inspired shoes for everyday wear",
            "parent_id": 2
        },
        {
            "id": 12,
            "name": "Slip-Ons",
            "description": "Easy to wear shoes without laces",
            "parent_id": 2
        },
        {
            "id": 13,
            "name": "Sandals",
            "description": "Open shoes with straps for warm weather",
            "parent_id": 2
        },
        {
            "id": 14,
            "name": "Loafers",
            "description": "Slip-on shoes with a moccasin-like construction",
            "parent_id": 2
        },
        
        # Formal subcategories
        {
            "id": 15,
            "name": "Oxfords",
            "description": "Classic lace-up dress shoes",
            "parent_id": 3
        },
        {
            "id": 16,
            "name": "Derbies",
            "description": "Less formal lace-up dress shoes with open lacing",
            "parent_id": 3
        },
        {
            "id": 17,
            "name": "Monk Straps",
            "description": "Formal shoes with buckle closure instead of laces",
            "parent_id": 3
        },
        {
            "id": 18,
            "name": "Dress Boots",
            "description": "Formal boots suitable for business attire",
            "parent_id": 3
        },
        
        # Outdoor subcategories
        {
            "id": 19,
            "name": "Hiking Boots",
            "description": "Rugged boots for trail hiking and outdoor adventures",
            "parent_id": 4
        },
        {
            "id": 20,
            "name": "Work Boots",
            "description": "Durable boots for construction and industrial work",
            "parent_id": 4
        },
        {
            "id": 21,
            "name": "Trail Running",
            "description": "Running shoes designed for off-road terrain",
            "parent_id": 4
        },
        {
            "id": 22,
            "name": "Winter Boots",
            "description": "Insulated boots for cold weather protection",
            "parent_id": 4
        },
        
        # Special Purpose subcategories
        {
            "id": 23,
            "name": "Cycling",
            "description": "Shoes designed for cycling with stiff soles",
            "parent_id": 5
        },
        {
            "id": 24,
            "name": "Golf",
            "description": "Shoes with spikes or traction for golfing",
            "parent_id": 5
        },
        {
            "id": 25,
            "name": "Skateboarding",
            "description": "Durable shoes with flat soles for skateboarding",
            "parent_id": 5
        },
        {
            "id": 26,
            "name": "Dance",
            "description": "Specialized shoes for various dance styles",
            "parent_id": 5
        }
    ]
    
    return categories 