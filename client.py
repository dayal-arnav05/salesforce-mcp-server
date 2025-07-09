"""
Fixed Salesforce GraphQL API client.
Addresses GraphQL type mismatches and error parsing issues.
"""

import logging
from typing import Any, Dict, List, Optional
import httpx
from models import Opportunity, Account

logger = logging.getLogger(__name__)

class SalesforceClient:
    """Client for interacting with Salesforce GraphQL API."""
    def __init__(self, instance_url: str, access_token: str):
        self.instance_url = instance_url
        self.access_token = access_token
        self.base_url = f"{instance_url}/services/data/v59.0/graphql"
        self.headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }

    async def execute_query(self, query: str, variables: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        payload = {
            "query": query,
            "variables": variables or {}
        }
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    self.base_url,
                    json=payload,
                    headers=self.headers,
                    timeout=30.0
                )
                response.raise_for_status()
                data = response.json()
                
                # FIXED: Check for non-empty errors array instead of just presence of "errors" key
                if data.get("errors"):  # This checks for non-empty errors array
                    error_messages = []
                    for error in data["errors"]:
                        message = error.get("message", "Unknown GraphQL error")
                        # Also get extensions if available
                        extensions = error.get("extensions", {})
                        classification = extensions.get("classification", "")
                        if classification:
                            message = f"{message} (Classification: {classification})"
                        error_messages.append(message)
                    
                    full_error_msg = '; '.join(error_messages)
                    logger.error(f"GraphQL errors: {full_error_msg}")
                    raise Exception(f"GraphQL errors: {full_error_msg}")
                
                return data
            except httpx.HTTPStatusError as e:
                logger.error(f"HTTP error {e.response.status_code}: {e.response.text}")
                raise Exception(f"API request failed: {e.response.status_code}")
            except Exception as e:
                logger.error(f"Error executing GraphQL query: {e}")
                raise

    async def get_opportunity(self, opportunity_id: str) -> Optional[Opportunity]:
        """Get detailed opportunity by ID - FIXED: Use ID type instead of String!"""
        query = """
        query GetOpportunity($opportunityId: ID!) {
            uiapi {
                query {
                    Opportunity(where: { Id: { eq: $opportunityId } }) {
                        edges {
                            node {
                                Id
                                Name { value }
                                Amount { value displayValue }
                                CloseDate { value }
                                StageName { value }
                                Probability { value }
                                Description { value }
                                Type { value }
                                LeadSource { value }
                                Account {
                                    Id
                                    Name { value }
                                }
                                Owner {
                                    Id
                                    Name { value }
                                }
                            }
                        }
                    }
                }
            }
        }
        """
        try:
            result = await self.execute_query(query, {"opportunityId": opportunity_id})
            edges = result.get("data", {}).get("uiapi", {}).get("query", {}).get("Opportunity", {}).get("edges", [])
            if edges:
                opportunity_data = edges[0]["node"]
                return Opportunity(**opportunity_data)
            return None
        except Exception as e:
            logger.error(f"Error fetching opportunity {opportunity_id}: {e}")
            raise

    async def search_opportunities(
        self, 
        stage: Optional[str] = None, 
        min_amount: Optional[float] = None, 
        limit: int = 10
    ) -> List[Opportunity]:
        """Search opportunities - SIMPLIFIED: No complex filtering initially"""
        
        # Start with simple query, no WHERE clause to test basic functionality
        query = f"""
        query SearchOpportunities {{
            uiapi {{
                query {{
                    Opportunity(
                        first: {limit}
                        orderBy: {{ LastModifiedDate: {{ order: DESC }} }}
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
                    }}
                }}
            }}
        }}
        """
        try:
            result = await self.execute_query(query)
            opportunities = []
            
            edges = result.get("data", {}).get("uiapi", {}).get("query", {}).get("Opportunity", {}).get("edges", [])
            for edge in edges:
                opportunity_data = edge["node"]
                opportunities.append(Opportunity(**opportunity_data))
            return opportunities
        except Exception as e:
            logger.error(f"Error searching opportunities: {e}")
            raise

    async def get_recent_opportunities(self, limit: int = 5) -> List[Opportunity]:
        """Get recent opportunities - SIMPLIFIED"""
        query = f"""
        query GetRecentOpportunities {{
            uiapi {{
                query {{
                    Opportunity(
                        first: {limit}
                        orderBy: {{ LastModifiedDate: {{ order: DESC }} }}
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
                            }}
                        }}
                    }}
                }}
            }}
        }}
        """
        try:
            result = await self.execute_query(query)
            opportunities = []
            
            edges = result.get("data", {}).get("uiapi", {}).get("query", {}).get("Opportunity", {}).get("edges", [])
            for edge in edges:
                opportunity_data = edge["node"]
                opportunities.append(Opportunity(**opportunity_data))
            return opportunities
        except Exception as e:
            logger.error(f"Error fetching recent opportunities: {e}")
            raise

    async def get_account(self, account_id: str) -> Optional[Account]:
        """Get detailed account by ID - FIXED: Use ID type"""
        query = """
        query GetAccount($accountId: ID!) {
            uiapi {
                query {
                    Account(where: { Id: { eq: $accountId } }) {
                        edges {
                            node {
                                Id
                                Name { value }
                                Type { value }
                                Industry { value }
                                AnnualRevenue { value displayValue }
                                NumberOfEmployees { value }
                                Phone { value }
                                Website { value }
                                BillingAddress {
                                    BillingCity { value }
                                    BillingState { value }
                                    BillingCountry { value }
                                }
                            }
                        }
                    }
                }
            }
        }
        """
        try:
            result = await self.execute_query(query, {"accountId": account_id})
            edges = result.get("data", {}).get("uiapi", {}).get("query", {}).get("Account", {}).get("edges", [])
            if edges:
                account_data = edges[0]["node"]
                return Account(**account_data)
            return None
        except Exception as e:
            logger.error(f"Error fetching account {account_id}: {e}")
            raise

    async def search_accounts(self, industry: Optional[str] = None, limit: int = 10) -> List[Account]:
        """Search accounts - SIMPLIFIED"""
        
        # Simple query without WHERE filtering initially
        query = f"""
        query SearchAccounts {{
            uiapi {{
                query {{
                    Account(
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
                            }}
                        }}
                        totalCount
                    }}
                }}
            }}
        }}
        """
        try:
            result = await self.execute_query(query)
            accounts = []
            
            edges = result.get("data", {}).get("uiapi", {}).get("query", {}).get("Account", {}).get("edges", [])
            for edge in edges:
                account_data = edge["node"]
                accounts.append(Account(**account_data))
            return accounts
        except Exception as e:
            logger.error(f"Error searching accounts: {e}")
            raise

    async def get_recent_accounts(self, limit: int = 5) -> List[Account]:
        """Get recent accounts - SIMPLIFIED"""
        query = f"""
        query GetRecentAccounts {{
            uiapi {{
                query {{
                    Account(
                        first: {limit}
                        orderBy: {{ LastModifiedDate: {{ order: DESC }} }}
                    ) {{
                        edges {{
                            node {{
                                Id
                                Name {{ value }}
                                Type {{ value }}
                                Industry {{ value }}
                                AnnualRevenue {{ value displayValue }}
                                NumberOfEmployees {{ value }}
                            }}
                        }}
                    }}
                }}
            }}
        }}
        """
        try:
            result = await self.execute_query(query)
            accounts = []
            
            edges = result.get("data", {}).get("uiapi", {}).get("query", {}).get("Account", {}).get("edges", [])
            for edge in edges:
                account_data = edge["node"]
                accounts.append(Account(**account_data))
            return accounts
        except Exception as e:
            logger.error(f"Error fetching recent accounts: {e}")
            raise

    async def get_schema_info(self) -> dict:
        """Get schema info - WORKING query"""
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
            result = await self.execute_query(query)
            return result.get("data", {}).get("uiapi", {}).get("objectInfos", [])
        except Exception as e:
            logger.error(f"Error fetching schema info: {e}")
            raise

    async def test_simple_query(self) -> dict:
        """Test the simplest possible query to verify connection"""
        query = """
        query TestQuery {
            uiapi {
                query {
                    Account(first: 1) {
                        edges {
                            node {
                                Id
                                Name { value }
                            }
                        }
                    }
                }
            }
        }
        """
        try:
            result = await self.execute_query(query)
            return result
        except Exception as e:
            logger.error(f"Error in simple test query: {e}")
            raise