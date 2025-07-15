-- Critical indexes for search performance
-- Run these on your Railway PostgreSQL database

-- 1. Primary search index on property_address
CREATE INDEX IF NOT EXISTS idx_property_address_upper 
ON properties (UPPER(property_address));

-- 2. Trigram index for fuzzy matching (LIKE queries)
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE INDEX IF NOT EXISTS idx_property_address_trgm 
ON properties USING gin (property_address gin_trgm_ops);

-- 3. Composite index for location queries
CREATE INDEX IF NOT EXISTS idx_property_location 
ON properties (centroid_lat, centroid_lon);

-- 4. Index for value queries
CREATE INDEX IF NOT EXISTS idx_property_value 
ON properties (total_value);

-- 5. Partial index for non-zero value properties
CREATE INDEX IF NOT EXISTS idx_property_value_nonzero 
ON properties (total_value) 
WHERE total_value > 0;

-- 6. Index for city searches
CREATE INDEX IF NOT EXISTS idx_property_city 
ON properties (UPPER(city));

-- Analyze tables for query planner
ANALYZE properties;