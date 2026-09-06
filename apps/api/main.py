from time import perf_counter

from fastapi import FastAPI, Request, Response
from prometheus_client import CONTENT_TYPE_LATEST

from apps.api.routes import router as research_router
from packages.observability import metrics
from packages.trading.config import get_settings

settings = get_settings()

app = FastAPI(
    title="AI Trading Platform API",
    version="0.1.0",
    description="Control and research API for the research-first trading platform.",
)

app.include_router(research_router)


@app.middleware("http")
async def observe_http(request: Request, call_next):
    started = perf_counter()
    metrics.http_in_flight.inc()
    try:
        response = await call_next(request)
        status = str(response.status_code)
        return response
    except Exception:
        status = "500"
        raise
    finally:
        route = getattr(request.scope.get("route"), "path", request.url.path)
        metrics.http_requests.labels(request.method, route, status).inc()
        metrics.http_latency.labels(request.method, route).observe(perf_counter() - started)
        metrics.http_in_flight.dec()


@app.get("/metrics", tags=["system"])
def prometheus_metrics() -> Response:
    return Response(content=metrics.exposition(), media_type=CONTENT_TYPE_LATEST)


@app.get("/health", tags=["system"])
def health() -> dict[str, str]:
    return {"status": "ok", "environment": settings.app_env}


@app.get("/ready", tags=["system"])
def ready() -> dict[str, object]:
    return {
        "status": "ready",
        "trading_enabled": settings.trading_enabled,
        "kill_switch": settings.trading_kill_switch,
    }
