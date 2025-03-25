-- Create Schema for Supportly Shoe Product Database

-- Create extension for generating UUIDs
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create brands table
CREATE TABLE IF NOT EXISTS brands (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    description TEXT,
    logo_url VARCHAR(255),
    website_url VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create categories table
CREATE TABLE IF NOT EXISTS categories (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    description TEXT,
    parent_id INTEGER REFERENCES categories(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create products table with JSONB for flexible attributes
CREATE TABLE IF NOT EXISTS products (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    sku VARCHAR(50) NOT NULL UNIQUE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    brand_id INTEGER REFERENCES brands(id),
    category_id INTEGER REFERENCES categories(id),
    price DECIMAL(10, 2) NOT NULL,
    sale_price DECIMAL(10, 2),
    is_on_sale BOOLEAN DEFAULT FALSE,
    is_featured BOOLEAN DEFAULT FALSE,
    is_active BOOLEAN DEFAULT TRUE,
    -- Store detailed product attributes in JSONB
    attributes JSONB NOT NULL DEFAULT '{}'::JSONB,
    -- Store images in JSONB array
    images JSONB NOT NULL DEFAULT '[]'::JSONB,
    -- Store additional metadata in JSONB
    metadata JSONB NOT NULL DEFAULT '{}'::JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create inventory table to track stock levels by size and color
CREATE TABLE IF NOT EXISTS inventory (
    id SERIAL PRIMARY KEY,
    product_id UUID REFERENCES products(id),
    -- Store size and color as part of a composite key with product_id
    size VARCHAR(20) NOT NULL,
    color VARCHAR(50) NOT NULL,
    quantity INTEGER NOT NULL DEFAULT 0,
    -- Store location data in JSONB
    location_data JSONB DEFAULT '{"warehouse": "main"}'::JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(product_id, size, color)
);

-- Create reviews table
CREATE TABLE IF NOT EXISTS reviews (
    id SERIAL PRIMARY KEY,
    product_id UUID REFERENCES products(id),
    customer_name VARCHAR(100),
    rating INTEGER NOT NULL CHECK (rating BETWEEN 1 AND 5),
    review_text TEXT,
    verified_purchase BOOLEAN DEFAULT FALSE,
    -- Store review metadata in JSONB
    metadata JSONB DEFAULT '{}'::JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create product_related table to establish relationships between products (similar, accessories, etc.)
CREATE TABLE IF NOT EXISTS product_relations (
    id SERIAL PRIMARY KEY,
    product_id UUID REFERENCES products(id),
    related_product_id UUID REFERENCES products(id),
    relation_type VARCHAR(50) NOT NULL, -- e.g., 'similar', 'accessory', 'alternative', etc.
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(product_id, related_product_id, relation_type)
);

-- Create materialized view for product search
CREATE MATERIALIZED VIEW IF NOT EXISTS product_search AS
SELECT 
    p.id,
    p.sku,
    p.name,
    p.description,
    b.name AS brand_name,
    c.name AS category_name,
    p.price,
    p.sale_price,
    p.is_on_sale,
    p.is_featured,
    p.is_active,
    p.attributes,
    p.images,
    COALESCE(
        (SELECT jsonb_agg(
            jsonb_build_object(
                'size', i.size,
                'color', i.color,
                'quantity', i.quantity
            )
        )
        FROM inventory i WHERE i.product_id = p.id),
        '[]'::jsonb
    ) AS inventory,
    COALESCE(
        (SELECT AVG(r.rating)::NUMERIC(3,2)
         FROM reviews r
         WHERE r.product_id = p.id),
        0
    ) AS avg_rating,
    COALESCE(
        (SELECT COUNT(r.id)
         FROM reviews r
         WHERE r.product_id = p.id),
        0
    ) AS review_count
FROM 
    products p
JOIN 
    brands b ON p.brand_id = b.id
JOIN 
    categories c ON p.category_id = c.id;

-- Create index for product search on various fields
CREATE INDEX IF NOT EXISTS idx_product_search_name ON products USING gin (to_tsvector('english', name));
CREATE INDEX IF NOT EXISTS idx_product_description ON products USING gin (to_tsvector('english', description));
CREATE INDEX IF NOT EXISTS idx_product_attributes ON products USING gin (attributes);

-- Create trigger to update the updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply the trigger to tables
CREATE TRIGGER update_brand_updated_at BEFORE UPDATE ON brands FOR EACH ROW EXECUTE PROCEDURE update_updated_at_column();
CREATE TRIGGER update_category_updated_at BEFORE UPDATE ON categories FOR EACH ROW EXECUTE PROCEDURE update_updated_at_column();
CREATE TRIGGER update_product_updated_at BEFORE UPDATE ON products FOR EACH ROW EXECUTE PROCEDURE update_updated_at_column();
CREATE TRIGGER update_inventory_updated_at BEFORE UPDATE ON inventory FOR EACH ROW EXECUTE PROCEDURE update_updated_at_column();

-- Create function to refresh product_search materialized view
CREATE OR REPLACE FUNCTION refresh_product_search()
RETURNS TRIGGER AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY product_search;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

-- Refresh product_search when products, brands, categories, or inventory is updated
CREATE TRIGGER refresh_product_search_on_product_change
AFTER INSERT OR UPDATE OR DELETE ON products
FOR EACH STATEMENT EXECUTE PROCEDURE refresh_product_search();

CREATE TRIGGER refresh_product_search_on_brand_change
AFTER INSERT OR UPDATE OR DELETE ON brands
FOR EACH STATEMENT EXECUTE PROCEDURE refresh_product_search();

CREATE TRIGGER refresh_product_search_on_category_change
AFTER INSERT OR UPDATE OR DELETE ON categories
FOR EACH STATEMENT EXECUTE PROCEDURE refresh_product_search();

CREATE TRIGGER refresh_product_search_on_inventory_change
AFTER INSERT OR UPDATE OR DELETE ON inventory
FOR EACH STATEMENT EXECUTE PROCEDURE refresh_product_search();
