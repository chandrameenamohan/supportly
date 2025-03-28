#!/usr/bin/env python
"""
Generate synthetic brand data for the shoe store database.
"""

from typing import List, Dict

def generate_brands() -> List[Dict]:
    """
    Generate a list of shoe brands with relevant information.
    
    Returns:
        List[Dict]: A list of brand dictionaries
    """
    brands = [
        {
            "id": 1,
            "name": "Nike",
            "description": "American multinational corporation that designs, develops, manufactures, and markets footwear, apparel, equipment, and accessories worldwide.",
            "logo_url": "https://example.com/logos/nike.png",
            "website_url": "https://www.nike.com"
        },
        {
            "id": 2,
            "name": "Adidas",
            "description": "German multinational corporation that designs and manufactures shoes, clothing and accessories.",
            "logo_url": "https://example.com/logos/adidas.png",
            "website_url": "https://www.adidas.com"
        },
        {
            "id": 3,
            "name": "Puma",
            "description": "German multinational corporation that designs and manufactures athletic and casual footwear, apparel and accessories.",
            "logo_url": "https://example.com/logos/puma.png",
            "website_url": "https://www.puma.com"
        },
        {
            "id": 4,
            "name": "New Balance",
            "description": "American multinational corporation that designs and manufactures athletic footwear and apparel.",
            "logo_url": "https://example.com/logos/new_balance.png",
            "website_url": "https://www.newbalance.com"
        },
        {
            "id": 5,
            "name": "Converse",
            "description": "American shoe company that designs, distributes, and licenses sneakers, skating shoes, lifestyle brand footwear, apparel, and accessories.",
            "logo_url": "https://example.com/logos/converse.png",
            "website_url": "https://www.converse.com"
        },
        {
            "id": 6,
            "name": "Reebok",
            "description": "Global athletic footwear and apparel company, producing and distributing fitness, running and CrossFit sportswear.",
            "logo_url": "https://example.com/logos/reebok.png",
            "website_url": "https://www.reebok.com"
        },
        {
            "id": 7,
            "name": "Vans",
            "description": "American manufacturer of skateboarding shoes and related apparel, started in California.",
            "logo_url": "https://example.com/logos/vans.png",
            "website_url": "https://www.vans.com"
        },
        {
            "id": 8,
            "name": "ASICS",
            "description": "Japanese multinational corporation that produces footwear and sports equipment designed for a wide range of sports.",
            "logo_url": "https://example.com/logos/asics.png",
            "website_url": "https://www.asics.com"
        },
        {
            "id": 9,
            "name": "Saucony",
            "description": "American manufacturer of athletic shoes, known for their running shoes.",
            "logo_url": "https://example.com/logos/saucony.png",
            "website_url": "https://www.saucony.com"
        },
        {
            "id": 10,
            "name": "Under Armour",
            "description": "American sports equipment company that manufactures footwear, sports and casual apparel.",
            "logo_url": "https://example.com/logos/under_armour.png",
            "website_url": "https://www.underarmour.com"
        },
        {
            "id": 11,
            "name": "Brooks",
            "description": "American sports equipment company that designs and markets high-performance running shoes and apparel.",
            "logo_url": "https://example.com/logos/brooks.png",
            "website_url": "https://www.brooksrunning.com"
        },
        {
            "id": 12,
            "name": "Timberland",
            "description": "American manufacturer and retailer of outdoors wear, with a focus on footwear.",
            "logo_url": "https://example.com/logos/timberland.png",
            "website_url": "https://www.timberland.com"
        }
    ]
    
    return brands 