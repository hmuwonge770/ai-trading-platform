# Stage 24 — Promotion Control API

The control API now uses the PostgreSQL promotion repository instead of process-local state.

Endpoints:

- `POST /promotions` — persist a promotion request and its capital allocation.
- `GET /promotions/{promotion_id}` — retrieve persisted promotion state.
- `POST /promotions/{promotion_id}/approve` — record an independent approval through the transactional repository.
- `POST /promotions/{promotion_id}/activate` — activate only after Risk Manager and Admin approvals are persisted.
- `POST /promotions/{promotion_id}/authorization` — persist a bounded authorization snapshot.
- `POST /promotions/{promotion_id}/halt` — persist an active-promotion halt.

All mutating lifecycle operations use the repository transaction boundary. The API does not submit exchange orders and does not expose exchange credentials.
