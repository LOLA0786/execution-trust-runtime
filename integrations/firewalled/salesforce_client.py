"""
integrations/firewalled/salesforce_client.py
Firewalled Salesforce client per spec. Every call must go through PrivateVault (via FirewalledProxy in __init__.py).
Supports real requests (when env vars set) or realistic mock data for demo/live_demo.
Compatible with simple-salesforce patterns but uses direct REST for minimal deps.
"""
from __future__ import annotations
import os
import requests
from typing import Dict, Any, List, Optional
from datetime import datetime
import logging
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class FirewalledSalesforceClient:
    def __init__(self):
        self.instance_url = os.getenv("SALESFORCE_INSTANCE_URL", "")
        self.access_token = os.getenv("SALESFORCE_ACCESS_TOKEN", "")
        self._connected = bool(self.instance_url and self.access_token)
        if not self._connected:
            logger.warning("Salesforce not connected (missing SALESFORCE_INSTANCE_URL or ACCESS_TOKEN). Using mock mode for demo.")

    def query(self, soql: str = None, threshold: float = 0.15) -> List["OpportunityRecord"]:
        """Execute SOQL query or return structured OpportunityRecord list.
        Supports both direct SOQL (real) and threshold param (for firewalled proxy compatibility).
        Returns mock with 70% discount for live_demo anomaly detection.
        """
        if soql is None:
            # Called from proxy with threshold kwarg - generate mock for demo
            soql = f"SELECT Id, Name, Amount, Discount__c, StageName FROM Opportunity WHERE Discount__c > {threshold}"
        
        raw = self._mock_query(soql) if not self._connected else self._real_query(soql)
        
        # Convert raw records to Pydantic models (handles both real and mock)
        records = raw.get("records", [])
        opportunities = []
        for rec in records:
            # Normalize for Pydantic aliasing
            flat = {
                **rec,
                "AccountName": rec.get("Account", {}).get("Name") or rec.get("AccountName", "Acme Corp"),
            }
            try:
                opp = OpportunityRecord.model_validate(flat)
                opportunities.append(opp)
            except Exception:
                # Fallback for mock dict structure
                opp = OpportunityRecord(
                    id=rec.get("Id", "OPP-MOCK"),
                    name=rec.get("Name", "Mock Deal"),
                    account_name=rec.get("AccountName", "Acme Corp"),
                    amount=rec.get("Amount", 2400000),
                    discount=rec.get("Discount__c", 70.0),
                    stage=rec.get("StageName", "Negotiation"),
                    metadata={"source": "mock", "drift": "high_discount"}
                )
                opportunities.append(opp)
        return opportunities

    def _real_query(self, soql: str) -> dict:
        """Real REST call (when connected)."""
        headers = {"Authorization": f"Bearer {self.access_token}"}
        url = f"{self.instance_url}/services/data/v57.0/query"
        resp = requests.get(url, headers=headers, params={"q": soql})
        resp.raise_for_status()
        return resp.json()

    def update_opportunity(self, opp_id: str, fields: dict) -> bool:
        """Update Opportunity record. Mock success in demo mode."""
        if not self._connected:
            return True  # mock success
        import requests
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
        url = f"{self.instance_url}/services/data/v57.0/sobjects/Opportunity/{opp_id}"
        resp = requests.patch(url, headers=headers, json=fields)
        return resp.status_code == 204

    def _mock_query(self, soql: str) -> dict:
        """Returns realistic mock data for demo/testing (triggers 70% discount anomaly in Revenue Ops)."""
        # Detect if query is for high discount (live_demo uses threshold ~0.15)
        if "Discount__c >" in soql or "discount" in soql.lower():
            return {
                "totalSize": 2,
                "done": True,
                "records": [
                    {
                        "Id": "OPP-987654",
                        "Name": "Acme Corp Enterprise Deal",
                        "Amount": 2400000,
                        "Discount__c": 70,  # triggers anomaly in agent
                        "StageName": "Negotiation",
                        "Account": {"Name": "Acme Corp"}
                    },
                    {
                        "Id": "OPP-123456",
                        "Name": "Small Deal",
                        "Amount": 500000,
                        "Discount__c": 10,
                        "StageName": "Closed Won",
                        "Account": {"Name": "Beta Inc"}
                    }
                ]
            }
        return {
            "totalSize": 1,
            "done": True,
            "records": [{
                "Id": "OPP-987654",
                "Name": "Acme Corp Enterprise Deal",
                "Amount": 2400000,
                "Discount__c": 10,
                "StageName": "Negotiation",
                "AccountName": "Acme Corp"
            }]
        }


class OpportunityRecord(BaseModel):
    """Structured record for Salesforce Opportunity with discount focus (Revenue Ops)."""
    id: str = Field(..., alias='Id')
    name: str = Field(..., alias='Name')
    account_name: str = Field(..., alias='AccountName')
    amount: Optional[float] = Field(None, alias='Amount')
    discount: Optional[float] = Field(None, alias='Discount__c')
    stage: str = Field(..., alias='StageName')
    close_date: Optional[datetime] = Field(None, alias='CloseDate')
    probability: Optional[float] = Field(None, alias='Probability')
    metadata: Dict[str, Any] = Field(default_factory=dict)

    model_config = {"populate_by_name": True}


# Singleton (injected into FirewalledProxy("salesforce", real_client=salesforce_client))
salesforce_client = FirewalledSalesforceClient()
