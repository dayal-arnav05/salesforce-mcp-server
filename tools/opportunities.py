from fastmcp import FastMCP
from typing import Callable, List, Optional
from client import SalesforceClient
import json
from datetime import datetime, timedelta
from enum import Enum

class DateRange(Enum):
    """Date range options for filtering"""
    THIS_WEEK = "this_week"
    LAST_WEEK = "last_week"
    THIS_MONTH = "this_month" 
    LAST_MONTH = "last_month"
    THIS_QUARTER = "this_quarter"
    LAST_QUARTER = "last_quarter"
    THIS_YEAR = "this_year"
    LAST_YEAR = "last_year"

def get_date_range(range_type: DateRange) -> tuple[str, str]:
    """Convert relative date ranges to ISO format"""
    now = datetime.now()
    
    if range_type == DateRange.THIS_WEEK:
        start = now - timedelta(days=now.weekday())
        end = start + timedelta(days=6)
    elif range_type == DateRange.LAST_WEEK:
        start = now - timedelta(days=now.weekday() + 7)
        end = start + timedelta(days=6)
    elif range_type == DateRange.THIS_MONTH:
        start = now.replace(day=1)
        end = (start + timedelta(days=32)).replace(day=1) - timedelta(days=1)
    elif range_type == DateRange.LAST_MONTH:
        start = (now.replace(day=1) - timedelta(days=1)).replace(day=1)
        end = now.replace(day=1) - timedelta(days=1)
    elif range_type == DateRange.THIS_QUARTER:
        quarter = (now.month - 1) // 3 + 1
        start = now.replace(month=(quarter - 1) * 3 + 1, day=1)
        end = (start + timedelta(days=95)).replace(day=1) - timedelta(days=1)
    elif range_type == DateRange.LAST_QUARTER:
        quarter = (now.month - 1) // 3
        if quarter == 0:
            quarter = 4
            start = now.replace(year=now.year - 1, month=10, day=1)
        else:
            start = now.replace(month=(quarter - 1) * 3 + 1, day=1)
        end = (start + timedelta(days=95)).replace(day=1) - timedelta(days=1)
    elif range_type == DateRange.THIS_YEAR:
        start = now.replace(month=1, day=1)
        end = now.replace(month=12, day=31)
    elif range_type == DateRange.LAST_YEAR:
        start = now.replace(year=now.year - 1, month=1, day=1)
        end = now.replace(year=now.year - 1, month=12, day=31)
    else:
        raise ValueError(f"Unsupported date range: {range_type}")
    
    return start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d")

def setup_opportunity_tools(mcp: FastMCP, get_salesforce_client: Callable[[], SalesforceClient]):
    @mcp.tool()
    async def get_opportunity(opportunity_id: str):
        """Get detailed opportunity by ID."""
        client = get_salesforce_client()
        return await client.get_opportunity(opportunity_id)

    @mcp.tool()
    async def search_opportunities(stage: str = "", min_amount: float = None, limit: int = 10):
        """Search opportunities by stage and amount."""
        client = get_salesforce_client()
        stage_filter = stage if stage else None
        return await client.search_opportunities(stage_filter, min_amount, limit)

    @mcp.tool()
    async def get_recent_opportunities(limit: int = 5):
        """Get recent opportunities."""
        client = get_salesforce_client()
        return await client.get_recent_opportunities(limit)

    @mcp.tool()
    async def query_opportunities(time_period: str = "last_quarter", stage: str = "", min_amount: float = None, limit: int = 50):
        """
        Query Salesforce opportunities (deals) with advanced filtering options.
        
        Args:
            time_period: Time range to query (this_week, last_week, this_month, last_month, this_quarter, last_quarter, this_year, last_year)
            stage: Filter by opportunity stage (e.g., 'Closed Won', 'Negotiation')
            min_amount: Minimum deal amount to include
            limit: Maximum number of results (up to 100)
        
        Returns:
            JSON string with opportunity data including account information, amounts, stages, and probabilities
        """
        client = get_salesforce_client()
        
        # Build dynamic WHERE conditions
        conditions = []
        
        # Add date range condition
        if time_period:
            try:
                date_range = DateRange(time_period.lower().replace(" ", "_"))
                start_date, end_date = get_date_range(date_range)
                conditions.append(f'CloseDate: {{ range: {{ gte: "{start_date}", lte: "{end_date}" }} }}')
            except ValueError:
                return {
                    "error": f"Invalid time period: {time_period}",
                    "valid_options": [range_type.value for range_type in DateRange]
                }
        
        if stage:
            conditions.append(f'StageName: {{ eq: "{stage}" }}')
        
        if min_amount is not None:
            conditions.append(f'Amount: {{ range: {{ gte: {min_amount} }} }}')
        
        where_clause = f"where: {{ {', '.join(conditions)} }}" if conditions else ""
        
        # Static template with dynamic WHERE clause
        query = f"""
        query GetOpportunities {{
            uiapi {{
                query {{
                    Opportunity(
                        {where_clause}
                        first: {limit}
                        orderBy: {{ CloseDate: {{ order: DESC }} }}
                    ) {{
                        edges {{
                            node {{
                                Id
                                Name {{ value }}
                                Amount {{ value displayValue }}
                                CloseDate {{ value }}
                                StageName {{ value }}
                                Probability {{ value }}
                                Account {{
                                    Id
                                    Name {{ value }}
                                }}
                                Owner {{
                                    Id
                                    Name {{ value }}
                                }}
                            }}
                        }}
                        totalCount
                        pageInfo {{
                            hasNextPage
                            endCursor
                        }}
                    }}
                }}
            }}
        }}
        """
        
        try:
            result = await client.execute_query(query)
            
            # Process results
            edges = result.get("data", {}).get("uiapi", {}).get("query", {}).get("Opportunity", {}).get("edges", [])
            total_count = result.get("data", {}).get("uiapi", {}).get("query", {}).get("Opportunity", {}).get("totalCount", 0)
            
            opportunities = []
            total_value = 0
            
            for edge in edges:
                node = edge.get("node", {})
                amount = node.get("Amount", {}).get("value", 0) or 0
                
                opp = {
                    "id": node.get("Id"),
                    "name": node.get("Name", {}).get("value", ""),
                    "amount": amount,
                    "amount_display": node.get("Amount", {}).get("displayValue", ""),
                    "close_date": node.get("CloseDate", {}).get("value", ""),
                    "stage": node.get("StageName", {}).get("value", ""),
                    "probability": node.get("Probability", {}).get("value", 0),
                    "account": {
                        "id": node.get("Account", {}).get("Id"),
                        "name": node.get("Account", {}).get("Name", {}).get("value", "")
                    },
                    "owner": {
                        "id": node.get("Owner", {}).get("Id"),
                        "name": node.get("Owner", {}).get("Name", {}).get("value", "")
                    }
                }
                
                opportunities.append(opp)
                total_value += amount
            
            return {
                "success": True,
                "summary": {
                    "total_opportunities": len(opportunities),
                    "total_count_in_org": total_count,
                    "total_value": total_value,
                    "average_deal_size": total_value / len(opportunities) if opportunities else 0,
                    "filters_applied": {
                        "time_period": time_period,
                        "stage": stage,
                        "min_amount": min_amount,
                        "limit": limit
                    }
                },
                "opportunities": opportunities,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__
            }

    @mcp.tool()
    async def analyze_opportunity_trends(limit: int = 20):
        """Analyze trends across recent opportunities including deal patterns and stages."""
        client = get_salesforce_client()
        opportunities = await client.get_recent_opportunities(limit)
        
        if not opportunities:
            return {"message": "No opportunities found"}
        
        analysis = {
            "total_opportunities": len(opportunities),
            "deal_patterns": {},
            "stage_distribution": {},
            "amount_analysis": {},
            "probability_analysis": {}
        }
        
        amounts = []
        probabilities = []
        stages = []
        
        for opp in opportunities:
            # Amount analysis
            if hasattr(opp, 'Amount') and opp.Amount and opp.Amount.get('value'):
                amounts.append(float(opp.Amount['value']))
            
            # Probability analysis
            if hasattr(opp, 'Probability') and opp.Probability and opp.Probability.get('value'):
                probabilities.append(float(opp.Probability['value']))
            
            # Stage analysis
            if hasattr(opp, 'StageName') and opp.StageName and opp.StageName.get('value'):
                stages.append(opp.StageName['value'])
        
        # Amount statistics
        if amounts:
            analysis["amount_analysis"] = {
                "average_amount": round(sum(amounts) / len(amounts), 2),
                "min_amount": min(amounts),
                "max_amount": max(amounts),
                "total_pipeline": round(sum(amounts), 2)
            }
        
        # Probability statistics
        if probabilities:
            analysis["probability_analysis"] = {
                "average_probability": round(sum(probabilities) / len(probabilities), 2),
                "min_probability": min(probabilities),
                "max_probability": max(probabilities)
            }
        
        # Stage distribution
        if stages:
            from collections import Counter
            stage_counts = Counter(stages)
            analysis["stage_distribution"] = dict(stage_counts)
        
        return analysis

    @mcp.tool()
    async def find_opportunities_by_stage(stage: str, limit: int = 10):
        """Find opportunities in a specific stage."""
        client = get_salesforce_client()
        opportunities = await client.search_opportunities(stage=stage, limit=limit)
        
        return {
            "stage": stage,
            "opportunities_found": len(opportunities),
            "opportunities": [
                {
                    "id": getattr(opp, 'Id', 'Unknown'),
                    "name": getattr(opp, 'Name', {}).get('value', 'Unknown') if hasattr(opp, 'Name') else 'Unknown',
                    "amount": getattr(opp, 'Amount', {}).get('displayValue', 'Unknown') if hasattr(opp, 'Amount') else 'Unknown',
                    "close_date": getattr(opp, 'CloseDate', {}).get('value', 'Unknown') if hasattr(opp, 'CloseDate') else 'Unknown',
                    "probability": getattr(opp, 'Probability', {}).get('value', 0) if hasattr(opp, 'Probability') else 0
                }
                for opp in opportunities
            ]
        }