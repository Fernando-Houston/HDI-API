"""Property change tracking service"""

import psycopg2
from psycopg2.extras import RealDictCursor, Json
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import structlog
import json

logger = structlog.get_logger(__name__)

class PropertyChangeTracker:
    """Track and analyze property changes over time"""
    
    def __init__(self, db_url: str):
        self.db_url = db_url
        self._ensure_tables_exist()
    
    def _ensure_tables_exist(self):
        """Ensure tracking tables exist in database"""
        try:
            with psycopg2.connect(self.db_url) as conn:
                with conn.cursor() as cur:
                    # Check if tables exist
                    cur.execute("""
                        SELECT EXISTS (
                            SELECT FROM information_schema.tables 
                            WHERE table_name = 'property_history'
                        )
                    """)
                    
                    if not cur.fetchone()[0]:
                        logger.warning("Property tracking tables don't exist. Please run create_tracking_tables.sql")
        except Exception as e:
            logger.error(f"Error checking tracking tables: {str(e)}")
    
    def track_property(self, account_number: str) -> Dict:
        """Track changes for a specific property"""
        try:
            with psycopg2.connect(self.db_url) as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    # Call the tracking function
                    cur.execute(
                        "SELECT * FROM track_property_changes(%s, FALSE)",
                        (account_number,)
                    )
                    
                    result = cur.fetchone()
                    
                    if result:
                        change_data = {
                            'change_detected': result['change_detected'],
                            'change_type': result['change_type'],
                            'details': result['details'] if result['details'] else {}
                        }
                        
                        logger.info("Property tracked", 
                                   account_number=account_number,
                                   change_detected=result['change_detected'])
                        
                        return change_data
                    
                    return {'change_detected': False, 'change_type': 'error'}
                    
        except Exception as e:
            logger.error(f"Error tracking property: {str(e)}")
            return {'change_detected': False, 'change_type': 'error', 'error': str(e)}
    
    def get_property_history(self, account_number: str, days: int = 90) -> List[Dict]:
        """Get change history for a property"""
        try:
            with psycopg2.connect(self.db_url) as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute("""
                        SELECT 
                            change_date,
                            change_type,
                            prev_owner_name,
                            new_owner_name,
                            prev_total_value,
                            new_total_value,
                            value_change_amount,
                            value_change_percent
                        FROM property_history
                        WHERE account_number = %s
                        AND change_date > CURRENT_DATE - INTERVAL '%s days'
                        ORDER BY change_date DESC
                    """, (account_number, days))
                    
                    return [dict(row) for row in cur.fetchall()]
                    
        except Exception as e:
            logger.error(f"Error getting property history: {str(e)}")
            return []
    
    def get_recent_changes(self, 
                          change_type: Optional[str] = None,
                          days: int = 7,
                          limit: int = 100) -> List[Dict]:
        """Get recent property changes across all properties"""
        try:
            with psycopg2.connect(self.db_url) as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    query = """
                        SELECT * FROM recent_property_changes
                        WHERE change_date > CURRENT_DATE - INTERVAL '%s days'
                    """
                    params = [days]
                    
                    if change_type:
                        query += " AND change_type = %s"
                        params.append(change_type)
                    
                    query += " ORDER BY change_date DESC LIMIT %s"
                    params.append(limit)
                    
                    cur.execute(query, params)
                    
                    return [dict(row) for row in cur.fetchall()]
                    
        except Exception as e:
            logger.error(f"Error getting recent changes: {str(e)}")
            return []
    
    def track_multiple_properties(self, account_numbers: List[str]) -> Dict:
        """Track changes for multiple properties"""
        results = {
            'total': len(account_numbers),
            'changes_detected': 0,
            'errors': 0,
            'details': []
        }
        
        for account_number in account_numbers:
            result = self.track_property(account_number)
            
            if result.get('change_detected'):
                results['changes_detected'] += 1
                results['details'].append({
                    'account_number': account_number,
                    'change_type': result['change_type'],
                    'details': result.get('details', {})
                })
            elif result.get('change_type') == 'error':
                results['errors'] += 1
        
        return results
    
    def get_market_trends(self, days: int = 30) -> Dict:
        """Analyze market trends from property changes"""
        try:
            with psycopg2.connect(self.db_url) as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    # Get value change statistics
                    cur.execute("""
                        SELECT 
                            COUNT(*) as total_changes,
                            COUNT(CASE WHEN value_change_amount > 0 THEN 1 END) as increases,
                            COUNT(CASE WHEN value_change_amount < 0 THEN 1 END) as decreases,
                            AVG(value_change_percent) as avg_change_percent,
                            MAX(value_change_percent) as max_increase_percent,
                            MIN(value_change_percent) as max_decrease_percent,
                            SUM(value_change_amount) as total_value_change
                        FROM property_history
                        WHERE change_date > CURRENT_DATE - INTERVAL '%s days'
                        AND change_type IN ('value_change', 'both')
                    """, (days,))
                    
                    value_stats = dict(cur.fetchone())
                    
                    # Get ownership change statistics
                    cur.execute("""
                        SELECT 
                            COUNT(*) as ownership_changes,
                            COUNT(DISTINCT prev_owner_name) as unique_sellers,
                            COUNT(DISTINCT new_owner_name) as unique_buyers
                        FROM property_history
                        WHERE change_date > CURRENT_DATE - INTERVAL '%s days'
                        AND change_type IN ('owner_change', 'both')
                    """, (days,))
                    
                    ownership_stats = dict(cur.fetchone())
                    
                    return {
                        'period_days': days,
                        'value_trends': value_stats,
                        'ownership_trends': ownership_stats,
                        'market_direction': 'up' if value_stats.get('avg_change_percent', 0) > 0 else 'down',
                        'activity_level': 'high' if value_stats.get('total_changes', 0) > 100 else 'normal'
                    }
                    
        except Exception as e:
            logger.error(f"Error analyzing market trends: {str(e)}")
            return {}
    
    def find_flipped_properties(self, days: int = 180, min_profit: float = 50000) -> List[Dict]:
        """Find properties that were bought and sold quickly for profit"""
        try:
            with psycopg2.connect(self.db_url) as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute("""
                        WITH property_sales AS (
                            SELECT 
                                account_number,
                                property_address,
                                change_date,
                                new_owner_name as buyer,
                                new_total_value as purchase_price,
                                LAG(new_total_value) OVER (PARTITION BY account_number ORDER BY change_date) as prev_sale_price,
                                LAG(change_date) OVER (PARTITION BY account_number ORDER BY change_date) as prev_sale_date
                            FROM property_history
                            WHERE change_type IN ('owner_change', 'both')
                        )
                        SELECT 
                            account_number,
                            property_address,
                            buyer,
                            purchase_price,
                            prev_sale_price,
                            purchase_price - prev_sale_price as profit,
                            change_date - prev_sale_date as days_held,
                            ((purchase_price - prev_sale_price) / prev_sale_price * 100) as profit_percent
                        FROM property_sales
                        WHERE prev_sale_price IS NOT NULL
                        AND change_date - prev_sale_date < %s
                        AND purchase_price - prev_sale_price > %s
                        ORDER BY profit DESC
                        LIMIT 20
                    """, (days, min_profit))
                    
                    return [dict(row) for row in cur.fetchall()]
                    
        except Exception as e:
            logger.error(f"Error finding flipped properties: {str(e)}")
            return []


# API endpoint helpers
def add_change_tracking_to_property(property_data: Dict, db_url: str) -> Dict:
    """Add change tracking data to property response"""
    tracker = PropertyChangeTracker(db_url)
    
    # Get recent history
    account_number = property_data.get('account_number')
    if account_number:
        history = tracker.get_property_history(account_number, days=90)
        
        if history:
            property_data['change_history'] = {
                'has_changes': True,
                'change_count': len(history),
                'latest_change': history[0] if history else None,
                'history': history[:5]  # Last 5 changes
            }
        else:
            property_data['change_history'] = {
                'has_changes': False,
                'change_count': 0
            }
    
    return property_data