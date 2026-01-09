import asyncio
import logging
import os
from typing import Any, Dict, Tuple

import requests
from pyzeebe import Job, ZeebeWorker, create_camunda_cloud_channel, create_insecure_channel

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(levelname)s %(message)s")
logger = logging.getLogger("magento-worker")

DEFAULT_API_BASE = "http://localhost:8100/commerce"


def _get_env(name: str, default: str | None = None) -> str | None:
    value = os.getenv(name)
    return value if value not in (None, "") else default


def _create_channel():
    """Create Zeebe channel for Camunda 8 (SaaS or self-managed)."""
    client_id = _get_env("ZEEBE_CLIENT_ID")
    if client_id:
        logger.info("Using Camunda 8 SaaS channel")
        return create_camunda_cloud_channel(
            client_id=client_id,
            client_secret=_get_env("ZEEBE_CLIENT_SECRET", ""),
            cluster_id=_get_env("ZEEBE_ADDRESS", ""),
            region=_get_env("ZEEBE_REGION", "bru-2"),
            auth_server=_get_env(
                "ZEEBE_AUTHORIZATION_SERVER_URL",
                "https://login.cloud.camunda.io/oauth/token",
            ),
        )

    address = _get_env("ZEEBE_ADDRESS", "localhost:26500")
    if ":" in address:
        host, port = address.split(":", 1)
    else:
        host, port = address, "26500"
    logger.info("Using self-managed Zeebe channel to %s:%s", host, port)
    return create_insecure_channel(hostname=host, port=int(port))

class MagentoConnectorError(Exception):
    """Raised when the Magento connector call fails."""


def _request(method: str, url: str, params: Dict[str, Any] | None = None) -> Tuple[int, Any]:
    try:
        response = requests.request(method=method, url=url, params=params, timeout=15)
        content_type = response.headers.get("Content-Type", "")
        if "application/json" in content_type:
            body = response.json()
        else:
            body = response.text
        return response.status_code, body
    except Exception as exc:  # pragma: no cover - demo-oriented
        raise MagentoConnectorError(f"Failed to call {url}: {exc}") from exc


def _build_url(base: str, path: str) -> str:
    return f"{base.rstrip('/')}/{path.lstrip('/')}"


def _get(vars: Dict[str, Any], *keys: str, default: Any = None) -> Any:
    for key in keys:
        if key in vars and vars[key] not in (None, ""):
            return vars[key]
    return default


def _handle_operation(operation: str, vars: Dict[str, Any]) -> Dict[str, Any]:
    base = _get(vars, "apiBaseUrl", default=_get_env("MAGENTO_API_BASE", DEFAULT_API_BASE))

    match operation:
        case "listOrders":
            customer_id = _get(vars, "customerId", "customer_id")
            limit = _get(vars, "limit", default=5)
            if not customer_id:
                raise MagentoConnectorError("customerId is required for listOrders")
            url = _build_url(base, f"customers/{customer_id}/orders")
            status, body = _request("GET", url, params={"limit": limit})
        case "productSearch":
            params = {}
            for key in ("category", "wifiMin", "tags"):
                value = _get(vars, key)
                if value not in (None, ""):
                    params[key] = value
            url = _build_url(base, "catalog/products")
            status, body = _request("GET", url, params=params or None)
        case "createRma":
            order_id = _get(vars, "orderId", "order_id")
            customer_id = _get(vars, "customerId", "customer_id")
            sku = _get(vars, "sku")
            reason = _get(vars, "reason")
            if not all([order_id, customer_id, sku, reason]):
                raise MagentoConnectorError("orderId, customerId, sku, and reason are required for createRma")
            url = _build_url(base, "rmas")
            status, body = _request(
                "POST", url, params={"order_id": order_id, "customer_id": customer_id, "sku": sku, "reason": reason}
            )
        case "createCart":
            customer_id = _get(vars, "customerId", "customer_id")
            if not customer_id:
                raise MagentoConnectorError("customerId is required for createCart")
            url = _build_url(base, "carts")
            status, body = _request("POST", url, params={"customer_id": customer_id})
        case "addCartItem":
            cart_id = _get(vars, "cartId", "cart_id")
            sku = _get(vars, "sku")
            quantity = int(_get(vars, "quantity", default=1))
            if not cart_id or not sku:
                raise MagentoConnectorError("cartId and sku are required for addCartItem")
            url = _build_url(base, f"carts/{cart_id}/items")
            status, body = _request("POST", url, params={"sku": sku, "quantity": quantity})
        case "applyStoreCredit":
            cart_id = _get(vars, "cartId", "cart_id")
            amount = _get(vars, "amount")
            if cart_id is None or amount is None:
                raise MagentoConnectorError("cartId and amount are required for applyStoreCredit")
            url = _build_url(base, f"carts/{cart_id}/discounts/store-credit")
            status, body = _request("POST", url, params={"amount": amount})
        case "placeOrder":
            cart_id = _get(vars, "cartId", "cart_id")
            payment_method = _get(vars, "paymentMethod", default="credit_card")
            if not cart_id:
                raise MagentoConnectorError("cartId is required for placeOrder")
            url = _build_url(base, "orders")
            status, body = _request("POST", url, params={"cart_id": cart_id, "payment_method": payment_method})
        case _:
            raise MagentoConnectorError(f"Unsupported operation: {operation}")

    return {"status": status, "body": body}


def magento_connector(job: Job) -> Dict[str, Any]:
    """Route Camunda job to the fake Magento endpoints based on operation selection."""
    variables = job.variables or {}
    operation = _get(variables, "operation")
    if not operation:
        raise MagentoConnectorError("operation is required")

    logger.info("Executing Magento operation %s", operation)
    result = _handle_operation(operation, variables)

    result_variable = _get(variables, "resultVariable", default="magentoResponse")
    return {result_variable: result}


async def _worker_main():
    # Ensure channel is created inside the running event loop (required by grpc.aio)
    channel = _create_channel()
    worker = ZeebeWorker(channel)

    # register task dynamically to avoid binding to a worker created on a different loop
    worker.task(task_type="magento-connector", timeout_ms=120000)(magento_connector)

    await worker.work()


def run_worker():
    logger.info("Starting Magento connector worker ...")
    # pyzeebe 3.x work() is async; create loop inside this thread
    asyncio.run(_worker_main())


if __name__ == "__main__":
    run_worker()
