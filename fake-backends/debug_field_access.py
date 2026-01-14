#!/usr/bin/env python
"""Debug field access in FEEL evaluator"""

import sys
sys.path.insert(0, ".")

from routers.commerce import list_recent_orders
from camunda_worker import _evaluate_field_access
import asyncio

async def test():
    orders = await list_recent_orders("0039Q00001VsHMXQA3", limit=5)
    orders_dicts = [o.model_dump(mode='json') for o in orders]
    response = {"status": 200, "body": orders_dicts}
    
    # Test various field accesses
    test_paths = [
        "response.body",
        "response.body[1]",
        "response.body[1].order_id",
        "response.body[1].delivery_date",
        "response.body[1].items",
        "response.body[1].items[1]",
        "response.body[1].items[1].product_name",
    ]
    
    eval_context = {"response": response}
    
    for path in test_paths:
        result = _evaluate_field_access(path, eval_context)
        print(f"{path:45} => {result}")
        
asyncio.run(test())
