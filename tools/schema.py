from fastmcp import FastMCP
from typing import Callable, List, Optional
from client import SalesforceClient
import json
from datetime import datetime

def setup_schema_tools(mcp: FastMCP, get_salesforce_client: Callable[[], SalesforceClient]):
    
    @mcp.tool()
    async def execute_custom_graphql(query: str):
        """
        Execute a custom GraphQL query against Salesforce.
        
        Args:
            query: Raw GraphQL query to execute against Salesforce
        
        Returns:
            JSON string with query results. Query should follow Salesforce GraphQL schema conventions and include the 'uiapi' wrapper.
        """
        client = get_salesforce_client()
        
        # Clean up the query string
        clean_query = query.strip()
        
        # Validate query has basic structure
        if "uiapi" not in clean_query.lower():
            return {
                "success": False,
                "error": "Query must include 'uiapi' field",
                "hint": "Start your query with: query { uiapi { ... } }",
                "received_query": clean_query[:100] + "..." if len(clean_query) > 100 else clean_query
            }
        
        # Validate it looks like a GraphQL query
        if not (clean_query.strip().startswith(('query', 'mutation', '{')) and '{' in clean_query):
            return {
                "success": False,
                "error": "Invalid GraphQL query format",
                "hint": "Query should start with 'query' or '{' and contain braces",
                "received_query": clean_query[:100] + "..." if len(clean_query) > 100 else clean_query
            }
        
        try:
            result = await client.execute_query(clean_query)
            
            return {
                "success": True,
                "data": result,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__,
                "query_preview": query[:100] + "..." if len(query) > 100 else query
            }

    @mcp.tool()
    async def get_salesforce_schema_info():
        """
        Get information about the Salesforce GraphQL schema and available objects.
        
        Returns:
            JSON string with metadata about queryable objects and their capabilities
        """
        client = get_salesforce_client()
        
        # Static template for schema info
        query = """
        query GetObjectInfo {
            uiapi {
                objectInfos(apiNames: ["Account", "Opportunity", "Contact", "Lead", "Case"]) {
                    ApiName
                    label
                    labelPlural
                    queryable
                    custom
                    keyPrefix
                }
            }
        }
        """
        
        try:
            result = await client.execute_query(query)
            object_infos = result.get("data", {}).get("uiapi", {}).get("objectInfos", [])
            
            schema_info = {
                "success": True,
                "salesforce_info": {
                    "api_version": "v59.0",
                    "instance_url": client.instance_url,
                    "graphql_endpoint": client.base_url
                },
                "common_objects": object_infos,
                "available_tools": [
                    "query_opportunities - Query Salesforce opportunities with filtering",
                    "get_opportunity - Get detailed opportunity by ID",
                    "search_opportunities - Search opportunities by stage and amount",
                    "get_recent_opportunities - Get recent opportunities",
                    "analyze_opportunity_trends - Analyze opportunity trends and patterns",
                    "find_opportunities_by_stage - Find opportunities in specific stage",
                    "query_accounts - Query Salesforce accounts with optional filters",
                    "get_account - Get detailed account by ID", 
                    "search_accounts - Search accounts by industry",
                    "get_recent_accounts - Get recent accounts",
                    "get_account_statistics - Get account statistics and distributions",
                    "find_accounts_by_industry - Find accounts in specific industry",
                    "analyze_account_trends - Analyze account trends and patterns",
                    "execute_custom_graphql - Execute custom GraphQL queries",
                    "get_salesforce_schema_info - Get schema information (this tool)"
                ],
                "date_range_options": [
                    "this_week", "last_week", "this_month", "last_month", 
                    "this_quarter", "last_quarter", "this_year", "last_year"
                ],
                "example_queries": {
                    "basic_opportunities": """
                    query {
                        uiapi {
                            query {
                                Opportunity(first: 5) {
                                    edges {
                                        node {
                                            Id
                                            Name { value }
                                            Amount { displayValue }
                                            StageName { value }
                                        }
                                    }
                                }
                            }
                        }
                    }
                    """,
                    "filtered_accounts": """
                    query {
                        uiapi {
                            query {
                                Account(
                                    where: { Industry: { eq: "Technology" } }
                                    first: 10
                                ) {
                                    edges {
                                        node {
                                            Id
                                            Name { value }
                                            Industry { value }
                                            AnnualRevenue { displayValue }
                                        }
                                    }
                                }
                            }
                        }
                    }
                    """
                },
                "timestamp": datetime.utcnow().isoformat()
            }
            
            return schema_info
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__
            }

    @mcp.tool()
    async def get_object_fields(object_name: str):
        """
        Get field information for a specific Salesforce object.
        
        Args:
            object_name: Name of the Salesforce object (e.g., 'Account', 'Opportunity')
        
        Returns:
            Information about the object's fields and their properties
        """
        client = get_salesforce_client()
        
        # Static template for object field info
        query = f"""
        query GetObjectFields {{
            uiapi {{
                objectInfo(apiName: "{object_name}") {{
                    ApiName
                    label
                    labelPlural
                    queryable
                    custom
                    keyPrefix
                }}
            }}
        }}
        """
        
        try:
            result = await client.execute_query(query)
            object_info = result.get("data", {}).get("uiapi", {}).get("objectInfo")
            
            if not object_info:
                return {
                    "success": False,
                    "error": f"Object '{object_name}' not found or not accessible",
                    "available_objects": ["Account", "Opportunity", "Contact", "Lead", "Case"]
                }
            
            return {
                "success": True,
                "object_info": object_info,
                "note": "Field-level metadata requires additional permissions. Use execute_custom_graphql for specific field queries.",
                "example_field_query": f"""
                query {{
                    uiapi {{
                        query {{
                            {object_name}(first: 1) {{
                                edges {{
                                    node {{
                                        Id
                                        # Add specific fields you want to query
                                    }}
                                }}
                            }}
                        }}
                    }}
                }}
                """,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__
            }