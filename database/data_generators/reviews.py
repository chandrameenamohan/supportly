#!/usr/bin/env python
"""
Generate synthetic review data for the shoe store database.
"""

import random
from datetime import datetime, timedelta
from typing import List, Dict, Any
from .utils import get_random_customer_name, generate_random_review_text, random_date

def generate_reviews(products: List[Dict]) -> List[Dict]:
    """
    Generate product reviews with ratings and comments.
    
    Args:
        products: List of product dictionaries
        
    Returns:
        List of review dictionaries
    """
    reviews = []
    review_id = 1
    
    # Start date for reviews (1 year ago)
    start_date = datetime.now() - timedelta(days=365)
    end_date = datetime.now()
    
    for product in products:
        product_id = product["id"]
        product_name = product["name"]
        
        # Generate between 0-20 reviews per product
        # More popular products have more reviews
        is_featured = product["is_featured"]
        is_on_sale = product["is_on_sale"]
        
        # Base review count
        if is_featured:
            review_count = random.randint(5, 20)
        else:
            review_count = random.randint(0, 10)
        
        # Adjust for sales items
        if is_on_sale:
            review_count += random.randint(0, 5)
        
        # Generate the reviews
        for _ in range(review_count):
            # Ratings with a bias toward higher ratings
            # More products have 4-5 star ratings than 1-3 star ratings
            rating_weights = [0.05, 0.1, 0.15, 0.3, 0.4]  # Weights for 1-5 stars
            rating = random.choices([1, 2, 3, 4, 5], weights=rating_weights)[0]
            
            # Generate customer name
            customer_name = get_random_customer_name()
            
            # Generate review text based on rating
            review_text = generate_random_review_text(product_name, rating)
            
            # 70% chance of being a verified purchase
            verified_purchase = random.random() < 0.7
            
            # Generate a random date for the review
            review_date = random_date(start_date, end_date)
            
            # Additional metadata
            metadata = {
                "helpful_votes": random.randint(0, 20) if rating in [1, 5] else random.randint(0, 5),
                "purchase_date": (review_date - timedelta(days=random.randint(7, 90))).isoformat() if verified_purchase else None,
                "reviewed_on": review_date.isoformat()
            }
            
            # Create review
            review = {
                "id": review_id,
                "product_id": product_id,
                "customer_name": customer_name,
                "rating": rating,
                "review_text": review_text,
                "verified_purchase": verified_purchase,
                "metadata": metadata,
                "created_at": review_date.isoformat()
            }
            
            reviews.append(review)
            review_id += 1
    
    return reviews 