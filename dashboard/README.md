# Laravel Control Dashboard

The dashboard is the human-facing control and observability surface for the AI Trading Platform.

## Boundary

- Shows environment, service health and promotion posture.
- Defaults to `paper` and trading disabled.
- Reads only the FastAPI health endpoint from the configured control API.
- Never reads Binance credentials.
- Never submits exchange orders.
- Does not bypass promotion, risk, authorization, canary, limited-live or full-live gates.

## Local development

```bash
composer install
php artisan serve
```

Configure `TRADING_API_URL` when the FastAPI service is available. The default is `http://127.0.0.1:8000`.
