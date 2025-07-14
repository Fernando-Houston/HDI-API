-- Property Change Tracking Tables
-- Run this in your PostgreSQL database

-- Table to track property changes
CREATE TABLE IF NOT EXISTS property_history (
    id SERIAL PRIMARY KEY,
    account_number VARCHAR(50) NOT NULL,
    property_address VARCHAR(255),
    change_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    change_type VARCHAR(50), -- 'value_change', 'owner_change', 'both'
    
    -- Previous values
    prev_owner_name VARCHAR(255),
    prev_total_value NUMERIC(15,2),
    prev_land_value NUMERIC(15,2),
    prev_building_value NUMERIC(15,2),
    
    -- New values
    new_owner_name VARCHAR(255),
    new_total_value NUMERIC(15,2),
    new_land_value NUMERIC(15,2),
    new_building_value NUMERIC(15,2),
    
    -- Change metrics
    value_change_amount NUMERIC(15,2),
    value_change_percent NUMERIC(5,2),
    
    -- Metadata
    detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    notification_sent BOOLEAN DEFAULT FALSE
);

-- Index for fast lookups
CREATE INDEX idx_property_history_account ON property_history(account_number);
CREATE INDEX idx_property_history_date ON property_history(change_date DESC);
CREATE INDEX idx_property_history_type ON property_history(change_type);

-- Table to store property snapshots for comparison
CREATE TABLE IF NOT EXISTS property_snapshots (
    id SERIAL PRIMARY KEY,
    account_number VARCHAR(50) NOT NULL,
    snapshot_date DATE DEFAULT CURRENT_DATE,
    property_data JSONB NOT NULL,
    hash VARCHAR(64), -- MD5 hash for quick comparison
    UNIQUE(account_number, snapshot_date)
);

-- Index for fast lookups
CREATE INDEX idx_property_snapshots_account ON property_snapshots(account_number);
CREATE INDEX idx_property_snapshots_date ON property_snapshots(snapshot_date DESC);

-- View to get latest changes
CREATE OR REPLACE VIEW recent_property_changes AS
SELECT 
    ph.*,
    p.property_type,
    p.property_class_desc
FROM property_history ph
LEFT JOIN properties p ON ph.account_number = p.account_number
WHERE ph.change_date > CURRENT_DATE - INTERVAL '90 days'
ORDER BY ph.change_date DESC;

-- Function to detect and record changes
CREATE OR REPLACE FUNCTION track_property_changes(
    p_account_number VARCHAR,
    p_check_all BOOLEAN DEFAULT FALSE
) RETURNS TABLE (
    change_detected BOOLEAN,
    change_type VARCHAR,
    details JSONB
) AS $$
DECLARE
    v_current_data JSONB;
    v_previous_data JSONB;
    v_current_hash VARCHAR;
    v_previous_hash VARCHAR;
    v_changes JSONB = '{}'::JSONB;
BEGIN
    -- Get current property data
    SELECT row_to_json(p.*)::JSONB INTO v_current_data
    FROM properties p
    WHERE p.account_number = p_account_number;
    
    IF v_current_data IS NULL THEN
        RETURN QUERY SELECT FALSE, NULL::VARCHAR, NULL::JSONB;
        RETURN;
    END IF;
    
    -- Calculate current hash
    v_current_hash := md5(v_current_data::TEXT);
    
    -- Get most recent snapshot
    SELECT property_data, hash INTO v_previous_data, v_previous_hash
    FROM property_snapshots
    WHERE account_number = p_account_number
    ORDER BY snapshot_date DESC
    LIMIT 1;
    
    -- If no previous data, create snapshot and return
    IF v_previous_data IS NULL THEN
        INSERT INTO property_snapshots (account_number, property_data, hash)
        VALUES (p_account_number, v_current_data, v_current_hash);
        
        RETURN QUERY SELECT FALSE, 'first_snapshot'::VARCHAR, v_current_data;
        RETURN;
    END IF;
    
    -- Check if data changed
    IF v_current_hash = v_previous_hash AND NOT p_check_all THEN
        RETURN QUERY SELECT FALSE, 'no_change'::VARCHAR, NULL::JSONB;
        RETURN;
    END IF;
    
    -- Detect specific changes
    IF (v_current_data->>'owner_name') != (v_previous_data->>'owner_name') THEN
        v_changes := v_changes || jsonb_build_object(
            'owner_changed', true,
            'previous_owner', v_previous_data->>'owner_name',
            'new_owner', v_current_data->>'owner_name'
        );
    END IF;
    
    IF (v_current_data->>'total_value')::NUMERIC != (v_previous_data->>'total_value')::NUMERIC THEN
        v_changes := v_changes || jsonb_build_object(
            'value_changed', true,
            'previous_value', (v_previous_data->>'total_value')::NUMERIC,
            'new_value', (v_current_data->>'total_value')::NUMERIC,
            'change_amount', (v_current_data->>'total_value')::NUMERIC - (v_previous_data->>'total_value')::NUMERIC,
            'change_percent', 
                CASE WHEN (v_previous_data->>'total_value')::NUMERIC > 0 
                THEN ((v_current_data->>'total_value')::NUMERIC - (v_previous_data->>'total_value')::NUMERIC) / (v_previous_data->>'total_value')::NUMERIC * 100
                ELSE NULL END
        );
    END IF;
    
    -- Record changes if any
    IF jsonb_typeof(v_changes) != 'null' AND v_changes != '{}'::JSONB THEN
        -- Insert into history
        INSERT INTO property_history (
            account_number,
            property_address,
            change_type,
            prev_owner_name,
            prev_total_value,
            prev_land_value,
            prev_building_value,
            new_owner_name,
            new_total_value,
            new_land_value,
            new_building_value,
            value_change_amount,
            value_change_percent
        ) VALUES (
            p_account_number,
            v_current_data->>'property_address',
            CASE 
                WHEN v_changes ? 'owner_changed' AND v_changes ? 'value_changed' THEN 'both'
                WHEN v_changes ? 'owner_changed' THEN 'owner_change'
                WHEN v_changes ? 'value_changed' THEN 'value_change'
                ELSE 'other'
            END,
            v_previous_data->>'owner_name',
            (v_previous_data->>'total_value')::NUMERIC,
            (v_previous_data->>'land_value')::NUMERIC,
            (v_previous_data->>'building_value')::NUMERIC,
            v_current_data->>'owner_name',
            (v_current_data->>'total_value')::NUMERIC,
            (v_current_data->>'land_value')::NUMERIC,
            (v_current_data->>'building_value')::NUMERIC,
            (v_changes->>'change_amount')::NUMERIC,
            (v_changes->>'change_percent')::NUMERIC
        );
        
        -- Update snapshot
        INSERT INTO property_snapshots (account_number, property_data, hash)
        VALUES (p_account_number, v_current_data, v_current_hash)
        ON CONFLICT (account_number, snapshot_date) 
        DO UPDATE SET property_data = v_current_data, hash = v_current_hash;
        
        RETURN QUERY SELECT TRUE, 
            CASE 
                WHEN v_changes ? 'owner_changed' AND v_changes ? 'value_changed' THEN 'both'
                WHEN v_changes ? 'owner_changed' THEN 'owner_change'
                WHEN v_changes ? 'value_changed' THEN 'value_change'
                ELSE 'other'
            END::VARCHAR, 
            v_changes;
    ELSE
        RETURN QUERY SELECT FALSE, 'no_significant_change'::VARCHAR, NULL::JSONB;
    END IF;
END;
$$ LANGUAGE plpgsql;

-- Grant permissions (adjust role as needed)
-- GRANT SELECT, INSERT, UPDATE ON property_history TO your_app_role;
-- GRANT SELECT, INSERT, UPDATE ON property_snapshots TO your_app_role;
-- GRANT SELECT ON recent_property_changes TO your_app_role;