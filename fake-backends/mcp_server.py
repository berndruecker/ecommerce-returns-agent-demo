"""MCP Server exposing SAP ERP endpoints as tools."""
import logging
import os
from typing import Any

import httpx
from mcp.server import Server
from mcp.server.sse import SseServerTransport
from mcp.types import Tool, TextContent

logger = logging.getLogger("mcp-sap-server")

# MCP Server instance
mcp_server = Server("sap-erp-connector")

# Base URL for SAP endpoints (defaults to local)
SAP_BASE_URL = os.getenv("SAP_API_BASE", "http://localhost:8100/erp")


@mcp_server.list_tools()
async def list_tools() -> list[Tool]:
    """List available SAP ERP tools."""
    return [
        Tool(
            name="sap_check_return_eligibility",
            description="Check if a SKU is eligible for return based on order ID and days since delivery",
            inputSchema={
                "type": "object",
                "properties": {
                    "sku": {
                        "type": "string",
                        "description": "Product SKU to check return eligibility for"
                    },
                    "orderId": {
                        "type": "string",
                        "description": "Order ID containing the SKU"
                    },
                    "daysSinceDelivery": {
                        "type": "integer",
                        "description": "Number of days since the order was delivered"
                    }
                },
                "required": ["sku", "orderId", "daysSinceDelivery"]
            }
        ),
        Tool(
            name="sap_get_sku_info",
            description="Get SKU lifecycle and clearance information from SAP",
            inputSchema={
                "type": "object",
                "properties": {
                    "sku": {
                        "type": "string",
                        "description": "Product SKU to retrieve information for"
                    }
                },
                "required": ["sku"]
            }
        ),
        Tool(
            name="sap_check_availability",
            description="Check product availability and stock level in SAP",
            inputSchema={
                "type": "object",
                "properties": {
                    "sku": {
                        "type": "string",
                        "description": "Product SKU to check availability for"
                    }
                },
                "required": ["sku"]
            }
        )
    ]


@mcp_server.call_tool()
async def call_tool(name: str, arguments: Any) -> list[TextContent]:
    """Handle tool calls by routing to SAP endpoints."""
    
    async with httpx.AsyncClient(timeout=15.0) as client:
        try:
            if name == "sap_check_return_eligibility":
                sku = arguments["sku"]
                order_id = arguments["orderId"]
                days_since_delivery = arguments["daysSinceDelivery"]
                
                url = f"{SAP_BASE_URL}/skus/{sku}/return-eligibility"
                params = {
                    "orderId": order_id,
                    "daysSinceDelivery": days_since_delivery
                }
                response = await client.get(url, params=params)
                response.raise_for_status()
                result = response.json()
                
                return [TextContent(
                    type="text",
                    text=f"Return Eligibility Check:\n"
                         f"SKU: {sku}\n"
                         f"Eligible: {result['eligible']}\n"
                         f"Reason: {result['reason']}\n"
                         f"Days Remaining: {result.get('days_remaining', 'N/A')}\n"
                         f"Restocking Fee: ${result.get('restocking_fee', 0)}\n"
                         f"\nRaw Response: {result}"
                )]
            
            elif name == "sap_get_sku_info":
                sku = arguments["sku"]
                
                url = f"{SAP_BASE_URL}/skus/{sku}"
                response = await client.get(url)
                response.raise_for_status()
                result = response.json()
                
                return [TextContent(
                    type="text",
                    text=f"SKU Information:\n"
                         f"SKU: {result['sku']}\n"
                         f"Name: {result['name']}\n"
                         f"Lifecycle Status: {result['lifecycle_status']}\n"
                         f"Is Clearance: {result['is_clearance']}\n"
                         f"Is Discontinued: {result['is_discontinued']}\n"
                         f"Current Price: ${result['current_price']}\n"
                         f"\nRaw Response: {result}"
                )]
            
            elif name == "sap_check_availability":
                sku = arguments["sku"]
                
                url = f"{SAP_BASE_URL}/availability"
                params = {"sku": sku}
                response = await client.get(url, params=params)
                response.raise_for_status()
                result = response.json()
                
                return [TextContent(
                    type="text",
                    text=f"Product Availability:\n"
                         f"SKU: {result['sku']}\n"
                         f"Available: {result['available']}\n"
                         f"Quantity: {result['quantity']}\n"
                         f"Warehouse: {result['warehouse_location']}\n"
                         f"\nRaw Response: {result}"
                )]
            
            else:
                return [TextContent(
                    type="text",
                    text=f"Error: Unknown tool '{name}'"
                )]
        
        except httpx.HTTPStatusError as e:
            return [TextContent(
                type="text",
                text=f"HTTP Error: {e.response.status_code} - {e.response.text}"
            )]
        except Exception as e:
            return [TextContent(
                type="text",
                text=f"Error executing tool '{name}': {str(e)}"
            )]


# Create SSE transport for MCP
# The endpoint must be the full path from the application root since it's sent to clients
_sse_transport = SseServerTransport("/mcp/sse")


def create_mcp_app():
    """Create ASGI app for MCP server with SSE transport.
    
    Returns a simple ASGI app that routes requests to the SSE transport methods.
    The transport's connect_sse is an async context manager that yields read/write streams.
    We need to run the server with those streams.
    """
    async def mcp_asgi_app(scope, receive, send):
        """Custom ASGI router for MCP endpoints."""
        if scope["type"] != "http":
            return
        
        path = scope["path"]
        method = scope["method"]
        
        # Debug: log the path and method
        print(f"[mcp-debug] Received {method} request to path: '{path}'")
        
        # Strip /mcp prefix since we're mounted at /mcp
        if path.startswith("/mcp"):
            path = path[4:]  # Remove '/mcp'
            print(f"[mcp-debug] Stripped path: '{path}'")
        
        # Route to appropriate handler
        if path == "/sse" and method == "GET":
            print(f"[mcp-debug] Routing to connect_sse")
            # Don't modify scope path - keep it as /mcp/sse for the transport
            # connect_sse is an async context manager
            async with _sse_transport.connect_sse(scope, receive, send) as (read_stream, write_stream):
                # Run the MCP server with these streams
                await mcp_server.run(read_stream, write_stream, mcp_server.create_initialization_options())
        elif path == "/sse" and method == "POST":
            print(f"[mcp-debug] Routing to handle_post_message for session messages")
            # Don't modify scope path - keep it as /mcp/sse for the transport
            await _sse_transport.handle_post_message(scope, receive, send)
        elif path == "/messages" and method == "POST":
            print(f"[mcp-debug] Routing to handle_post_message")
            # Don't modify scope path - keep it as /mcp/messages for the transport
            await _sse_transport.handle_post_message(scope, receive, send)
        else:
            # Return 404
            print(f"[mcp-debug] No route matched, returning 404")
            await send({
                "type": "http.response.start",
                "status": 404,
                "headers": [[b"content-type", b"text/plain"]],
            })
            await send({
                "type": "http.response.body",
                "body": f"Not Found. Path: {path}, Method: {method}".encode(),
            })
    
    return mcp_asgi_app

