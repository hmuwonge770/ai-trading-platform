from fastapi import FastAPI

from packages.trading.config import get_settings

settings = get_settings()

app = FastAPI(
    title="AI Trading Platform API",
    version="0.1.0",
    description="Control and research API for the research-first trading platform.",
)


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
