# Security policy

Guardian X PRISM V16 is a **research demonstration**. It is not audited, production-hardened, or intended for live payments or sensitive personal information.

Please avoid publishing exploitation details affecting real deployments. Report suspected vulnerabilities privately through the repository owner's GitHub contact or private vulnerability reporting, if enabled.

## Known boundaries

- Local HTTP server only; no authenticated remote API.
- HMAC proof of consent is illustrative and does not implement Passkeys/WebAuthn.
- Nonces are stored in memory; production requires atomic persistent replay prevention.
- Random auditing and fatigue handling are simulation mechanics.
- Test cases are not equivalent to security audit or real-world fraud detection benchmarks.
