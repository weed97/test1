# P0 Security & Fairness

Production-hardening layer for CPoW areas, governance, and API access.

## Session authentication

- **Module:** `cpow_engine/auth/` — HMAC session tokens (stdlib, no PyJWT).
- **API:** `POST /v1/auth/register`, `POST /v1/auth/login`, `GET /v1/auth/me`
- **Env:** `CPOW_JWT_SECRET` — signing key (default dev secret; change in production).

Bearer tokens bind the session `user_id` to area/governance actor fields. Payload actor IDs that disagree with the session return `403 actor_identity_mismatch`.

## Identity (`person_key`)

- `POST /v1/identity/register` requires a valid Bearer session.
- `person_key` is registered for the authenticated account only (1 account ↔ 1 person binding).
- OAuth / card / PASS verification is **not** implemented in P0 — only structural session + person_key binding.

## Governance fairness

| Control | Behavior |
|---------|----------|
| Per-area powers | `_powers_by_area` — creation/destruction gauges scoped per area |
| Weighted votes | `vote_weight()` — log-scale margin, caps grind from raw creation score |
| Vote collab gate | `min_collab_signals_for_vote` (default 2) |
| Cosponsor Sybil | Unique `person_key` cosponsors; `max_active_cosponsors_per_user` |
| Voting TTL | `voting_ttl_sec` enforced in `GovernanceLedger.tick()` |

## Diplomacy & expansion

| Action | Gate |
|--------|------|
| Hostile declaration | ≥2 human members; founder initiates, second human confirms |
| Area expand | ≥2 humans; actor `collab_signals >= 1` |

## Client usage

```http
POST /v1/auth/register
{"user_id": "aria", "password": "securepass1"}

POST /v1/auth/login
{"user_id": "aria", "password": "securepass1"}
→ {"token": "...", "token_type": "Bearer"}

POST /v1/identity/register
Authorization: Bearer <token>
{"person_key": "verified-person-secret"}

POST /v1/areas/found
Authorization: Bearer <token>
{"label": "My World"}
```

## Tests

```bash
python3 -m unittest discover -s cpow_engine/tests -v
```

`test_auth.py`, updated governance/diplomacy/siege tests cover P0 behavior.
