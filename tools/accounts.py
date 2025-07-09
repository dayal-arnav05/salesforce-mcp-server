from fastmcp import FastMCP
from typing import Callable, List, Optional
from client import SalesforceClient
import json
from datetime import datetime

def setup_account_tools(mcp: FastMCP, get_salesforce_client: Callable[[], SalesforceClient]):
    
    @mcp.tool()
    async def get_account(account_id: str):
        """Get detailed account by ID."""
        client = get_salesforce_client()
        return await client.get_account(account_id)

    @mcp.tool()
    async def search_accounts(industry: str = "", limit: int = 10):
        """Search accounts by industry."""
        client = get_salesforce_client()
        industry_filter = industry if industry else None
        return await client.search_accounts(industry_filter, limit)

    @mcp.tool()
    async def get_recent_accounts(limit: int = 5):
        """Get recent accounts."""
        client = get_salesforce_client()
        return await client.get_recent_accounts(limit)

    @mcp.tool()
    async def query_accounts(limit: int = 50, industry: str = ""):
        """
        Query Salesforce accounts with optional industry filtering.
        
        Args:
            limit: Maximum number of accounts to return (up to 100)
            industry: Filter by industry type
        
        Returns:
            JSON string with account information including name, type, industry, revenue, and contact details
        """
        client = get_salesforce_client()
        
        # Build WHERE clause
        where_clause = ""
        if industry:
            where_clause = f'where: {{ Industry: {{ eq: "{industry}" }} }}'
        
        # Static template with dynamic WHERE clause
        query = f"""
        query GetAccounts {{
            uiapi {{
                query {{
                    Account(
                        {where_clause}
                        first: {limit}
                        orderBy: {{ Name: {{ order: ASC }} }}
                    ) {{
                        edges {{
                            node {{
                                Id
                                Name {{ value }}
                                Type {{ value }}
                                Industry {{ value }}
                                AnnualRevenue {{ value displayValue }}
                                NumberOfEmployees {{ value }}
                                Phone {{ value }}
                                Website {{ value }}
                                BillingAddress {{
                                    BillingCity {{ value }}
                                    BillingState {{ value }}
                                    BillingCountry {{ value }}
                                }}
                            }}
                        }}
                        totalCount
                    }}
                }}
            }}
        }}
        """
        
        try:
            result = await client.execute_query(query)
            
            # Process results
            edges = result.get("data", {}).get("uiapi", {}).get("query", {}).get("Account", {}).get("edges", [])
            total_count = result.get("data", {}).get("uiapi", {}).get("query", {}).get("Account", {}).get("totalCount", 0)
            
            accounts = []
            
            for edge in edges:
                node = edge.get("node", {})
                billing_address = node.get("BillingAddress", {})
                
                account = {
                    "id": node.get("Id"),
                    "name": node.get("Name", {}).get("value", ""),
                    "type": node.get("Type", {}).get("value", ""),
                    "industry": node.get("Industry", {}).get("value", ""),
                    "annual_revenue": node.get("AnnualRevenue", {}).get("value"),
                    "annual_revenue_display": node.get("AnnualRevenue", {}).get("displayValue", ""),
                    "employees": node.get("NumberOfEmployees", {}).get("value"),
                    "phone": node.get("Phone", {}).get("value", ""),
                    "website": node.get("Website", {}).get("value", ""),
                    "billing_address": {
                        "city": billing_address.get("BillingCity", {}).get("value", ""),
                        "state": billing_address.get("BillingState", {}).get("value", ""),
                        "country": billing_address.get("BillingCountry", {}).get("value", "")
                    }
                }
                
                accounts.append(account)
            
            return {
                "success": True,
                "summary": {
                    "total_accounts": len(accounts),
                    "total_count_in_org": total_count,
                    "filter_applied": {"industry": industry} if industry else None
                },
                "accounts": accounts,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__
            }

    @mcp.tool()
    async def get_account_statistics(limit: int = 20):
        """Get statistics about accounts including industry distribution, revenue analysis, etc."""
        client = get_salesforce_client()
        accounts = await client.get_recent_accounts(limit)
        
        if not accounts:
            return {"message": "No accounts found"}
        
        total_accounts = len(accounts)
        industries = []
        revenues = []
        employee_counts = []
        
        for account in accounts:
            if hasattr(account, 'Industry') and account.Industry and account.Industry.get('value'):
                industries.append(account.Industry['value'])
            if hasattr(account, 'AnnualRevenue') and account.AnnualRevenue and account.AnnualRevenue.get('value'):
                revenues.append(float(account.AnnualRevenue['value']))
            if hasattr(account, 'NumberOfEmployees') and account.NumberOfEmployees and account.NumberOfEmployees.get('value'):
                employee_counts.append(int(account.NumberOfEmployees['value']))
        
        # Industry distribution
        industry_distribution = {}
        if industries:
            from collections import Counter
            industry_counts = Counter(industries)
            industry_distribution = dict(industry_counts)
        
        # Revenue analysis
        revenue_analysis = {}
        if revenues:
            revenue_analysis = {
                "average_revenue": round(sum(revenues) / len(revenues), 2),
                "min_revenue": min(revenues),
                "max_revenue": max(revenues),
                "total_revenue": round(sum(revenues), 2)
            }
        
        # Employee analysis
        employee_analysis = {}
        if employee_counts:
            employee_analysis = {
                "average_employees": round(sum(employee_counts) / len(employee_counts), 1),
                "min_employees": min(employee_counts),
                "max_employees": max(employee_counts)
            }
        
        return {
            "total_accounts": total_accounts,
            "industry_distribution": industry_distribution,
            "revenue_analysis": revenue_analysis,
            "employee_analysis": employee_analysis
        }

    @mcp.tool()
    async def find_accounts_by_industry(industry: str, limit: int = 10):
        """Find accounts in a specific industry."""
        client = get_salesforce_client()
        accounts = await client.search_accounts(industry=industry, limit=limit)
        
        return {
            "industry": industry,
            "accounts_found": len(accounts),
            "accounts": [
                {
                    "id": getattr(account, 'Id', 'Unknown'),
                    "name": getattr(account, 'Name', {}).get('value', 'Unknown') if hasattr(account, 'Name') else 'Unknown',
                    "type": getattr(account, 'Type', {}).get('value', 'Unknown') if hasattr(account, 'Type') else 'Unknown',
                    "revenue": getattr(account, 'AnnualRevenue', {}).get('displayValue', 'Unknown') if hasattr(account, 'AnnualRevenue') else 'Unknown',
                    "employees": getattr(account, 'NumberOfEmployees', {}).get('value', 'Unknown') if hasattr(account, 'NumberOfEmployees') else 'Unknown',
                    "website": getattr(account, 'Website', {}).get('value', 'Unknown') if hasattr(account, 'Website') else 'Unknown'
                }
                for account in accounts
            ]
        }

    @mcp.tool()
    async def analyze_account_trends(limit: int = 20):
        """Analyze trends across recent accounts including industry patterns and revenue distribution."""
        client = get_salesforce_client()
        accounts = await client.get_recent_accounts(limit)
        
        if not accounts:
            return {"message": "No accounts found"}
        
        analysis = {
            "total_accounts": len(accounts),
            "industry_patterns": {},
            "revenue_distribution": {},
            "size_analysis": {},
            "geographic_distribution": {}
        }
        
        industries = []
        revenues = []
        employee_counts = []
        locations = []
        
        for account in accounts:
            # Industry analysis
            if hasattr(account, 'Industry') and account.Industry and account.Industry.get('value'):
                industries.append(account.Industry['value'])
            
            # Revenue analysis
            if hasattr(account, 'AnnualRevenue') and account.AnnualRevenue and account.AnnualRevenue.get('value'):
                revenues.append(float(account.AnnualRevenue['value']))
            
            # Size analysis
            if hasattr(account, 'NumberOfEmployees') and account.NumberOfEmployees and account.NumberOfEmployees.get('value'):
                employee_counts.append(int(account.NumberOfEmployees['value']))
            
            # Geographic analysis
            if hasattr(account, 'BillingAddress') and account.BillingAddress:
                country = account.BillingAddress.get('BillingCountry', {}).get('value', '')
                if country:
                    locations.append(country)
        
        # Industry patterns
        if industries:
            from collections import Counter
            industry_counts = Counter(industries)
            analysis["industry_patterns"] = dict(industry_counts)
        
        # Revenue distribution
        if revenues:
            analysis["revenue_distribution"] = {
                "average_revenue": round(sum(revenues) / len(revenues), 2),
                "median_revenue": round(sorted(revenues)[len(revenues)//2], 2),
                "total_revenue": round(sum(revenues), 2),
                "revenue_ranges": {
                    "under_1M": len([r for r in revenues if r < 1000000]),
                    "1M_10M": len([r for r in revenues if 1000000 <= r < 10000000]),
                    "10M_100M": len([r for r in revenues if 10000000 <= r < 100000000]),
                    "over_100M": len([r for r in revenues if r >= 100000000])
                }
            }
        
        # Size analysis
        if employee_counts:
            analysis["size_analysis"] = {
                "average_employees": round(sum(employee_counts) / len(employee_counts), 1),
                "median_employees": sorted(employee_counts)[len(employee_counts)//2],
                "size_ranges": {
                    "small_1_50": len([e for e in employee_counts if e < 50]),
                    "medium_50_500": len([e for e in employee_counts if 50 <= e < 500]),
                    "large_500_5000": len([e for e in employee_counts if 500 <= e < 5000]),
                    "enterprise_5000+": len([e for e in employee_counts if e >= 5000])
                }
            }
        
        # Geographic distribution
        if locations:
            from collections import Counter
            location_counts = Counter(locations)
            analysis["geographic_distribution"] = dict(location_counts)
        
        return analysis