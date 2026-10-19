#!/usr/bin/env python3
"""
Unit tests for ArcPay-x402 Gateway (Circle USDC M2M Settlement Engine)
Author: @dextermos / @dextermos-dev
Settlement Address: 0x8366bCe3a2D379Dec7656D7A67015789FaF999f20
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from gateway import ArcCircleX402Gateway


class TestArcCircleX402Gateway(unittest.TestCase):
    def setUp(self):
        self.gateway = ArcCircleX402Gateway()

    def test_challenge_generation(self):
        challenge = self.gateway.generate_payment_challenge("/api/v1/wallet/reputation", "client_agent_1")
        self.assertEqual(challenge["status"], 402)
        self.assertEqual(challenge["price_usdc"], 1.00)
        self.assertEqual(challenge["currency"], "USDC")
        self.assertEqual(challenge["settlement_wallet"], "0x8366bCe3a2D379Dec7656D7A67015789FaF999f20")
        self.assertTrue("nonce" in challenge)

    def test_verify_valid_receipt_and_service_execution(self):
        receipt = {
            "tx_hash": "0x4a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b",
            "amount_usdc": 1.00,
            "recipient_wallet": "0x8366bCe3a2D379Dec7656D7A67015789FaF999f20",
            "nonce": "test_nonce_123",
            "endpoint": "/api/v1/wallet/reputation"
        }
        res = self.gateway.verify_payment_receipt(receipt)
        self.assertTrue(res["valid"])
        self.assertTrue(res["settlement_confirmed"])
        self.assertEqual(res["settlement_wallet"], "0x8366bCe3a2D379Dec7656D7A67015789FaF999f20")

        # Execute service with received token
        token = res["access_token"]
        payload = {"wallet": "0xd8da6bf26964af9d7eed9e03e53415d37aa96045"}
        exec_res = self.gateway.execute_paid_service("/api/v1/wallet/reputation", token, payload)
        self.assertEqual(exec_res["status"], 200)
        self.assertEqual(exec_res["service"], "wallet_reputation")
        self.assertGreater(exec_res["reputation_score"], 90)

    def test_prevent_replay_attacks(self):
        receipt = {
            "tx_hash": "0x999999994e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b",
            "amount_usdc": 2.50,
            "recipient_wallet": "0x8366bCe3a2D379Dec7656D7A67015789FaF999f20",
            "nonce": "nonce_replay_1",
            "endpoint": "/api/v1/security/contract-audit"
        }
        res1 = self.gateway.verify_payment_receipt(receipt)
        self.assertTrue(res1["valid"])

        # Second attempt with identical tx_hash must fail
        res2 = self.gateway.verify_payment_receipt(receipt)
        self.assertFalse(res2["valid"])
        self.assertEqual(res2["reason"], "REPLAY_ATTACK_DETECTED_TX_ALREADY_USED")

    def test_reject_wrong_recipient(self):
        receipt = {
            "tx_hash": "0x888888884e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b",
            "amount_usdc": 1.00,
            "recipient_wallet": "0x0000000000000000000000000000000000000000",
            "endpoint": "/api/v1/wallet/reputation"
        }
        res = self.gateway.verify_payment_receipt(receipt)
        self.assertFalse(res["valid"])
        self.assertEqual(res["reason"], "WRONG_RECIPIENT_WALLET")


if __name__ == "__main__":
    unittest.main()
