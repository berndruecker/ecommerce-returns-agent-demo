#!/usr/bin/env python
"""Quick test to verify logging and second customer data"""

import sys
import asyncio
sys.path.insert(0, ".")

from routers.commerce import list_recent_orders

async def test():
    print("Testing customer 0039Q00001VsHMXQA3:")
    orders1 = await list_recent_orders("0039Q00001VsHMXQA3", limit=5)
    print(f"  Found {len(orders1)} orders")
    for i, order in enumerate(orders1):
        print(f"  [{i}] {order.order_id}: {len(order.items)} items")
    
    print("\nTesting customer 0039Q00001VcSaVQAV:")
    orders2 = await list_recent_orders("0039Q00001VcSaVQAV", limit=5)
    print(f"  Found {len(orders2)} orders")
    for i, order in enumerate(orders2):
        print(f"  [{i}] {order.order_id}: {len(order.items)} items")

asyncio.run(test())
