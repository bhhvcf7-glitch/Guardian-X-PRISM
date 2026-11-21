"""Guardian X PRISM: educational, local decision engine (no real payment access)."""
from dataclasses import dataclass, asdict
import hashlib
import hmac
import json
import math
import random
import secrets
import time


@dataclass(frozen=True)
class Policy:
    fraud_loss: float = 9000
    challenge_cost: float = 40
    false_block_cost: float = 600
    residual_attack_rate: float = 0.05
    delay_cost: float = 25
    audit_floor: float = 0.01


def mixed_residual(attacker_types):
    """Weighted residual success; shares must sum to one."""
    if not attacker_types or any(s < 0 or not 0 <= r <= 1 for s, r in attacker_types):
        raise ValueError("Invalid attacker shares or residual rates")
    if not math.isclose(sum(s for s, _ in attacker_types), 1, abs_tol=1e-9):
        raise ValueError("Attacker shares must sum to 1")
    return sum(s * r for s, r in attacker_types)


def losses(p, policy):
    if not 0 <= p <= 1 or not 0 <= policy.residual_attack_rate <= 1:
        raise ValueError("Probabilities must be between 0 and 1")
    return {
        "allow": policy.fraud_loss * p,
        "verify": policy.fraud_loss * policy.residual_attack_rate * p + policy.challenge_cost * (1-p),
        "block": policy.false_block_cost * (1-p),
    }


def select_action(p, policy):
    options = losses(p, policy)
    return min(options, key=options.get)


def thresholds(policy):
    L, C, B, r = policy.fraud_loss, policy.challenge_cost, policy.false_block_cost, policy.residual_attack_rate
    return {"allow_verify": C/(L*(1-r)+C), "verify_block": (B-C)/(L*r+B-C)}


def bayes_signal(prior, sensitivity, false_positive):
    if any(not 0 <= x <= 1 for x in (prior, sensitivity, false_positive)):
        raise ValueError("Signal parameters outside [0,1]")
    pos = prior*sensitivity + (1-prior)*false_positive
    neg = 1-pos
    posterior_pos = prior*sensitivity/pos if pos else 0
    posterior_neg = prior*(1-sensitivity)/neg if neg else 0
    return ((pos, posterior_pos), (neg, posterior_neg))


def hold_value(prior, sensitivity, false_positive, policy, evidence_level="E2"):
    immediate = min(losses(prior, policy).values())
    signals = bayes_signal(prior, sensitivity, false_positive)
    future = sum(weight*min(losses(posterior, policy).values()) for weight, posterior in signals)
    future += policy.delay_cost*(1-prior)
    value = immediate-future
    return {"immediate_loss": immediate, "hold_loss": future, "value": value,
            "recommended": value > 0 and evidence_level in {"E1", "E2", "E3"},
            "positive": {"probability": signals[0][0], "posterior": signals[0][1], "action": select_action(signals[0][1], policy)},
            "negative": {"probability": signals[1][0], "posterior": signals[1][1], "action": select_action(signals[1][1], policy)}}


def audit_decision(p, policy, rng=None):
    """Random verification on allowed low-risk transactions; simulation only."""
    action = select_action(p, policy)
    if action == "allow" and (rng or random).random() < policy.audit_floor:
        return "verify_audit"
    return action


class IntentLock:
    """One-time, expiring, HMAC-authenticated authorization tied to full transaction details."""
    def __init__(self, key=None):
        self.key = key if key is not None else secrets.token_bytes(32)
        self.used = set()

    def issue(self, user_id, transaction, ttl_seconds=120, now=None):
        if ttl_seconds <= 0:
            raise ValueError("TTL must be positive")
        payload = {"user_id": user_id, "transaction": transaction, "expires": (time.time() if now is None else now)+ttl_seconds,
                   "nonce": secrets.token_hex(16)}
        body = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        sig = hmac.new(self.key, body.encode(), hashlib.sha256).hexdigest()
        return json.dumps({"payload": payload, "signature": sig}, ensure_ascii=False)

    def redeem(self, token, user_id, transaction, now=None):
        try:
            wrapped = json.loads(token)
            payload = wrapped["payload"]
            body = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
            signature = hmac.new(self.key, body.encode(), hashlib.sha256).hexdigest()
            nonce = payload["nonce"]
            if not hmac.compare_digest(signature, wrapped["signature"]):
                return False
            if nonce in self.used or (time.time() if now is None else now) >= payload["expires"]:
                return False
            if payload["user_id"] != user_id or payload["transaction"] != transaction:
                return False
            self.used.add(nonce)
            return True
        except (ValueError, KeyError, TypeError):
            return False


class FatigueGuard:
    """Reduces repeat challenges and estimates elevated social-engineering residual risk."""
    def __init__(self, window=300, max_challenges=2):
        self.window = window
        self.max_challenges = max_challenges
        self.events = {}

    def evaluate(self, user, fast_approvals, now=0):
        history = [t for t in self.events.get(user, []) if now-t < self.window]
        self.events[user] = history
        multiplier = min(2.5, 1+0.4*fast_approvals)
        if len(history) >= self.max_challenges:
            return {"challenge_allowed": False, "social_residual_multiplier": multiplier, "action": "cooldown"}
        history.append(now)
        return {"challenge_allowed": True, "social_residual_multiplier": multiplier, "action": "challenge"}


def benchmark(n=10000, seed=42, policy=None, attacker_aware=False):
    """Synthetic scenario generator; NOT measured attack-detection performance."""
    policy = policy or Policy()
    rng = random.Random(seed)
    counts = {"allow": 0, "verify": 0, "block": 0, "verify_audit": 0}
    realized = 0
    for _ in range(n):
        p = rng.betavariate(0.8, 35) if not attacker_aware else rng.uniform(0, thresholds(policy)["allow_verify"]*0.99)
        decision = audit_decision(p, policy, rng)
        counts[decision] += 1
        canonical = "verify" if decision == "verify_audit" else decision
        realized += losses(p, policy)[canonical]
    return {"samples": n, "seed": seed, "attacker_aware": attacker_aware,
            "mean_modelled_cost": realized/n, "counts": counts,
            "warning": "Synthetic probabilities and assumed costs; not real-world validation."}
