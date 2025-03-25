#!/usr/bin/env python
"""
Generate synthetic product data for the shoe store database.
"""

import json
import random
from typing import List, Dict, Any
from .utils import (
    generate_sku, generate_price, generate_sale_price, 
    generate_uuid, get_random_materials, get_random_colors
)

# Product models by brand and category
PRODUCT_TEMPLATES = {
    # Nike products
    "Nike": {
        # Running shoes
        6: [
            {"name": "Air Zoom Pegasus", "gender": "Men", "description": "Responsive cushioning for your daily runs."},
            {"name": "ZoomX Invincible Run", "gender": "Women", "description": "Maximum cushioning for long-distance comfort."},
            {"name": "Air Zoom Tempo", "gender": "Men", "description": "Responsive and fast for tempo runs and race day."},
            {"name": "React Infinity Run", "gender": "Women", "description": "Designed to help reduce injury with smooth transitions."}
        ],
        # Basketball shoes
        7: [
            {"name": "LeBron Witness", "gender": "Men", "description": "Responsive cushioning and support for the court."},
            {"name": "Kyrie Flytrap", "gender": "Men", "description": "Quick cuts and responsive feel for dynamic players."},
            {"name": "Zoom Freak", "gender": "Men", "description": "Designed for versatile forwards with responsive cushioning."}
        ],
        # Casual/Sneakers
        11: [
            {"name": "Air Force 1", "gender": "Men", "description": "Classic style with premium leather upper."},
            {"name": "Air Max 90", "gender": "Women", "description": "Iconic design with visible Air cushioning."},
            {"name": "Blazer Mid", "gender": "Men", "description": "Vintage basketball style for everyday wear."}
        ]
    },
    # Adidas products
    "Adidas": {
        # Running shoes
        6: [
            {"name": "Ultraboost", "gender": "Men", "description": "Responsive Boost cushioning for energy return."},
            {"name": "Supernova", "gender": "Women", "description": "Balanced cushioning for everyday training runs."},
            {"name": "Adizero Adios", "gender": "Men", "description": "Lightweight and fast for race day performance."}
        ],
        # Soccer shoes
        8: [
            {"name": "Predator Edge", "gender": "Men", "description": "Enhanced ball control and striking power."},
            {"name": "X Speedflow", "gender": "Men", "description": "Ultralight speed for the fastest players."},
            {"name": "Copa Sense", "gender": "Men", "description": "Premium touch and comfort for technical players."}
        ],
        # Casual/Sneakers
        11: [
            {"name": "Stan Smith", "gender": "Women", "description": "Classic tennis style with a clean, minimalist design."},
            {"name": "Superstar", "gender": "Men", "description": "Iconic shell toe design that's been a staple since 1970."},
            {"name": "Gazelle", "gender": "Women", "description": "Vintage trainer with a sleek profile."}
        ]
    },
    # Add more brands and their products here...
}

# Additional descriptive text for product features
FEATURE_DESCRIPTIONS = {
    "Running": [
        "Responsive cushioning for a smooth ride",
        "Breathable mesh upper keeps feet cool",
        "Strategic rubber placement for durability and traction",
        "Heel collar wraps ankle for comfortable fit",
        "Reflective details for visibility in low light",
        "Flexible grooves allow natural foot movement"
    ],
    "Basketball": [
        "Zoom Air units provide responsive cushioning",
        "High-top design offers ankle support",
        "Multidirectional traction pattern for court grip",
        "Reinforced toe cap for durability",
        "Padded collar for comfort during play",
        "Lightweight design for quick movements"
    ],
    "Training": [
        "Stable base for lifting weights",
        "Responsive cushioning for high-intensity workouts",
        "Durable upper for lateral movements",
        "Flexible forefoot for natural movement",
        "Extra grippy outsole for indoor surfaces"
    ],
    "Casual": [
        "Classic design for everyday style",
        "Cushioned insole for all-day comfort",
        "Durable construction for long-lasting wear",
        "Versatile design pairs with multiple outfits",
        "Iconic silhouette with heritage details"
    ],
    "Hiking": [
        "Waterproof membrane keeps feet dry",
        "Aggressive outsole pattern for trail traction",
        "Protective toe cap for rocky terrain",
        "Supportive midsole for long hikes",
        "Gusseted tongue keeps debris out"
    ]
}

def generate_product_description(template: Dict, category_name: str) -> str:
    """Generate a detailed product description based on template and category."""
    base_description = template["description"]
    
    # Add category-specific feature descriptions
    features = []
    if category_name in FEATURE_DESCRIPTIONS:
        # Select 2-4 random features
        feature_count = random.randint(2, 4)
        features = random.sample(FEATURE_DESCRIPTIONS[category_name], min(feature_count, len(FEATURE_DESCRIPTIONS[category_name])))
    
    # Combine base description with features
    full_description = f"{base_description}\n\n"
    if features:
        full_description += "Features:\n"
        for feature in features:
            full_description += f"• {feature}\n"
    
    return full_description.strip()

def generate_product_attributes(template: Dict, category_id: int, brand_name: str) -> Dict:
    """Generate detailed attributes for a product in JSONB format."""
    # Basic attributes from template
    gender = template.get("gender", random.choice(["Men", "Women"]))
    
    # Get appropriate category name for feature descriptions
    category_map = {
        6: "Running", 7: "Basketball", 9: "Training", 
        11: "Casual", 19: "Hiking"
    }
    category_name = category_map.get(category_id, "Casual")
    
    # Generate materials based on category
    materials = get_random_materials()
    
    # Generate attributes structure
    attributes = {
        "gender": gender,
        "materials": materials,
        "features": [],
        "specifications": {
            "weight": f"{random.randint(200, 450)} g",
            "heel_drop": f"{random.randint(0, 12)} mm",
            "arch_support": random.choice(["Neutral", "Support", "Minimal"]),
            "closure": random.choice(["Lace-up", "Slip-on", "Hook-and-loop", "Buckle"]),
            "outsole": random.choice(["Rubber", "Carbon rubber", "Blown rubber", "Gum rubber"]),
            "midsole": random.choice(["EVA", "Foam", "React", "Boost", "Gel", "Air"])
        },
        "care_instructions": "Wipe clean with a damp cloth. Air dry only. Do not machine wash."
    }
    
    # Add category-specific features
    if category_name in FEATURE_DESCRIPTIONS:
        # Select 2-4 random features
        feature_count = random.randint(2, 4)
        features = random.sample(FEATURE_DESCRIPTIONS[category_name], min(feature_count, len(FEATURE_DESCRIPTIONS[category_name])))
        attributes["features"] = features
    
    return attributes

def generate_products(brands: List[Dict], categories: List[Dict]) -> List[Dict]:
    """
    Generate synthetic product data based on brands and categories.
    
    Args:
        brands: List of brand dictionaries
        categories: List of category dictionaries
        
    Returns:
        List of product dictionaries
    """
    products = []
    product_id_counter = 1
    
    # Create mapping for categories by ID for easy lookup
    categories_by_id = {category["id"]: category for category in categories}
    
    for brand in brands:
        brand_name = brand["name"]
        brand_prefix = brand_name[:4].upper()
        
        # Check if we have templates for this brand
        if brand_name in PRODUCT_TEMPLATES:
            for category_id, templates in PRODUCT_TEMPLATES[brand_name].items():
                for template in templates:
                    # Generate a unique product ID
                    product_uuid = generate_uuid()
                    
                    # Get the category name for better descriptions
                    category_name = categories_by_id.get(category_id, {}).get("name", "General")
                    
                    # Generate SKU
                    sku = generate_sku(brand_prefix, category_id, product_id_counter)
                    
                    # Generate price based on category
                    price = generate_price(category_id)
                    sale_price, is_on_sale = generate_sale_price(price)
                    
                    # Generate detailed product description
                    description = generate_product_description(template, category_name)
                    
                    # Generate product attributes
                    attributes = generate_product_attributes(template, category_id, brand_name)
                    
                    # Generate images URLs (placeholder)
                    images = [
                        {"url": f"https://example.com/images/{sku}_1.jpg", "is_primary": True},
                        {"url": f"https://example.com/images/{sku}_2.jpg", "is_primary": False},
                        {"url": f"https://example.com/images/{sku}_3.jpg", "is_primary": False}
                    ]
                    
                    # Create the product object
                    product = {
                        "id": product_uuid,
                        "sku": sku,
                        "name": f"{brand_name} {template['name']}",
                        "description": description,
                        "brand_id": brand["id"],
                        "category_id": category_id,
                        "price": price,
                        "sale_price": sale_price,
                        "is_on_sale": is_on_sale,
                        "is_featured": random.random() < 0.2,  # 20% chance to be featured
                        "is_active": True,
                        "attributes": attributes,
                        "images": images,
                        "metadata": {
                            "search_keywords": [
                                brand_name.lower(),
                                template["name"].lower(),
                                category_name.lower(),
                                attributes["gender"].lower(),
                                *[material.lower() for material in attributes["materials"]]
                            ]
                        }
                    }
                    
                    products.append(product)
                    product_id_counter += 1
    
    # Add placeholder message to remind that this is a skeleton implementation
    if not products:
        print("WARNING: This is a skeleton implementation. Expand PRODUCT_TEMPLATES with more brands and categories.")
    
    return products 