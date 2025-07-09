"""
Salesforce MCP Server with Business Analysis Tools
"""

import logging
import os
from dotenv import load_dotenv
from fastmcp import FastMCP
from typing import Optional
from client import SalesforceClient
from tools.opportunities import setup_opportunity_tools
from tools.accounts import setup_account_tools
from tools.schema import setup_schema_tools
from tools.business_analysis_tools import setup_business_analysis_tools  # NEW

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

mcp = FastMCP("Salesforce MCP Server")
salesforce_client: Optional[SalesforceClient] = None

def get_salesforce_client() -> SalesforceClient:
    """Get or create Salesforce client instance."""
    global salesforce_client
    if salesforce_client is None:
        instance_url = os.getenv("SALESFORCE_INSTANCE_URL")
        access_token = os.getenv("SALESFORCE_ACCESS_TOKEN")
        
        if not instance_url:
            raise ValueError("SALESFORCE_INSTANCE_URL environment variable is required")
        if not access_token:
            raise ValueError("SALESFORCE_ACCESS_TOKEN environment variable is required")
        
        salesforce_client = SalesforceClient(instance_url, access_token)
        logger.info("Salesforce client initialized")
    return salesforce_client

# Register all tools
def register_tools():
    """Register tools for the MCP server."""
    setup_opportunity_tools(mcp, get_salesforce_client)
    setup_account_tools(mcp, get_salesforce_client)
    setup_schema_tools(mcp, get_salesforce_client)
    
    # NEW: Register business analysis tools
    setup_business_analysis_tools(mcp, get_salesforce_client)
    
    logger.info("Available tools registered successfully")

@mcp.resource("salesforce://server/info")
class ServerInfoResource:
    """Server information resource."""
    async def read(self) -> str:
        return """# Salesforce MCP Server with Business Intelligence

This server provides integration with Salesforce GraphQL API for CRM data access and business analysis.

## Core Tools:
- execute_custom_graphql: Execute any custom GraphQL query
- get_salesforce_schema_info: Get schema information

## Business Intelligence Tools:
- sales_pipeline_analysis: Advanced pipeline analysis with date filtering
- customer_analysis_by_industry: Industry-based customer segmentation
- sales_performance_by_owner: Sales rep performance analysis
- quarterly_business_review: Comprehensive quarterly reports

## Usage:
Make sure your SALESFORCE_INSTANCE_URL and SALESFORCE_ACCESS_TOKEN are set in the environment.
"""

def main():
    """Main entry point for running the server."""
    try:
        instance_url = os.getenv("SALESFORCE_INSTANCE_URL")
        access_token = os.getenv("SALESFORCE_ACCESS_TOKEN")
        
        if not instance_url:
            error_message = "SALESFORCE_INSTANCE_URL environment variable is required. Please set it in your .env file."
            logger.error(error_message)
            raise ValueError(error_message)
        if not access_token:
            error_message = "SALESFORCE_ACCESS_TOKEN environment variable is required. Please set it in your .env file."
            logger.error(error_message)
            raise ValueError(error_message)
        
        register_tools()
        
        logger.info("Starting Salesforce MCP Server with Business Intelligence...")
        mcp.run(transport="streamable-http", host="0.0.0.0", port=8000)
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
        raise ValueError("Server stopped by user")
    except Exception as e:
        logger.error(f"Failed to start server: {e}")
        raise ValueError(f"Failed to start server: {e}")

if __name__ == "__main__":
    exit(main())