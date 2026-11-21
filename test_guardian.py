import random
import unittest
from guardian import Policy, IntentLock, FatigueGuard, audit_decision, benchmark, hold_value, losses, mixed_residual, select_action, thresholds


class GuardianAcceptance(unittest.TestCase):
    def setUp(self):
        self.policy = Policy()
        self.lock = IntentLock(b"test-secret-key")
        self.tx = {"recipient": "SA0001", "amount": 9000, "currency": "SAR", "destination": "bank", "purpose": "invoice"}

    def test_T01_intent_exact(self):
        token = self.lock.issue("u1", self.tx, now=100)
        self.assertTrue(self.lock.redeem(token, "u1", self.tx, now=101))

    def test_T02_amount_mutation_rejected(self):
        token = self.lock.issue("u1", self.tx, now=100)
        self.assertFalse(self.lock.redeem(token, "u1", {**self.tx, "amount": 9001}, now=101))

    def test_T03_recipient_mutation_rejected(self):
        token = self.lock.issue("u1", self.tx, now=100)
        self.assertFalse(self.lock.redeem(token, "u1", {**self.tx, "recipient": "SA9999"}, now=101))

    def test_T04_expired_rejected(self):
        token = self.lock.issue("u1", self.tx, ttl_seconds=10, now=100)
        self.assertFalse(self.lock.redeem(token, "u1", self.tx, now=110))

    def test_T05_replay_rejected(self):
        token = self.lock.issue("u1", self.tx, now=100)
        self.assertTrue(self.lock.redeem(token, "u1", self.tx, now=101))
        self.assertFalse(self.lock.redeem(token, "u1", self.tx, now=102))

    def test_T06_wrong_user_rejected(self):
        token = self.lock.issue("u1", self.tx, now=100)
        self.assertFalse(self.lock.redeem(token, "u2", self.tx, now=101))

    def test_T07_signature_tamper_rejected(self):
        token = self.lock.issue("u1", self.tx, now=100)
        self.assertFalse(self.lock.redeem(token.replace("invoice", "stolen"), "u1", self.tx, now=101))

    def test_T08_minimum_expected_loss(self):
        for p in (0, .003, .03, .3, .8, 1):
            self.assertEqual(losses(p, self.policy)[select_action(p, self.policy)], min(losses(p, self.policy).values()))

    def test_T09_thresholds(self):
        t = thresholds(self.policy)
        self.assertAlmostEqual(t["allow_verify"], 40/8590)
        self.assertAlmostEqual(t["verify_block"], 560/1010)

    def test_T10_strong_signal_value(self):
        result = hold_value(.3, .8, .1, self.policy)
        self.assertAlmostEqual(result["hold_loss"], 111.7)
        self.assertTrue(result["recommended"])

    def test_T11_mixed_attacker(self):
        rate = mixed_residual([(.5,.02), (.3,.03), (.2,.40)])
        self.assertAlmostEqual(rate, .099)
        self.assertAlmostEqual(thresholds(Policy(residual_attack_rate=rate))["verify_block"], 560/1451)

    def test_T12_weak_E0_no_hold(self):
        result = hold_value(.3, .6, .3, self.policy, "E0")
        self.assertAlmostEqual(result["hold_loss"], 180.5)
        self.assertFalse(result["recommended"])

    def test_T13_threshold_aware_audit(self):
        p = .001
        self.assertEqual(audit_decision(p, Policy(audit_floor=1), random.Random(3)), "verify_audit")
        self.assertEqual(audit_decision(p, Policy(audit_floor=0), random.Random(3)), "allow")
        result = benchmark(100, seed=42, attacker_aware=True)
        self.assertEqual(result["samples"], 100)

    def test_T14_fatigue_cooldown(self):
        guard = FatigueGuard(max_challenges=2)
        self.assertTrue(guard.evaluate("u1", 0, 100)["challenge_allowed"])
        self.assertTrue(guard.evaluate("u1", 1, 101)["challenge_allowed"])
        result = guard.evaluate("u1", 3, 102)
        self.assertFalse(result["challenge_allowed"])
        self.assertGreater(result["social_residual_multiplier"], 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
