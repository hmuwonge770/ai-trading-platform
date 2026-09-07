# Stage AI Completion Checklist

1. Design & contract: exclusive lease, expiry, fencing token, injected store.
2. Core implementation: atomic reference coordinator.
3. Safety/control integration: valid ownership required; outages and conflicts fail closed.
4. Tests & failure scenarios: contention, expiry, stale lease, release ownership, coordinator outage, invalid input.
5. CI → merge → post-merge verification: required before AI is considered complete.

The coordinator has no exchange credentials, order authority, capital authority, or ability to approve live execution.
