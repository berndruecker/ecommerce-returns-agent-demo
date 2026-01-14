#!/usr/bin/env python
"""Quick test of orders"""

import sys
sys.path.insert(0, ".")

from routers.commerce import list_recent_orders
import asyncio

async def test():
    orders = await list_recent_orders("0039Q00001VsHMXQA3", limit=5)
    print(f"Orders found: {len(orders)}")
    for i, order in enumerate(orders):
        print(f"[{i}] {order.order_id}: {len(order.items)} items")

asyncio.run(test())
