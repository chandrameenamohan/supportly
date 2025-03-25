# Supportly Shoe Store Product Database

This directory contains the database schema and data generation scripts for the Supportly shoe product database. The database uses PostgreSQL with JSONB fields to store product attributes and other flexible data.

## Database Structure

The database consists of the following tables:

- **brands** - Shoe brands (Nike, Adidas, etc.)
- **categories** - Product categories with hierarchical structure (Athletic, Running, etc.)
- **products** - Main product table with JSONB fields for flexible attributes
- **inventory** - Stock levels by product, size, and color
- **reviews** - Customer reviews and ratings
- **product_relations** - Relationships between products (similar, accessories, etc.)

Additionally, a materialized view called `product_search` provides an optimized view for product search and lookup.

## Schema Design

The schema uses:

- UUIDs for product IDs
- JSONB for flexible attribute storage
- Proper indexing for efficient queries
- Optimized materialized views for search
- Triggers to maintain data consistency

## Data Generation

The synthetic data generation scripts create realistic shoe product data:

1. `seed_data.py` - Main script to generate all data
2. `data_generators/` - Directory with individual data generator modules:
   - `brands.py` - Brand data
   - `categories.py` - Category data
   - `products.py` - Product data
   - `inventory.py` - Inventory data
   - `reviews.py` - Review data
   - `relations.py` - Product relation data

## Usage

### Setting up the database

```bash
# Create a PostgreSQL database
createdb supportly_shoes

# Apply the schema
psql supportly_shoes < schema.sql
```

### Generating and loading data

```bash
# Generate synthetic data
python seed_data.py

# Load data into the database
# (This will be added in a future update)
```

## Integration with Products Agent

The products agent can use this database to look up relevant information before responding to customer queries. The agent can:

1. Search for products by name, category, or attributes
2. Retrieve detailed product information
3. Check inventory availability
4. Get related products
5. Access customer reviews and ratings

This enables the agent to provide accurate and detailed responses to customer inquiries about the shoe store's products. 