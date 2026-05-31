"""
integrations/salesforce_client.py
Live Salesforce sandbox client for Revenue Ops Agent.
- OAuth2 / username-password flow via simple-salesforce.
- SOQL query for opportunities with discount > threshold.
- Returns list of structured OpportunityRecord (Pydantic).
- Fully compatible with FirewalledProxy (real_client injected).
- Uses env vars for sandbox creds (add to .env).
- All calls MUST route through firewalled.salesforce.query(...) for vault enforcement.
"""
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from simple_salesforce import Salesforce, SalesforceAuthenticationFailed
import os
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class OpportunityRecord(BaseModel):
    """Structured record for Salesforce Opportunity with discount focus (Revenue Ops)."""
    id: str = Field(..., alias='Id')
    name: str = Field(..., alias='Name')
    account_name: Optional[str] = Field(None, alias='Account.Name')
    amount: Optional[float] = Field(None, alias='Amount')
    discount: Optional[float] = Field(None, alias='Discount__c')  # custom field assumed; fallback to StageName logic
    stage: str = Field(..., alias='StageName')
    close_date: Optional[datetime] = Field(None, alias='CloseDate')
    probability: Optional[float] = Field(None, alias='Probability')
    last_modified: Optional[datetime] = Field(None, alias='LastModifiedDate')
    metadata: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        populate_by_name = True


class SalesforceClient:
    """Production Salesforce client (sandbox by default). Supports OAuth2-like login."""
    
    def __init__(self):
        self.sf: Optional[Salesforce] = None
        self.instance_url: Optional[str] = None
        self._connect()
    
    def _connect(self):
        """Connect using username/password/security token (sandbox)."""
        username = os.getenv("SF_USERNAME")
        password = os.getenv("SF_PASSWORD")
        security_token = os.getenv("SF_SECURITY_TOKEN")
        sandbox = os.getenv("SF_SANDBOX", "true").lower() == "true"
        
        if not username or not password:
            logger.warning("Salesforce creds not set in env (SF_USERNAME, SF_PASSWORD, SF_SECURITY_TOKEN). Using mock mode.")
            return
        
        try:
            self.sf = Salesforce(
                username=username,
                password=password,
                security_token=security_token or "",
                domain='test' if sandbox else None,  # sandbox domain
                version='59.0'  # current stable
            )
            self.instance_url = self.sf.sf_instance
            logger.info(f"✅ Connected to Salesforce {'sandbox' if sandbox else 'production'} as {username}")
        except SalesforceAuthenticationFailed as e:
            logger.error(f"Salesforce auth failed: {e}. Check sandbox creds.")
        except Exception as e:
            logger.error(f"Salesforce connection error: {e}")
    
    def query_high_discount_opportunities(self, threshold: float = 0.15) -> List[OpportunityRecord]:
        """SOQL query for opportunities where discount > threshold.
        Returns structured Pydantic models. (Assumes custom Discount__c field; adapt as needed.)
        """
        if not self.sf:
            # Mock for no-creds/demo
            return [
                OpportunityRecord(
                    Id="OPP-MOCK-001",
                    Name="Large Enterprise Renewal",
                    Account={"Name": "Acme Corp"},
                    Amount=2500000.0,
                    Discount__c=0.25,  # > threshold
                    StageName="Negotiation",
                    CloseDate=datetime(2026, 6, 30),
                    Probability=0.75,
                    metadata={"source": "mock_sandbox", "drift_risk": "high"}
                )
            ]
        
        soql = f"""
            SELECT Id, Name, Account.Name, Amount, Discount__c, StageName, 
                   CloseDate, Probability, LastModifiedDate
            FROM Opportunity 
            WHERE Discount__c > {threshold} 
              AND StageName IN ('Negotiation', 'Proposal', 'Closed Won')
            ORDER BY Amount DESC
            LIMIT 20
        """
        try:
            result = self.sf.query(soql)
            records = result.get('records', [])
            opportunities = []
            for rec in records:
                # simple-salesforce returns nested dicts; flatten for Pydantic
                flat = {
                    **rec,
                    'Account.Name': rec.get('Account', {}).get('Name'),
                }
                opp = OpportunityRecord.model_validate(flat)
                opportunities.append(opp)
            logger.info(f"Retrieved {len(opportunities)} high-discount opportunities (> {threshold}) from Salesforce sandbox")
            return opportunities
        except Exception as e:
            logger.error(f"SOQL query failed: {e}")
            return []
    
    def update_opportunity(self, opportunity_id: str, **kwargs) -> Dict[str, Any]:
        """Update Opportunity (e.g. status, discount). Routes through firewall in proxy."""
        if not self.sf:
            return {"status": "MOCK_UPDATE", "id": opportunity_id, "changes": kwargs}
        
        try:
            result = self.sf.Opportunity.update(opportunity_id, kwargs)
            logger.info(f"Updated Salesforce Opportunity {opportunity_id}: {kwargs}")
            return {"success": True, "id": opportunity_id, "result": result}
        except Exception as e:
            logger.error(f"Update failed for {opportunity_id}: {e}")
            return {"success": False, "error": str(e)}


# Singleton client (injected into FirewalledProxy)
salesforce_client = SalesforceClient()
