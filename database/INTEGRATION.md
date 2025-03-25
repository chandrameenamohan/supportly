# Products Database Integration

This document explains how to integrate the products database with the Supportly chatbot.

## Overview

The products database integration consists of several components:

1. **Database Connection** - Manages connections to the PostgreSQL database
2. **Products Repository** - Contains database queries for product-related operations
3. **Products Agent** - Provides natural language interface to the database
4. **Products Tool** - Exposes database functionality to the chatbot
5. **API Endpoints** - RESTful API for interacting with the database
6. **Integration Module** - Registers the products tool with the Supportly application

## Setup

### Prerequisites

- PostgreSQL database with the product schema initialized
- Python 3.8+
- Supportly chatbot application

### Environment Variables

Add the following environment variables to your `.env` file:

```
DB_HOST=localhost
DB_PORT=5432
DB_NAME=supportly_shoes
DB_USER=postgres
DB_PASSWORD=your_password
```

### Database Initialization

1. Create the database schema:

```bash
psql -U postgres -c "CREATE DATABASE supportly_shoes;"
psql -U postgres -d supportly_shoes -f database/schema.sql
```

2. Generate and load synthetic data:

```bash
python -m database.seed_data
```

### Integration

The integration happens automatically when the application starts. The `startup_event` function in `api.py` initializes the products integration:

```python
@app.on_event("startup")
async def startup_event():
    """Initialize components on startup"""
    # Initialize orchestrator
    get_orchestrator()
    # Set up products integration
    await setup_products_integration()
    logger.info("Application startup complete")
```

## Architecture

### Database Connection

The `DatabaseConnection` class in `db_connection.py` handles connections to the PostgreSQL database using connection pooling:

```python
from database import db

# Execute a query
results = await db.execute_query("SELECT * FROM products LIMIT 10")
```

### Products Repository

The `ProductsRepository` class in `products_repository.py` contains all the database queries:

```python
from database import ProductsRepository

# Search for products
results = await ProductsRepository.search_products(query="running shoes")
```

### Products Agent

The `ProductsAgent` class in `products_agent.py` provides a natural language interface to the database, extracting search parameters from user messages and formatting responses:

```python
from database import ProductsAgent

agent = ProductsAgent()
result = await agent.search_products("show me red Nike running shoes")
```

### Products Tool

The `ProductsTool` class in `products_tool.py` exposes the database functionality to the chatbot:

```python
from database import ProductsTool

tool = ProductsTool()
result = await tool.execute("search", query="red Nike running shoes")
```

### API Endpoints

The products API is exposed through FastAPI endpoints in `api.py`:

```
POST /products/search - Search for products
POST /products/details - Get product details
POST /products/availability - Check product availability
POST /products/category - Get products in a category

GET /products/raw/search - Direct access to product search
GET /products/raw/product/{product_id} - Direct access to product details
GET /products/raw/categories/{category_name}/products - Direct access to category products
```

## Usage Examples

### Searching for Products

```python
from database import ProductsAgent

agent = ProductsAgent()
result = await agent.search_products("show me red Nike running shoes")
print(result["response"])
```

### Getting Product Details

```python
from database import ProductsRepository

product = await ProductsRepository.get_product_details_complete("product-uuid")
```

### Checking Product Availability

```python
from database import ProductsRepository

inventory = await ProductsRepository.check_inventory("product-uuid", "10", "red")
```

## Customization

### Adding New Actions

To add a new action to the products tool:

1. Add the action to the `execute` method in `products_tool.py`
2. Add a corresponding method to handle the action
3. Update the tool description in `get_tool_description` to include the new action

### Updating the Database Schema

If you need to update the database schema:

1. Modify `schema.sql` with your changes
2. Create a migration script in `database/migrations/`
3. Update the repository methods in `products_repository.py` to work with the new schema

## Troubleshooting

### Connection Issues

If you encounter database connection issues:

1. Check your environment variables
2. Ensure the PostgreSQL server is running
3. Check database logs for errors

### Query Performance

If queries are slow:

1. Check that appropriate indexes are created
2. Consider optimizing the query in `products_repository.py`
3. Use the materialized view `product_search` for complex searches

### Integration Issues

If the integration is not working properly:

1. Check the application logs for errors
2. Ensure the database is properly initialized
3. Verify that the products tool is being registered with the application 