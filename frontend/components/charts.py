"""Chart components for HDI Dashboard"""

import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from typing import List, Dict, Any
import streamlit as st

def create_property_value_chart(properties: List[Dict[str, Any]]) -> go.Figure:
    """Create property value comparison chart"""
    if not properties:
        return go.Figure()
    
    addresses = [prop.get('address', f'Property {i+1}') for i, prop in enumerate(properties)]
    values = [prop.get('estimated_value', 0) for prop in properties]
    
    fig = px.bar(
        x=addresses,
        y=values,
        title="Property Value Comparison",
        labels={'x': 'Property', 'y': 'Estimated Value ($)'}
    )
    
    fig.update_layout(
        xaxis_tickangle=-45,
        height=400
    )
    
    return fig

def create_permit_timeline(permits: List[Dict[str, Any]]) -> go.Figure:
    """Create permit activity timeline"""
    if not permits:
        return go.Figure()
    
    df = pd.DataFrame(permits)
    
    if 'issue_date' not in df.columns:
        return go.Figure()
    
    # Convert date and group by month
    df['issue_date'] = pd.to_datetime(df['issue_date'])
    df['month'] = df['issue_date'].dt.to_period('M')
    
    monthly_permits = df.groupby('month').agg({
        'permit_number': 'count',
        'estimated_cost': 'sum'
    }).reset_index()
    
    monthly_permits['month'] = monthly_permits['month'].astype(str)
    
    fig = go.Figure()
    
    # Add permit count
    fig.add_trace(go.Scatter(
        x=monthly_permits['month'],
        y=monthly_permits['permit_number'],
        mode='lines+markers',
        name='Permit Count',
        yaxis='y'
    ))
    
    # Add total value on secondary axis
    fig.add_trace(go.Scatter(
        x=monthly_permits['month'],
        y=monthly_permits['estimated_cost'],
        mode='lines+markers',
        name='Total Value ($)',
        yaxis='y2',
        line=dict(color='red')
    ))
    
    fig.update_layout(
        title='Permit Activity Over Time',
        xaxis=dict(title='Month'),
        yaxis=dict(title='Number of Permits', side='left'),
        yaxis2=dict(title='Total Value ($)', side='right', overlaying='y'),
        height=400
    )
    
    return fig

def create_opportunity_scatter(opportunities: List[Dict[str, Any]]) -> go.Figure:
    """Create opportunity score vs price scatter plot"""
    if not opportunities:
        return go.Figure()
    
    scores = [opp.get('match_score', 0) for opp in opportunities]
    prices = [opp.get('estimated_price', 0) for opp in opportunities]
    addresses = [opp.get('address', f'Property {i+1}') for i, opp in enumerate(opportunities)]
    
    fig = px.scatter(
        x=prices,
        y=scores,
        hover_name=addresses,
        title="Investment Opportunities: Score vs Price",
        labels={'x': 'Estimated Price ($)', 'y': 'Match Score'}
    )
    
    fig.update_layout(height=400)
    
    return fig

def create_neighborhood_metrics(neighborhood_data: Dict[str, Any]) -> go.Figure:
    """Create neighborhood metrics radar chart"""
    categories = list(neighborhood_data.keys())
    values = list(neighborhood_data.values())
    
    fig = go.Figure()
    
    fig.add_trace(go.Scatterpolar(
        r=values,
        theta=categories,
        fill='toself',
        name='Neighborhood Score'
    ))
    
    fig.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[0, 10]
            )),
        showlegend=False,
        title="Neighborhood Metrics",
        height=400
    )
    
    return fig

def create_cost_breakdown_pie(cost_data: Dict[str, float]) -> go.Figure:
    """Create cost breakdown pie chart"""
    if not cost_data:
        return go.Figure()
    
    fig = px.pie(
        values=list(cost_data.values()),
        names=list(cost_data.keys()),
        title="Platform Cost Breakdown"
    )
    
    fig.update_layout(height=400)
    
    return fig

def create_usage_trends(usage_data: List[Dict[str, Any]]) -> go.Figure:
    """Create usage trends line chart"""
    if not usage_data:
        return go.Figure()
    
    df = pd.DataFrame(usage_data)
    
    fig = px.line(
        df,
        x='date',
        y='queries',
        title="Daily Query Volume",
        labels={'queries': 'Number of Queries', 'date': 'Date'}
    )
    
    fig.update_layout(height=400)
    
    return fig