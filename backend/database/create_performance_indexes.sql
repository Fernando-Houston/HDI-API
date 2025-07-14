-- Performance Indexes for HDI Platform
-- Run this to significantly improve query performance

-- Primary lookup indexes
CREATE INDEX IF NOT EXISTS idx_properties_account ON properties(account_number);
CREATE INDEX IF NOT EXISTS idx_properties_address ON properties(property_address);
CREATE INDEX IF NOT EXISTS idx_properties_owner ON properties(owner_name);

-- Value-based queries
CREATE INDEX IF NOT EXISTS idx_properties_total_value ON properties(total_value);
CREATE INDEX IF NOT EXISTS idx_properties_value_range ON properties(total_value) 
    WHERE total_value > 0;

-- Geographic queries
CREATE INDEX IF NOT EXISTS idx_properties_centroid ON properties(centroid_lat, centroid_lon)
    WHERE centroid_lat IS NOT NULL AND centroid_lon IS NOT NULL;

-- Spatial index for geometry (if PostGIS available)
-- CREATE INDEX IF NOT EXISTS idx_properties_geometry ON properties USING GIST(geometry_wkt);

-- Property type filtering
CREATE INDEX IF NOT EXISTS idx_properties_type ON properties(property_type);
CREATE INDEX IF NOT EXISTS idx_properties_class ON properties(property_class);

-- Combined indexes for common queries
CREATE INDEX IF NOT EXISTS idx_properties_type_value ON properties(property_type, total_value);
CREATE INDEX IF NOT EXISTS idx_properties_city_value ON properties(city, total_value);

-- Text search indexes for autocomplete
CREATE EXTENSION IF NOT EXISTS pg_trgm;  -- Trigram extension for fuzzy search

CREATE INDEX IF NOT EXISTS idx_properties_address_trgm ON properties 
    USING gin(property_address gin_trgm_ops);

CREATE INDEX IF NOT EXISTS idx_properties_owner_trgm ON properties 
    USING gin(owner_name gin_trgm_ops);

-- Partial indexes for better performance
CREATE INDEX IF NOT EXISTS idx_properties_valuable ON properties(account_number, total_value)
    WHERE total_value > 100000;

CREATE INDEX IF NOT EXISTS idx_properties_commercial ON properties(account_number, property_address)
    WHERE property_class_desc LIKE '%Commercial%';

-- Index for year built queries
CREATE INDEX IF NOT EXISTS idx_properties_year_built ON properties(year_built)
    WHERE year_built IS NOT NULL AND year_built > 1900;

-- Analyze tables to update statistics
ANALYZE properties;

-- Function to check index usage
CREATE OR REPLACE FUNCTION check_index_usage() 
RETURNS TABLE(
    schemaname text,
    tablename text,
    indexname text,
    index_size text,
    index_scans bigint,
    index_efficiency numeric
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        s.schemaname::text,
        s.tablename::text,
        s.indexname::text,
        pg_size_pretty(pg_relation_size(s.indexrelid)) as index_size,
        s.idx_scan as index_scans,
        CASE 
            WHEN s.idx_scan = 0 THEN 0
            ELSE ROUND(100.0 * s.idx_scan / (s.seq_scan + s.idx_scan), 2)
        END as index_efficiency
    FROM pg_stat_user_indexes s
    JOIN pg_stat_user_tables t ON s.schemaname = t.schemaname 
        AND s.tablename = t.tablename
    WHERE s.schemaname NOT IN ('pg_catalog', 'information_schema')
    ORDER BY s.idx_scan DESC;
END;
$$ LANGUAGE plpgsql;

-- Check current index usage
-- SELECT * FROM check_index_usage();

-- Maintenance commands (run periodically)
-- REINDEX TABLE properties;
-- VACUUM ANALYZE properties;