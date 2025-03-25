#!/usr/bin/env python
"""
Seed script for generating synthetic data for the Supportly Shoe Store product database.
This script will:
1. Generate brands
2. Generate categories
3. Generate products with detailed attributes
4. Generate inventory data
5. Generate reviews
6. Generate product relations
"""

import json
import os
import sys
import random
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Any

# Add the parent directory to sys.path to make imports work
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import the data generators
from database.data_generators.brands import generate_brands
from database.data_generators.categories import generate_categories
from database.data_generators.products import generate_products
from database.data_generators.inventory import generate_inventory
from database.data_generators.reviews import generate_reviews
from database.data_generators.relations import generate_product_relations

# Create directory if it doesn't exist
os.makedirs('database/data', exist_ok=True)

def save_data_to_json(data: List[Dict], filename: str) -> None:
    """Save generated data to a JSON file."""
    file_path = f"database/data/{filename}.json"
    with open(file_path, 'w') as f:
        json.dump(data, f, indent=2)
    print(f"Generated {len(data)} records and saved to {file_path}")

def main():
    """Main function to generate all the seed data."""
    # Generate brand data
    brands = generate_brands()
    save_data_to_json(brands, "brands")
    
    # Generate category data
    categories = generate_categories()
    save_data_to_json(categories, "categories")
    
    # Generate product data (with dependencies on brands and categories)
    products = generate_products(brands, categories)
    save_data_to_json(products, "products")
    
    # Generate inventory data
    inventory = generate_inventory(products)
    save_data_to_json(inventory, "inventory")
    
    # Generate review data
    reviews = generate_reviews(products)
    save_data_to_json(reviews, "reviews")
    
    # Generate product relations
    relations = generate_product_relations(products)
    save_data_to_json(relations, "product_relations")
    
    print("All seed data generated successfully!")

if __name__ == "__main__":
    main()
