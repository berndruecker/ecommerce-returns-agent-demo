#!/usr/bin/env python
"""Test what the API actually returns"""

import sys
import json
sys.path.insert(0, "fake-backends")

from routers.commerce import list_recent_orders
import asyncio

async def test():
    result = await list_recent_orders("0039Q00001VsHMXQA3", limit=5)
    print(f"Type: {type(result)}")
    print(f"Length: {len(result)}")
    print(f"\nFirst order (index [0]):")
    print(f"  order_id: {result[0].order_id}")
    print(f"  items count: {len(result[0].items)}")
    print(f"  items[0]: {result[0].items[0].product_name}")
    print(f"  items[1]: {result[0].items[1].product_name}")
    
    print(f"\nSecond order (index [1]):")
    print(f"  order_id: {result[1].order_id}")
    print(f"  items count: {len(result[1].items)}")
    print(f"  items[0]: {result[1].items[0].product_name}")
    print(f"  items[1]: {result[1].items[1].product_name}")
    
    # Now serialize to JSON to see what the API returns
    print(f"\nJSON serialized (first order):")
    # Use pydantic's model_dump to serialize
    order_dict = result[1].model_dump()
    print(json.dumps(order_dict, indent=2, default=str)[:500])

asyncio.run(test())
