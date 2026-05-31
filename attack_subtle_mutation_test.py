#!/usr/bin/env python3
from privatevault.ai_firewall_core import CognitiveExecutionKernel
import json

# Simple Mock Snapshot class (agar real nahi hai toh yeh use hoga)
class MerkleSnapshot:
    def __init__(self, beneficiary, amount, po_number, bank_account, intent, trust_score=0.9, reasoning_integrity_score=0.9):
        self.beneficiary = beneficiary
        self.amount = amount
        self.po_number = po_number
        self.bank_account = bank_account
        self.intent = intent
        self.trust_score = trust_score
        self.reasoning_integrity_score = reasoning_integrity_score
        self.merkle_node_hash = hash(str(beneficiary) + str(amount) + str(po_number))

kernel = CognitiveExecutionKernel()

print("=== SUBTLE MUTATION ATTACK TEST ===\n")

# 1. Clean Approval
clean = MerkleSnapshot(
    beneficiary="Acme Solutions Limited",
    amount=4750000,
    po_number="PO-98765",
    bank_account="987654321098",
    intent="Release payment as per PO",
    trust_score=0.92
)

approval = {"cognition_snapshot_hash": clean.merkle_node_hash}

print("✅ Clean approval sealed\n")

# 2. Attacker Poison (Subtle change)
poisoned = MerkleSnapshot(
    beneficiary="Acme Solutions International Ltd",   # subtle name change
    amount=4750000,
    po_number="PO-98765",
    bank_account="555555555555",                     # account changed
    intent="Release as per latest compliance policy update",
    trust_score=0.78,
    reasoning_integrity_score=0.35
)

print("🔴 Subtle poisoning injected after approval\n")

# 3. PrivateVault Check
decision = kernel.evaluate(snapshot=poisoned, action={"amount": 4750000}, approval=approval)

print("=== PRIVATEVAULT VERDICT ===")
print(json.dumps(decision, indent=2))
