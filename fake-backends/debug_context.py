#!/usr/bin/env python
"""Debug field access with context inspection"""

import sys
sys.path.insert(0, ".")

from routers.commerce import list_recent_orders
import asyncio

async def test():
    orders = await list_recent_orders("0039Q00001VsHMXQA3", limit=5)
    orders_dicts = [o.model_dump(mode='json') for o in orders]
    response = {"status": 200, "body": orders_dicts}
    
    # Manually test what the function should do
    eval_context = {"response": response}
    
    # Step through what _evaluate_field_access should do
    field_str = "response.body[1].order_id"
    print(f"field_str: {field_str}")
    print(f"eval_context['response']: {type(eval_context['response'])}")
    print(f"eval_context['response'].keys(): {eval_context['response'].keys()}")
    print()
    
    # Get response
    result = eval_context.get('response')
    print(f"1. result = eval_context.get('response')")
    print(f"   result: {type(result)}")
    print()
    
    # Remove 'response' prefix
    rest = field_str[8:]  # 'response' = 8 chars
    print(f"2. rest = field_str[8:] = '{rest}'")
    print()
    
    # Process .body
    print(f"3. rest[0] = '{rest[0]}' (expect '.')")
    i = 1
    field_name = "body"
    print(f"4. field_name = '{field_name}'")
    print(f"5. result is dict: {isinstance(result, dict)}")
    print(f"6. result.get('body'): {result.get('body') is not None}")
    result = result.get(field_name)
    print(f"7. result = result.get('{field_name}')")
    print(f"   result: {type(result)}, len={len(result)}")
    
asyncio.run(test())
