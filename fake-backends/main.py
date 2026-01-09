import os
import threading

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.cors import CORSMiddleware
import uvicorn

from routers import commerce, erp, wms, policy, returns_provider, payments, notifications
from data_store import data_store

app = FastAPI(
    title="E-Commerce Returns Agent Demo Backend",
    description="Mock backend systems for returns agent demonstration",
    version="1.0.0"
)

# Add CORS middleware for MCP remote access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include all routers
app.include_router(commerce.router, prefix="/commerce", tags=["Magento Commerce"])
app.include_router(erp.router, prefix="/erp", tags=["SAP ERP"])
app.include_router(wms.router, prefix="/wms", tags=["Manhattan WMS"])
app.include_router(policy.router, prefix="/policy", tags=["Returns Policy"])
app.include_router(returns_provider.router, prefix="/returns", tags=["Returns Provider"])
app.include_router(payments.router, prefix="/payments", tags=["Payments"])
app.include_router(notifications.router, prefix="/notify", tags=["Notifications"])

# Templates for homepage
templates = Jinja2Templates(directory="templates")


def _start_camunda_worker_if_enabled():
    """Start the Camunda 8 worker in-process unless explicitly disabled."""
    flag = os.getenv("CAMUNDA_WORKER_ENABLED", "true").lower()
    if flag in {"0", "false", "no", "off"}:
        return None

    try:
        from camunda_worker import run_worker
    except Exception as exc:  # pragma: no cover - guard against missing deps in minimal runs
        # Log import failure but keep API running
        print(f"[camunda-worker] Failed to import worker: {exc}")
        return None

    thread = threading.Thread(target=run_worker, daemon=True)
    thread.start()
    print("[camunda-worker] Started background Camunda worker")
    return thread


@app.on_event("startup")
async def startup_event():
    # Start worker only when explicitly enabled via env var
    app.state.camunda_worker_thread = _start_camunda_worker_if_enabled()
    
    # Mount MCP server for SAP endpoints
    try:
        from mcp_server import create_mcp_app
        mcp_app = create_mcp_app()
        app.mount("/mcp", mcp_app)
        print("[mcp-server] Mounted SAP MCP server at /mcp/sse")
    except Exception as exc:
        print(f"[mcp-server] Failed to mount MCP server: {exc}")

@app.get("/", response_class=HTMLResponse)
async def homepage(request: Request):
    """Homepage showing demo entities"""
    return templates.TemplateResponse("index.html", {
        "request": request,
        "customers": data_store.customers,
        "products": list(data_store.products.values()),
        "orders": data_store.orders,
    })

@app.get("/health")
async def health_check():
    """Health check endpoint for Cloud Run"""
    return {"status": "healthy"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8100)
