#!/usr/bin/env python
"""
Convert the generated JSON data to SQL INSERT statements.
"""

import json
import os
import sys
from typing import Dict, List, Any

def json_to_sql_value(value: Any) -> str:
    """
    Convert a Python value to an SQL value string.
    
    Args:
        value: The value to convert
        
    Returns:
        String representation for SQL
    """
    if value is None:
        return "NULL"
    elif isinstance(value, (int, float)):
        return str(value)
    elif isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    elif isinstance(value, (dict, list)):
        # Convert to JSON string and escape single quotes
        json_str = json.dumps(value).replace("'", "''")
        return f"'{json_str}'::jsonb"
    else:
        # String - escape single quotes
        return f"'{str(value).replace('', '')}'"

def generate_insert_statement(table_name: str, data: List[Dict]) -> List[str]:
    """
    Generate SQL INSERT statements for a table.
    
    Args:
        table_name: Name of the table
        data: List of dictionaries containing the data
        
    Returns:
        List of SQL INSERT statements
    """
    if not data:
        return []
    
    statements = []
    
    # Get column names from the first item
    columns = data[0].keys()
    
    # Generate INSERT statements
    for item in data:
        values = [json_to_sql_value(item.get(column)) for column in columns]
        
        stmt = f"INSERT INTO {table_name} ({', '.join(columns)}) "
        stmt += f"VALUES ({', '.join(values)});"
        
        statements.append(stmt)
    
    return statements

def main():
    """Convert all JSON data files to SQL."""
    data_dir = "database/data"
    output_file = "database/seed_data.sql"
    
    # Check if data directory exists
    if not os.path.exists(data_dir):
        print(f"Error: Data directory {data_dir} not found")
        sys.exit(1)
    
    # File to table name mapping
    file_table_map = {
        "brands.json": "brands",
        "categories.json": "categories",
        "products.json": "products",
        "inventory.json": "inventory",
        "reviews.json": "reviews",
        "product_relations.json": "product_relations"
    }
    
    # Create output file
    with open(output_file, "w") as f_out:
        # Write header
        f_out.write("-- Supportly Shoe Store seed data\n")
        f_out.write("-- Generated from JSON files\n\n")
        
        # Process each data file
        for file_name, table_name in file_table_map.items():
            file_path = os.path.join(data_dir, file_name)
            
            if not os.path.exists(file_path):
                print(f"Warning: {file_path} not found, skipping")
                continue
            
            # Read JSON data
            with open(file_path, "r") as f_in:
                data = json.load(f_in)
            
            # Generate SQL statements
            statements = generate_insert_statement(table_name, data)
            
            # Write to output file
            f_out.write(f"-- {table_name} data\n")
            f_out.write(f"-- {len(statements)} records\n\n")
            
            for stmt in statements:
                f_out.write(f"{stmt}\n")
            
            f_out.write("\n\n")
            
            print(f"Processed {file_name}: {len(statements)} records")
        
        # Add statement to refresh materialized view
        f_out.write("-- Refresh materialized view\n")
        f_out.write("REFRESH MATERIALIZED VIEW product_search;\n")
    
    print(f"\nSQL data generated in {output_file}")

if __name__ == "__main__":
    main() 