"""Geometry utilities for property analysis"""

from shapely import wkt
from shapely.geometry import Polygon, Point
from typing import Dict, Optional, Tuple, List
import math

def calculate_geometry_fields(property_data: Dict) -> Dict:
    """Calculate additional fields from geometry data"""
    geometry_data = property_data.get('geometry', {})
    wkt_string = geometry_data.get('wkt')
    
    if not wkt_string:
        return property_data
    
    try:
        # Parse WKT to shapely geometry
        shape = wkt.loads(wkt_string)
        
        # Calculate area in square feet
        if isinstance(shape, Polygon):
            # Project to local coordinate system for accurate area
            # Using simple approximation for Houston area
            lat = geometry_data.get('centroid', {}).get('lat', 29.7604)
            
            # Convert to feet (approximation for Houston latitude)
            lat_to_feet = 364000  # feet per degree latitude
            lon_to_feet = 364000 * math.cos(math.radians(lat))
            
            # Calculate area
            coords = list(shape.exterior.coords)
            area_sqft = calculate_polygon_area(coords, lat_to_feet, lon_to_feet)
            
            # Calculate perimeter
            perimeter_ft = calculate_polygon_perimeter(coords, lat_to_feet, lon_to_feet)
            
            # Determine if corner lot
            is_corner = detect_corner_lot(shape, property_data.get('property_address', ''))
            
            # Calculate lot dimensions (approximate)
            dimensions = estimate_lot_dimensions(shape, area_sqft)
            
            # Add calculated fields
            property_data['geometry_analysis'] = {
                'calculated_area_sqft': round(area_sqft, 2),
                'calculated_perimeter_ft': round(perimeter_ft, 2),
                'is_corner_lot': is_corner,
                'estimated_dimensions': dimensions,
                'shape_type': 'polygon',
                'vertex_count': len(coords) - 1,  # Minus 1 because first/last are same
                'regularity_score': calculate_regularity(shape)
            }
            
            # Compare with recorded area if available
            if property_data.get('land_sqft', 0) > 0:
                area_diff = abs(area_sqft - property_data['land_sqft'])
                property_data['geometry_analysis']['area_accuracy'] = {
                    'recorded_sqft': property_data['land_sqft'],
                    'calculated_sqft': area_sqft,
                    'difference_sqft': area_diff,
                    'difference_percent': (area_diff / property_data['land_sqft']) * 100
                }
        
    except Exception as e:
        property_data['geometry_analysis'] = {
            'error': f"Failed to analyze geometry: {str(e)}"
        }
    
    return property_data

def calculate_polygon_area(coords: List[Tuple[float, float]], 
                          lat_scale: float, lon_scale: float) -> float:
    """Calculate area of polygon using shoelace formula"""
    area = 0.0
    n = len(coords)
    
    for i in range(n - 1):
        lon1, lat1 = coords[i]
        lon2, lat2 = coords[i + 1]
        
        # Convert to feet
        x1 = lon1 * lon_scale
        y1 = lat1 * lat_scale
        x2 = lon2 * lon_scale
        y2 = lat2 * lat_scale
        
        area += (x1 * y2 - x2 * y1)
    
    return abs(area) / 2.0

def calculate_polygon_perimeter(coords: List[Tuple[float, float]], 
                               lat_scale: float, lon_scale: float) -> float:
    """Calculate perimeter of polygon"""
    perimeter = 0.0
    n = len(coords)
    
    for i in range(n - 1):
        lon1, lat1 = coords[i]
        lon2, lat2 = coords[i + 1]
        
        # Convert to feet
        x1 = lon1 * lon_scale
        y1 = lat1 * lat_scale
        x2 = lon2 * lon_scale
        y2 = lat2 * lat_scale
        
        # Distance
        dist = math.sqrt((x2 - x1)**2 + (y2 - y1)**2)
        perimeter += dist
    
    return perimeter

def detect_corner_lot(shape: Polygon, address: str) -> bool:
    """Detect if property is a corner lot based on shape and address"""
    # Simple heuristic: corner lots often have more vertices or irregular shapes
    coords = list(shape.exterior.coords)
    
    # Check if address contains common corner indicators
    corner_indicators = ['CORNER', 'COR ', ' & ', ' AND ']
    address_upper = address.upper()
    
    for indicator in corner_indicators:
        if indicator in address_upper:
            return True
    
    # Check shape characteristics
    if len(coords) > 6:  # More complex shape
        return True
    
    # Check regularity - corner lots are often less regular
    regularity = calculate_regularity(shape)
    if regularity < 0.7:
        return True
    
    return False

def calculate_regularity(shape: Polygon) -> float:
    """Calculate how regular/rectangular the shape is (0-1)"""
    # Compare to minimum bounding rectangle
    min_rect = shape.minimum_rotated_rectangle
    
    if min_rect.area > 0:
        regularity = shape.area / min_rect.area
        return min(1.0, regularity)
    
    return 0.0

def estimate_lot_dimensions(shape: Polygon, area_sqft: float) -> Dict:
    """Estimate approximate lot dimensions"""
    # Get minimum bounding rectangle
    min_rect = shape.minimum_rotated_rectangle
    
    if isinstance(min_rect, Polygon):
        coords = list(min_rect.exterior.coords)
        if len(coords) >= 4:
            # Calculate sides
            side1 = math.sqrt((coords[1][0] - coords[0][0])**2 + 
                             (coords[1][1] - coords[0][1])**2)
            side2 = math.sqrt((coords[2][0] - coords[1][0])**2 + 
                             (coords[2][1] - coords[1][1])**2)
            
            # Convert to feet (rough approximation)
            width_ft = min(side1, side2) * 364000
            depth_ft = max(side1, side2) * 364000
            
            return {
                'width_ft': round(width_ft, 1),
                'depth_ft': round(depth_ft, 1),
                'width_to_depth_ratio': round(width_ft / depth_ft, 2) if depth_ft > 0 else 0
            }
    
    # Fallback: estimate as square
    side = math.sqrt(area_sqft)
    return {
        'width_ft': round(side, 1),
        'depth_ft': round(side, 1),
        'width_to_depth_ratio': 1.0
    }

def find_property_orientation(shape: Polygon) -> float:
    """Find the orientation angle of the property"""
    min_rect = shape.minimum_rotated_rectangle
    
    if isinstance(min_rect, Polygon):
        coords = list(min_rect.exterior.coords)
        if len(coords) >= 2:
            # Calculate angle of first edge
            dx = coords[1][0] - coords[0][0]
            dy = coords[1][1] - coords[0][1]
            angle = math.degrees(math.atan2(dy, dx))
            
            # Normalize to 0-180 degrees
            if angle < 0:
                angle += 180
            if angle > 90:
                angle -= 90
                
            return round(angle, 1)
    
    return 0.0

# Helper function to enhance property data
def enhance_with_geometry_analysis(property_data: Dict) -> Dict:
    """Add geometry analysis to property data if geometry exists"""
    if property_data.get('geometry', {}).get('wkt'):
        return calculate_geometry_fields(property_data)
    return property_data