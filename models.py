from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any

class OpportunityAccount(BaseModel):
    Id: Optional[str] = None
    Name: Optional[Dict[str, Any]] = None

class OpportunityOwner(BaseModel):
    Id: Optional[str] = None
    Name: Optional[Dict[str, Any]] = None

class Opportunity(BaseModel):
    Id: Optional[str] = None
    Name: Optional[Dict[str, Any]] = None
    Amount: Optional[Dict[str, Any]] = None
    CloseDate: Optional[Dict[str, Any]] = None
    StageName: Optional[Dict[str, Any]] = None
    Probability: Optional[Dict[str, Any]] = None
    Description: Optional[Dict[str, Any]] = None
    Type: Optional[Dict[str, Any]] = None
    LeadSource: Optional[Dict[str, Any]] = None
    Account: Optional[OpportunityAccount] = None
    Owner: Optional[OpportunityOwner] = None

class AccountBillingAddress(BaseModel):
    BillingCity: Optional[Dict[str, Any]] = None
    BillingState: Optional[Dict[str, Any]] = None
    BillingCountry: Optional[Dict[str, Any]] = None

class Account(BaseModel):
    Id: Optional[str] = None
    Name: Optional[Dict[str, Any]] = None
    Type: Optional[Dict[str, Any]] = None
    Industry: Optional[Dict[str, Any]] = None
    AnnualRevenue: Optional[Dict[str, Any]] = None
    NumberOfEmployees: Optional[Dict[str, Any]] = None
    Phone: Optional[Dict[str, Any]] = None
    Website: Optional[Dict[str, Any]] = None
    BillingAddress: Optional[AccountBillingAddress] = None