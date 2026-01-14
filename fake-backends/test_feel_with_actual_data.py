#!/usr/bin/env python
"""Test FEEL expression with actual API data"""

import sys
import asyncio
import logging
sys.path.insert(0, ".")

# Enable DEBUG logging
logging.basicConfig(level=logging.DEBUG)

from routers.commerce import list_recent_orders
from camunda_worker import _evaluate_result_expression

EXPRESSION = """if response.body = null or count(response.body) = 0 then
{
  recentOrders: [],
  selectedOrderCandidate: null,
  toolCallResult: {
    status: "no_orders",
    message: "No recent orders found for this customer."
  }
}
else
{
  recentOrders: response.body,
  selectedOrderCandidate: response.body[1],
  toolCallResult: {
    status: "orders_found",
    candidate: {
      orderId: response.body[1].order_id,
      deliveryDate: response.body[1].delivery_date,
      status: response.body[1].status,
      firstItem: response.body[1].items[1]
    },
    message:
      "Found a delivered order. Likely match: " +
      response.body[1].items[1].product_name +
      " delivered on " + response.body[1].delivery_date +
      " for $" + string(response.body[1].items[1].unit_price) +
      ". Ask the customer to confirm this is the one to return."
  }
}
"""

async def test():
    orders = await list_recent_orders("0039Q00001VsHMXQA3", limit=5)
    
    # Convert Pydantic models to dicts (like the API would do)
    orders_dicts = [o.model_dump(mode='json') for o in orders]
    
    response = {"status": 200, "body": orders_dicts}
    
    print(f"Response has {len(response['body'])} orders")
    print(f"\nOrder[1] (should be ORD-2025-007892):")
    print(f"  order_id: {response['body'][1]['order_id']}")
    print(f"  items[1] product_name: {response['body'][1]['items'][1]['product_name']}")
    print(f"  items[1] unit_price: {response['body'][1]['items'][1]['unit_price']}")
    
    print(f"\nEvaluating FEEL expression...")
    result = _evaluate_result_expression(EXPRESSION, response)
    
    print(f"\nResult keys: {result.keys()}")
    print(f"recentOrders count: {len(result.get('recentOrders', []))}")
    
    candidate = result.get('selectedOrderCandidate', {})
    print(f"\nSelectedOrderCandidate (full order dict):")
    print(f"  order_id: {candidate.get('order_id')}")
    print(f"  delivery_date: {candidate.get('delivery_date')}")
    print(f"  items count: {len(candidate.get('items', []))}")
    
    tool_result = result.get('toolCallResult', {})
    tool_candidate = tool_result.get('candidate', {})
    print(f"\nToolCallResult.candidate (transformed data):")
    print(f"  orderId: {tool_candidate.get('orderId')}")
    print(f"  deliveryDate: {tool_candidate.get('deliveryDate')}")
    print(f"  status: {tool_candidate.get('status')}")
    print(f"  firstItem: {tool_candidate.get('firstItem')}")
    print(f"\nToolCallResult:")
    print(f"  status: {tool_result.get('status')}")
    print(f"  message: {tool_result.get('message')}")
    
asyncio.run(test())
