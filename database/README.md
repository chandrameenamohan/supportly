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
python json_to_sql.py
```

## Integration with Products Agent

The products agent can use this database to look up relevant information before responding to customer queries. The agent can:

1. Search for products by name, category, or attributes
2. Retrieve detailed product information
3. Check inventory availability
4. Get related products
5. Access customer reviews and ratings

This enables the agent to provide accurate and detailed responses to customer inquiries about the shoe store's products.

## Components

The following components work together to enable product database functionality:

- `products_agent.py` - Main class that handles natural language queries about products
- `products_repository.py` - Repository class that handles database interaction
- `db_connection.py` - Database connection manager
- `integration.py` - Integration with the main Supportly application
- `products_agent_demo.py` - Demo script showing the agent functionality

## Testing

### Integration Tests

The `tests/` directory contains comprehensive test cases for the product database functionality:

- `test_products_agent.py` - Tests for the ProductsAgent class
- `test_products_tool.py` - Tests for the ProductsTool class
- `test_products_repository.py` - Tests for the ProductsRepository class
- `test_api_and_integration.py` - Tests for API endpoints and integration
- `test_main_application.py` - Tests for integration with the main application

### Sample Tests

Sample tests demonstrate how to test the product database functionality:

- `test_main_application_sample.py` - Sample integration tests with clear examples
- `run_sample_test.py` - Script to run sample tests with detailed output

To run the sample tests:

```bash
# Run all sample tests
python -m database.tests.run_sample_test

# Run with verbose output
python -m database.tests.run_sample_test -v

# Run specific test
python -m database.tests.run_sample_test -t TestProductsAgentSample.test_search_products

# Show detailed help
python -m database.tests.run_sample_test --help-more
```

For more details on testing, see the [tests/README.md](tests/README.md) file. 