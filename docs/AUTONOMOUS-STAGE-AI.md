# Autonomous Stage AI — Multi-Instance Safety

## Objective

Prevent multiple autonomous workers from concurrently acting on the same logical strategy, symbol, or execution key. Coordination is an ownership boundary, not an authorization or order-execution boundary.

## Five implementation phases

### Phase 1 — Design & contract
Define exclusive lease ownership, expiry, monotonic fencing tokens, and an injected coordination-store protocol.

### Phase 2 — Core implementation
Implement an atomic in-memory reference coordinator. Production deployments can inject a shared transactional/distributed store without changing the autonomy contract.

### Phase 3 — Safety/control integration
Require a currently valid lease before an instance may proceed. Lease expiry, ownership conflicts, and coordination outages fail closed. Fencing tokens distinguish newer ownership from stale instances.

### Phase 4 — Tests & failure scenarios
Cover contention, expiry, fencing-token advancement, owner-only release, coordinator failure, lease validity, and invalid input.

### Phase 5 — CI → merge → post-merge verification
Run the complete lint/test pipeline, merge only after green checks, and verify the post-merge `main` workflow before declaring AI complete.

## Safety boundaries

- Only one live lease may exist for a coordination key at a time.
- Expired leases cannot remain valid.
- A stale instance cannot release or validate a newer owner's lease.
- Coordination failure never becomes permission to trade.
- Fencing tokens are monotonic and can be enforced by downstream shared-state implementations.
- The coordinator does not hold credentials, approve live execution, allocate capital, or submit/cancel orders.
- A shared production store must provide atomic compare-and-set/transactional semantics; the in-memory store is only a reference implementation.
