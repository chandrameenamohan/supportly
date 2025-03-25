#!/usr/bin/env python
"""
Generate synthetic product relation data for the shoe store database.
"""

import random
from typing import List, Dict, Any

def generate_product_relations(products: List[Dict]) -> List[Dict]:
    """
    Generate relations between products (similar, accessories, alternatives).
    
    Args:
        products: List of product dictionaries
        
    Returns:
        List of product relation dictionaries
    """
    relations = []
    relation_id = 1
    
    # Create product lookup by brand and category
    product_by_brand_category = {}
    for product in products:
        brand_id = product["brand_id"]
        category_id = product["category_id"]
        
        if brand_id not in product_by_brand_category:
            product_by_brand_category[brand_id] = {}
        
        if category_id not in product_by_brand_category[brand_id]:
            product_by_brand_category[brand_id][category_id] = []
        
        product_by_brand_category[brand_id][category_id].append(product)
    
    # Relation types
    relation_types = ["similar", "accessory", "alternative", "recommended_with"]
    
    # Process each product
    for product in products:
        product_id = product["id"]
        brand_id = product["brand_id"]
        category_id = product["category_id"]
        
        # Generate "similar" relations (same brand, same category)
        same_category_products = product_by_brand_category.get(brand_id, {}).get(category_id, [])
        similar_candidates = [p for p in same_category_products if p["id"] != product_id]
        
        # Take up to 3 similar products
        if similar_candidates:
            similar_count = min(len(similar_candidates), 3)
            for similar_product in random.sample(similar_candidates, similar_count):
                relation = {
                    "id": relation_id,
                    "product_id": product_id,
                    "related_product_id": similar_product["id"],
                    "relation_type": "similar"
                }
                relations.append(relation)
                relation_id += 1
        
        # Generate "alternative" relations (different brand, same category)
        alternative_candidates = []
        for alt_brand_id in product_by_brand_category:
            if alt_brand_id != brand_id and category_id in product_by_brand_category[alt_brand_id]:
                alternative_candidates.extend(product_by_brand_category[alt_brand_id][category_id])
        
        # Take up to 2 alternative products
        if alternative_candidates:
            alt_count = min(len(alternative_candidates), 2)
            for alt_product in random.sample(alternative_candidates, alt_count):
                relation = {
                    "id": relation_id,
                    "product_id": product_id,
                    "related_product_id": alt_product["id"],
                    "relation_type": "alternative"
                }
                relations.append(relation)
                relation_id += 1
        
        # Generate "accessory" relations (products from accessory categories)
        # Example: Running shoes -> Running socks, insoles, etc.
        # For this sample we'll just randomly select from other categories
        accessory_candidates = []
        for acc_category in product_by_brand_category.get(brand_id, {}):
            if acc_category != category_id:
                accessory_candidates.extend(product_by_brand_category[brand_id][acc_category])
        
        # Take 1 accessory product if available
        if accessory_candidates:
            acc_count = min(len(accessory_candidates), 1)
            for acc_product in random.sample(accessory_candidates, acc_count):
                relation = {
                    "id": relation_id,
                    "product_id": product_id,
                    "related_product_id": acc_product["id"],
                    "relation_type": "accessory"
                }
                relations.append(relation)
                relation_id += 1
        
        # Generate "recommended_with" relations (any other product with some randomness)
        # 30% chance to have recommended products
        if random.random() < 0.3:
            # Pick any random product that's not this one
            recommended_candidates = [p for p in products if p["id"] != product_id]
            
            # Take 1-2 recommended products
            if recommended_candidates:
                rec_count = random.randint(1, min(2, len(recommended_candidates)))
                for rec_product in random.sample(recommended_candidates, rec_count):
                    relation = {
                        "id": relation_id,
                        "product_id": product_id,
                        "related_product_id": rec_product["id"],
                        "relation_type": "recommended_with"
                    }
                    relations.append(relation)
                    relation_id += 1
    
    return relations 