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

# Supportly Database Layer

## Hybrid Search and Database Architecture

This module implements a hybrid approach to database operations:

1. **Vector Database (ChromaDB)** - For semantic search and natural language understanding
2. **SQL Database** - For precise filtering, inventory management, and reporting

## Why a Hybrid Approach?

The hybrid approach leverages the strengths of both technologies:

### Vector Database Strengths
- **Natural Language Understanding**: Finds products based on semantic meaning, not just exact keywords
- **Semantic Similarity**: Discovers products that are conceptually related even with different terminology 
- **Fuzzy Matching**: Handles typos, synonyms, and concept-based queries
- **Understanding Context**: Interprets the meaning behind search terms

### SQL Database Strengths
- **Precise Filtering**: Exact matches on structured attributes (price, brand, category, etc.)
- **Complex Aggregations**: Efficiently calculates totals, averages, counts across many dimensions
- **Reporting**: Generates detailed business reports with grouping and analytics
- **Inventory Management**: Tracks exact stock counts, sizes, and availability
- **Transaction Support**: Ensures data consistency for inventory changes

## Implementation Details

### Hybrid Search Implementation

The hybrid search approach works in two stages:

1. **Vector Search Phase**: Uses OpenAI embeddings to find semantically relevant products
2. **SQL Filtering Phase**: Applies precise filters (price, size, etc.) to the candidate set

This provides the best of both worlds - the natural language understanding of vector search with the precise filtering capabilities of SQL.

Example: When a user searches for "comfortable running shoes under $100", the system:
1. Uses vector search to find products related to "comfortable running shoes"
2. Uses SQL to filter those results to only show items under $100

### SQL Reporting Features

SQL excels at complex analytical queries needed for business reporting:

- **Inventory Reports**: Track stock levels, value, and distribution by category/brand
- **Price Analysis**: Analyze pricing trends, discounts, and promotional effectiveness
- **Most Discounted Products**: Find the best deals currently available
- **Sales Performance**: Track product performance by various dimensions

## API Endpoints

### Search and Product Information
- `POST /products/search` - Search products with flexible filtering
- `POST /products/semantic-search` - Natural language search using vector database
- `GET /products/details/{product_id}` - Get detailed product information

### SQL-Based Reporting
- `POST /products/reports/inventory` - Generate inventory reports
- `POST /products/reports/price-analysis` - Generate price analysis
- `GET /products/reports/most-discounted` - Find most discounted products

## Fallback Mechanisms

The system includes robust fallback mechanisms:
- If vector search fails, the system falls back to keyword search
- If SQL queries fail, the system uses in-memory data processing

This ensures the application remains functional even if certain components are unavailable.

## Architecture Diagram

```
┌──────────────────┐     ┌───────────────────┐     ┌─────────────────┐
│  User Interface  │────▶│  Product Search   │────▶│  Vector Search  │
└──────────────────┘     │    (Hybrid)       │     │  (Semantic)     │
                         └─────────┬─────────┘     └─────────────────┘
                                   │
                                   ▼
┌──────────────────┐     ┌───────────────────┐     ┌─────────────────┐
│  Admin Reports   │◀────│  SQL Database     │◀────│  SQL Filtering  │
└──────────────────┘     │  (Precise)        │     │  (Exact Match)  │
                         └───────────────────┘     └─────────────────┘
```

## Best Practices for Extension

When extending this system:

1. Use vector search for:
   - Natural language queries
   - Concept-based search
   - Recommendation systems
   - Finding similar products

2. Use SQL for:
   - Exact attribute filtering
   - Inventory management
   - Analytics and reporting
   - Transaction processing
   - Complex grouping and aggregation

3. Consider combining both in a pipeline:
   - Vector search to find candidate products based on meaning
   - SQL to apply precise business rules and filters 